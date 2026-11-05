"""
ctrader_gateway.py — PrimeEdge cTrader OpenAPI v2 Client
=========================================================
Uses the `ctrader-open-api` Python package (pip install ctrader-open-api).

Legacy MetaAPI account UUID kept for reference only (do NOT use):
    6a06790a-743a-4a0d-bda5-12448199348d

Connection:
  LIVE : EndPoints.PROTOBUF_LIVE_HOST : 5035
  DEMO : EndPoints.PROTOBUF_DEMO_HOST : 5036
"""

import asyncio
import logging
import threading
import time
from typing import Callable, Optional, Dict, List, Any

try:
    from twisted.internet import reactor
    from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
    from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import (
        ProtoOAPayloadType,
        ProtoOAOrderType,
        ProtoOATradeSide,
    )
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAApplicationAuthReq,
        ProtoOAApplicationAuthRes,
        ProtoOAAccountAuthReq,
        ProtoOAAccountAuthRes,
        ProtoOATraderReq,
        ProtoOATraderRes,
        ProtoOANewOrderReq,
        ProtoOAExecutionEvent,
        ProtoOAClosePositionReq,
        ProtoOASymbolsListReq,
        ProtoOASymbolByIdReq,
        ProtoOAReconcileReq,
        ProtoOAGetAccountListByAccessTokenReq,
        ProtoOAErrorRes,
    )
    CTRADER_AVAILABLE = True
except ImportError:
    CTRADER_AVAILABLE = False
    reactor = None
    Client = Protobuf = TcpProtocol = EndPoints = None
    ProtoMessage = None
    ProtoOAPayloadType = ProtoOAOrderType = ProtoOATradeSide = None
    ProtoOAApplicationAuthReq = ProtoOAApplicationAuthRes = None
    ProtoOAAccountAuthReq = ProtoOAAccountAuthRes = None
    ProtoOATraderReq = ProtoOATraderRes = ProtoOANewOrderReq = None
    ProtoOAExecutionEvent = ProtoOAClosePositionReq = None
    ProtoOASymbolsListReq = ProtoOASymbolByIdReq = ProtoOAReconcileReq = None
    ProtoOAGetAccountListByAccessTokenReq = ProtoOAErrorRes = None

def _ensure_reactor():
    if not CTRADER_AVAILABLE or reactor is None:
        raise CTraderConnectionError("cTrader OpenAPI dependencies are not available on this server")
    if not reactor.running:
        t = threading.Thread(
            target=reactor.run,
            kwargs={"installSignalHandlers": False},
            name="TwistedReactorThread",
            daemon=True,
        )
        t.start()
        time.sleep(0.1)
logger = logging.getLogger("ctrader_gateway")

# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class CTraderConnectionError(Exception):
    """Raised when the TCP connection to cTrader OpenAPI cannot be established."""


class CTraderAuthError(Exception):
    """Raised when application or account authorisation fails."""


