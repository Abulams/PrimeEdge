import datetime
import os
import secrets
import hashlib
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Header, status, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserBrokerAccount, WorkerNode, ExecutionAuditLog, TradeRecord, SetupSnapshot, WaitlistLead, ExecutionOrderQueue
from ..journal_service import JournalService
from ..auth import get_current_user, get_current_admin
from ..execution.base import ExecutionOrder, OrderDirection, OrderType, PlatformType
from ..execution.crypto import encrypt_credential, decrypt_credential, mask_credential
from ..execution.cloud_router import CloudExecutionRouter

router = APIRouter(prefix="/api/v1/execution", tags=["cloud_execution"])
cloud_router = CloudExecutionRouter()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ConnectCloudMT5Request(BaseModel):
    broker_server: str
    login: int
    password: str
    platform_type: str = "MT5_CLOUD"


class ToggleAutoExecRequest(BaseModel):
    enabled: bool


class WorkerProvisionRequest(BaseModel):
    worker_id: str
    hostname: str
    max_capacity: int = 10


class WorkerHeartbeatRequest(BaseModel):
    worker_id: str
    cpu_pct: float
    ram_pct: float
    active_terminals: int
    terminal_statuses: Dict[str, Dict[str, Any]]  # account_id -> {status, ping_ms, equity, balance}


class WorkerFillReportRequest(BaseModel):
    account_id: int
    ticket_id: Optional[str] = None   # None when order was REJECTED before a ticket was assigned
    signal_id: str
    instrument: str
    direction: str
    fill_price: float
    volume: float
    sl: float
    tp: float
    latency_ms: float
    status: str = "FILLED"            # "FILLED" or "REJECTED"
    error_comment: Optional[str] = None
    retcode: Optional[int] = None


class WorkerCloseReportRequest(BaseModel):
    account_id: int
    ticket_id: str
    exit_reason: str
    exit_price: float
    pnl_r: float
    pnl_currency: float = 0.0


