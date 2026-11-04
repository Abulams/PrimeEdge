import asyncio
from unittest.mock import MagicMock
from app.execution.ctrader_gateway import CTraderGateway
from app.execution.ctrader_copier_service import CTraderCopierService
from app.models import UserBrokerAccount

def test_us100_symbol_details_fallback():
    async def _test():
        gateway = CTraderGateway(client_id="dummy", client_secret="dummy", is_demo=True)
        # Register dummy symbol name in gateway cache
        gateway._symbol_name_by_id["12345:999"] = "US100.cash"

        details = await gateway.get_symbol_details(12345, 999)
        assert details["digits"] == 2
        assert details["lot_size"] == 10000
        assert details["min_volume"] == 100
        assert details["step_volume"] == 100

    asyncio.run(_test())

def test_us100_volume_calculation_fixed_and_master():
    service = CTraderCopierService(db_session_factory=MagicMock(), gateway=MagicMock())
    client_acc = MagicMock(spec=UserBrokerAccount)
    client_acc.risk_mode = "FIXED_LOT"
    client_acc.fixed_lot_size = 0.5

    # Fixed lot size returns fixed_lot_size
    vol = service._calculate_volume(client_acc, master_volume_units=10000, account_balance=10000.0, lot_size=10000)
    assert vol == 0.5

    # Fixed lot size fallback when not set uses master_volume / lot_size
    client_acc.fixed_lot_size = None
    # 1 contract of US100 = 10,000 units
    vol_master = service._calculate_volume(client_acc, master_volume_units=10000, account_balance=10000.0, lot_size=10000)
    assert vol_master == 1.0

def test_us100_dynamic_risk_volume():
    service = CTraderCopierService(db_session_factory=MagicMock(), gateway=MagicMock())
    client_acc = MagicMock(spec=UserBrokerAccount)
    client_acc.risk_mode = "DYNAMIC_RISK_PCT"
    client_acc.risk_pct = 1.0  # 1% of $10,000 = $100

    # For US100 (lot_size=10000 <= 100000), pip_val=1.0, sl_pips=100.0 -> lots = 100 / (100 * 1) = 1.0 lot
    vol = service._calculate_volume(client_acc, master_volume_units=10000, account_balance=10000.0, lot_size=10000)
    assert vol == 1.0
