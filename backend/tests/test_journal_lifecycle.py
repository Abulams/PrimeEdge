"""
Unit tests for Auto Journal lifecycle & reproducibility:
- SetupSnapshot immutability
- Accept / Pass workflow
- Execution deviation tracking
- Live MAE/MFE threshold updates
- Close trade & outcome classification (Setup Outcome vs Execution Outcome)
- API endpoint integration
"""

import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool
from app.main import app, get_db
from app.database import Base
from app.models import SetupSnapshot, TradeRecord, DailyMarketRegime, MarketSignature, PriceCache
from app.journal_service import JournalService

client = TestClient(app)

# In-memory SQLite for unit tests with StaticPool for thread-safe shared connection
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    today = datetime.date.today()

    # Seed regime
    regime = DailyMarketRegime(
        date=today,
        dxy_regime="BEARISH",
        yields_regime="STEEPENING",
        risk_sentiment="RISK_ON",
        macro_summary="Test macro environment",
        overall_confidence_score=80.0
    )
    db.add(regime)

    # Seed PriceCache for trend calculation
    for inst in ["GBPUSD", "EURUSD", "XAUUSD", "AUDUSD", "USDJPY"]:
        base = 1.3400 if "GBP" in inst else 1.0800 if "EUR" in inst else 2350.0 if "XAU" in inst else 0.6500 if "AUD" in inst else 155.0
        for i in range(25):
            d = today - datetime.timedelta(days=i)
            pc = PriceCache(
                instrument=inst,
                date=d,
                open=base + (i * 0.0002),
                high=base + 0.0020,
                low=base - 0.0020,
                close=base + (i * 0.0001),
                volume=1000.0
            )
            db.add(pc)

        # Seed matching signatures for statistical profile generation
        for i in range(35):
            sig = MarketSignature(
                instrument=inst,
                date=today - datetime.timedelta(days=i+1),
                session="LONDON",
                trend="BULLISH",
                dxy_state="BEARISH",
                risk_sentiment="RISK_ON",
                news_environment="LOW_IMPACT",
                volatility_regime="NORMAL",
                continuation_or_reversal="CONTINUATION",
                mae_pips=5.0 + (i % 10),
                mfe_pips=25.0 + (i % 15),
                holding_time_minutes=120,
                outcome="WIN" if i % 3 != 0 else "LOSS"
            )
            db.add(sig)

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


def test_create_snapshot_immutability():
    db = TestingSessionLocal()
    snapshot = JournalService.create_setup_snapshot(db, "GBPUSD", source="TEST")
    
    assert snapshot.id is not None
    assert snapshot.instrument == "GBPUSD"
    assert snapshot.setup_ref_price > 0
    assert snapshot.status_at_snapshot in ["READY", "WAIT", "INVALID", "NO EDGE", "NO SETUP"]
    
    # Store initial setup ref price
    initial_ref = snapshot.setup_ref_price
    
    # Create another snapshot — original snapshot record must remain untouched
    snapshot2 = JournalService.create_setup_snapshot(db, "GBPUSD", source="TEST2")
    
    saved_snap1 = db.query(SetupSnapshot).filter(SetupSnapshot.id == snapshot.id).first()
    assert saved_snap1.setup_ref_price == initial_ref
    db.close()


def test_accept_setup_lifecycle():
    db = TestingSessionLocal()
    snapshot = JournalService.create_setup_snapshot(db, "GBPUSD", source="TEST")
    
    entry_price = snapshot.setup_ref_price - 0.0005
    sl_price = snapshot.setup_ref_price - 0.0030
    tp_price = snapshot.setup_ref_price + 0.0050
    
    trade = JournalService.accept_setup(
        db=db,
        snapshot_id=snapshot.id,
        actual_entry=entry_price,
        actual_sl=sl_price,
        actual_tp=tp_price,
        entry_type="LIMIT",
        position_size_lots=0.5
    )
    
    assert trade.id is not None
    assert trade.lifecycle_state == "ACTIVE"
    assert trade.decision_type == "ACCEPTED"
    assert trade.actual_entry == entry_price
    assert trade.position_size_lots == 0.5
    assert trade.entry_deviation_pips >= 0.0
    db.close()


