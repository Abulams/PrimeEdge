"""
Unit tests for Historical Replay & Simulation Environment — Scientific Test Harness:
- Strict DB Invariant: Passed setups generate NO ReplayTradeRecord
- Immutable T0 Level Freezing
- Point-in-time anti-look-ahead protection (as_of_date filtering)
- Hostile execution assumptions (SL-first bar resolution, limit fill realism, friction penalties)
- Replay database isolation (zero contamination of live trader tables)
- Automated Replay Integrity Checksum
"""

import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.database import Base, engine as db_engine
from app.models import (
    DailyMarketRegime, MarketSignature, PriceCache, SetupSnapshot, TradeRecord,
    ReplayBatch, ReplaySetupSnapshot, ReplayTradeRecord
)
from app.engine import DecisionIntelligenceEngine
from app.replay_service import ReplayService
from app.replay_engine import ReplayEngine

client = TestClient(app)

# In-memory SQLite for unit tests with StaticPool for thread safety
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
    t0 = datetime.date(2025, 6, 1)

    # Seed regime
    regime = DailyMarketRegime(
        date=t0,
        dxy_regime="BEARISH",
        yields_regime="STEEPENING",
        risk_sentiment="RISK_ON",
        macro_summary="Test historical macro regime",
        overall_confidence_score=85.0
    )
    db.add(regime)

    # Seed PriceCache for historical trend and candle stepping
    for inst in ["GBPUSD", "EURUSD", "XAUUSD", "AUDUSD", "USDJPY"]:
        base = 1.3400 if "GBP" in inst else 1.0800 if "EUR" in inst else 2350.0 if "XAU" in inst else 0.6500 if "AUD" in inst else 155.0
        # Historical bars prior to T0
        for i in range(25, 0, -1):
            d = t0 - datetime.timedelta(days=i)
            pc = PriceCache(
                instrument=inst,
                date=d,
                open=base + (i * 0.0001),
                high=base + 0.0020,
                low=base - 0.0020,
                close=base + (i * 0.00015),
                volume=1000.0
            )
            db.add(pc)

        # T0 bar
        db.add(PriceCache(
            instrument=inst,
            date=t0,
            open=base,
            high=base + 0.0030,
            low=base - 0.0010,
            close=base + 0.0020,
            volume=1200.0
        ))

        # Future bars (t > T0)
        for i in range(1, 10):
            d = t0 + datetime.timedelta(days=i)
            pc = PriceCache(
                instrument=inst,
                date=d,
                open=base + 0.0020 + (i * 0.0005),
                high=base + 0.0040 + (i * 0.0005),
                low=base + 0.0010 + (i * 0.0005),
                close=base + 0.0035 + (i * 0.0005),
                volume=1000.0
            )
            db.add(pc)

        # Seed matching signatures strictly prior to T0
        for i in range(35):
            sig = MarketSignature(
                instrument=inst,
                date=t0 - datetime.timedelta(days=i+1),
                session="LONDON",
                trend="BULLISH",
                dxy_state="BEARISH",
                risk_sentiment="RISK_ON",
                news_environment="LOW_IMPACT",
                volatility_regime="NORMAL",
                continuation_or_reversal="CONTINUATION",
                mae_pips=4.0 + (i % 8),
                mfe_pips=25.0 + (i % 12),
                holding_time_minutes=120,
                outcome="WIN" if i % 3 != 0 else "LOSS"
            )
            db.add(sig)

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


def test_anti_look_ahead_protection():
    """Verifies that inserting future data for t > T0 does NOT alter T0 profile outputs."""
    db = TestingSessionLocal()
    t0 = datetime.date(2025, 6, 1)

    trend1 = DecisionIntelligenceEngine.get_current_trend(db, "GBPUSD", as_of_date=t0)
    profile1 = DecisionIntelligenceEngine.generate_daily_profile_v2(db, "GBPUSD", t0, trend1, as_of_date=t0)

    assert profile1 is not None
    initial_n = profile1["historical_sample_size"]
    initial_prob = profile1["continuation_probability"]

    # Insert future signatures
    for i in range(10):
        sig = MarketSignature(
            instrument="GBPUSD",
            date=t0 + datetime.timedelta(days=i+1),
            session="LONDON",
            trend="BULLISH",
            dxy_state="BEARISH",
            risk_sentiment="RISK_ON",
            news_environment="LOW_IMPACT",
            volatility_regime="NORMAL",
            continuation_or_reversal="CONTINUATION",
            mae_pips=100.0,
            mfe_pips=0.0,
            holding_time_minutes=120,
            outcome="LOSS"
        )
        db.add(sig)
    db.commit()

    trend2 = DecisionIntelligenceEngine.get_current_trend(db, "GBPUSD", as_of_date=t0)
    profile2 = DecisionIntelligenceEngine.generate_daily_profile_v2(db, "GBPUSD", t0, trend2, as_of_date=t0)

    assert profile2["historical_sample_size"] == initial_n
    assert profile2["continuation_probability"] == initial_prob
    db.close()