# ---------------------------------------------------------------------------
# Individual Worker Auth Dependency
# ---------------------------------------------------------------------------
def authenticate_worker(
    x_worker_id: Optional[str] = Header(None),
    x_worker_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> WorkerNode:
    if not x_worker_id or not x_worker_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing worker identification headers")

    worker = db.query(WorkerNode).filter(WorkerNode.worker_id == x_worker_id).first()
    if not worker:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown worker node")

    # Verify individual hashed worker key
    if getattr(worker, "key_hash", None):
        if hash_token(x_worker_key) != worker.key_hash:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid worker authentication credential")

    if worker.status == "REVOKED":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Worker credentials revoked")

    return worker


# ---------------------------------------------------------------------------
# 1. SUBSCRIBER ZERO-INSTALL CLOUD ENDPOINTS
# ---------------------------------------------------------------------------

def get_primary_user_account(db: Session, user_id: int) -> Optional[UserBrokerAccount]:
    """Retrieve the primary broker account for a user, prioritizing cTrader and active accounts."""
    return (
        db.query(UserBrokerAccount)
        .filter(UserBrokerAccount.user_id == user_id)
        .order_by(
            (UserBrokerAccount.platform == "ctrader").desc(),
            UserBrokerAccount.is_active.desc(),
            UserBrokerAccount.id.desc(),
        )
        .first()
    )


@router.post("/cloud/connect")
def connect_cloud_account(
    req: ConnectCloudMT5Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Subscriber connects MT5 broker account.
    Auto-assigned to least-loaded active Windows VPS worker based on capacity.
    """
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.user_id == current_user.id).first()

    # Dynamic Worker Routing: find online worker with lowest active_terminals/max_terminals ratio
    workers = db.query(WorkerNode).filter(WorkerNode.status == "ONLINE").all()
    available_worker = None
    if workers:
        available_worker = min(workers, key=lambda w: (w.active_terminals / max(1, w.max_terminals)))

    allocated_worker_id = available_worker.worker_id if available_worker else "vps-lon-worker-1"
    encrypted_pw = encrypt_credential(req.password)

    if not account:
        account = UserBrokerAccount(
            user_id=current_user.id,
            broker_server=req.broker_server.strip(),
            login=req.login,
            encrypted_password=encrypted_pw,
            platform_type=req.platform_type,
            is_active=True,
            auto_execution_enabled=True,
            allocated_worker_id=allocated_worker_id,
            balance=0.0,
            equity=0.0,
            currency="USD",
            leverage=100,
            ping_ms=3.8,
            last_heartbeat=datetime.datetime.utcnow(),
        )
        db.add(account)
    else:
        account.broker_server = req.broker_server.strip()
        account.login = req.login
        account.encrypted_password = encrypted_pw
        account.is_active = True
        account.allocated_worker_id = allocated_worker_id
        account.error_message = None

    db.commit()
    db.refresh(account)

    return {
        "status": "CONNECTED",
        "account_id": account.id,
        "login": account.login,
        "server": account.broker_server,
        "auto_execution_enabled": account.auto_execution_enabled,
        "allocated_worker": account.allocated_worker_id,
        "balance": account.balance,
        "equity": account.equity,
        "ping_ms": account.ping_ms,
    }


@router.get("/cloud/status")
def get_cloud_account_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_primary_user_account(db, current_user.id)
    if not account or not account.is_active:
        return {
            "connected": False,
            "auto_execution_enabled": False,
            "account_info": {},
            "open_positions_count": 0,
            "guardrail_config": {
                "max_spread_pips": 2.5,
                "max_slippage_pips": 1.5,
                "early_invalidation_mae_r": -0.35,
                "mfe_disarm_r": 0.35
            }
        }

    positions = cloud_router.get_positions_for_account(account.id)
    return {
        "connected": account.is_active,
        "account_id": account.id,
        "auto_execution_enabled": account.auto_execution_enabled and cloud_router.is_execution_allowed(account.id),
        "account_info": {
            "login": account.login,
            "server": account.broker_server,
            "platform": account.platform or "ctrader",
            "balance": account.balance,
            "equity": account.equity,
            "currency": account.currency,
            "leverage": account.leverage,
            "ping_ms": account.ping_ms,
            "allocated_worker": account.allocated_worker_id,
            "last_heartbeat": account.last_heartbeat.isoformat() if account.last_heartbeat else None,
        },
        "open_positions_count": len(positions),
        "guardrail_config": {
            "max_spread_pips": 2.5,
            "max_slippage_pips": 1.5,
            "early_invalidation_mae_r": -0.35,
            "mfe_disarm_r": 0.35
        }
    }


@router.post("/cloud/toggle-auto")
def toggle_cloud_auto_execution(
    req: ToggleAutoExecRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_primary_user_account(db, current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="No connected broker account found")

    account.auto_execution_enabled = req.enabled
    db.commit()
    return {"status": "SUCCESS", "auto_execution_enabled": account.auto_execution_enabled}


@router.post("/cloud/disconnect")
def disconnect_cloud_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_primary_user_account(db, current_user.id)
    if account:
        account.is_active = False
        account.auto_execution_enabled = False
        db.commit()
    return {"status": "DISCONNECTED"}


class UpdatePreferencesRequest(BaseModel):
    risk_mode: Optional[str] = "DYNAMIC_RISK_PCT"  # "FIXED_LOT" or "DYNAMIC_RISK_PCT"
    risk_pct: Optional[float] = 1.0
    fixed_lot_size: Optional[float] = 0.01
    allowed_instruments: Optional[List[str]] = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US100", "USDCHF"]
    max_concurrent_trades: Optional[int] = 3
    max_daily_loss_pct: Optional[float] = 3.0


@router.get("/cloud/preferences")
def get_user_execution_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_primary_user_account(db, current_user.id)
    if not account:
        return {
            "risk_mode": "DYNAMIC_RISK_PCT",
            "risk_pct": 1.0,
            "fixed_lot_size": 0.01,
            "allowed_instruments": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US100", "USDCHF"],
            "max_concurrent_trades": 3,
            "max_daily_loss_pct": 3.0,
        }

    return {
        "risk_mode": account.risk_mode or "DYNAMIC_RISK_PCT",
        "risk_pct": account.risk_pct or 1.0,
        "fixed_lot_size": account.fixed_lot_size or 0.01,
        "allowed_instruments": account.allowed_instruments if isinstance(account.allowed_instruments, list) else ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US100", "USDCHF"],
        "max_concurrent_trades": account.max_concurrent_trades or 3,
        "max_daily_loss_pct": account.max_daily_loss_pct or 3.0,
    }


@router.post("/cloud/preferences")
def update_user_execution_preferences(
    req: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_primary_user_account(db, current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="No active broker account found to configure preferences")

    if req.risk_mode:
        account.risk_mode = req.risk_mode
    if req.risk_pct is not None:
        account.risk_pct = max(0.1, min(5.0, req.risk_pct))
    if req.fixed_lot_size is not None:
        account.fixed_lot_size = max(0.01, min(10.0, req.fixed_lot_size))
    if req.allowed_instruments is not None:
        account.allowed_instruments = [sym.upper() for sym in req.allowed_instruments]
    if req.max_concurrent_trades is not None:
        account.max_concurrent_trades = max(1, min(10, req.max_concurrent_trades))
    if req.max_daily_loss_pct is not None:
        account.max_daily_loss_pct = max(0.5, min(15.0, req.max_daily_loss_pct))

    db.commit()
    db.refresh(account)

    return {
        "status": "UPDATED",
        "preferences": {
            "risk_mode": account.risk_mode,
            "risk_pct": account.risk_pct,
            "fixed_lot_size": account.fixed_lot_size,
            "allowed_instruments": account.allowed_instruments,
            "max_concurrent_trades": account.max_concurrent_trades,
            "max_daily_loss_pct": account.max_daily_loss_pct,
        }
    }


class ForceTestTradeRequest(BaseModel):
    instrument: str = "EURUSD"
    direction: str = "LONG"
    volume: float = 0.01


@router.post("/cloud/force-test-trade")
def force_test_trade(
    req: ForceTestTradeRequest = Body(default=ForceTestTradeRequest()),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Forces an immediate test trade through the 24/7 Cloud MT5 Bridge.
    Validates end-to-end routing, order reception, and broker fill confirmation.
    """
    import time
    try:
        account = get_primary_user_account(db, current_user.id)
        if not account:
            account = db.query(UserBrokerAccount).first()
        account_id = account.id if account else 1

        dir_enum = OrderDirection.LONG if req.direction.upper() == "LONG" else OrderDirection.SHORT
        test_order = ExecutionOrder(
            signal_id=f"TEST-MANUAL-{int(time.time())}",
            instrument=req.instrument.upper(),
            direction=dir_enum,
            order_type=OrderType.MARKET,
            entry_reference_price=1.0850 if "EUR" in req.instrument else 1.2550,
            stop_loss=1.0800 if "EUR" in req.instrument else 1.2500,
            take_profit=1.0950 if "EUR" in req.instrument else 1.2650,
            risk_r_pips=50.0,
            position_size_lots=req.volume,
            risk_pct=1.0,
            account_balance=100000.0,
        )

        res = cloud_router.queue_order_for_account(account_id=account_id, order=test_order)
        return {
            "status": "DISPATCHED",
            "message": f"Test trade for {req.instrument} {req.direction} ({req.volume} lots) queued for London MT5 Cloud Worker.",
            "order": test_order.dict(),
            "router_result": res,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to dispatch test trade: {str(e)}")


@router.get("/cloud/positions")
def get_cloud_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_primary_user_account(db, current_user.id)
    if not account:
        return []

    from ..models import TradeRecord, SetupSnapshot
    from ..realtime import realtime_service

    # Query active trades for this account
    active_trades = (
        db.query(TradeRecord)
        .join(SetupSnapshot, TradeRecord.setup_snapshot_id == SetupSnapshot.id)
        .filter(
            TradeRecord.account_id == account.id,
            TradeRecord.lifecycle_state == "ACTIVE"
        )
        .order_by(TradeRecord.created_at.desc())
        .all()
    )

    positions = []
    quotes = getattr(realtime_service, "current_quotes", {}) or {}

    for t in active_trades:
        inst = t.setup.instrument if t.setup else "XAUUSD"
        direction = t.setup.direction if t.setup else "LONG"
        pip_mult = 100.0 if "JPY" in inst else (10.0 if "XAU" in inst else 10000.0)

        # Get current price
        curr_price = quotes.get(inst, {}).get("price") or t.actual_entry or 1.0

        # Calculate live pnl pips
        if direction == "LONG":
            pnl_pips = round((curr_price - (t.actual_entry or curr_price)) * pip_mult, 1)
        else:
            pnl_pips = round(((t.actual_entry or curr_price) - curr_price) * pip_mult, 1)

        positions.append({
            "ticket_id": t.broker_ticket or f"TR-{t.id}",
            "trade_id": t.id,
            "instrument": inst,
            "direction": direction,
            "position_size_lots": t.position_size_lots or 0.01,
            "open_price": round(t.actual_entry or 0.0, 5),
            "current_price": round(curr_price, 5),
            "stop_loss": round(t.actual_sl or 0.0, 5),
            "take_profit": round(t.actual_tp or 0.0, 5),
            "current_pnl_pips": pnl_pips,
            "max_mae_pips": round(t.max_mae_pips or 0.0, 1),
            "max_mfe_pips": round(t.max_mfe_pips or 0.0, 1),
            "early_inval_armed": True if (t.max_mfe_pips or 0.0) < 15.0 else False,
            "entry_time": t.entry_timestamp.isoformat() if t.entry_timestamp else t.created_at.isoformat()
        })

    # Fallback to router positions if no DB trades
    if not positions:
        router_pos = cloud_router.get_positions_for_account(account.id)
        if router_pos:
            return router_pos

    return positions


@router.get("/cloud/history")
def get_cloud_execution_history(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_primary_user_account(db, current_user.id)
    if not account:
        return []

    from ..models import TradeRecord, SetupSnapshot

    closed_trades = (
        db.query(TradeRecord)
        .join(SetupSnapshot, TradeRecord.setup_snapshot_id == SetupSnapshot.id)
        .filter(
            TradeRecord.account_id == account.id,
            TradeRecord.lifecycle_state == "CLOSED"
        )
        .order_by(TradeRecord.updated_at.desc())
        .limit(limit)
        .all()
    )

    history = []
    for t in closed_trades:
        inst = t.setup.instrument if t.setup else "XAUUSD"
        direction = t.setup.direction if t.setup else "LONG"
        history.append({
            "id": t.id,
            "ticket_id": t.broker_ticket or f"TR-{t.id}",
            "instrument": inst,
            "direction": direction,
            "position_size_lots": t.position_size_lots or 0.01,
            "entry_price": round(t.actual_entry or 0.0, 5),
            "exit_price": round(t.exit_price or 0.0, 5) if t.exit_price else None,
            "exit_reason": t.exit_reason or "CLOSED",
            "outcome": t.outcome or ("WIN" if (t.pnl_pips or 0) > 0 else "LOSS" if (t.pnl_pips or 0) < 0 else "BE"),
            "pnl_pips": round(t.pnl_pips or 0.0, 1) if t.pnl_pips is not None else 0.0,
            "pnl_r": round(t.pnl_r or 0.0, 2) if t.pnl_r is not None else 0.0,
            "entry_time": t.entry_timestamp.isoformat() if t.entry_timestamp else t.created_at.isoformat(),
            "exit_time": t.exit_timestamp.isoformat() if t.exit_timestamp else t.updated_at.isoformat(),
        })

    return history


# ---------------------------------------------------------------------------
# 2. DYNAMIC WORKER ENDPOINTS (Individually Authenticated)
# ---------------------------------------------------------------------------

@router.post("/worker/heartbeat")
def worker_heartbeat(
    req: WorkerHeartbeatRequest,
    worker: WorkerNode = Depends(authenticate_worker),
    db: Session = Depends(get_db),
):
    worker.cpu_pct = req.cpu_pct
    worker.ram_pct = req.ram_pct
    worker.active_terminals = req.active_terminals
    worker.status = "ONLINE"
    worker.last_heartbeat = datetime.datetime.utcnow()

    for acc_str_id, t_status in req.terminal_statuses.items():
        try:
            acc_id = int(acc_str_id)
            account = db.query(UserBrokerAccount).filter(UserBrokerAccount.id == acc_id).first()
            if account:
                account.balance = t_status.get("balance", account.balance)
                account.equity = t_status.get("equity", account.equity)
                account.ping_ms = t_status.get("ping_ms", account.ping_ms)
                account.last_heartbeat = datetime.datetime.utcnow()
                if "error" in t_status:
                    account.error_message = t_status["error"]
        except Exception:
            pass

    db.commit()
    return {"status": "ACK", "global_killswitch": cloud_router.global_killswitch_active}


@router.get("/worker/accounts")
def get_assigned_accounts_for_worker(
    worker: WorkerNode = Depends(authenticate_worker),
    db: Session = Depends(get_db),
):
    accounts = db.query(UserBrokerAccount).filter(
        UserBrokerAccount.allocated_worker_id == worker.worker_id,
        UserBrokerAccount.is_active == True,
    ).all()

    results = []
    for acc in accounts:
        decrypted_pw = decrypt_credential(acc.encrypted_password)
        results.append({
            "account_id": acc.id,
            "user_id": acc.user_id,
            "login": acc.login,
            "password": decrypted_pw,
            "server": acc.broker_server,
            "auto_execution_enabled": acc.auto_execution_enabled and cloud_router.is_execution_allowed(acc.id),
            "risk_mode": acc.risk_mode or "DYNAMIC_RISK_PCT",
            "risk_pct": acc.risk_pct or 1.0,
            "fixed_lot_size": acc.fixed_lot_size or 0.01,
            "allowed_instruments": acc.allowed_instruments if isinstance(acc.allowed_instruments, list) else ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US100", "USDCHF"],
            "max_concurrent_trades": acc.max_concurrent_trades or 3,
            "max_daily_loss_pct": acc.max_daily_loss_pct or 3.0,
        })
    return results


@router.get("/worker/poll-orders")
def poll_orders_for_worker(
    account_id: Optional[int] = None,
    worker: WorkerNode = Depends(authenticate_worker),
    db: Session = Depends(get_db),
):
    if account_id:
        target_ids = [account_id]
    else:
        accounts = db.query(UserBrokerAccount).filter(
            UserBrokerAccount.is_active == True,
            UserBrokerAccount.auto_execution_enabled == True,
        ).all()
        target_ids = [acc.id for acc in accounts]

    allowed_ids = [aid for aid in target_ids if cloud_router.is_execution_allowed(aid)]
    if not allowed_ids:
        return {"orders": [], "count": 0}

    now = datetime.datetime.utcnow()

    # 1. Lease recovery: if an order has been stuck in DISPATCHED for > 120s with no fill report, recover or expire it
    stale_lease = now - datetime.timedelta(seconds=120)
    stuck_orders = db.query(ExecutionOrderQueue).filter(
        ExecutionOrderQueue.account_id.in_(allowed_ids),
        ExecutionOrderQueue.status == "DISPATCHED",
        ExecutionOrderQueue.dispatched_at < stale_lease
    ).all()
    for stuck in stuck_orders:
        if (now - stuck.created_at).total_seconds() > 300:
            stuck.status = "EXPIRED"
            stuck.completed_at = now
            if stuck.trade_id:
                stuck_trade = db.query(TradeRecord).filter(TradeRecord.id == stuck.trade_id).first()
                if stuck_trade and stuck_trade.execution_status == "QUEUED":
                    stuck_trade.execution_status = "EXPIRED"
                    stuck_trade.lifecycle_state = "CANCELLED"
                    stuck_trade.notes = "Order lease expired after 300s without worker fill"
        else:
            stuck.status = "QUEUED"

    # 2. Fetch all durable QUEUED orders for these allowed accounts
    queued_orders = db.query(ExecutionOrderQueue).filter(
        ExecutionOrderQueue.account_id.in_(allowed_ids),
        ExecutionOrderQueue.status == "QUEUED"
    ).order_by(ExecutionOrderQueue.id.asc()).all()

    orders_to_dispatch = []
    for o in queued_orders:
        orders_to_dispatch.append({
            "action_type": o.action_type,
            "ticket_id": o.ticket_id,
            "signal_id": o.signal_id,
            "instrument": o.instrument,
            "direction": o.direction,
            "order_type": o.order_type,
            "entry_reference_price": o.entry_reference_price,
            "stop_loss": o.stop_loss,
            "take_profit": o.take_profit,
            "position_size_lots": o.position_size_lots,
            "risk_pct": o.risk_pct,
            "account_id": o.account_id,
            "account_balance": o.account_balance,
            "queued_at": o.created_at.isoformat() if o.created_at else now.isoformat()
        })
        o.status = "DISPATCHED"
        o.dispatched_at = now

    if queued_orders or stuck_orders:
        db.commit()

    return {"orders": orders_to_dispatch, "count": len(orders_to_dispatch)}


@router.post("/worker/report-fill")
def report_order_fill(
    req: WorkerFillReportRequest,
    worker: WorkerNode = Depends(authenticate_worker),
    db: Session = Depends(get_db),
):
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.id == req.account_id).first()
    user_id = account.user_id if account else 1

    audit_entry = ExecutionAuditLog(
        user_id=user_id,
        worker_id=worker.worker_id,
        ticket_id=req.ticket_id or "NONE",
        signal_id=req.signal_id,
        instrument=req.instrument,
        direction=req.direction,
        order_type="MARKET",
        entry_price=req.fill_price,
        sl=req.sl,
        tp=req.tp,
        volume=req.volume,
        status="FILLED" if req.status == "FILLED" else "REJECTED",
        latency_ms=req.latency_ms,
        details={"comment": f"Executed by Worker {worker.worker_id}"},
    )
    db.add(audit_entry)

    # 1. Update Durable Outbox Queue record
    queue_order = db.query(ExecutionOrderQueue).filter(ExecutionOrderQueue.signal_id == req.signal_id).first()
    if queue_order:
        queue_order.completed_at = datetime.datetime.utcnow()
        if req.status == "FILLED":
            queue_order.status = "FILLED"
            queue_order.ticket_id = str(req.ticket_id)
        else:
            queue_order.status = "REJECTED"
            queue_order.error_comment = getattr(req, "error_comment", None)
            queue_order.retcode = getattr(req, "retcode", None)

    # 2. Synchronize real MT5 ticket ID and actual fill price with TradeRecord in Auto Journal
    trade = None
    if "-TR-" in req.signal_id:
        try:
            tr_part = req.signal_id.split("-TR-")[1].split("-")[0]
            trade_id = int(tr_part)
            trade = db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
        except Exception:
            trade = None

    if not trade and req.account_id:
        trade = db.query(TradeRecord).join(SetupSnapshot, SetupSnapshot.id == TradeRecord.setup_snapshot_id).filter(
            TradeRecord.account_id == req.account_id,
            TradeRecord.lifecycle_state == "ACTIVE",
            SetupSnapshot.instrument == req.instrument,
            TradeRecord.broker_ticket.is_(None)
        ).order_by(TradeRecord.id.desc()).first()

    # Link audit entry to trade for complete traceability
    if trade:
        audit_entry.trade_id = trade.id
    elif queue_order and queue_order.trade_id:
        # Fallback: use trade_id from queue order if direct lookup failed
        audit_entry.trade_id = queue_order.trade_id

    # ── REJECTION PATH ─────────────────────────────────────────────────
    if req.status == "REJECTED":
        if trade:
            trade.execution_status = "REJECTED"
            trade.lifecycle_state = "CLOSED"
            trade.exit_reason = "BROKER_REJECTED"
            trade.exit_timestamp = datetime.datetime.utcnow()
            trade.outcome = "REJECTED"
        audit_entry.status = "REJECTED"
        db.commit()
        return {"status": "REJECTION_LOGGED", "signal_id": req.signal_id}

    # ── FILL PATH ──────────────────────────────────────────────────────
    if trade:
        trade.broker_ticket = str(req.ticket_id)
        trade.actual_entry = req.fill_price
        trade.execution_status = "FILLED"
        trade.entry_timestamp = datetime.datetime.utcnow()

    db.commit()

    # Store in active positions list for instant UI display
    pos_entry = {
        "ticket_id": req.ticket_id,
        "platform": "MT5_CLOUD",
        "instrument": req.instrument,
        "direction": req.direction,
        "open_price": req.fill_price,
        "current_price": req.fill_price,
        "stop_loss": req.sl,
        "take_profit": req.tp,
        "position_size_lots": req.volume,
        "max_mae_pips": 0.0,
        "max_mfe_pips": 0.0,
        "current_pnl_pips": 0.0,
        "current_pnl_r": 0.0,
        "early_inval_armed": True,
        "early_inval_pips": 7.0,
        "mfe_disarm_pips": 7.0,
        "open_time": datetime.datetime.utcnow().isoformat(),
        "comment": f"Executed by London Worker {worker.worker_id}"
    }

    # Add or update position
    existing = [p for p in cloud_router.active_positions[req.account_id] if p.get("ticket_id") != req.ticket_id]
    existing.append(pos_entry)
    cloud_router.active_positions[req.account_id] = existing

    return {"status": "LOGGED", "ticket_id": req.ticket_id}


@router.post("/worker/report-positions/{account_id}")
def report_positions(
    account_id: int,
    payload: Union[List[Dict[str, Any]], Dict[str, Any]] = Body(...),
    worker: WorkerNode = Depends(authenticate_worker),
    db: Session = Depends(get_db),
):
    if isinstance(payload, dict):
        positions = payload.get("positions", [])
        balance = payload.get("balance")
        equity = payload.get("equity")
        ping_ms = payload.get("ping_ms")
    else:
        positions = payload
        balance = None
        equity = None
        ping_ms = None

    # Update account live balance, equity, and heartbeat in database
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.id == account_id).first()
    if account:
        if balance is not None and float(balance) > 0.0:
            account.balance = float(balance)
        if equity is not None and float(equity) > 0.0:
            account.equity = float(equity)
        if ping_ms is not None:
            account.ping_ms = float(ping_ms)
        account.last_heartbeat = datetime.datetime.utcnow()
        if isinstance(payload, dict) and payload.get("error"):
            account.error_message = str(payload["error"])
        elif balance is not None:
            account.error_message = None

    cloud_router.update_positions_from_worker(account_id, positions)

    # Closed-loop live reconciliation with database TradeRecords
    active_mt5_tickets = {str(p.get("ticket_id")) for p in positions if p.get("ticket_id")}

    # Update live MAE/MFE/PnL from MT5 ticks directly into TradeRecords
    for p in positions:
        t_id = str(p.get("ticket_id"))
        if not t_id:
            continue
        trade = db.query(TradeRecord).filter(
            TradeRecord.broker_ticket == t_id,
            TradeRecord.lifecycle_state == "ACTIVE"
        ).first()
        if trade:
            trade.max_mae_pips = max(trade.max_mae_pips or 0.0, float(p.get("max_mae_pips", 0.0)))
            trade.max_mfe_pips = max(trade.max_mfe_pips or 0.0, float(p.get("max_mfe_pips", 0.0)))
            trade.pnl_pips = float(p.get("current_pnl_pips", trade.pnl_pips or 0.0))
            # Calculate floating R-multiple so active trades in Auto-Journal show live R
            setup = trade.setup
            if setup:
                from ..journal_service import get_pip_multiplier
                pip_mult = get_pip_multiplier(setup.instrument)
                entry = trade.actual_entry or setup.setup_ref_price
                risk_dist = abs(entry - trade.actual_sl) if trade.actual_sl else (setup.mae_p90_pips / pip_mult if setup.mae_p90_pips else 0.0020)
                risk_pips = max(1.0, risk_dist * pip_mult)
                trade.pnl_r = round(trade.pnl_pips / risk_pips, 2)

    db.commit()
    return {"status": "SYNCED", "count": len(positions)}


@router.post("/worker/report-close")
def report_order_close(
    req: WorkerCloseReportRequest,
    worker: WorkerNode = Depends(authenticate_worker),
    db: Session = Depends(get_db),
):
    # 1. Update ExecutionAuditLog
    audit = db.query(ExecutionAuditLog).filter(ExecutionAuditLog.ticket_id == req.ticket_id).first()
    if audit:
        audit.exit_reason = req.exit_reason
        audit.exit_price = req.exit_price
        audit.pnl_r = req.pnl_r
        audit.status = "CLOSED"

    # 2. Update TradeRecord in AutoJournal!
    # Check for active trade, or recently closed trade (to overwrite any race-condition placeholders)
    trade = db.query(TradeRecord).filter(
        TradeRecord.broker_ticket == str(req.ticket_id),
        TradeRecord.lifecycle_state == "ACTIVE"
    ).first()

    if not trade:
        trade = db.query(TradeRecord).filter(
            TradeRecord.broker_ticket == str(req.ticket_id),
            TradeRecord.lifecycle_state == "CLOSED"
        ).order_by(TradeRecord.id.desc()).first()

    if trade:
        JournalService._finalize_trade(trade, exit_price=req.exit_price, exit_reason=req.exit_reason)
        if audit:
            audit.pnl_r = trade.pnl_r
            audit.exit_reason = trade.exit_reason
            audit.exit_price = trade.exit_price
            audit.trade_id = trade.id

    # 3. Clean up active positions cache in cloud router
    cloud_router.active_positions[req.account_id] = [
        p for p in cloud_router.active_positions.get(req.account_id, [])
        if str(p.get("ticket_id")) != str(req.ticket_id)
    ]

    db.commit()
    return {"status": "CLOSED_LOGGED", "ticket_id": req.ticket_id}


# ---------------------------------------------------------------------------
# 3. SOLO-FOUNDER ADMIN OPERATIONS CONSOLE ENDPOINTS
# ---------------------------------------------------------------------------

@router.post("/admin/workers/provision")
def provision_new_worker(
    req: WorkerProvisionRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Provisions a new worker node and generates an individual secure API key."""
    raw_key = f"wkey_{secrets.token_hex(24)}"
    key_hash = hash_token(raw_key)

    worker = db.query(WorkerNode).filter(WorkerNode.worker_id == req.worker_id).first()
    if not worker:
        worker = WorkerNode(
            worker_id=req.worker_id,
            hostname=req.hostname,
            max_terminals=req.max_capacity,
            status="ONLINE",
            last_heartbeat=datetime.datetime.utcnow(),
        )
        setattr(worker, "key_hash", key_hash)
        db.add(worker)
    else:
        worker.hostname = req.hostname
        worker.max_terminals = req.max_capacity
        worker.status = "ONLINE"
        setattr(worker, "key_hash", key_hash)

    db.commit()
    return {
        "status": "PROVISIONED",
        "worker_id": worker.worker_id,
        "worker_api_key": raw_key,  # Returned ONCE upon provisioning
        "message": "Save this worker API key securely. It will not be shown again."
    }


@router.post("/admin/workers/{worker_id}/revoke")
def revoke_worker(
    worker_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Instantly revokes a worker's authorization."""
    worker = db.query(WorkerNode).filter(WorkerNode.worker_id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    worker.status = "REVOKED"
    db.commit()
    return {"status": "REVOKED", "worker_id": worker.worker_id}


@router.get("/admin/operations")
def get_admin_operations_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    workers = db.query(WorkerNode).all()
    accounts = db.query(UserBrokerAccount).all()
    all_users = db.query(User).order_by(User.id.asc()).all()
    recent_audits = db.query(ExecutionAuditLog).order_by(ExecutionAuditLog.timestamp.desc()).limit(40).all()

    account_summaries = []
    for acc in accounts:
        user = db.query(User).filter(User.id == acc.user_id).first()
        positions = cloud_router.get_positions_for_account(acc.id)
        
        # Determine execution mode: LIVE_BROKER vs SANDBOX_SIMULATION
        # An account is LIVE_BROKER if it has ping_ms < 5000 and valid balance, otherwise SANDBOX_FALLBACK
        is_live_broker = (acc.ping_ms is not None and acc.ping_ms < 2000.0 and acc.balance > 0.0)
        mode_label = "LIVE_BROKER" if is_live_broker else "SANDBOX_FALLBACK"

        account_summaries.append({
            "account_id": acc.id,
            "user_id": acc.user_id,
            "user_email": user.email if user else "Unknown",
            "user_role": user.role if user else "trader",
            "login": acc.login,
            "server": acc.broker_server,
            "worker_id": acc.allocated_worker_id,
            "balance": acc.balance,
            "equity": acc.equity,
            "ping_ms": acc.ping_ms,
            "is_active": acc.is_active,
            "auto_execution_enabled": acc.auto_execution_enabled,
            "execution_mode": mode_label,
            "killswitch_active": cloud_router.account_killswitches[acc.id],
            "open_positions": len(positions),
            "allowed_instruments": acc.allowed_instruments,
            "risk_pct": acc.risk_pct,
            "fixed_lot_size": acc.fixed_lot_size,
            "last_heartbeat": acc.last_heartbeat.isoformat() if acc.last_heartbeat else None,
            "error": acc.error_message,
        })

    worker_summaries = []
    for w in workers:
        is_healthy = False
        if w.last_heartbeat:
            age_s = (datetime.datetime.utcnow() - w.last_heartbeat).total_seconds()
            is_healthy = (age_s < 120)

        worker_summaries.append({
            "worker_id": w.worker_id,
            "hostname": w.hostname,
            "ip_address": w.ip_address,
            "status": "ONLINE" if is_healthy and w.status != "REVOKED" else ("OFFLINE" if w.status == "ONLINE" else w.status),
            "cpu_pct": w.cpu_pct,
            "ram_pct": w.ram_pct,
            "active_terminals": w.active_terminals,
            "max_terminals": w.max_terminals,
            "last_heartbeat": w.last_heartbeat.isoformat() if w.last_heartbeat else None,
        })

    audit_summaries = []
    for a in recent_audits:
        is_sandbox = a.ticket_id.startswith("MT5-W-") if a.ticket_id else False
        audit_summaries.append({
            "id": a.id,
            "user_id": a.user_id,
            "ticket_id": a.ticket_id,
            "is_sandbox": is_sandbox,
            "signal_id": a.signal_id,
            "instrument": a.instrument,
            "direction": a.direction,
            "entry_price": a.entry_price,
            "exit_price": a.exit_price,
            "status": a.status,
            "exit_reason": a.exit_reason,
            "pnl_r": a.pnl_r,
            "latency_ms": a.latency_ms,
            "timestamp": a.timestamp.isoformat(),
        })

    user_summaries = []
    for u in all_users:
        has_acc = db.query(UserBrokerAccount).filter(UserBrokerAccount.user_id == u.id).first()
        user_summaries.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "has_broker_linked": bool(has_acc),
            "linked_login": has_acc.login if has_acc else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None,
        })

    return {
        "global_killswitch_active": cloud_router.global_killswitch_active,
        "total_users": len(all_users),
        "total_subscribers": len(accounts),
        "total_workers": len(workers),
        "workers": worker_summaries,
        "accounts": account_summaries,
        "users": user_summaries,
        "recent_audits": audit_summaries,
    }


@router.post("/admin/killswitch/global")
def toggle_admin_global_killswitch(
    req: ToggleAutoExecRequest,
    _: User = Depends(get_current_admin),
):
    res = cloud_router.toggle_global_killswitch(req.enabled)
    return {"status": "SUCCESS", "global_killswitch_active": res}


@router.post("/admin/killswitch/account/{account_id}")
def toggle_admin_account_killswitch(
    account_id: int,
    req: ToggleAutoExecRequest,
    _: User = Depends(get_current_admin),
):
    res = cloud_router.toggle_account_killswitch(account_id, req.enabled)
    return {"status": "SUCCESS", "account_id": account_id, "killswitch_active": res}


class AdminUserActionRequest(BaseModel):
    action: str  # "toggle_active", "toggle_admin", "delete"


@router.post("/admin/users/{user_id}/action")
def manage_user_account(
    user_id: int,
    req: AdminUserActionRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == current_admin.id and req.action in ["delete", "toggle_active"]:
        raise HTTPException(status_code=400, detail="Cannot disable or delete your own admin account.")

    if req.action == "toggle_active":
        target.is_active = not target.is_active
        db.commit()
        return {"status": "SUCCESS", "user_id": user_id, "is_active": target.is_active}

    elif req.action == "toggle_admin":
        target.is_admin = not target.is_admin
        target.role = "admin" if target.is_admin else "trader"
        db.commit()
        return {"status": "SUCCESS", "user_id": user_id, "is_admin": target.is_admin, "role": target.role}

    elif req.action == "delete":
        # Cascade delete broker account
        db.query(UserBrokerAccount).filter(UserBrokerAccount.user_id == user_id).delete()
        db.query(ExecutionAuditLog).filter(ExecutionAuditLog.user_id == user_id).delete()
        db.delete(target)
        db.commit()
        return {"status": "SUCCESS", "deleted_user_id": user_id}

    raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")


class AdminCreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = "Beta Trader"
    role: Optional[str] = "trader"


@router.post("/admin/users/create")
def admin_create_user(
    req: AdminCreateUserRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from ..auth import hash_password
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    is_adm = (req.role == "admin")
    user = User(
        email=req.email.lower(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=req.role,
        is_active=True,
        is_admin=is_adm,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "SUCCESS", "user_id": user.id, "email": user.email}


@router.post("/admin/flatten-fleet")
def emergency_flatten_fleet(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Emergency liquidate all open positions across all active broker accounts."""
    accounts = db.query(UserBrokerAccount).filter(UserBrokerAccount.is_active == True).all()
    closed_orders_count = 0

    for acc in accounts:
        positions = cloud_router.get_positions_for_account(acc.id)
        for pos in positions:
            ticket = pos.get("ticket_id")
            inst = pos.get("instrument", "EURUSD")
            if ticket:
                cloud_router.queue_close_order(acc.id, str(ticket), inst, reason="EMERGENCY_ADMIN_FLATTEN")
                closed_orders_count += 1

    return {"status": "SUCCESS", "liquidated_positions_queued": closed_orders_count}
 
 
@router.get("/admin/waitlist")
def get_admin_waitlist_leads(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Fetch all waitlist applicants for founder review and cohort selection."""
    leads = db.query(WaitlistLead).order_by(WaitlistLead.created_at.desc()).all()
    return [
        {
            "id": l.id,
            "full_name": l.full_name,
            "email": l.email,
            "broker_platform": l.broker_platform or "MT5",
            "contact_method": l.contact_method or "Email",
            "why_interested": l.why_interested or "",
            "consent_given": l.consent_given,
            "status": l.status or "PENDING",
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in leads
    ]


@router.post("/admin/waitlist/{lead_id}/approve")
def approve_waitlist_lead(
    lead_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Approve a waitlist lead, mark as INVITED, and send their activation email with invite token."""
    lead = db.query(WaitlistLead).filter(WaitlistLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Waitlist lead not found")

    from ..auth import create_invite_token
    from ..email_service import send_applicant_invite_email

    invite_token = create_invite_token(lead.email, lead.full_name)
    email_sent = False
    try:
        email_sent = send_applicant_invite_email(
            full_name=lead.full_name,
            email=lead.email,
            invite_token=invite_token,
            spot_number=lead.id,
        )
    except Exception as err:
        logger.error(f"Error sending invite email to {lead.email}: {err}")

    lead.status = "INVITED"
    db.commit()
    return {
        "status": "SUCCESS",
        "message": f"Invitation email sent to {lead.email}" if email_sent else f"Lead marked as INVITED (email send failed or pending)",
        "lead_id": lead.id,
        "email_sent": email_sent,
        "activation_url": f"https://primeedge.app/activate?token={invite_token}"
    }


@router.delete("/admin/waitlist/{lead_id}")
def delete_waitlist_lead(
    lead_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a spam or test waitlist submission."""
    lead = db.query(WaitlistLead).filter(WaitlistLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Waitlist lead not found")
    db.delete(lead)
    db.commit()
    return {"status": "SUCCESS", "message": "Lead deleted"}

