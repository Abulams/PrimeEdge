import os
import datetime
import logging
from typing import Optional, Dict, List, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import UserBrokerAccount, ExecutionOrderQueue, TradeRecord, ExecutionAuditLog, SetupSnapshot

logger = logging.getLogger("EaBridgeRouter")

router = APIRouter(prefix="/api/v1/execution/ea", tags=["EA Bridge Execution"])

WORKER_KEY = os.getenv("WORKER_KEY", "wkey_master_cloud_london")


def verify_ea_auth(
    request: Request,
    x_worker_key: Optional[str] = Header(None),
):
    """Allows authenticated worker key or direct local loopback connections."""
    client_host = getattr(request.client, "host", "")
    if client_host in ("127.0.0.1", "localhost", "::1"):
        return True
    if x_worker_key == WORKER_KEY:
        return True
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized EA connection",
    )


# --- Schemas ---

class EaFillReportRequest(BaseModel):
    login: int
    order_id: int
    signal_id: str
    instrument: str
    direction: str
    volume: float
    fill_price: float
    sl: float
    tp: float
    ticket_id: str
    status: str  # "FILLED" or "REJECTED"
    error_comment: Optional[str] = ""
    retcode: Optional[int] = 0
    latency_ms: Optional[float] = 0.0


class EaCloseReportRequest(BaseModel):
    login: int
    ticket_id: str
    instrument: str
    exit_price: float
    profit: float
    exit_reason: str  # "STOP_LOSS", "TAKE_PROFIT", "SIGNAL_CLOSE", "ALREADY_CLOSED", "MANUAL"


class EaHeartbeatRequest(BaseModel):
    login: int
    balance: float
    equity: float
    margin: float
    free_margin: float


# --- Endpoints ---

@router.get("/poll-orders")
def poll_orders_for_ea(
    login: int,
    db: Session = Depends(get_db),
    authorized: bool = Depends(verify_ea_auth),
):
    """Native MQL5 EA calls this every ~1 second to fetch queued orders for its account."""
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.login == login).first()
    if not account or not account.is_active or not account.auto_execution_enabled:
        return {"orders": [], "count": 0}

    now = datetime.datetime.utcnow()

    # 1. Lease recovery on stuck DISPATCHED orders
    stale_lease = now - datetime.timedelta(seconds=120)
    stuck_orders = db.query(ExecutionOrderQueue).filter(
        ExecutionOrderQueue.account_id == account.id,
        ExecutionOrderQueue.status == "DISPATCHED",
        ExecutionOrderQueue.dispatched_at < stale_lease
    ).all()
    for stuck in stuck_orders:
        if (now - stuck.created_at).total_seconds() > 300:
            stuck.status = "EXPIRED"
            stuck.completed_at = now
            if stuck.trade_id:
                trade = db.query(TradeRecord).filter(TradeRecord.id == stuck.trade_id).first()
                if trade and trade.execution_status == "QUEUED":
                    trade.execution_status = "EXPIRED"
                    trade.lifecycle_state = "CANCELLED"
                    trade.notes = "Order lease expired after 300s without EA fill"
        else:
            stuck.status = "QUEUED"

    # 2. Fetch all durable QUEUED orders for this account
    queued_orders = db.query(ExecutionOrderQueue).filter(
        ExecutionOrderQueue.account_id == account.id,
        ExecutionOrderQueue.status == "QUEUED"
    ).order_by(ExecutionOrderQueue.id.asc()).all()

    orders_to_dispatch = []
    for o in queued_orders:
        orders_to_dispatch.append({
            "order_id": o.id,
            "action_type": o.action_type,
            "signal_id": o.signal_id,
            "instrument": o.instrument,
            "direction": o.direction,
            "position_size_lots": o.position_size_lots,
            "stop_loss": o.stop_loss,
            "take_profit": o.take_profit,
            "ticket_id": int(o.ticket_id) if o.ticket_id and str(o.ticket_id).isdigit() else 0,
        })
        o.status = "DISPATCHED"
        o.dispatched_at = now

    if queued_orders or stuck_orders:
        db.commit()

    return {"orders": orders_to_dispatch, "count": len(orders_to_dispatch)}