def test_passed_setups_invariant_no_trade_records():
    """Verifies strict DB invariant: PASSED setups create snapshots with opportunity outcomes but ZERO trade records."""
    db = TestingSessionLocal()
    t0 = datetime.date(2025, 6, 1)

    batch = ReplayService.create_batch(
        db=db,
        start_date=t0,
        end_date=t0,
        instruments=["GBPUSD"],
        batch_name="Passed Invariant Test",
        execution_policy="STRICT_V4_LIMIT"
    )

    ReplayService.run_batch(db, batch.id)

    snapshots = db.query(ReplaySetupSnapshot).all()
    trades = db.query(ReplayTradeRecord).all()

    # Every snapshot exists
    assert len(snapshots) >= 1
    for s in snapshots:
        # If setup was passed or unfilled, no trade records exist for it!
        if s.opportunity_outcome is not None:
            assert len(s.trades) == 0

    db.close()


def test_replay_data_isolation():
    """Verifies that running a replay batch leaves live setup_snapshots and trade_records untouched."""
    db = TestingSessionLocal()
    t0 = datetime.date(2025, 6, 1)

    batch = ReplayService.create_batch(
        db=db,
        start_date=t0,
        end_date=t0,
        instruments=["GBPUSD"],
        batch_name="Isolation Test"
    )

    ReplayService.run_batch(db, batch.id)

    assert db.query(ReplaySetupSnapshot).count() >= 1
    assert db.query(SetupSnapshot).count() == 0
    assert db.query(TradeRecord).count() == 0
    db.close()


def test_pessimistic_sl_first_resolution():
    """Verifies Hostile SL-First Rule when both TP and SL are hit on the same bar."""
    db = TestingSessionLocal()

    snapshot = ReplaySetupSnapshot(
        batch_id=1,
        instrument="GBPUSD",
        date=datetime.date(2025, 6, 1),
        direction="LONG",
        trend="BULLISH",
        status_at_snapshot="READY",
        setup_ref_price=1.3400,
        frozen_entry=1.3400,
        frozen_sl=1.3350,
        frozen_tp=1.3500,
        mae_p25_pips=5.0,
        mae_p75_pips=15.0,
        mae_p90_pips=25.0,
        mfe_p50_pips=25.0,
        mfe_p75_pips=35.0,
        created_at=datetime.datetime.utcnow()
    )
    db.add(snapshot)
    db.flush()

    trade = ReplayTradeRecord(
        replay_snapshot_id=snapshot.id,
        lifecycle_state="ACTIVE",
        actual_entry=1.3400,
        actual_sl=1.3350,
        actual_tp=1.3500,
        entry_type="MARKET",
        created_at=datetime.datetime.utcnow()
    )
    db.add(trade)
    db.commit()

    future_bars = [
        PriceCache(
            instrument="GBPUSD",
            date=datetime.date(2025, 6, 2),
            open=1.3400,
            high=1.3510,
            low=1.3340,
            close=1.3450
        )
    ]

    ReplayEngine.simulate_trade_trajectory(trade, snapshot, future_bars, friction_pips=2.5)

    assert trade.lifecycle_state == "CLOSED"
    assert trade.outcome == "LOSS"
    assert trade.exit_reason == "STOP_LOSS_PESSIMISTIC_SAME_BAR"
    assert trade.exit_price == 1.3350
    db.close()


def test_replay_integrity_checksum():
    """Verifies automated Replay Integrity Checksum produces VERIFIED status."""
    db = TestingSessionLocal()
    t0 = datetime.date(2025, 6, 1)

    batch = ReplayService.create_batch(db, t0, t0, ["GBPUSD"])
    ReplayService.run_batch(db, batch.id)

    checksum = ReplayService.run_replay_integrity_checksum(db)
    assert checksum["status"] == "VERIFIED SCIENTIFIC HARNESS"
    assert checksum["checks"]["PASSED_SETUPS_NO_TRADE_RECORDS"] == "PASS"
    db.close()


def test_replay_api_flow():
    """Verifies API endpoints /api/v1/replay/*."""
    t0 = "2025-06-01"

    payload = {
        "batch_name": "API Audit Test",
        "start_date": t0,
        "end_date": t0,
        "instruments": ["GBPUSD"],
        "execution_policy": "STRICT_V4_LIMIT",
        "friction_pips": 2.5
    }
    res = client.post("/api/v1/replay/run", json=payload)
    assert res.status_code == 200
    batch_data = res.json()
    assert batch_data["status"] == "COMPLETED"
    batch_id = batch_data["id"]

    res = client.get(f"/api/v1/replay/status/{batch_id}")
    assert res.status_code == 200
    assert res.json()["id"] == batch_id

    res = client.get("/api/v1/replay/analytics")
    assert res.status_code == 200
    analytics = res.json()
    assert "integrity_checksum" in analytics
    assert analytics["integrity_checksum"]["status"] == "VERIFIED SCIENTIFIC HARNESS"

    res = client.post("/api/v1/replay/reset")
    assert res.status_code == 200
    assert res.json()["records_wiped"] >= 1
