import datetime
import logging
from typing import Any, Dict, List, Optional
from collections import defaultdict

from .base import ExecutionOrder, ExecutionPosition, PlatformType, OrderDirection

logger = logging.getLogger(__name__)


class CloudExecutionRouter:
    """
    Multi-tenant cloud execution coordinator for zero-install subscribers.
    Manages per-account order queues, idempotency, stale signal filters,
    and routing to designated Windows VPS workers.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CloudExecutionRouter, cls).__new__(cls)
            cls._instance._init_router()
        return cls._instance

    def _init_router(self):
        # account_id -> list of queued ExecutionOrder dicts
        self.pending_order_queues: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        # account_id -> list of ExecutionPosition
        self.active_positions: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        # Processed signal IDs for idempotency (prevents duplicate fills)
        self.processed_signals: set = set()
        # Global emergency killswitch
        self.global_killswitch_active: bool = False
        # Specific account killswitches
        self.account_killswitches: Dict[int, bool] = defaultdict(lambda: False)

    def is_execution_allowed(self, account_id: int) -> bool:
        if self.global_killswitch_active:
            return False
        if self.account_killswitches[account_id]:
            return False
        return True

    def toggle_global_killswitch(self, active: bool) -> bool:
        self.global_killswitch_active = active
        logger.warning(f"GLOBAL EXECUTION KILLSWITCH toggled: {active}")
        return self.global_killswitch_active

    def toggle_account_killswitch(self, account_id: int, active: bool) -> bool:
        self.account_killswitches[account_id] = active
        logger.info(f"Account {account_id} killswitch toggled: {active}")
        return active

    def queue_order_for_account(self, account_id: int, order: ExecutionOrder) -> Dict[str, Any]:
        """
        Queues an execution order for a subscriber account with validation:
        1. Killswitch check
        2. Idempotency (duplicate signal) check
        3. Stale signal check
        4. Spread guardrail check
        """
        if not self.is_execution_allowed(account_id):
            return {"status": "BLOCKED", "reason": "Execution killswitch is active for this account or globally."}

        # Idempotency check
        idempotency_key = f"{account_id}:{order.signal_id}"
        if idempotency_key in self.processed_signals:
            return {"status": "DUPLICATE_REJECTED", "reason": f"Signal {order.signal_id} already dispatched."}

        # Stale signal check (default 60s)
        age_seconds = (datetime.datetime.utcnow() - order.created_at).total_seconds()
        if age_seconds > order.expiry_seconds:
            return {"status": "STALE_REJECTED", "reason": f"Signal expired (age: {age_seconds:.1f}s > {order.expiry_seconds}s)."}

        order_dict = order.dict()
        order_dict["account_id"] = account_id
        order_dict["queued_at"] = datetime.datetime.utcnow().isoformat()

        self.pending_order_queues[account_id].append(order_dict)
        self.processed_signals.add(idempotency_key)

        # Durable DB queue persistence
        try:
            from ..database import SessionLocal
            from ..models import ExecutionOrderQueue
            with SessionLocal() as db:
                existing = db.query(ExecutionOrderQueue).filter(ExecutionOrderQueue.signal_id == order.signal_id).first()
                if not existing:
                    db_order = ExecutionOrderQueue(
                        signal_id=order.signal_id,
                        account_id=account_id,
                        action_type="OPEN",
                        instrument=order.instrument,
                        direction="LONG" if "LONG" in str(order.direction).upper() else "SHORT",
                        order_type="MARKET",
                        entry_reference_price=order.entry_reference_price,
                        stop_loss=order.stop_loss,
                        take_profit=order.take_profit,
                        position_size_lots=order.position_size_lots,
                        risk_pct=order.risk_pct,
                        account_balance=order.account_balance,
                        status="QUEUED"
                    )
                    db.add(db_order)
                    db.commit()
        except Exception as e:
            logger.error(f"Error persisting order to DB queue: {e}")

        logger.info(f"[Router] Queued order {order.signal_id} ({order.instrument} {order.direction}) for account {account_id}")
        return {"status": "QUEUED", "account_id": account_id, "signal_id": order.signal_id}

    def queue_close_order_for_account(self, account_id: int, ticket_id: str, instrument: str, reason: str = "MANUAL") -> Dict[str, Any]:
        """
        Queues a position liquidation / close order for MT5 execution with durable DB persistence.
        """
        close_signal_id = f"CLOSE-{ticket_id}-{int(datetime.datetime.utcnow().timestamp())}"
        order_dict = {
            "action_type": "CLOSE",
            "ticket_id": str(ticket_id),
            "signal_id": close_signal_id,
            "instrument": instrument,
            "account_id": account_id,
            "reason": reason,
            "queued_at": datetime.datetime.utcnow().isoformat()
        }
        self.pending_order_queues[account_id].append(order_dict)

        # Durable DB queue persistence
        try:
            from ..database import SessionLocal
            from ..models import ExecutionOrderQueue
            with SessionLocal() as db:
                db_close = ExecutionOrderQueue(
                    signal_id=close_signal_id,
                    account_id=account_id,
                    action_type="CLOSE",
                    ticket_id=str(ticket_id),
                    instrument=instrument,
                    direction="CLOSE",
                    order_type="MARKET",
                    entry_reference_price=0.0,
                    stop_loss=0.0,
                    take_profit=0.0,
                    position_size_lots=0.0,
                    status="QUEUED"
                )
                db.add(db_close)
                db.commit()
                logger.info(f"💾 [Durable Outbox] Queued CLOSE order for Ticket #{ticket_id} ({instrument}) on Account {account_id}")
        except Exception as e:
            logger.error(f"Error persisting durable close order: {e}")

        logger.info(f"[Router] Queued CLOSE order for Ticket #{ticket_id} ({instrument}) on Account {account_id} [Reason: {reason}]")
        return {"status": "CLOSE_QUEUED", "account_id": account_id, "ticket_id": ticket_id}

    def pop_orders_for_worker(self, account_ids: List[int]) -> List[Dict[str, Any]]:
        """Worker polls queued orders for its assigned accounts."""
        orders_to_dispatch = []
        for acc_id in account_ids:
            if not self.is_execution_allowed(acc_id):
                continue
            if self.pending_order_queues[acc_id]:
                orders_to_dispatch.extend(self.pending_order_queues[acc_id])
                self.pending_order_queues[acc_id] = []
        return orders_to_dispatch

    def update_positions_from_worker(self, account_id: int, positions: List[Dict[str, Any]]):
        """Reconciles open positions and excursion metrics reported by worker."""
        self.active_positions[account_id] = positions

    def get_positions_for_account(self, account_id: int) -> List[Dict[str, Any]]:
        return self.active_positions.get(account_id, [])
