"""
Remote MQL4 / MQL5 Bridge Handler
Manages polling, signal dispatching, and fill confirmations for remote MetaTrader EAs.
"""

import datetime
from typing import Any, Dict, List, Optional
from .base import ExecutionOrder, ExecutionPosition, PlatformType, OrderDirection


class MQLRemoteBridge:
    """Handles communications between Market OS and remote MT4/MT5 Bridge EAs."""

    def __init__(self):
        self.pending_signals: List[Dict[str, Any]] = []
        self.active_ea_positions: Dict[str, ExecutionPosition] = {}
        self.connected_eas: Dict[str, Dict[str, Any]] = {}

    def register_ea(self, client_id: str, platform: str, account_login: int, broker: str) -> Dict[str, Any]:
        self.connected_eas[client_id] = {
            "client_id": client_id,
            "platform": platform,
            "account_login": account_login,
            "broker": broker,
            "last_heartbeat": datetime.datetime.utcnow().isoformat()
        }
        return {"status": "REGISTERED", "client_id": client_id}

    def push_signal(self, order: ExecutionOrder):
        payload = {
            "signal_id": order.signal_id,
            "instrument": order.instrument,
            "direction": order.direction.value,
            "order_type": order.order_type.value,
            "entry_price": order.entry_reference_price,
            "sl": order.stop_loss,
            "tp": order.take_profit,
            "volume": order.position_size_lots,
            "early_inval_r": order.mae_early_inval_r,
            "early_inval_price": order.mae_early_inval_price,
            "mfe_disarm_r": order.mfe_disarm_r,
            "mfe_disarm_price": order.mfe_disarm_price,
            "max_spread_pips": order.max_allowed_spread_pips,
            "max_slippage_pips": order.max_slippage_pips,
            "created_at": order.created_at.isoformat()
        }
        self.pending_signals.append(payload)

    def poll_signals(self, client_id: str) -> List[Dict[str, Any]]:
        if client_id in self.connected_eas:
            self.connected_eas[client_id]["last_heartbeat"] = datetime.datetime.utcnow().isoformat()
        
        signals = list(self.pending_signals)
        self.pending_signals.clear()
        return signals

    def report_fill(self, fill_data: Dict[str, Any]) -> Dict[str, Any]:
        ticket = str(fill_data.get("ticket_id"))
        pos = ExecutionPosition(
            ticket_id=ticket,
            platform=PlatformType.MT5_REMOTE_EA if "MT5" in fill_data.get("platform", "") else PlatformType.MT4_REMOTE_EA,
            instrument=fill_data.get("instrument", "GBPUSD"),
            direction=OrderDirection.LONG if fill_data.get("direction") == "LONG" else OrderDirection.SHORT,
            open_price=float(fill_data.get("fill_price", 1.0)),
            current_price=float(fill_data.get("fill_price", 1.0)),
            stop_loss=float(fill_data.get("stop_loss", 0.0)),
            take_profit=float(fill_data.get("take_profit", 0.0)),
            position_size_lots=float(fill_data.get("volume", 0.1)),
            open_time=datetime.datetime.utcnow()
        )
        self.active_ea_positions[ticket] = pos
        return {"status": "RECORDED", "ticket_id": ticket}

    def report_close(self, close_data: Dict[str, Any]) -> Dict[str, Any]:
        ticket = str(close_data.get("ticket_id"))
        if ticket in self.active_ea_positions:
            self.active_ea_positions.pop(ticket)
        return {"status": "RECORDED", "ticket_id": ticket}

    def get_positions(self) -> List[ExecutionPosition]:
        return list(self.active_ea_positions.values())
