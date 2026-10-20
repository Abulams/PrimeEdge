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
    master_acc = os.getenv("MASTER_CTRADER_ACCOUNT_ID")
    master_tok = os.getenv("MASTER_ACCESS_TOKEN")

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

    return None, None


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

    async def resolve_symbol_id(instrument: str):
        cache_key = instrument.upper()
        if cache_key in symbol_cache:
            return symbol_cache[cache_key]
        try:
            symbols = await gateway.get_symbols(master_account_id)
            for sym in symbols:
                symbol_cache[sym["name"].upper()] = sym["id"]
            return symbol_cache.get(cache_key)
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
                            UserBrokerAccount.ctrader_account_id == str(master_account_id)
                        ).first()
                        if not acc:
                            acc = db_sync.query(UserBrokerAccount).filter(
                                UserBrokerAccount.login == master_account_id
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
                                logger.info("Position %s closed on cTrader broker side. Finalizing trade #%s", tr.broker_ticket, tr.id)
                                from app.journal_service import JournalService
                                JournalService._finalize_trade(tr, tr.actual_entry, "BROKER_CLOSE")
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
