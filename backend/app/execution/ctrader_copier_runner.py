"""
ctrader_copier_runner.py — Standalone Runner for PrimeEdge cTrader Copier
==========================================================================
Executes the background copier service on Linode.

Run directly with:
    python -m app.execution.ctrader_copier_runner
Or via systemd:
    systemctl start ctrader-copier.service
"""

import asyncio
import datetime
import logging
import os
import signal
import sys
import time

from app.database import SessionLocal
from app.execution.ctrader_gateway import CTraderGateway
from app.execution.ctrader_copier_service import CTraderCopierService
from app.models import UserBrokerAccount

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ctrader_copier_runner")

CTRADER_CLIENT_ID = os.getenv(
    "CTRADER_CLIENT_ID", "43796_NUbyz1CxFRhD01Tm0Jqc1hMVHd4ubgk5lZQcwtftpuH5zJozj1"
)
CTRADER_CLIENT_SECRET = os.getenv(
    "CTRADER_CLIENT_SECRET", "j9WYsJ4mG80iyHKbale8Fuxx75fO9eaMuUoOhrZWSlCS653C9C"
)
CTRADER_IS_DEMO = os.getenv("CTRADER_IS_DEMO", "true").lower() == "true"


def get_master_credentials():
    master_acc = os.getenv("MASTER_CTRADER_ACCOUNT_ID", "49127263")
    master_tok = os.getenv("MASTER_ACCESS_TOKEN", "X2PjO7w-bEXwBQl0xiyfdExZ8zrQQGpHRBQA_S2xRD8")

    if master_acc and master_tok:
        return int(master_acc), master_tok

    # Fallback to database for master cTrader account
    with SessionLocal() as db:
        master_uba = db.query(UserBrokerAccount).filter(
            UserBrokerAccount.platform == "ctrader",
            UserBrokerAccount.ctrader_access_token != None,
        ).first()

        if master_uba and master_uba.ctrader_account_id and master_uba.ctrader_access_token:
            logger.info("Loaded master account credentials from DB (ID: %s)", master_uba.ctrader_account_id)
            return int(master_uba.ctrader_account_id), master_uba.ctrader_access_token

    return 49127263, "X2PjO7w-bEXwBQl0xiyfdExZ8zrQQGpHRBQA_S2xRD8"


# ---------------------------------------------------------------------------
# PrimeEdge Signal Queue Poller
# ---------------------------------------------------------------------------

