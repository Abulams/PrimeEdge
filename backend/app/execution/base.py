"""
Market OS Abstract Execution Interface
Defines platform-agnostic models, contracts, and abstract connector interfaces.
"""

import datetime
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    MT5_NATIVE = "MT5_NATIVE"
    MT5_REMOTE_EA = "MT5_REMOTE_EA"
    MT4_REMOTE_EA = "MT4_REMOTE_EA"
    CTRADER_OPEN_API = "CTRADER_OPEN_API"
    SIMULATED_TEST = "SIMULATED_TEST"


class OrderDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class ExecutionOrder(BaseModel):
    action_type: str = "OPEN"  # "OPEN" or "CLOSE"
    ticket_id: Optional[str] = None
    signal_id: str
    instrument: str
    direction: OrderDirection
    order_type: OrderType = OrderType.MARKET
    entry_reference_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_r_pips: float = 20.0
    position_size_lots: float = 0.1
    risk_pct: float = 1.0

    # Invalidation rules
    mae_early_inval_r: float = -0.35
    mae_early_inval_price: Optional[float] = None
    mfe_disarm_r: float = 0.35
    mfe_disarm_price: Optional[float] = None

    # Guardrails
    max_allowed_spread_pips: float = 2.5
    max_slippage_pips: float = 1.5
    expiry_seconds: int = 60
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class ExecutionPosition(BaseModel):
    ticket_id: str
    platform: PlatformType
    instrument: str
    direction: OrderDirection
    open_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    position_size_lots: float

    # Real-time Excursions
    max_mae_pips: float = 0.0
    max_mfe_pips: float = 0.0
    current_pnl_pips: float = 0.0
    current_pnl_r: float = 0.0

    # Invalidation State
    early_inval_armed: bool = True
    early_inval_pips: float = 0.0
    early_inval_price: float = 0.0
    mfe_disarm_pips: float = 0.0

    # Metadata
    open_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    comment: str = "Market OS V4"


class AbstractExecutionClient(ABC):
    """Abstract base for all broker/platform execution connectors."""

    def __init__(self, platform: PlatformType):
        self.platform = platform
        self.is_connected = False
        self.account_info: Dict[str, Any] = {}

    @abstractmethod
    def connect(self, **kwargs) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        pass

    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_positions(self) -> List[ExecutionPosition]:
        pass

    @abstractmethod
    def send_order(self, order: ExecutionOrder) -> Dict[str, Any]:
        pass

    @abstractmethod
    def close_position(self, ticket_id: str, exit_reason: str = "MANUAL") -> Dict[str, Any]:
        pass

    @abstractmethod
    def check_spread(self, instrument: str) -> Dict[str, Any]:
        pass
