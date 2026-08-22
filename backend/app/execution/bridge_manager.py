"""
Market OS Execution Gateway Manager
Central hub for routing signals, tick-level sub-second MAE monitoring,
spread guardrails, and automated synchronization with Auto Journal.
"""

import logging
import datetime
from typing import Any, Dict, List, Optional
from .base import AbstractExecutionClient, ExecutionOrder, ExecutionPosition, PlatformType, OrderDirection
from .mt5_client import MT5NativeClient
from .mql_bridge import MQLRemoteBridge

logger = logging.getLogger(__name__)


class ExecutionBridgeManager:
    """Central gateway coordinator for all broker and execution bridge connections."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExecutionBridgeManager, cls).__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self.mt5_client = MT5NativeClient()
        self.mql_bridge = MQLRemoteBridge()
        self.active_platform: PlatformType = PlatformType.MT5_NATIVE
        self.is_auto_execution_enabled: bool = True
        self.execution_history: List[Dict[str, Any]] = []

    def connect_platform(self, platform: PlatformType = PlatformType.MT5_NATIVE, **kwargs) -> Dict[str, Any]:
        self.active_platform = platform
        if platform == PlatformType.MT5_NATIVE:
            success = self.mt5_client.connect(**kwargs)
            return {
                "status": "CONNECTED" if success else "FAILED",
                "platform": platform.value,
                "account": self.mt5_client.get_account_info()
            }
        return {"status": "READY", "platform": platform.value}

    def disconnect_platform(self) -> Dict[str, Any]:
        if self.active_platform == PlatformType.MT5_NATIVE:
            self.mt5_client.disconnect()
        return {"status": "DISCONNECTED"}

    def get_status(self) -> Dict[str, Any]:
        acc = self.mt5_client.get_account_info() if self.mt5_client.is_connected else {}
        positions = self.get_all_positions()
        return {
            "gateway_status": "ONLINE",
            "active_platform": self.active_platform.value,
            "auto_execution_enabled": self.is_auto_execution_enabled,
            "connected_to_terminal": self.mt5_client.is_connected,
            "account_info": acc,
            "open_positions_count": len(positions),
            "guardrail_config": {
                "max_spread_pips": 2.5,
                "max_slippage_pips": 1.5,
                "early_invalidation_mae_r": -0.35,
                "mfe_disarm_r": 0.35
            },
            "connected_remote_eas": len(self.mql_bridge.connected_eas)
        }

    def get_all_positions(self) -> List[ExecutionPosition]:
        positions = []
        if self.mt5_client.is_connected:
            positions.extend(self.mt5_client.get_positions())
        positions.extend(self.mql_bridge.get_positions())
        return positions

    def dispatch_signal_order(self, order: ExecutionOrder) -> Dict[str, Any]:
        """Dispatches an order to the connected platform, pushing to remote EAs as well."""
        if not self.is_auto_execution_enabled:
            return {"status": "SKIPPED", "message": "Auto-execution is paused"}

        # Push to remote MQL bridge queue
        self.mql_bridge.push_signal(order)

        # Execute on native MT5 client if active
        if self.active_platform == PlatformType.MT5_NATIVE:
            res = self.mt5_client.send_order(order)
            self.execution_history.append({
                "signal_id": order.signal_id,
                "instrument": order.instrument,
                "direction": order.direction.value,
                "result": res,
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
            return res

        return {"status": "QUEUED_FOR_REMOTE_EA", "signal_id": order.signal_id}

    def on_tick_update(self, instrument: str, current_price: float, high_price: float, low_price: float) -> List[Dict[str, Any]]:
        """
        Sub-second MAE/MFE tick monitor:
        Enforces the -0.35R early invalidation rule immediately upon adverse excursion.
        """
        actions_taken = []
        positions = self.get_all_positions()

        for pos in positions:
            if pos.instrument != instrument:
                continue

            pip_mult = 100.0 if "JPY" in instrument else (10.0 if "XAU" in instrument else 10000.0)
            is_long = (pos.direction == OrderDirection.LONG)

            # Update excursions
            if is_long:
                adverse = max(0.0, (pos.open_price - low_price) * pip_mult)
                favorable = max(0.0, (high_price - pos.open_price) * pip_mult)
            else:
                adverse = max(0.0, (high_price - pos.open_price) * pip_mult)
                favorable = max(0.0, (pos.open_price - low_price) * pip_mult)

            pos.max_mae_pips = max(pos.max_mae_pips, adverse)
            pos.max_mfe_pips = max(pos.max_mfe_pips, favorable)
            pos.current_price = current_price

            risk_pips = abs(pos.open_price - pos.stop_loss) * pip_mult if pos.stop_loss else 35.0
            pos.early_inval_pips = 0.35 * risk_pips
            pos.mfe_disarm_pips = 0.35 * risk_pips

            # Check Disarm Condition: MFE >= +0.35R first
            if pos.early_inval_armed and pos.max_mfe_pips >= pos.mfe_disarm_pips and pos.max_mae_pips < pos.early_inval_pips:
                pos.early_inval_armed = False
                actions_taken.append({
                    "action": "EARLY_INVALIDATION_DISARMED",
                    "ticket_id": pos.ticket_id,
                    "mfe_pips": pos.max_mfe_pips
                })

            # Check Trigger Condition: MAE >= -0.35R while armed
            if pos.early_inval_armed and pos.max_mae_pips >= pos.early_inval_pips:
                # Immediate early invalidation market exit
                close_res = self.close_position(pos.ticket_id, exit_reason="EARLY_INVALIDATION_MAE")
                actions_taken.append({
                    "action": "EARLY_INVALIDATION_EXECUTED",
                    "ticket_id": pos.ticket_id,
                    "exit_price": current_price,
                    "mae_pips": pos.max_mae_pips,
                    "result": close_res
                })

        return actions_taken

    def close_position(self, ticket_id: str, exit_reason: str = "MANUAL") -> Dict[str, Any]:
        if self.mt5_client.is_connected:
            return self.mt5_client.close_position(ticket_id, exit_reason)
        return self.mql_bridge.report_close({"ticket_id": ticket_id, "exit_reason": exit_reason})


execution_bridge = ExecutionBridgeManager()