class CTraderOrderError(Exception):
    """Raised when an order request is rejected by the broker."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOTS_TO_CTRADER_UNITS = 100  # 1 standard lot = 100 cTrader volume units


def _lots_to_volume(lots: float) -> int:
    """Convert human-readable lot size to cTrader OpenAPI volume units."""
    return int(round(lots * _LOTS_TO_CTRADER_UNITS))


def _direction_to_side(direction: str) -> int:
    """Convert 'BUY'/'SELL' string to ProtoOATradeSide constant."""
    direction = direction.upper()
    if direction == "BUY":
        return ProtoOATradeSide.Value("BUY")
    elif direction == "SELL":
        return ProtoOATradeSide.Value("SELL")
    raise ValueError(f"Unknown direction: {direction!r}. Expected 'BUY' or 'SELL'.")


# ---------------------------------------------------------------------------
# CTraderGateway
# ---------------------------------------------------------------------------

class CTraderGateway:
    """
    Async wrapper around the ctrader-open-api Client.

    The ctrader-open-api library is callback-based.  This class bridges those
    callbacks to coroutine-friendly asyncio.Future / asyncio.Queue objects so
    callers can simply ``await`` any request.
    """

    def __init__(self, client_id: str, client_secret: str, is_demo: bool = True):
        self._client_id = client_id
        self._client_secret = client_secret
        self._is_demo = is_demo

        # Pending one-shot futures keyed by clientMsgId (str)
        self._pending: Dict[str, asyncio.Future] = {}
        self._msg_counter = 0

        # Per-account execution callbacks  {account_id: Callable}
        self._exec_callbacks: Dict[int, Callable] = {}

        self._client: Optional[Client] = None
        self._connected = False
        self._app_authed = False

        self._symbol_details_cache: Dict[str, Dict[str, Any]] = {}
        self._symbol_name_by_id: Dict[str, str] = {}

        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Internal – message counter / future tracking
    # ------------------------------------------------------------------

    def _next_msg_id(self) -> str:
        self._msg_counter += 1
        return str(self._msg_counter)

    def _register_future(self, msg_id: str) -> asyncio.Future:
        fut = self._loop.create_future()
        self._pending[msg_id] = fut
        return fut

    def _resolve_future(self, msg_id: str, result: Any) -> None:
        fut = self._pending.pop(msg_id, None)
        if fut and not fut.done():
            fut.set_result(result)

    def _reject_future(self, msg_id: str, exc: Exception) -> None:
        fut = self._pending.pop(msg_id, None)
        if fut and not fut.done():
            fut.set_exception(exc)

    # ------------------------------------------------------------------
    # Internal – central message handler
    # ------------------------------------------------------------------

    def _on_message(self, client: Client, message: ProtoMessage) -> None:
        """
        Central incoming-message dispatcher.

        The ctrader-open-api library calls this from its I/O thread.
        We schedule work safely onto the event loop via call_soon_threadsafe.
        """
        payload_type = message.payloadType
        msg_id = message.clientMsgId  # may be empty string

        logger.debug("Received payloadType=%s clientMsgId=%r", payload_type, msg_id)

        try:
            extracted = Protobuf.extract(message)

            if payload_type == ProtoOAPayloadType.Value("PROTO_OA_APPLICATION_AUTH_RES"):
                self._loop.call_soon_threadsafe(
                    self._resolve_future, msg_id, extracted
                )

            elif payload_type == ProtoOAPayloadType.Value("PROTO_OA_ACCOUNT_AUTH_RES"):
                self._loop.call_soon_threadsafe(
                    self._resolve_future, msg_id, extracted
                )

            elif payload_type == ProtoOAPayloadType.Value("PROTO_OA_TRADER_RES"):
                self._loop.call_soon_threadsafe(
                    self._resolve_future, msg_id, extracted
                )

            elif payload_type == ProtoOAPayloadType.Value("PROTO_OA_EXECUTION_EVENT"):
                exec_event = extracted
                account_id = exec_event.ctidTraderAccountId

                # Only resolve order-placement futures on terminal events (FILLED, REJECTED, CANCELLED)
                # ProtoOAExecutionType: 2 = ORDER_ACCEPTED, 3 = ORDER_FILLED, 4 = ORDER_CANCELLED, 5 = ORDER_EXPIRED, 6 = ORDER_REJECTED
                exec_type = getattr(exec_event, "executionType", 0)
                is_terminal = exec_type in (3, 4, 5, 6)

                # Resolve order-placement future: try by msg_id first, then oldest pending on terminal event
                resolved = False
                if msg_id and msg_id in self._pending:
                    self._loop.call_soon_threadsafe(
                        self._resolve_future, msg_id, exec_event
                    )
                    resolved = True
                elif is_terminal and self._pending:
                    # cTrader doesn't always echo clientMsgId on execution events.
                    # Resolve the oldest outstanding future (FIFO assumption) when filled.
                    oldest_id = next(iter(self._pending))
                    self._loop.call_soon_threadsafe(
                        self._resolve_future, oldest_id, exec_event
                    )
                    resolved = True

                # Fan-out to per-account subscription callback
                if account_id in self._exec_callbacks:
                    cb = self._exec_callbacks[account_id]
                    self._loop.call_soon_threadsafe(
                        lambda e=exec_event, c=cb: asyncio.ensure_future(c(e), loop=self._loop)
                    )

            elif payload_type in (
                ProtoOAPayloadType.Value("PROTO_OA_SYMBOLS_LIST_RES"),
                ProtoOAPayloadType.Value("PROTO_OA_SYMBOL_BY_ID_RES"),
            ):
                self._loop.call_soon_threadsafe(
                    self._resolve_future, msg_id, extracted
                )

            elif payload_type == ProtoOAPayloadType.Value("PROTO_OA_RECONCILE_RES"):
                self._loop.call_soon_threadsafe(
                    self._resolve_future, msg_id, extracted
                )

            elif payload_type == ProtoOAPayloadType.Value("PROTO_OA_GET_ACCOUNTS_BY_ACCESS_TOKEN_RES"):
                self._loop.call_soon_threadsafe(
                    self._resolve_future, msg_id, extracted
                )

            elif payload_type == ProtoOAPayloadType.Value("PROTO_OA_ERROR_RES"):
                err = extracted
                exc = CTraderOrderError(
                    f"cTrader error {getattr(err, 'errorCode', '?')}: {getattr(err, 'description', str(err))}"
                )
                if msg_id and msg_id in self._pending:
                    self._loop.call_soon_threadsafe(self._reject_future, msg_id, exc)
                elif self._pending:
                    # Reject oldest pending future if no msg_id match
                    oldest_id = next(iter(self._pending))
                    self._loop.call_soon_threadsafe(self._reject_future, oldest_id, exc)
                else:
                    logger.error(
                        "Unmatched cTrader error: %s – %s",
                        getattr(err, "errorCode", "?"), getattr(err, "description", str(err)),
                    )

            elif payload_type == ProtoOAPayloadType.Value("PROTO_OA_ORDER_ERROR_EVENT"):
                # Order-level rejection (e.g. outside market hours, insufficient margin)
                err = extracted
                exc = CTraderOrderError(
                    f"Order error {getattr(err, 'errorCode', '?')}: {getattr(err, 'description', str(err))}"
                )
                if self._pending:
                    oldest_id = next(iter(self._pending))
                    self._loop.call_soon_threadsafe(self._reject_future, oldest_id, exc)
                logger.error("cTrader order error: %s", exc)

            else:
                logger.debug("Unhandled payloadType %s", payload_type)

        except Exception as exc:  # pragma: no cover
            logger.exception("Error in _on_message handler: %s", exc)

    def _on_error(self, client: Client, failure) -> None:
        logger.error("cTrader client connection error: %s", failure)
        for msg_id, fut in list(self._pending.items()):
            if not fut.done():
                self._loop.call_soon_threadsafe(
                    fut.set_exception,
                    CTraderConnectionError(f"Connection error: {failure}"),
                )
        self._pending.clear()
        self._connected = False

    def _send(self, req, clientMsgId=None):
        """Thread-safely dispatch request on Twisted reactor thread."""
        if self._client:
            reactor.callFromThread(self._client.send, req, clientMsgId=clientMsgId)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Establish TCP+TLS connection and authenticate the application
        with ProtoOAApplicationAuthReq.
        """
        _ensure_reactor()
        self._loop = asyncio.get_running_loop()

        host = EndPoints.PROTOBUF_DEMO_HOST if self._is_demo else EndPoints.PROTOBUF_LIVE_HOST
        port = EndPoints.PROTOBUF_PORT

        logger.info(
            "Connecting to cTrader OpenAPI %s:%s (demo=%s)", host, port, self._is_demo
        )

        connect_event = asyncio.Event()

        def _connected_cb(client):
            logger.info("TCP connection established")
            self._connected = True
            self._loop.call_soon_threadsafe(connect_event.set)

        try:
            self._client = Client(host, port, TcpProtocol)
            self._client.setMessageReceivedCallback(self._on_message)
            self._client.setDisconnectedCallback(self._on_error)
            self._client.setConnectedCallback(_connected_cb)

            reactor.callFromThread(self._client.startService)

            await asyncio.wait_for(connect_event.wait(), timeout=15)
        except asyncio.TimeoutError:
            raise CTraderConnectionError("Timed out connecting to cTrader OpenAPI")
        except Exception as exc:
            raise CTraderConnectionError(f"Failed to connect: {exc}") from exc

        # Authenticate the application
        await self._app_auth()

    async def _app_auth(self) -> None:
        """Send ProtoOAApplicationAuthReq and await confirmation."""
        msg_id = self._next_msg_id()
        req = ProtoOAApplicationAuthReq()
        req.clientId = self._client_id
        req.clientSecret = self._client_secret

        fut = self._register_future(msg_id)
        self._send(req, clientMsgId=msg_id)

        try:
            await asyncio.wait_for(fut, timeout=10)
            self._app_authed = True
            logger.info("Application authenticated with cTrader OpenAPI")
        except asyncio.TimeoutError:
            raise CTraderAuthError("Timeout during application auth")
        except CTraderOrderError as exc:
            raise CTraderAuthError(str(exc)) from exc

    async def authorize_account(self, account_id: int, access_token: str) -> None:
        """
        Authorise a specific cTrader account via ProtoOAAccountAuthReq.
        Must be called before any account-scoped requests.
        """
        if not self._app_authed:
            raise CTraderAuthError("Application is not authenticated. Call connect() first.")

        msg_id = self._next_msg_id()
        req = ProtoOAAccountAuthReq()
        req.ctidTraderAccountId = account_id
        req.accessToken = access_token

        fut = self._register_future(msg_id)
        self._send(req, clientMsgId=msg_id)

        try:
            await asyncio.wait_for(fut, timeout=10)
            logger.info("Account %s authorised", account_id)
        except asyncio.TimeoutError:
            raise CTraderAuthError(f"Timeout authorising account {account_id}")
        except CTraderOrderError as exc:
            raise CTraderAuthError(str(exc)) from exc

    async def get_account_info(self, account_id: int) -> dict:
        """
        Fetch trader/account details via ProtoOATraderReq.

        Returns a dict with keys: balance, equity, currency, leverage, etc.
        """
        msg_id = self._next_msg_id()
        req = ProtoOATraderReq()
        req.ctidTraderAccountId = account_id

        fut = self._register_future(msg_id)
        self._send(req, clientMsgId=msg_id)

        try:
            res: ProtoOATraderRes = await asyncio.wait_for(fut, timeout=10)
        except asyncio.TimeoutError:
            raise CTraderConnectionError(
                f"Timeout fetching account info for {account_id}"
            )

        trader = res.trader
        balance = getattr(trader, "balance", 0) / 100.0
        equity = getattr(trader, "equity", None)
        equity_val = (equity / 100.0) if equity is not None else balance
        return {
            "account_id": account_id,
            "balance": balance,
            "equity": equity_val,
            "currency": "USD",
            "leverage": trader.leverageInCents / 100 if getattr(trader, "leverageInCents", None) else None,
            "broker_name": getattr(trader, "brokerName", None) or getattr(trader, "brokerTitle", None) or "cTrader",
            "account_type": getattr(trader, "accountType", None),
        }

    async def get_symbol_details(self, account_id: int, symbol_id: int) -> Dict[str, Any]:
        """
        Retrieve detailed symbol metadata (digits, pipPosition, minVolume, stepVolume, lotSize).
        Results are cached per symbol_id.
        """
        if not hasattr(self, "_symbol_details_cache"):
            self._symbol_details_cache = {}
        if not hasattr(self, "_symbol_name_by_id"):
            self._symbol_name_by_id = {}

        cache_key = f"{account_id}:{symbol_id}"
        if cache_key in self._symbol_details_cache:
            return self._symbol_details_cache[cache_key]

        try:
            msg_id = self._next_msg_id()
            req = ProtoOASymbolByIdReq()
            req.ctidTraderAccountId = account_id
            req.symbolId.append(symbol_id)

            fut = self._register_future(msg_id)
            self._send(req, clientMsgId=msg_id)
            res = await asyncio.wait_for(fut, timeout=10)

            for s in res.symbol:
                info = {
                    "id": s.symbolId,
                    "digits": getattr(s, "digits", 5),
                    "pip_position": getattr(s, "pipPosition", 4),
                    "min_volume": getattr(s, "minVolume", 100000),
                    "step_volume": getattr(s, "stepVolume", 100000),
                    "lot_size": getattr(s, "lotSize", 10000000) or 10000000,
                }
                self._symbol_details_cache[f"{account_id}:{s.symbolId}"] = info
        except Exception as exc:
            logger.warning("Failed to fetch detailed symbol metadata for %s: %s", symbol_id, exc)

        # Smart fallback if details could not be fetched from broker
        sym_name = self._symbol_name_by_id.get(cache_key, "").upper()
        is_index = any(k in sym_name for k in ["100", "NAS", "TEC", "US30", "SPX", "GER", "DAX", "DOW"]) or symbol_id == 41
        is_gold = any(k in sym_name for k in ["XAU", "GOLD"])
        is_jpy = "JPY" in sym_name or symbol_id == 4

        if is_index:
            fallback = {
                "id": symbol_id,
                "digits": 2,
                "pip_position": 1,
                "min_volume": 100,
                "step_volume": 100,
                "lot_size": 10000,
            }
        elif is_gold:
            fallback = {
                "id": symbol_id,
                "digits": 2,
                "pip_position": 2,
                "min_volume": 100,
                "step_volume": 100,
                "lot_size": 10000000,
            }
        elif is_jpy:
            fallback = {
                "id": symbol_id,
                "digits": 3,
                "pip_position": 2,
                "min_volume": 1000,
                "step_volume": 1000,
                "lot_size": 10000000,
            }
        else:
            fallback = {
                "id": symbol_id,
                "digits": 5,
                "pip_position": 4,
                "min_volume": 100000,
                "step_volume": 100000,
                "lot_size": 10000000,
            }

        return self._symbol_details_cache.get(cache_key, fallback)

    async def execute_market_order(
        self,
        account_id: int,
        symbol_id: int,
        volume_lots: float,
        direction: str,
        stop_loss_pips: Optional[float] = None,
        take_profit_pips: Optional[float] = None,
        entry_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> dict:
        """
        Place a market order via ProtoOANewOrderReq with precise broker-level
        volume scaling and tick-aligned relative Stop Loss / Take Profit.
        """
        details = await self.get_symbol_details(account_id, symbol_id)
        digits = details.get("digits", 5)
        lot_size = details.get("lot_size", 10000000)
        min_vol = details.get("min_volume", 100000)
        step_vol = details.get("step_volume", 100000)

        msg_id = self._next_msg_id()
        req = ProtoOANewOrderReq()
        req.ctidTraderAccountId = account_id
        req.symbolId = symbol_id
        req.orderType = ProtoOAOrderType.Value("MARKET")
        req.tradeSide = _direction_to_side(direction)

        # Precise volume calculation
        vol = int(round(volume_lots * lot_size))
        if vol < min_vol:
            vol = min_vol
        if step_vol > 0:
            vol = (vol // step_vol) * step_vol
        req.volume = vol

        # Step size in 1/100,000 units according to symbol digits
        tick_step = 100000 // (10 ** digits) if digits <= 5 else 1

        # Relative Stop Loss
        if stop_loss_price is not None and entry_price is not None:
            diff = round(abs(entry_price - stop_loss_price), digits)
            rel_sl = int(round(diff * 100000))
            if tick_step > 0:
                rel_sl = (rel_sl // tick_step) * tick_step
            if rel_sl > 0:
                req.relativeStopLoss = rel_sl
        elif stop_loss_pips is not None:
            # pips_unit converts a pip count to cTrader's relative price integer
            # (which has 5 implied decimal places, i.e. raw = price * 100000).
            #
            # Forex 5-digit (e.g. EURUSD, digits=5): 1 pip = 0.00010 → raw 10
            # Forex 3-digit (e.g. USDJPY, digits=3): 1 pip = 0.010   → raw 1000
            # Indices  2-digit (e.g. US100, digits=2): 1 point = 1.0  → raw 100000
            # Indices  0-digit (e.g. some CFDs):        1 point = 1.0  → raw 100000
            # We use pip_position from symbol details when available; fallback to
            # a digits-based heuristic otherwise.
            pip_position = details.get("pip_position", None)
            if pip_position is not None:
                # pip_size = 10^(-pip_position); relative unit = pip_size * 100000
                pips_unit = int(round(100000 * (10 ** (-pip_position))))
            elif digits == 5:
                pips_unit = 10       # 0.00010 * 100000
            elif digits == 3:
                pips_unit = 1000     # 0.010 * 100000
            elif digits <= 2:
                # Index / CFD (US100 = 2 digits, some at 0 or 1)
                # 1 full point = 1.00 in price → relative unit = 100000
                pips_unit = 100000
            else:
                pips_unit = 10       # safe fallback for 4-digit
            rel_sl = int(round(stop_loss_pips * pips_unit))
            if tick_step > 0:
                rel_sl = (rel_sl // tick_step) * tick_step
            if rel_sl > 0:
                req.relativeStopLoss = rel_sl

        # Relative Take Profit
        if take_profit_price is not None and entry_price is not None:
            diff = round(abs(take_profit_price - entry_price), digits)
            rel_tp = int(round(diff * 100000))
            if tick_step > 0:
                rel_tp = (rel_tp // tick_step) * tick_step
            if rel_tp > 0:
                req.relativeTakeProfit = rel_tp
        elif take_profit_pips is not None:
            pip_position = details.get("pip_position", None)
            if pip_position is not None:
                pips_unit = int(round(100000 * (10 ** (-pip_position))))
            elif digits == 5:
                pips_unit = 10
            elif digits == 3:
                pips_unit = 1000
            elif digits <= 2:
                pips_unit = 100000
            else:
                pips_unit = 10
            rel_tp = int(round(take_profit_pips * pips_unit))
            if tick_step > 0:
                rel_tp = (rel_tp // tick_step) * tick_step
            if rel_tp > 0:
                req.relativeTakeProfit = rel_tp

        logger.info(
            "Placing %s MARKET order: account=%s symbol=%s volume=%s (lots=%.2f) relSL=%s relTP=%s",
            direction, account_id, symbol_id, req.volume, volume_lots,
            getattr(req, "relativeStopLoss", None), getattr(req, "relativeTakeProfit", None),
        )

        fut = self._register_future(msg_id)
        self._send(req, clientMsgId=msg_id)

        try:
            exec_event: ProtoOAExecutionEvent = await asyncio.wait_for(fut, timeout=15)
        except asyncio.TimeoutError:
            raise CTraderOrderError(
                f"Timeout waiting for order execution on account {account_id}"
            )

        position = exec_event.position if exec_event.HasField("position") else None
        order = exec_event.order if exec_event.HasField("order") else None

        pos_id = position.positionId if position else None
        fill_price = position.price if position else None

        if not pos_id:
            try:
                open_positions = await self.get_open_positions(account_id)
                matching = [p for p in open_positions if p["symbol_id"] == symbol_id]
                if matching:
                    newest = max(matching, key=lambda p: p.get("open_timestamp", 0))
                    pos_id = newest["position_id"]
                    fill_price = newest["open_price"]
            except Exception as e:
                logger.warning("Could not reconcile open position after market order: %s", e)

        logger.info(
            "Order executed: position_id=%s order_id=%s fill_price=%s account=%s",
            pos_id,
            order.orderId if order else None,
            fill_price,
            account_id,
        )

        return {
            "execution_type": exec_event.executionType,
            "position_id": pos_id,
            "order_id": order.orderId if order else None,
            "fill_price": fill_price,
            "volume": position.tradeData.volume if position else req.volume,
            "direction": direction,
            "symbol_id": symbol_id,
            "account_id": account_id,
        }

    async def close_position(
        self, account_id: int, position_id: int, volume: int
    ) -> dict:
        """
        Fully or partially close a position via ProtoOAClosePositionReq.

        Args:
            account_id:  cTrader account ID.
            position_id: The position to close.
            volume:      Volume to close in cTrader units (not lots).

        Returns:
            dict with execution event details.
        """
        msg_id = self._next_msg_id()
        req = ProtoOAClosePositionReq()
        req.ctidTraderAccountId = account_id
        req.positionId = position_id
        req.volume = volume

        logger.info(
            "Closing position %s on account %s (volume=%s)",
            position_id, account_id, volume,
        )

        fut = self._register_future(msg_id)
        self._send(req, clientMsgId=msg_id)

        try:
            exec_event: ProtoOAExecutionEvent = await asyncio.wait_for(fut, timeout=15)
        except asyncio.TimeoutError:
            raise CTraderOrderError(
                f"Timeout closing position {position_id} on account {account_id}"
            )

        return {
            "execution_type": exec_event.executionType,
            "position_id": position_id,
            "account_id": account_id,
            "closed_volume": volume,
        }

    async def get_symbols(self, account_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all tradeable symbols for a given account.

        Returns:
            List of dicts: [{id, name, description, digits, category}, ...]
        """
        msg_id = self._next_msg_id()
        req = ProtoOASymbolsListReq()
        req.ctidTraderAccountId = account_id
        req.includeArchivedSymbols = False

        fut = self._register_future(msg_id)
        self._send(req, clientMsgId=msg_id)

        try:
            res: ProtoOASymbolsListRes = await asyncio.wait_for(fut, timeout=15)
        except asyncio.TimeoutError:
            raise CTraderConnectionError(
                f"Timeout fetching symbols for account {account_id}"
            )

        symbols_list = []
        if not hasattr(self, "_symbol_name_by_id"):
            self._symbol_name_by_id = {}

        for sym in res.symbol:
            s_id = getattr(sym, "symbolId", None)
            s_name = getattr(sym, "symbolName", None) or getattr(sym, "name", None) or ""
            if s_id and s_name:
                self._symbol_name_by_id[f"{account_id}:{s_id}"] = s_name

            symbols_list.append({
                "id": s_id,
                "name": s_name,
                "description": getattr(sym, "description", ""),
                "digits": getattr(sym, "digits", None),
                "category": getattr(sym, "tradingMode", None),
            })
        return symbols_list

    async def get_open_positions(self, account_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all open positions via ProtoOAReconcileReq.

        Returns:
            List of position dicts.
        """
        msg_id = self._next_msg_id()
        req = ProtoOAReconcileReq()
        req.ctidTraderAccountId = account_id

        fut = self._register_future(msg_id)
        self._send(req, clientMsgId=msg_id)

        try:
            res: ProtoOAReconcileRes = await asyncio.wait_for(fut, timeout=15)
        except asyncio.TimeoutError:
            raise CTraderConnectionError(
                f"Timeout fetching positions for account {account_id}"
            )

        positions = []
        raw_positions = getattr(res, "position", [])
        if not hasattr(raw_positions, "__iter__"):
            raw_positions = [raw_positions] if raw_positions else []
        for pos in raw_positions:
            td = pos.tradeData
            # unrealizedGrossPnl is in cents → convert to account currency units
            pnl_monetary = (getattr(pos, "unrealizedGrossPnl", 0) or 0) / 100.0

            # ------------------------------------------------------------------
            # Derive pnl_pips from price movement, not monetary PnL.
            # cTrader stores prices as integers with 5 implied decimal places
            # (i.e. price_int / 100000 = actual price).  open_price comes back
            # as a raw integer from the protobuf; bid/ask are not available here,
            # so we use pnl_monetary as a conservative directional indicator and
            # leave the precise pip calculation to the MAE monitor which already
            # has the SL distance in raw price units.
            #
            # For the MAE monitor all that matters is a same-unit comparison, so
            # we expose pnl_monetary under the key "pnl" and also store the
            # per-instrument metadata the monitor needs for a correct threshold.
            # ------------------------------------------------------------------
            symbol_id = td.symbolId
            # Fetch cached symbol details if available; fall back to safe defaults.
            details = {}
            if hasattr(self, "_symbol_details_cache"):
                details = self._symbol_details_cache.get(f"{account_id}:{symbol_id}", {})

            digits = details.get("digits", 5)
            pip_position = details.get("pip_position", 4)

            # pip_size: the price difference that equals 1 pip for this instrument.
            # For forex 5-digit (EUR/USD): pip_size = 0.0001
            # For indices like US100 (digits=2, pip_position=0 or 1): pip_size = 1.0
            # Formula: pip_size = 10 ^ (-pip_position)
            pip_size = 10 ** (-pip_position) if pip_position >= 0 else 1.0

            # open_price from ProtoOA is a scaled integer (divide by 100000 to get
            # the actual broker price).  We cannot reliably compute current price
            # here without a live tick, so pnl_pips is estimated from monetary PnL.
            # The MAE monitor will use this purely for sign and rough magnitude.
            # A proper per-instrument pip_value would require contract_size and
            # current price; we use pip_size as the normaliser for a direction check.
            lot_size = details.get("lot_size", 10_000_000)
            # Volume in standard lots = Proto volume (in cents) / lot_size
            volume_lots = td.volume / lot_size if lot_size > 0 else (td.volume / 100.0)
            # pip_value_per_lot: how much 1 pip of movement is worth in account
            # currency for 1 standard lot.  For indices: typically 1 pt = $1/lot.
            # Approximate: pip_value_per_lot = lot_size * pip_size (USD-denominated)
            pip_value_per_lot = lot_size * pip_size
            if pip_value_per_lot > 0 and volume_lots > 0:
                pnl_pips = pnl_monetary / (pip_value_per_lot * volume_lots)
            else:
                pnl_pips = 0.0

            positions.append(
                {
                    "position_id": pos.positionId,
                    "symbol_id": symbol_id,
                    "direction": "BUY"
                    if td.tradeSide == ProtoOATradeSide.Value("BUY")
                    else "SELL",
                    "volume": td.volume,
                    "volume_lots": volume_lots,
                    "open_price": pos.price,
                    "open_timestamp": td.openTimestamp,
                    "swap": getattr(pos, "swap", 0) / 100 if getattr(pos, "swap", None) is not None else 0.0,
                    "commission": getattr(pos, "commission", 0) / 100 if getattr(pos, "commission", None) is not None else 0.0,
                    "pnl": pnl_monetary,
                    # pnl_pips: normalised pip equivalent of unrealised PnL.
                    # Used by the MAE monitor; sign matches PnL (negative = adverse).
                    "pnl_pips": pnl_pips,
                    # Raw pip_size stored so MAE monitor can compute a
                    # correct instrument-specific threshold.
                    "pip_size": pip_size,
                    "account_id": account_id,
                }
            )
        return positions

    async def get_accounts_by_access_token(
        self, access_token: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all cTrader accounts linked to a given OAuth access token.
        Used during OAuth onboarding.

        Returns:
            List of dicts: [{ctid_trader_account_id, is_live, trader_login, broker_name}, ...]
        """
        msg_id = self._next_msg_id()
        req = ProtoOAGetAccountListByAccessTokenReq()
        req.accessToken = access_token

        fut = self._register_future(msg_id)
        self._send(req, clientMsgId=msg_id)

        try:
            res: ProtoOAGetAccountListByAccessTokenRes = await asyncio.wait_for(
                fut, timeout=15
            )
        except asyncio.TimeoutError:
            raise CTraderConnectionError("Timeout fetching accounts by access token")

        return [
            {
                "ctid_trader_account_id": getattr(acc, "ctidTraderAccountId", None),
                "is_live": getattr(acc, "isLive", False),
                "trader_login": getattr(acc, "traderLogin", None),
                "broker_name": getattr(acc, "brokerName", None) or getattr(acc, "brokerTitle", None) or "cTrader",
            }
            for acc in res.ctidTraderAccount
        ]

    async def subscribe_to_execution_events(
        self, account_id: int, callback: Callable
    ) -> None:
        """
        Register an async *callback* coroutine invoked for every
        ProtoOAExecutionEvent on *account_id*.

        Signature: ``async def callback(event: ProtoOAExecutionEvent) -> None``
        """
        self._exec_callbacks[account_id] = callback
        logger.info("Subscribed to execution events for account %s", account_id)

    async def disconnect(self) -> None:
        """Gracefully stop the cTrader client."""
        if self._client:
            try:
                reactor.callFromThread(self._client.stopService)
            except Exception as exc:
                logger.warning("Error during disconnect: %s", exc)
        self._connected = False
        self._app_authed = False
        self._connected = False
        self._app_authed = False
        logger.info("Disconnected from cTrader OpenAPI")