def test_pass_setup_lifecycle():
    db = TestingSessionLocal()
    snapshot = JournalService.create_setup_snapshot(db, "EURUSD", source="TEST")
    
    trade = JournalService.pass_setup(db, snapshot.id, notes="Low MSS score")
    
    assert trade.id is not None
    assert trade.lifecycle_state == "PASSED"
    assert trade.decision_type == "PASSED"
    assert trade.notes == "Low MSS score"
    db.close()


def test_close_trade_outcomes():
    db = TestingSessionLocal()
    snapshot = JournalService.create_setup_snapshot(db, "GBPUSD", source="TEST")
    
    entry_price = 1.3000
    sl_price = 1.2950
    tp_price = 1.3100
    
    snapshot.direction = "LONG"
    db.commit()
    
    trade = JournalService.accept_setup(
        db=db,
        snapshot_id=snapshot.id,
        actual_entry=entry_price,
        actual_sl=sl_price,
        actual_tp=tp_price
    )
    
    # Simulate trade moving +50 pips in favor
    quotes = {
        "GBPUSD": {"price": 1.3050, "high": 1.3060, "low": 1.2990}
    }
    JournalService.update_active_trades_with_quotes(db, quotes)
    
    # Close trade manually at 1.3050
    closed_trade = JournalService.close_trade(db, trade.id, exit_price=1.3050, exit_reason="MANUAL")
    
    assert closed_trade.lifecycle_state == "CLOSED"
    assert closed_trade.outcome == "WIN"
    assert closed_trade.pnl_pips == 50.0
    assert closed_trade.pnl_r == 1.0  # 50 pips / 50 pips risk
    assert closed_trade.setup_outcome in ["SUCCESSFUL", "FAILED"]
    assert closed_trade.execution_outcome in ["EXCELLENT_EXECUTION", "WIN_WITH_DEVIATION", "POOR_EXECUTION_SETUP_WORKED", "SYSTEM_LOSS"]
    db.close()


def test_api_auto_journal_flow():
    # 1. Take snapshot via API
    res = client.post("/api/v1/journal/snapshot", json={"instrument": "GBPUSD", "source": "API_TEST"})
    assert res.status_code == 200
    snap_data = res.json()
    assert "id" in snap_data
    snap_id = snap_data["id"]
    is_long = snap_data.get("direction", "LONG") == "LONG"
    
    # 2. Accept setup via API
    ref = snap_data["setup_ref_price"]
    sl_price = ref - 0.0030 if is_long else ref + 0.0030
    tp_price = ref + 0.0060 if is_long else ref - 0.0060
    exit_price = ref + 0.0020 if is_long else ref - 0.0020

    accept_payload = {
        "snapshot_id": snap_id,
        "actual_entry": ref,
        "actual_sl": sl_price,
        "actual_tp": tp_price,
        "entry_type": "MARKET",
        "position_size_lots": 0.2
    }
    res = client.post("/api/v1/journal/accept", json=accept_payload)
    assert res.status_code == 200
    trade_data = res.json()
    assert trade_data["lifecycle_state"] == "ACTIVE"
    trade_id = trade_data["id"]
    
    # 3. Verify active trades endpoint
    res = client.get("/api/v1/journal/active")
    assert res.status_code == 200
    active_list = res.json()
    assert any(t["id"] == trade_id for t in active_list)
    
    # 4. Close trade via API
    close_payload = {
        "trade_id": trade_id,
        "exit_price": exit_price,
        "exit_reason": "TAKE_PROFIT"
    }
    res = client.post("/api/v1/journal/close", json=close_payload)
    assert res.status_code == 200
    closed_data = res.json()
    assert closed_data["lifecycle_state"] == "CLOSED"
    assert closed_data["outcome"] == "WIN"
    
    # 5. Check performance summary endpoint
    res = client.get("/api/v1/journal/performance")
    assert res.status_code == 200
    perf = res.json()
    assert perf["total_trades_logged"] >= 1
    assert perf["win_count"] >= 1