@router.post("/report-fill")
def report_ea_fill(
    req: EaFillReportRequest,
    db: Session = Depends(get_db),
    authorized: bool = Depends(verify_ea_auth),
):
    """MQL5 EA reports back immediately when OrderSend finishes."""
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.login == req.login).first()
    user_id = account.user_id if account else 1

    audit_entry = ExecutionAuditLog(
        user_id=user_id,
        worker_id="mql5-native-bridge",
        ticket_id=str(req.ticket_id) if req.ticket_id else "NONE",
        signal_id=req.signal_id,
        instrument=req.instrument,
        direction=req.direction,
        order_type="MARKET",
        entry_price=req.fill_price,
        sl=req.sl,
        tp=req.tp,
        volume=req.volume,
        status=req.status,
        latency_ms=req.latency_ms,
        details={"retcode": req.retcode, "error_comment": req.error_comment},
    )
    db.add(audit_entry)

    # 1. Update queue order
    queue_order = db.query(ExecutionOrderQueue).filter(ExecutionOrderQueue.id == req.order_id).first()
    if not queue_order:
        queue_order = db.query(ExecutionOrderQueue).filter(ExecutionOrderQueue.signal_id == req.signal_id).first()

    now = datetime.datetime.utcnow()
    if queue_order:
        queue_order.completed_at = now
        queue_order.status = req.status
        queue_order.ticket_id = str(req.ticket_id)
        queue_order.retcode = req.retcode
        queue_order.error_comment = req.error_comment

    # 2. Update TradeRecord
    trade = None
    if "-TR-" in req.signal_id:
        try:
            tr_part = req.signal_id.split("-TR-")[1].split("-")[0]
            trade_id = int(tr_part)
            trade = db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
        except Exception:
            pass

    if not trade and account:
        trade = db.query(TradeRecord).join(SetupSnapshot, SetupSnapshot.id == TradeRecord.setup_snapshot_id).filter(
            TradeRecord.account_id == account.id,
            TradeRecord.lifecycle_state == "ACTIVE",
            SetupSnapshot.instrument == req.instrument,
            TradeRecord.broker_ticket.is_(None)
        ).order_by(TradeRecord.id.desc()).first()

    if trade:
        if req.status == "FILLED":
            trade.broker_ticket = str(req.ticket_id)
            trade.actual_entry = req.fill_price
            trade.execution_status = "FILLED"
            trade.entry_timestamp = now
        else:
            trade.execution_status = "REJECTED"
            trade.lifecycle_state = "CLOSED"
            trade.exit_reason = req.error_comment or "BROKER_REJECTED"
            trade.exit_timestamp = now
            trade.outcome = "REJECTED"

    db.commit()
    logger.info(f"Reported EA fill for #{req.login} | Ticket: {req.ticket_id} | Status: {req.status}")
    return {"status": "SUCCESS", "signal_id": req.signal_id}


@router.post("/report-close")
def report_ea_close(
    req: EaCloseReportRequest,
    db: Session = Depends(get_db),
    authorized: bool = Depends(verify_ea_auth),
):
    """MQL5 EA reports back via OnTradeTransaction when a position closes (SL/TP/Manual)."""
    now = datetime.datetime.utcnow()

    # Find matching TradeRecord
    trade = db.query(TradeRecord).filter(TradeRecord.broker_ticket == req.ticket_id).first()
    if trade:
        trade.lifecycle_state = "CLOSED"
        trade.execution_status = "CLOSED"
        trade.exit_price = req.exit_price
        trade.exit_timestamp = now
        trade.exit_reason = req.exit_reason
        trade.realized_pnl = req.profit
        trade.outcome = "WIN" if req.profit > 0 else ("LOSS" if req.profit < 0 else "BE")

    # Complete any pending CLOSE orders in the queue
    close_orders = db.query(ExecutionOrderQueue).filter(
        ExecutionOrderQueue.ticket_id == req.ticket_id,
        ExecutionOrderQueue.action_type == "CLOSE",
        ExecutionOrderQueue.status.in_(["QUEUED", "DISPATCHED"])
    ).all()
    for co in close_orders:
        co.status = "FILLED"
        co.completed_at = now

    db.commit()
    logger.info(f"Reported EA position close for #{req.login} | Ticket: {req.ticket_id} | Reason: {req.exit_reason} | PnL: ${req.profit:.2f}")
    return {"status": "SUCCESS", "ticket_id": req.ticket_id}


@router.post("/heartbeat")
def report_ea_heartbeat(
    req: EaHeartbeatRequest,
    db: Session = Depends(get_db),
    authorized: bool = Depends(verify_ea_auth),
):
    """MQL5 EA sends balance, equity, margin heartbeat."""
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.login == req.login).first()
    if account:
        account.balance = req.balance
        account.last_heartbeat = datetime.datetime.utcnow()
        account.error_message = None
        db.commit()
    return {"status": "OK", "login": req.login}
