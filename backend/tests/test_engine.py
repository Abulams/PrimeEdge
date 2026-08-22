import pytest
from app.database import SessionLocal
from app.engine import SignatureEngine, DecisionIntelligenceEngine, TradePlannerEngine

def test_signature_engine_calculations():
    # Test Bullish trend
    bullish_prices = [1.2500, 1.2510, 1.2520, 1.2530, 1.2540, 1.2550]
    trend = SignatureEngine.calculate_trend(bullish_prices)
    assert trend == "BULLISH"

    # Test Bearish trend
    bearish_prices = [1.2550, 1.2540, 1.2530, 1.2520, 1.2510, 1.2500]
    trend = SignatureEngine.calculate_trend(bearish_prices)
    assert trend == "BEARISH"

    # Test Ranging trend
    ranging_prices = [1.2500, 1.2501, 1.2502, 1.2502, 1.2501, 1.2500]
    trend = SignatureEngine.calculate_trend(ranging_prices)
    assert trend == "RANGING"

    # Test Volatility Regimes
    hist_vols = [10.0, 12.0, 11.5, 9.8, 10.5, 11.0] # Mean ~10.8, std ~0.76
    current_high_vol = [15.0]  # Z-score ~5.5 (HIGH)
    current_low_vol = [7.0]   # Z-score ~-5.0 (LOW)
    current_normal_vol = [11.0] # Z-score ~0.2 (COMPRESSING)

    assert SignatureEngine.calculate_volatility_regime(current_high_vol, hist_vols) == "HIGH"
    assert SignatureEngine.calculate_volatility_regime(current_low_vol, hist_vols) == "LOW"
    assert SignatureEngine.calculate_volatility_regime(current_normal_vol, hist_vols) in ["COMPRESSING", "EXPANDING"]

def test_decision_and_trade_engines():
    db = SessionLocal()
    try:
        # Test similar signatures retrieval
        sigs = DecisionIntelligenceEngine.find_similar_signatures(
            db, "GBPUSD", "BULLISH", "BULLISH", "RISK_ON"
        )
        assert len(sigs) > 0, "Expected mock signatures to be matched."
        
        # Test daily profile generation
        import datetime
        today = datetime.date(2026, 7, 19)
        profile = DecisionIntelligenceEngine.generate_daily_profile(db, "GBPUSD", today)
        assert profile is not None
        assert profile["instrument"] == "GBPUSD"
        assert profile["continuation_probability"] > 0
        assert profile["confidence_score"] > 0
        
        # Test trade planner evaluations
        # Case A: Normal trade setup
        setup_ok = TradePlannerEngine.evaluate_setup(
            db, "GBPUSD", entry=1.2540, stop=1.2500, target=1.2620, risk_pct=1.0, account_balance=10000.0
        )
        assert "error" not in setup_ok
        assert setup_ok["risk_pips"] == 40.0
        assert setup_ok["reward_pips"] == 80.0
        assert setup_ok["risk_reward_ratio"] == 2.0
        assert setup_ok["position_size_lots"] == 0.25 # $100 risk / (40 pips * 10/pip) = 0.25 lots

        # Case B: Stop loss too tight (should trigger warning)
        setup_tight = TradePlannerEngine.evaluate_setup(
            db, "GBPUSD", entry=1.2540, stop=1.2536, target=1.2600, risk_pct=1.0, account_balance=10000.0
        )
        assert any("tighter than the average" in w or "extremely tight" in w for w in setup_tight["warnings"])
        
    finally:
        db.close()