async def poll_signal_queue(gateway: CTraderGateway, master_account_id: int, master_token: str):
    """
    Polls ExecutionOrderQueue for QUEUED PrimeEdge signals and auto-executes
    them directly on the master cTrader account via the OpenAPI gateway.

    This is the bridge between PrimeEdge signal generation and cTrader execution.
    """
    import datetime
    from app.models import ExecutionOrderQueue

    # Symbol name -> cTrader symbol_id cache
    symbol_cache: dict = {}
    _alerted_tickets: set = set()

    ALIASES = {
        "US100": ["USTEC", "NAS100", "US100", "NDX", "TECH100"],
        "XAUUSD": ["XAUUSD", "GOLD", "XAUUSD-24_7"],
        "EURUSD": ["EURUSD", "EURUSD.", "EURUSDt"],
        "GBPUSD": ["GBPUSD", "GBPUSD."],
        "USDJPY": ["USDJPY", "USDJPY."],
        "USDCHF": ["USDCHF", "USDCHF."],
        "AUDUSD": ["AUDUSD", "AUDUSD."],
        "US30": ["US30", "DJ30", "WS30"],
        "SPX500": ["US500", "SPX500", "SP500"]
    }

    async def resolve_symbol_id(instrument: str):
        cache_key = instrument.upper()
        if cache_key in symbol_cache:
            return symbol_cache[cache_key]
        try:
            symbols = await gateway.get_symbols(master_account_id)
            for sym in symbols:
                symbol_cache[sym["name"].upper()] = sym["id"]

            if cache_key in symbol_cache:
                return symbol_cache[cache_key]

            # Try broker aliases (e.g. US100 -> USTEC on IC Markets)
            for alias in ALIASES.get(cache_key, []):
                if alias.upper() in symbol_cache:
                    symbol_cache[cache_key] = symbol_cache[alias.upper()]
                    logger.info("Mapped instrument %s -> cTrader broker symbol %s (ID: %s)", cache_key, alias, symbol_cache[cache_key])
                    return symbol_cache[cache_key]

            # Fuzzy match
            for sym_name, sym_id in symbol_cache.items():
                if cache_key in sym_name:
                    symbol_cache[cache_key] = sym_id
                    return sym_id

            return None
        except Exception as exc:
            logger.error("Failed to resolve symbol %s: %s", instrument, exc)
            return None

    logger.info("Signal queue poller started - polling every 1s for PrimeEdge auto-execution orders.")
    last_account_sync = 0.0

    while True:
        try:
            await asyncio.sleep(1)
            now = time.time()

            # Periodic account balance & equity sync + position reconciliation (every 15s)
            if now - last_account_sync >= 15:
                last_account_sync = now
                try:
                    info = await gateway.get_account_info(master_account_id)
                    positions = await gateway.get_open_positions(master_account_id)

                    open_pos_ids = {str(p["position_id"]) for p in positions}
                    pnl_total = sum(p.get("pnl", 0.0) for p in positions)
                    balance = info.get("balance", 0.0)
                    equity = round(balance + pnl_total, 2)

                    with SessionLocal() as db_sync:
                        from app.models import UserBrokerAccount, TradeRecord
                        acc = db_sync.query(UserBrokerAccount).filter(
                            (UserBrokerAccount.ctrader_account_id == int(master_account_id)) |
                            (UserBrokerAccount.login == 10124502) |
                            (UserBrokerAccount.platform == "ctrader")
                        ).first()
                        if acc:
                            acc.balance = balance
                            acc.equity = equity
                            if info.get("currency"):
                                acc.currency = info["currency"]
                            if info.get("leverage"):
                                acc.leverage = int(info["leverage"])
                            acc.last_heartbeat = datetime.datetime.utcnow()
                            db_sync.commit()
                            logger.debug("Synced cTrader Account %s: balance=%.2f equity=%.2f", master_account_id, balance, equity)

                        # Auto-reconcile closed positions:
                        # If an ACTIVE trade has a broker_ticket that is no longer in cTrader open positions,
                        # mark it CLOSED as BROKER_CLOSE
                        active_trades = db_sync.query(TradeRecord).filter(
                            TradeRecord.lifecycle_state == "ACTIVE",
                            TradeRecord.broker_ticket != None,
                        ).all()
                        for tr in active_trades:
                            if tr.broker_ticket not in open_pos_ids:
                                # Attempt to extract closing execution price from recent cTrader deals
                                exit_p = None
                                try:
                                    recent_deals = await gateway.get_deals(master_account_id, max_rows=20)
                                    for d in recent_deals:
                                        if d.get("position_id") == str(tr.broker_ticket):
                                            exit_p = d.get("execution_price")
                                            break
                                except Exception as ge:
                                    logger.debug("Could not fetch deal details for pos %s: %s", tr.broker_ticket, ge)

                                if not exit_p or exit_p <= 0:
                                    exit_p = tr.actual_tp if (tr.max_mfe_pips and tr.max_mfe_pips >= 10.0) else (tr.actual_sl or tr.actual_entry)

                                logger.info("Position %s closed on cTrader broker side (exit_price=%.5f). Finalizing trade #%s", tr.broker_ticket, exit_p or 0.0, tr.id)
                                from app.journal_service import JournalService
                                JournalService._finalize_trade(tr, exit_p, "BROKER_CLOSE")
                                db_sync.commit()

                except Exception as sync_exc:
                    logger.warning("Periodic account/position sync error: %s", sync_exc)

            with SessionLocal() as db:
                pending = (
                    db.query(ExecutionOrderQueue)
                    .filter(
                        ExecutionOrderQueue.status == "QUEUED",
                    )
                    .order_by(ExecutionOrderQueue.created_at.asc())
                    .all()
                )

                if not pending:
                    continue

                for order in pending:
                    if order.action_type == "CLOSE":
                        logger.info("Executing CLOSE order for Ticket %s on account %s", order.ticket_id, master_account_id)
                        order.status = "DISPATCHED"
                        order.dispatched_at = datetime.datetime.utcnow()
                        db.commit()

                        try:
                            pos_id = int(order.ticket_id) if order.ticket_id and str(order.ticket_id).isdigit() else None
                            if pos_id:
                                positions = await gateway.get_open_positions(master_account_id)
                                matching_pos = next((p for p in positions if p["position_id"] == pos_id), None)
                                if matching_pos:
                                    volume_units = matching_pos["volume"]
                                    await gateway.close_position(master_account_id, pos_id, volume_units)
                                    logger.info("cTrader position %s closed successfully", pos_id)
                                else:
                                    logger.info("cTrader position %s is already closed on broker", pos_id)

                            with SessionLocal() as db2:
                                db2.query(ExecutionOrderQueue).filter(
                                    ExecutionOrderQueue.id == order.id
                                ).update({
                                    "status": "FILLED",
                                    "completed_at": datetime.datetime.utcnow(),
                                })
                                db2.commit()
                        except Exception as exc:
                            logger.error("Failed to execute close order %s: %s", order.id, exc)
                            with SessionLocal() as db2:
                                db2.query(ExecutionOrderQueue).filter(
                                    ExecutionOrderQueue.id == order.id
                                ).update({
                                    "status": "REJECTED",
                                    "error_comment": str(exc)[:500],
                                    "completed_at": datetime.datetime.utcnow(),
                                })
                                db2.commit()
                        continue

                    # Mark dispatched immediately to prevent double-execution
                    order.status = "DISPATCHED"
                    order.dispatched_at = datetime.datetime.utcnow()
                    db.commit()

                    logger.info(
                        "Auto-executing signal %s: %s %s %.2f lots on account %s",
                        order.signal_id, order.instrument, order.direction,
                        order.position_size_lots, master_account_id,
                    )

                    try:
                        symbol_id = await resolve_symbol_id(order.instrument)
                        if symbol_id is None:
                            logger.error(
                                "Cannot resolve symbol %s - skipping signal %s",
                                order.instrument, order.signal_id,
                            )
                            with SessionLocal() as db2:
                                db2.query(ExecutionOrderQueue).filter(
                                    ExecutionOrderQueue.id == order.id
                                ).update({
                                    "status": "REJECTED",
                                    "error_comment": "Symbol not found in cTrader",
                                    "completed_at": datetime.datetime.utcnow(),
                                })
                                db2.commit()
                            continue

                        # cTrader direction: LONG -> BUY, SHORT -> SELL
                        ct_direction = "BUY" if order.direction.upper() == "LONG" else "SELL"

                        # ── Live-Broker Guardrails (apply to ALL accounts) ────────────────
                        # These run against the REAL broker state, not the local DB, so they
                        # catch cases where the DB is stale or the scanner bypassed DB guards.
                        try:
                            live_positions = await gateway.get_open_positions(master_account_id)
                            live_account_info = await gateway.get_account_info(master_account_id)

                            # Guard LB-1: Max Concurrent Positions (hard limit: 5)
                            # Uses LIVE broker count, not DB count which can be stale.
                            max_concurrent = 5
                            if len(live_positions) >= max_concurrent:
                                logger.warning(
                                    "LIVE GUARDRAIL: Account %s has %d/%d live positions open. "
                                    "Rejecting signal %s to enforce max concurrent cap.",
                                    master_account_id, len(live_positions), max_concurrent, order.signal_id
                                )
                                with SessionLocal() as db2:
                                    db2.query(ExecutionOrderQueue).filter(ExecutionOrderQueue.id == order.id).update({
                                        "status": "REJECTED",
                                        "error_comment": f"MAX_CONCURRENT_EXCEEDED: {len(live_positions)}/{max_concurrent} live positions open",
                                        "completed_at": datetime.datetime.utcnow(),
                                    })
                                    if order.trade_id:
                                        from ..models import TradeRecord
                                        db2.query(TradeRecord).filter(TradeRecord.id == order.trade_id).update({
                                            "execution_status": "REJECTED",
                                            "lifecycle_state": "CLOSED",
                                            "outcome": "MAX_CONCURRENT_EXCEEDED",
                                            "exit_reason": f"MAX_CONCURRENT_EXCEEDED_{len(live_positions)}_OF_{max_concurrent}",
                                            "exit_timestamp": datetime.datetime.utcnow(),
                                        })
                                    db2.commit()
                                continue

                            # Guard LB-2: Same instrument already open (ANY direction) — prevents hedges and doubles
                            existing_pos = next((p for p in live_positions if p.get("symbol_id") == symbol_id), None)
                            if existing_pos:
                                logger.warning(
                                    "LIVE GUARDRAIL: Duplicate prevented — Account %s already has position #%s on %s. Rejecting signal %s.",
                                    master_account_id, existing_pos.get("position_id"), order.instrument, order.signal_id
                                )
                                with SessionLocal() as db2:
                                    db2.query(ExecutionOrderQueue).filter(ExecutionOrderQueue.id == order.id).update({
                                        "status": "REJECTED",
                                        "error_comment": f"DUPLICATE_PREVENTED: position #{existing_pos.get('position_id')} already open on broker for {order.instrument}",
                                        "completed_at": datetime.datetime.utcnow(),
                                    })
                                    if order.trade_id:
                                        from ..models import TradeRecord
                                        db2.query(TradeRecord).filter(TradeRecord.id == order.trade_id).update({
                                            "execution_status": "REJECTED",
                                            "lifecycle_state": "CLOSED",
                                            "outcome": "DUPLICATE_PREVENTED",
                                            "exit_reason": f"DUPLICATE_PREVENTED_POS_{existing_pos.get('position_id')}",
                                            "exit_timestamp": datetime.datetime.utcnow(),
                                        })
                                    db2.commit()
                                continue

                            # Guard LB-3: Recalculate lot size using LIVE account balance
                            # (stored acc.balance can be minutes or hours stale)
                            live_balance = live_account_info.get("balance", 0.0)
                            if live_balance and live_balance > 100:
                                inst_upper_lb = (order.instrument or "").upper()
                                is_index_lb = any(k in inst_upper_lb for k in ("US100","NAS100","USTEC","NDX","TECH100","UK100","GER40","SPX","US30","AUS200","DJ30","WS30","DAX"))
                                is_gold_lb = any(k in inst_upper_lb for k in ("XAU","GOLD"))
                                is_jpy_lb = "JPY" in inst_upper_lb

                                if is_jpy_lb:
                                    pip_val_lb = 6.5
                                elif is_index_lb:
                                    pip_val_lb = 1.0   # $1 per point per lot (cTrader index CFD)
                                elif is_gold_lb:
                                    pip_val_lb = 10.0  # $10 per pip per lot
                                else:
                                    pip_val_lb = 10.0  # standard FX

                                risk_pct_lb = 1.0  # 1% per trade hardcoded as floor
                                risk_amount_lb = live_balance * (risk_pct_lb / 100.0)

                                # Determine SL distance from the queued order
                                if order.stop_loss and order.entry_reference_price and order.entry_reference_price > 0:
                                    sl_dist_lb = abs(order.entry_reference_price - order.stop_loss)
                                else:
                                    # Safe fallback SL distances
                                    if is_index_lb:   sl_dist_lb = 150.0
                                    elif is_gold_lb:  sl_dist_lb = 4.0
                                    else:             sl_dist_lb = 0.0025

                                if is_index_lb:
                                    risk_pips_lb = sl_dist_lb  # points are 1:1
                                elif is_jpy_lb:
                                    risk_pips_lb = sl_dist_lb * 100.0
                                elif is_gold_lb:
                                    risk_pips_lb = sl_dist_lb * 10.0
                                else:
                                    risk_pips_lb = sl_dist_lb * 10000.0

                                if risk_pips_lb > 0 and pip_val_lb > 0:
                                    calc_lots_lb = risk_amount_lb / (risk_pips_lb * pip_val_lb)
                                    # Hard caps per instrument class
                                    if is_index_lb:
                                        final_lots = max(0.1, min(round(calc_lots_lb * 10) / 10, 5.0))
                                    elif is_gold_lb:
                                        final_lots = max(0.01, min(round(calc_lots_lb, 2), 5.0))
                                    else:
                                        final_lots = max(0.01, min(round(calc_lots_lb, 2), 10.0))

                                    if abs(final_lots - order.position_size_lots) > 0.5:
                                        logger.info(
                                            "LIVE GUARDRAIL: Recalculated lot size for signal %s: "
                                            "queued=%.2f -> live_balance_based=%.2f (balance=%.2f, risk_pips=%.1f)",
                                            order.signal_id, order.position_size_lots, final_lots, live_balance, risk_pips_lb
                                        )
                                        order.position_size_lots = final_lots

                                # Absolute hard cap regardless of calculation
                                if is_index_lb and order.position_size_lots > 5.0:
                                    logger.warning("LIVE GUARDRAIL: Hard-capping index lots from %.2f to 5.0", order.position_size_lots)
                                    order.position_size_lots = 5.0
                                elif is_gold_lb and order.position_size_lots > 5.0:
                                    logger.warning("LIVE GUARDRAIL: Hard-capping gold lots from %.2f to 5.0", order.position_size_lots)
                                    order.position_size_lots = 5.0
                                elif not is_index_lb and not is_gold_lb and order.position_size_lots > 10.0:
                                    logger.warning("LIVE GUARDRAIL: Hard-capping FX lots from %.2f to 10.0", order.position_size_lots)
                                    order.position_size_lots = 10.0

                        except Exception as pos_check_err:
                            logger.warning("Could not run live broker guardrails: %s", pos_check_err)

                        result = await gateway.execute_market_order(
                            account_id=master_account_id,
                            symbol_id=symbol_id,
                            volume_lots=order.position_size_lots,
                            direction=ct_direction,
                            entry_price=order.entry_reference_price,
                            stop_loss_price=order.stop_loss,
                            take_profit_price=order.take_profit,
                        )

                        ticket_str = str(
                            result.get("position_id") or result.get("order_id") or ""
                        )
                        with SessionLocal() as db2:
                            db2.query(ExecutionOrderQueue).filter(
                                ExecutionOrderQueue.id == order.id
                            ).update({
                                "status": "FILLED",
                                "ticket_id": ticket_str,
                                "completed_at": datetime.datetime.utcnow(),
                            })
                            if order.trade_id:
                                from ..models import TradeRecord
                                update_dict = {
                                    "execution_status": "FILLED",
                                    "broker_ticket": ticket_str,
                                    "entry_timestamp": datetime.datetime.utcnow(),
                                }
                                if result.get("fill_price"):
                                    update_dict["actual_entry"] = result["fill_price"]
                                db2.query(TradeRecord).filter(
                                    TradeRecord.id == order.trade_id
                                ).update(update_dict)
                            db2.commit()

                        logger.info(
                            "Signal %s FILLED: position_id=%s instrument=%s dir=%s",
                            order.signal_id, result.get("position_id"),
                            order.instrument, ct_direction,
                        )

                        # DISPATCH TELEGRAM ALERT STRICTLY POST-EXECUTION (Only if trade genuinely executed on cTrader)
                        try:
                            if order.trade_id and ticket_str and ticket_str not in _alerted_tickets and result.get("position_id"):
                                _alerted_tickets.add(ticket_str)
                                with SessionLocal() as db_tg:
                                    from ..models import TradeRecord, SetupSnapshot
                                    tr = db_tg.query(TradeRecord).filter(TradeRecord.id == order.trade_id).first()
                                    if tr and tr.setup_snapshot_id:
                                        snap = db_tg.query(SetupSnapshot).filter(SetupSnapshot.id == tr.setup_snapshot_id).first()
                                        if snap:
                                            from ..telegram_service import TelegramService
                                            fill_p = result.get("fill_price") or order.entry_reference_price
                                            TelegramService.send_setup_alert(snap, current_live_price=fill_p)
                                            logger.info(f"[Telegram Commercial Channel] Dispatched verified fill alert for cTrader trade #{tr.id} (Ticket {ticket_str})")
                        except Exception as tg_err:
                            logger.error("Failed to dispatch post-execution telegram alert: %s", tg_err)

                    except Exception as exc:
                        logger.error("Failed to execute signal %s: %s", order.signal_id, exc)
                        with SessionLocal() as db2:
                            db2.query(ExecutionOrderQueue).filter(
                                ExecutionOrderQueue.id == order.id
                            ).update({
                                "status": "REJECTED",
                                "error_comment": str(exc)[:500],
                                "completed_at": datetime.datetime.utcnow(),
                            })
                            if order.trade_id:
                                from ..models import TradeRecord
                                db2.query(TradeRecord).filter(
                                    TradeRecord.id == order.trade_id
                                ).update({
                                    "execution_status": "REJECTED",
                                    "lifecycle_state": "CLOSED",
                                    "outcome": "REJECTED",
                                    "exit_reason": str(exc)[:200],
                                    "exit_timestamp": datetime.datetime.utcnow(),
                                })
                            db2.commit()

        except Exception as loop_exc:
            logger.error("Error in signal queue poller loop: %s", loop_exc, exc_info=True)
            await asyncio.sleep(5)


