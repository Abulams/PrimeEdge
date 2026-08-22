"""
Market OS Execution Gateway & Multi-Platform Bridge Layer
"""

from .base import AbstractExecutionClient, ExecutionOrder, ExecutionPosition, PlatformType, OrderDirection
from .bridge_manager import ExecutionBridgeManager, execution_bridge

__all__ = [
    "AbstractExecutionClient",
    "ExecutionOrder",
    "ExecutionPosition",
    "PlatformType",
    "OrderDirection",
    "ExecutionBridgeManager",
    "execution_bridge"
]
