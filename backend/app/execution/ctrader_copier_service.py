"""
ctrader_copier_service.py — PrimeEdge Trade Copier (cTrader OpenAPI v2)
========================================================================
Background service running on Linode that monitors the master account and
copies every execution to all active copier client accounts, enforcing each
client's guardrails as configured in UserBrokerAccount.

Position mapping:
    self.position_map[master_position_id] = [client_position_id, ...]
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from .ctrader_gateway import (
    CTraderGateway,
    CTraderOrderError,
    CTraderAuthError,
    CTraderConnectionError,
)

from app.models import UserBrokerAccount, TradeRecord, ExecutionAuditLog

logger = logging.getLogger("ctrader_copier")

# ProtoOAExecutionType enum values (int)
EXECUTION_TYPE_ORDER_FILLED = 2   # DEAL_ACCEPTED / position opened
EXECUTION_TYPE_ORDER_CANCELLED = 3
EXECUTION_TYPE_POSITION_OPENED = 4
EXECUTION_TYPE_POSITION_ROLL_OVER = 5
EXECUTION_TYPE_POSITION_CLOSED = 6
EXECUTION_TYPE_ORDER_PARTIAL_FILL = 7

RECONNECT_DELAY_SECONDS = 30


class CTraderCopierService:
    """
    Trade copier service for cTrader OpenAPI.

    Lifecycle:
        service = CTraderCopierService(db_session_factory, gateway)
        await service.start(master_account_id, master_access_token)
        ...
        await service.stop()
    """

    def __init__(self, db_session_factory, gateway: CTraderGateway):
        """
        Args:
            db_session_factory: Callable that returns a SQLAlchemy Session (e.g. SessionLocal).
            gateway:            CTraderGateway instance.
        """
        self._db_session_factory = db_session_factory
        self._gateway = gateway

        self._master_account_id: Optional[int] = None
        self._master_access_token: Optional[str] = None

        # master_position_id -> list of {"client_account_id", "client_position_id", "volume"}
        self.position_map: Dict[int, List[Dict[str, Any]]] = {}

        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Symbol name -> symbol_id cache
        self._symbol_cache: Dict[str, int] = {}

    def _get_db(self):
        """Context manager returning a database session."""
        return self._db_session_factory()

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    async def start(self, master_account_id: int, master_access_token: str) -> None:
        """
        Connect gateway, authorise master account, subscribe to execution events,
        and start background copy loop.
        """
        self._master_account_id = master_account_id
        self._master_access_token = master_access_token
        self._running = True

        await self._connect_and_authorise()

        logger.info(
            "CTraderCopierService started. Monitoring master account %s",
            master_account_id,
        )

        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Gracefully stop the copier service."""
        logger.info("Stopping CTraderCopierService...")
        self._running = False

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        await self._gateway.disconnect()
        logger.info("CTraderCopierService stopped.")

    # ------------------------------------------------------------------
    # Internal connection helpers
    # ------------------------------------------------------------------

    async def _connect_and_authorise(self) -> None:
        await self._gateway.connect()
        await self._gateway.authorize_account(
            self._master_account_id, self._master_access_token
        )
        await self._gateway.subscribe_to_execution_events(
            self._master_account_id, self._on_master_execution
        )
        logger.info("Gateway connected and master account authorised.")

    async def _monitor_loop(self) -> None:
        while self._running:
            await asyncio.sleep(10)
            if not getattr(self._gateway, "_connected", False) and self._running:
                logger.warning(
                    "Gateway disconnected. Reconnecting in %ss...",
                    RECONNECT_DELAY_SECONDS,
                )
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                try:
                    await self._connect_and_authorise()
                    logger.info("Reconnection successful.")
                except (CTraderConnectionError, CTraderAuthError) as exc:
                    logger.error("Reconnection failed: %s. Will retry.", exc)

    # ------------------------------------------------------------------
    # Master execution event handler
    # ------------------------------------------------------------------

    async def _on_master_execution(self, event) -> None:
        exec_type = event.executionType
        logger.debug(
            "Master execution event: type=%s account=%s",
            exec_type, self._master_account_id,
        )

        if exec_type in (EXECUTION_TYPE_POSITION_OPENED, EXECUTION_TYPE_ORDER_FILLED):
            if event.HasField("position"):
                await self._handle_position_open(event)

        elif exec_type == EXECUTION_TYPE_POSITION_CLOSED:
            if event.HasField("position"):
                master_pos_id = event.position.positionId
                await self._handle_position_close(master_pos_id)

    async def _handle_position_open(self, event) -> None:
        position = event.position
        td = position.tradeData
        master_pos_id = position.positionId
        symbol_id = td.symbolId
        volume = td.volume              # cTrader units
        direction = "BUY" if td.tradeSide == 1 else "SELL"

        logger.info(
            "Master OPENED position %s – symbol=%s dir=%s vol=%s",
            master_pos_id, symbol_id, direction, volume,
        )

        clients = []
        with self._get_db() as db:
            clients = self._get_active_copier_accounts(db)

        self.position_map.setdefault(master_pos_id, [])

        for client_account in clients:
            try:
                await self._execute_copy(
                    client_account,
                    master_position_id=master_pos_id,
                    symbol_id=symbol_id,
                    master_volume=volume,
                    direction=direction,
                )
            except Exception as exc:
                logger.error(
                    "Failed to copy open to client account %s: %s",
                    getattr(client_account, "ctrader_account_id", None), exc,
                )

    async def _handle_position_close(self, master_pos_id: int) -> None:
        logger.info("Master CLOSED position %s – propagating to clients", master_pos_id)

        copies = self.position_map.pop(master_pos_id, [])
        for copy_info in copies:
            client_account_id = copy_info["client_account_id"]
            client_pos_id = copy_info["client_position_id"]
            client_volume = copy_info["volume"]

            try:
                with self._get_db() as db:
                    uba = db.query(UserBrokerAccount).filter(
                        UserBrokerAccount.ctrader_account_id == client_account_id
                    ).first()

                if not uba:
                    logger.warning("Client account %s not found in DB – skipping close", client_account_id)
                    continue

                await self._gateway.authorize_account(
                    client_account_id, uba.ctrader_access_token
                )
                close_result = await self._gateway.close_position(
                    client_account_id, client_pos_id, client_volume
                )
                logger.info(
                    "Closed client position %s (account %s): %s",
                    client_pos_id, client_account_id, close_result,
                )

                self._log_close_audit(uba, master_pos_id, client_pos_id)

            except Exception as exc:
                logger.error(
                    "Failed to close position %s on client account %s: %s",
                    client_pos_id, client_account_id, exc,
                )

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _get_active_copier_accounts(self, db) -> List[UserBrokerAccount]:
        query = db.query(UserBrokerAccount).filter(
            UserBrokerAccount.is_copier_active == True,
            UserBrokerAccount.platform == "ctrader",
        )
        if self._master_account_id:
            query = query.filter(UserBrokerAccount.ctrader_account_id != str(self._master_account_id))
        return query.all()

    # ------------------------------------------------------------------
    # Copy execution with guardrails
    # ------------------------------------------------------------------

    async def _execute_copy(
        self,
        client_account: UserBrokerAccount,
        master_position_id: int,
        symbol_id: int,
        master_volume: int,
        direction: str,
    ) -> None:
        account_id = int(client_account.ctrader_account_id)
        access_token = client_account.ctrader_access_token

        logger.info("Evaluating copy for client account %s", account_id)

        await self._gateway.authorize_account(account_id, access_token)

        # 1. Allowed instruments
        symbol_name = await self._get_symbol_name(account_id, symbol_id)
        if client_account.allowed_instruments:
            allowed = client_account.allowed_instruments
            if isinstance(allowed, str):
                allowed = [s.strip().upper() for s in allowed.split(",")]
            elif isinstance(allowed, list):
                allowed = [str(s).strip().upper() for s in allowed]
            else:
                allowed = []

            if allowed and symbol_name.upper() not in allowed:
                logger.info("Client %s: %s not in allowed_instruments %s – skipped", account_id, symbol_name, allowed)
                return

        # 2. Max concurrent trades
        open_positions = await self._gateway.get_open_positions(account_id)
        if client_account.max_concurrent_trades and len(open_positions) >= client_account.max_concurrent_trades:
            logger.info("Client %s: max concurrent trades (%s) reached – skipped", account_id, client_account.max_concurrent_trades)
            return

        # 3. Daily loss guard
        account_info = await self._gateway.get_account_info(account_id)
        balance = account_info.get("balance", 0.0)
        equity = account_info.get("equity", balance)

        if client_account.max_daily_loss_pct and balance > 0:
            drawdown_pct = ((balance - equity) / balance) * 100
            if drawdown_pct >= client_account.max_daily_loss_pct:
                logger.info("Client %s: max daily loss (%.2f%%) reached – skipped", account_id, client_account.max_daily_loss_pct)
                return

        # 4. Volume calculation
        copy_volume_lots = self._calculate_volume(client_account, master_volume, balance)
        if copy_volume_lots <= 0:
            logger.warning("Client %s: calculated volume <= 0 – skipped", account_id)
            return

        # 5. Place order
        try:
            result = await self._gateway.execute_market_order(
                account_id=account_id,
                symbol_id=symbol_id,
                volume_lots=copy_volume_lots,
                direction=direction,
            )
        except CTraderOrderError as exc:
            logger.error("Order rejected for client %s: %s", account_id, exc)
            self._log_trade_record(
                client_account, symbol_name, direction, copy_volume_lots,
                master_position_id, status="REJECTED", error=str(exc),
            )
            return

        client_pos_id = result.get("position_id")
        client_volume = result.get("volume", int(round(copy_volume_lots * 100)))

        self.position_map.setdefault(master_position_id, []).append({
            "client_account_id": account_id,
            "client_position_id": client_pos_id,
            "volume": client_volume,
        })

        logger.info(
            "Copy trade executed: client=%s pos=%s symbol=%s dir=%s lots=%.4f",
            account_id, client_pos_id, symbol_name, direction, copy_volume_lots,
        )

        self._log_trade_record(
            client_account, symbol_name, direction, copy_volume_lots,
            master_position_id, status="FILLED", client_position_id=client_pos_id,
        )

    def _calculate_volume(
        self,
        client_account: UserBrokerAccount,
        master_volume_units: int,
        account_balance: float,
    ) -> float:
        master_lots = master_volume_units / 100.0
        mode = getattr(client_account, "risk_mode", "FIXED_LOT") or "FIXED_LOT"

        if mode == "FIXED_LOT":
            lot = getattr(client_account, "fixed_lot_size", None)
            if lot and lot > 0:
                return float(lot)
            return master_lots

        elif mode == "DYNAMIC_RISK_PCT":
            risk_pct = getattr(client_account, "risk_pct", None)
            if risk_pct and risk_pct > 0 and account_balance > 0:
                risk_amount = account_balance * (risk_pct / 100.0)
                pip_val = 10.0
                sl_pips = 50.0
                lots = risk_amount / (sl_pips * pip_val)
                return max(0.01, round(lots, 2))
            return master_lots

        return master_lots

    async def _get_symbol_name(self, account_id: int, symbol_id: int) -> str:
        cache_key = f"{account_id}:{symbol_id}"
        if cache_key not in self._symbol_cache:
            symbols = await self._gateway.get_symbols(account_id)
            for sym in symbols:
                self._symbol_cache[f"{account_id}:{sym['id']}"] = sym["name"]
        return self._symbol_cache.get(cache_key, str(symbol_id))

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    def _log_trade_record(
        self,
        client_account: UserBrokerAccount,
        symbol: str,
        direction: str,
        volume_lots: float,
        master_position_id: int,
        status: str,
        client_position_id: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        try:
            with self._get_db() as db:
                record = TradeRecord(
                    user_id=client_account.user_id,
                    broker_account_id=client_account.id,
                    symbol=symbol,
                    direction=direction,
                    volume_lots=volume_lots,
                    decision_type="COPIER_AUTO",
                    status=status,
                    broker_position_id=str(client_position_id) if client_position_id else None,
                    master_position_id=str(master_position_id),
                    error_message=error,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(record)
                db.commit()
        except Exception as exc:
            logger.error("Failed to log TradeRecord: %s", exc)

    def _log_close_audit(
        self,
        client_account: UserBrokerAccount,
        master_position_id: int,
        client_position_id: int,
    ) -> None:
        try:
            with self._get_db() as db:
                audit = ExecutionAuditLog(
                    user_id=client_account.user_id,
                    broker_account_id=client_account.id,
                    action="CLOSE_COPY",
                    master_position_id=str(master_position_id),
                    client_position_id=str(client_position_id),
                    platform="ctrader",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(audit)
                db.commit()
        except Exception as exc:
            logger.error("Failed to log ExecutionAuditLog: %s", exc)