async def main():
    logger.info("Initializing PrimeEdge cTrader Copier Service...")
    logger.info("Client ID: %s... Demo Mode: %s", CTRADER_CLIENT_ID[:12], CTRADER_IS_DEMO)

    master_account_id, master_token = get_master_credentials()

    if not master_account_id or not master_token:
        logger.warning(
            "No master cTrader account found yet in environment or DB.\n"
            "Please link your master account via OAuth at https://www.primeedge.app/api/v1/ctrader/auth?user_id=1\n"
            "Runner will poll every 15s until an account is connected..."
        )

    gateway = CTraderGateway(
        client_id=CTRADER_CLIENT_ID,
        client_secret=CTRADER_CLIENT_SECRET,
        is_demo=CTRADER_IS_DEMO,
    )

    service = CTraderCopierService(db_session_factory=SessionLocal, gateway=gateway)

    # Wait for master account if not configured yet
    while not master_account_id or not master_token:
        await asyncio.sleep(15)
        master_account_id, master_token = get_master_credentials()

    logger.info("Starting copy service for master account %s...", master_account_id)
    await service.start(master_account_id=master_account_id, master_access_token=master_token)

    # Keep runner alive until stop signal
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    logger.info("PrimeEdge cTrader Copier is actively running.")
    logger.info("Signal auto-execution ENABLED - PrimeEdge setups will fire on account %s", master_account_id)

    # Run supervised signal queue poller concurrently with the copier service
    async def supervised_poller():
        while not stop_event.is_set():
            try:
                await poll_signal_queue(gateway, master_account_id, master_token)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.critical("Signal poller crashed: %s. Auto-restarting in 2s...", e, exc_info=True)
                await asyncio.sleep(2)

    poller_task = asyncio.create_task(supervised_poller())

    await stop_event.wait()

    logger.info("Shutting down copier service...")
    poller_task.cancel()
    await service.stop()
    logger.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Copier runner terminated.")
