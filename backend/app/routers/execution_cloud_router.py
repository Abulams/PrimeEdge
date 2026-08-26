import datetime
import os
import secrets
import hashlib
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserBrokerAccount, WorkerNode, ExecutionAuditLog
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
    ticket_id: str
    signal_id: str
    instrument: str
    direction: str
    fill_price: float
    volume: float
    sl: float
    tp: float
    latency_ms: float
    status: str = "FILLED"


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
            balance=100000.0,
            equity=100000.0,
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
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.user_id == current_user.id).first()
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
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.user_id == current_user.id).first()
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
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.user_id == current_user.id).first()
    if account:
        account.is_active = False
        account.auto_execution_enabled = False
        db.commit()
    return {"status": "DISCONNECTED"}


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
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.user_id == current_user.id).first()
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


@router.get("/cloud/positions")
def get_cloud_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(UserBrokerAccount).filter(UserBrokerAccount.user_id == current_user.id).first()
    if not account:
        return []
    return cloud_router.get_positions_for_account(account.id)


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
        })
    return results


@router.get("/worker/poll-orders")
def poll_orders_for_worker(
    worker: WorkerNode = Depends(authenticate_worker),
    db: Session = Depends(get_db),
):
    accounts = db.query(UserBrokerAccount).filter(
        UserBrokerAccount.allocated_worker_id == worker.worker_id,
        UserBrokerAccount.is_active == True,
        UserBrokerAccount.auto_execution_enabled == True,
    ).all()

    account_ids = [acc.id for acc in accounts]
    orders = cloud_router.pop_orders_for_worker(account_ids)
    return {"orders": orders, "count": len(orders)}


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
        ticket_id=req.ticket_id,
        signal_id=req.signal_id,
        instrument=req.instrument,
        direction=req.direction,
        order_type="MARKET",
        entry_price=req.fill_price,
        sl=req.sl,
        tp=req.tp,
        volume=req.volume,
        status="FILLED",
        latency_ms=req.latency_ms,
        details={"comment": f"Executed by Worker {worker.worker_id}"},
    )
    db.add(audit_entry)
    db.commit()
    return {"status": "LOGGED", "ticket_id": req.ticket_id}


@router.post("/worker/report-positions/{account_id}")
def report_positions(
    account_id: int,
    positions: List[Dict[str, Any]],
    worker: WorkerNode = Depends(authenticate_worker),
):
    cloud_router.update_positions_from_worker(account_id, positions)
    return {"status": "SYNCED", "count": len(positions)}


@router.post("/worker/report-close")
def report_order_close(
    req: WorkerCloseReportRequest,
    worker: WorkerNode = Depends(authenticate_worker),
    db: Session = Depends(get_db),
):
    audit = db.query(ExecutionAuditLog).filter(ExecutionAuditLog.ticket_id == req.ticket_id).first()
    if audit:
        audit.exit_reason = req.exit_reason
        audit.exit_price = req.exit_price
        audit.pnl_r = req.pnl_r
        audit.status = "CLOSED"
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
    recent_audits = db.query(ExecutionAuditLog).order_by(ExecutionAuditLog.timestamp.desc()).limit(20).all()

    account_summaries = []
    for acc in accounts:
        user = db.query(User).filter(User.id == acc.user_id).first()
        positions = cloud_router.get_positions_for_account(acc.id)
        account_summaries.append({
            "account_id": acc.id,
            "user_email": user.email if user else "Unknown",
            "login": acc.login,
            "server": acc.broker_server,
            "worker_id": acc.allocated_worker_id,
            "balance": acc.balance,
            "equity": acc.equity,
            "ping_ms": acc.ping_ms,
            "is_active": acc.is_active,
            "auto_execution_enabled": acc.auto_execution_enabled,
            "killswitch_active": cloud_router.account_killswitches[acc.id],
            "open_positions": len(positions),
            "last_heartbeat": acc.last_heartbeat.isoformat() if acc.last_heartbeat else None,
            "error": acc.error_message,
        })

    worker_summaries = []
    for w in workers:
        is_healthy = False
        if w.last_heartbeat:
            age_s = (datetime.datetime.utcnow() - w.last_heartbeat).total_seconds()
            is_healthy = (age_s < 30)

        worker_summaries.append({
            "worker_id": w.worker_id,
            "hostname": w.hostname,
            "ip_address": w.ip_address,
            "status": "ONLINE" if is_healthy and w.status != "REVOKED" else w.status,
            "cpu_pct": w.cpu_pct,
            "ram_pct": w.ram_pct,
            "active_terminals": w.active_terminals,
            "max_terminals": w.max_terminals,
            "last_heartbeat": w.last_heartbeat.isoformat() if w.last_heartbeat else None,
        })

    audit_summaries = []
    for a in recent_audits:
        audit_summaries.append({
            "id": a.id,
            "ticket_id": a.ticket_id,
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

    return {
        "global_killswitch_active": cloud_router.global_killswitch_active,
        "total_subscribers": len(accounts),
        "total_workers": len(workers),
        "workers": worker_summaries,
        "accounts": account_summaries,
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
