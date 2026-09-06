"""
Market-OS Isolated Account Worker
=================================
Dedicated, single-account execution daemon.
Runs in its own OS process, bound to a private portable MT5 sandbox instance.
Zero account switching. Permanent, uninterrupted 24/7 broker session.

Usage:
  python account_worker.py --account-id <ID>
"""

import os
import sys
import time
import argparse
import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple
import requests

# Ensure worker directory in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from terminal_provisioner import provision_terminal_for_account, get_account_terminal_exe

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

CLOUD_URL = os.getenv("MARKETOS_CLOUD_URL", "http://127.0.0.1:8000")
WORKER_ID = os.getenv("WORKER_ID", "vps-lon-worker-1")
WORKER_KEY = os.getenv("WORKER_KEY", "wkey_master_cloud_london")

HEADERS = {
    "X-Worker-Id": WORKER_ID,
    "X-Worker-Key": WORKER_KEY,
    "Content-Type": "application/json"
}


def setup_logger(account_id: int, login: int) -> logging.Logger:
    logs_dir = r"C:\Market-OS\logs"
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, f"account_{account_id}.log")

    logger = logging.getLogger(f"Worker_Acc_{account_id}")
    logger.setLevel(logging.INFO)
    logger.handlers = []

    formatter = logging.Formatter(
        f"%(asctime)s [%(levelname)s] [Acc #{login}]: %(message)s"
    )
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def fetch_account_details(account_id: int) -> Optional[Dict]:
    """Fetch decrypted account credentials from cloud router."""
    try:
        r = requests.get(f"{CLOUD_URL}/api/v1/execution/worker/accounts", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            accounts = r.json()
            for acc in accounts:
                if acc.get("account_id") == account_id:
                    return acc
    except Exception as e:
        print(f"Error fetching account #{account_id} details: {e}")
    return None


def resolve_broker_symbol(symbol: str) -> str:
    """Resolves instrument alias across brokers (e.g. US100 -> USTEC on MetaQuotes/ICMarkets)."""
    if not MT5_AVAILABLE or not symbol:
        return symbol
    info = mt5.symbol_info(symbol)
    if info:
        mt5.symbol_select(symbol, True)
        return symbol

    aliases = {
        "US100": ["USTEC", "US100", "NAS100", "US100.cash", "NAS100USD", "USTECH100M", "NDX", "US_Tech100"],
        "NAS100": ["USTEC", "US100", "NAS100", "US100.cash", "NAS100USD", "USTECH100M", "NDX"],
        "US30": ["US30", "DJ30", "WS30", "US30.cash", "WALLSTREET30"],
        "XAUUSD": ["XAUUSD", "GOLD", "XAUUSD.cash"],
    }
    for c in aliases.get(symbol.upper(), []):
        if mt5.symbol_info(c):
            mt5.symbol_select(c, True)
            return c
    return symbol


def get_symbol_filling_mode(symbol: str) -> int:
    if not MT5_AVAILABLE:
        return 0
    info = mt5.symbol_info(symbol)
    if not info:
        return mt5.ORDER_FILLING_IOC
    modes = getattr(info, "filling_mode", 0)
    if modes & 1:  # FOK
        return mt5.ORDER_FILLING_FOK
    elif modes & 2:  # IOC
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def normalize_order_stops(symbol: str, direction: str, price: float, sl: float, tp: float) -> Tuple[float, float]:
    if not MT5_AVAILABLE:
        return 0.0, 0.0
    sym_info = mt5.symbol_info(symbol)
    if not sym_info:
        return 0.0, 0.0

    digits = sym_info.digits
    point = sym_info.point
    stops_level = getattr(sym_info, "trade_stops_level", 0) * point
    min_dist = max(stops_level, point * 15)

    norm_sl = 0.0
    norm_tp = 0.0

    if direction == "LONG":
        if sl > 0.0:
            norm_sl = round(sl, digits) if sl < (price - min_dist) else round(price - min_dist, digits)
        if tp > 0.0:
            norm_tp = round(tp, digits) if tp > (price + min_dist) else round(price + min_dist, digits)
    else:  # SHORT
        if sl > 0.0:
            norm_sl = round(sl, digits) if sl > (price + min_dist) else round(price + min_dist, digits)
        if tp > 0.0:
            norm_tp = round(tp, digits) if tp < (price - min_dist) else round(price - min_dist, digits)

    return norm_sl, norm_tp


class AccountWorker:
    def __init__(self, account_data: Dict):
        self.account_id = account_data["account_id"]
        self.login = account_data["login"]
        self.password = account_data["password"]
        self.server = account_data["server"]
        self.logger = setup_logger(self.account_id, self.login)
        self.tracked_positions: Dict[str, Dict] = {}
        self.terminal_exe = get_account_terminal_exe(self.account_id)

    def initialize_terminal(self) -> bool:
        """Provisions portable directory and establishes persistent MT5 connection."""
        self.logger.info(f"Provisioning portable MT5 sandbox for #{self.login}...")
        self.terminal_exe = provision_terminal_for_account(self.account_id, self.login, self.server)

        if not MT5_AVAILABLE:
            self.logger.error("MetaTrader5 python module not installed.")
            return False

        # Terminate any stale process for this specific terminal path
        self.logger.info(f"Connecting to dedicated MT5 instance: {self.terminal_exe}...")
        
        # Initialize terminal in portable mode
        ok = mt5.initialize(
            path=self.terminal_exe,
            login=self.login,
            password=self.password,
            server=self.server,
            portable=True,
            timeout=60000
        )

        if not ok:
            err = mt5.last_error()
            self.logger.error(f"mt5.initialize failed for #{self.login}: {err}")
            return False

        acc_info = mt5.account_info()
        if not acc_info:
            self.logger.error(f"Cannot get account_info for #{self.login}")
            return False

        self.logger.info(f"✅ CONNECTED! Account #{acc_info.login} ({acc_info.server}) | Balance: ${acc_info.balance:.2f} | Equity: ${acc_info.equity:.2f}")
        return True

    def sync_positions(self) -> List[Dict]:
        """Synchronizes active MT5 positions and de-bounces close reports."""
        raw_positions = mt5.positions_get()
        mt5_by_ticket = {str(p.ticket): p for p in (raw_positions or [])}
        positions_list = []

        for ticket_id, pos in list(self.tracked_positions.items()):
            inst = pos["instrument"]
            pip_mult = 100.0 if "JPY" in inst else (10.0 if "XAU" in inst else 10000.0)
            open_price = pos["open_price"]
            is_long = (pos["direction"] == "LONG")

            if ticket_id in mt5_by_ticket:
                pos["missing_cycles"] = 0
                mp = mt5_by_ticket[ticket_id]
                cur_price = mp.price_current
                pos["current_price"] = cur_price
                pnl_pips = ((cur_price - open_price) if is_long else (open_price - cur_price)) * pip_mult
                pos["current_pnl_pips"] = round(pnl_pips, 1)
                pos["max_mfe_pips"] = max(pos.get("max_mfe_pips", 0.0), max(0.0, pnl_pips))
                pos["max_mae_pips"] = max(pos.get("max_mae_pips", 0.0), max(0.0, -pnl_pips))
                positions_list.append(pos)
            else:
                # Missing cycle de-bounce: require 3 consecutive empty cycles (15s)
                pos["missing_cycles"] = pos.get("missing_cycles", 0) + 1
                if pos["missing_cycles"] < 3:
                    positions_list.append(pos)
                    continue

                self.logger.info(f"Position Ticket #{ticket_id} confirmed closed on MT5 broker.")
                exit_price = pos.get("current_price", open_price)
                try:
                    requests.post(
                        f"{CLOUD_URL}/api/v1/execution/worker/report-close",
                        json={
                            "account_id": self.account_id,
                            "ticket_id": ticket_id,
                            "exit_reason": "BROKER_SL_TP_OR_MANUAL",
                            "exit_price": exit_price,
                            "pnl_r": 0.0,
                            "pnl_currency": 0.0
                        },
                        headers=HEADERS, timeout=5
                    )
                except Exception:
                    pass
                del self.tracked_positions[ticket_id]

        # Track any new positions found directly on MT5
        for t_str, mp in mt5_by_ticket.items():
            if t_str not in self.tracked_positions:
                self.logger.info(f"Tracking MT5 position #{t_str} ({mp.symbol} {'BUY' if mp.type==0 else 'SELL'}).")
                self.tracked_positions[t_str] = {
                    "ticket_id": t_str,
                    "instrument": mp.symbol,
                    "direction": "LONG" if mp.type == 0 else "SHORT",
                    "open_price": mp.price_open,
                    "current_price": mp.price_current,
                    "stop_loss": mp.sl,
                    "take_profit": mp.tp,
                    "volume": mp.volume,
                    "max_mae_pips": 0.0,
                    "max_mfe_pips": 0.0,
                    "current_pnl_pips": 0.0,
                    "open_timestamp": datetime.datetime.utcnow().timestamp(),
                    "missing_cycles": 0
                }
                positions_list.append(self.tracked_positions[t_str])

        return positions_list

    def check_early_invalidation(self):
        """Enforces the -0.35R Early Invalidation guardrail with 45s grace period and noise floor."""
        now_ts = datetime.datetime.utcnow().timestamp()

        for ticket_id, pos in list(self.tracked_positions.items()):
            elapsed_sec = now_ts - pos.get("open_timestamp", now_ts)
            if elapsed_sec < 45.0:
                continue  # 45-second grace window to absorb spread

            inst = pos["instrument"]
            pip_mult = 100.0 if "JPY" in inst else (10.0 if "XAU" in inst else 10000.0)
            min_floor = 15.0 if ("XAU" in inst or "US100" in inst) else 6.0
            
            risk_dist = abs(pos["open_price"] - pos["stop_loss"]) if pos.get("stop_loss", 0.0) > 0 else (25.0 / pip_mult)
            risk_pips = max(1.0, risk_dist * pip_mult)
            early_inval_pips = max(min_floor, 0.35 * risk_pips)

            # Disarm if +0.35R MFE reached
            if pos.get("max_mfe_pips", 0.0) >= early_inval_pips:
                continue

            # Liquidate if MAE breached
            if pos.get("max_mae_pips", 0.0) >= early_inval_pips:
                self.logger.warning(f"Position #{ticket_id} hit -0.35R Early Invalidation ({pos['max_mae_pips']}p >= {early_inval_pips:.1f}p). Liquidating.")
                if ticket_id.isdigit():
                    try:
                        mt5.Close(inst, ticket=int(ticket_id))
                    except Exception as e:
                        self.logger.error(f"mt5.Close error: {e}")

                try:
                    requests.post(
                        f"{CLOUD_URL}/api/v1/execution/worker/report-close",
                        json={
                            "account_id": self.account_id,
                            "ticket_id": ticket_id,
                            "exit_reason": "EARLY_INVALIDATION_MAE",
                            "exit_price": pos.get("current_price", pos["open_price"]),
                            "pnl_r": -0.35,
                            "pnl_currency": 0.0
                        },
                        headers=HEADERS, timeout=5
                    )
                except Exception:
                    pass
                del self.tracked_positions[ticket_id]

    def execute_order(self, order: Dict):
        """Executes market order with broker stop normalization and resilient fallback."""
        raw_symbol = order.get("instrument", "")
        symbol = resolve_broker_symbol(raw_symbol)
        direction = order.get("direction", "LONG").upper()
        volume = float(order.get("position_size_lots", 0.01))
        sl = float(order.get("stop_loss", 0.0))
        tp = float(order.get("take_profit", 0.0))
        signal_id = order.get("signal_id", "MANUAL")

        self.logger.info(f"Received Order: {direction} {volume} lots on {symbol} (Signal: {signal_id})")

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            self.logger.error(f"No tick data available for {symbol}")
            return

        price = tick.ask if direction == "LONG" else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if direction == "LONG" else mt5.ORDER_TYPE_SELL
        norm_sl, norm_tp = normalize_order_stops(symbol, direction, price, sl, tp)
        filling_mode = get_symbol_filling_mode(symbol)

        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": norm_sl,
            "tp": norm_tp,
            "deviation": 20,
            "magic": 888001,
            "comment": f"MOS-{signal_id[:10]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        t0 = time.time()
        res = mt5.order_send(req)
        latency_ms = round((time.time() - t0) * 1000, 2)

        # Resilient Tier 2 fallback if tight stops rejected
        if not res or res.retcode != mt5.TRADE_RETCODE_DONE:
            self.logger.warning(f"Initial order_send retcode={res.retcode if res else 'None'}. Retrying pure market order...")
            for alt_fill in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]:
                req["sl"] = 0.0
                req["tp"] = 0.0
                req["type_filling"] = alt_fill
                t2 = mt5.symbol_info_tick(symbol)
                if t2:
                    req["price"] = t2.ask if direction == "LONG" else t2.bid
                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    break

        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            ticket_id = str(res.order)
            fill_price = float(res.price) if res.price > 0 else price
            self.logger.info(f"✅ [REAL BROKER FILL] {direction} {volume} lots on {symbol} @ {fill_price} (Ticket: #{ticket_id}, Latency: {latency_ms}ms)")

            # Attach SL/TP post-fill if opened pure market
            if (norm_sl > 0.0 or norm_tp > 0.0) and req.get("sl", 0.0) == 0.0:
                try:
                    mod_req = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": res.order,
                        "symbol": symbol,
                        "sl": norm_sl,
                        "tp": norm_tp,
                    }
                    mt5.order_send(mod_req)
                except Exception:
                    pass

            # Report fill to backend
            try:
                requests.post(
                    f"{CLOUD_URL}/api/v1/execution/worker/report-fill",
                    json={
                        "account_id": self.account_id,
                        "ticket_id": ticket_id,
                        "signal_id": signal_id,
                        "instrument": symbol,
                        "direction": direction,
                        "fill_price": fill_price,
                        "volume": volume,
                        "sl": norm_sl,
                        "tp": norm_tp,
                        "latency_ms": latency_ms,
                        "status": "FILLED"
                    },
                    headers=HEADERS, timeout=5
                )
            except Exception as fe:
                self.logger.error(f"Error reporting fill: {fe}")

            self.tracked_positions[ticket_id] = {
                "ticket_id": ticket_id,
                "instrument": symbol,
                "direction": direction,
                "open_price": fill_price,
                "current_price": fill_price,
                "stop_loss": norm_sl,
                "take_profit": norm_tp,
                "volume": volume,
                "max_mae_pips": 0.0,
                "max_mfe_pips": 0.0,
                "current_pnl_pips": 0.0,
                "open_timestamp": datetime.datetime.utcnow().timestamp(),
                "missing_cycles": 0
            }
        else:
            err_c = res.comment if res else str(mt5.last_error())
            self.logger.error(f"Order failed on broker for #{self.login}: {err_c}")

    def poll_orders(self):
        """Polls cloud router for pending orders for this specific account."""
        try:
            r = requests.get(
                f"{CLOUD_URL}/api/v1/execution/worker/poll-orders?account_id={self.account_id}",
                headers=HEADERS, timeout=5
            )
            if r.status_code == 200:
                orders = r.json().get("orders", [])
                for order in orders:
                    self.execute_order(order)
        except Exception as e:
            self.logger.debug(f"Order poll exception: {e}")

    def report_heartbeat(self, positions: List[Dict]):
        """Sends account telemetry and positions report."""
        try:
            requests.post(
                f"{CLOUD_URL}/api/v1/execution/worker/report-positions/{self.account_id}",
                json={"positions": positions},
                headers=HEADERS, timeout=5
            )
        except Exception:
            pass

    def run(self):
        """Continuous execution loop."""
        if not self.initialize_terminal():
            self.logger.error("Terminal initialization failed. Exiting worker.")
            sys.exit(1)

        self.logger.info(f"=== WORKER ACTIVE FOR ACCOUNT #{self.login} (Zero-Switch Dedicated Session) ===")
        last_hb = 0

        while True:
            try:
                # 1. Sync positions
                positions = self.sync_positions()

                # 2. Check early invalidation
                self.check_early_invalidation()

                # 3. Poll and execute incoming orders
                self.poll_orders()

                # 4. Report heartbeat every 10s
                if time.time() - last_hb >= 10:
                    self.report_heartbeat(positions)
                    last_hb = time.time()

                time.sleep(2)

            except KeyboardInterrupt:
                self.logger.info("Worker stopped by operator.")
                break
            except Exception as e:
                self.logger.error(f"Worker loop exception: {e}")
                time.sleep(3)


def main():
    parser = argparse.ArgumentParser(description="Market-OS Dedicated Account Worker")
    parser.add_argument("--account-id", type=int, required=True, help="Account ID in user_broker_accounts")
    args = parser.parse_args()

    acc_data = fetch_account_details(args.account_id)
    if not acc_data:
        print(f"Could not load account details for account ID {args.account_id}")
        sys.exit(1)

    worker = AccountWorker(acc_data)
    worker.run()


if __name__ == "__main__":
    main()
