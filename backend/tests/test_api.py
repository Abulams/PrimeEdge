import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Bloomberg Terminal" in response.json()["message"]

def test_regime_endpoint():
    response = client.get("/api/v1/dashboard/regime")
    assert response.status_code == 200
    data = response.json()
    assert "dxy_regime" in data
    assert "risk_sentiment" in data
    assert "macro_summary" in data

def test_watchlist_endpoint():
    response = client.get("/api/v1/dashboard/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Watchlist should be sorted by MSS (confidence) descending
    for i in range(len(data) - 1):
        assert data[i]["mss_score"] >= data[i + 1]["mss_score"]

def test_instrument_profile_endpoint():
    response = client.get("/api/v1/instruments/gbpusd/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["instrument"] == "GBPUSD"
    assert "continuation_probability" in data
    assert "expected_mae" in data

def test_trade_planner_evaluation():
    payload = {
        "instrument": "GBPUSD",
        "entry_price": 1.2540,
        "stop_loss": 1.2500,
        "take_profit": 1.2620,
        "risk_pct": 1.0,
        "account_balance": 10000.0
    }
    response = client.post("/api/v1/trade-planner/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["instrument"] == "GBPUSD"
    assert data["risk_pips"] == 40.0
    assert data["position_size_lots"] == 0.25
    assert "trade_quality_score" in data

def test_journal_endpoints():
    # 1. Fetch journals
    response = client.get("/api/v1/journal")
    assert response.status_code == 200
    journals = response.json()
    assert len(journals) > 0
    
    # 2. Add journal entry
    new_entry = {
        "instrument": "EURUSD",
        "date": "2026-07-18",
        "session": "LONDON",
        "market_regime": "BULLISH Trend under BEARISH DXY",
        "news_environment": "LOW_IMPACT",
        "mss_score": 75.0,
        "mae_actual": 5.0,
        "mfe_actual": 30.0,
        "execution_quality": "EXCELLENT",
        "risk_quality": "EXCELLENT",
        "outcome": "WIN",
        "lessons": "Perfect entry"
    }
    response = client.post("/api/v1/journal/log", json=new_entry)
    assert response.status_code == 200
    data = response.json()
    assert data["instrument"] == "EURUSD"
    assert data["outcome"] == "WIN"

# ============== v1.1 Tests ==============

def test_watchlist_mss_decomposition():
    """Verify watchlist returns MSS score breakdown factors."""
    response = client.get("/api/v1/dashboard/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    # At least one instrument should have decomposition
    has_decomposition = any(item.get("mss_decomposition") is not None for item in data)
    assert has_decomposition, "No watchlist item has mss_decomposition"
    for item in data:
        if item.get("mss_decomposition"):
            factors = item["mss_decomposition"]
            assert "base_probability" in factors
            assert "dxy_alignment" in factors
            assert "trend_alignment" in factors
            assert "session_suitability" in factors
            assert "news_buffer" in factors

def test_similar_days_endpoint():
    """Verify similarity explorer returns matching historical sessions."""
    response = client.get("/api/v1/instruments/GBPUSD/similar-days")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0 and len(data) <= 5
    first = data[0]
    assert "date" in first
    assert "session" in first
    assert "trend" in first
    assert "dxy_state" in first
    assert "outcome" in first
    assert "matching_variables" in first

def test_instrument_dna_endpoint():
    """Verify instrument DNA returns statistical profile."""
    response = client.get("/api/v1/instruments/GBPUSD/dna")
    assert response.status_code == 200
    dna = response.json()
    assert dna["instrument"] == "GBPUSD"
    assert "normal_mae_50" in dna
    assert "normal_mae_90" in dna
    assert "normal_mfe" in dna
    assert "best_session" in dna
    assert "worst_session" in dna
    assert "continuation_rate" in dna
    assert "best_dxy_state" in dna
    assert "worst_news_env" in dna
    assert "failure_signature" in dna
    assert dna["normal_mae_90"] >= dna["normal_mae_50"], "90th percentile MAE should be >= 50th"

def test_timeline_endpoint():
    """Verify decision timeline returns sequential events."""
    response = client.get("/api/v1/dashboard/timeline")
    assert response.status_code == 200
    timeline = response.json()
    assert isinstance(timeline, list)
    assert len(timeline) >= 3
    for event in timeline:
        assert "time" in event
        assert "event" in event
        assert "dxy" in event
        assert "sentiment" in event
        assert "narrative" in event

def test_trade_planner_survival_rate():
    """Verify trade planner returns MAE percentile and survival rate."""
    # Tight stop — should have low survival
    payload = {
        "instrument": "GBPUSD",
        "entry_price": 1.2540,
        "stop_loss": 1.2536,
        "take_profit": 1.2600,
        "risk_pct": 1.0,
        "account_balance": 10000.0
    }
    response = client.post("/api/v1/trade-planner/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "mae_percentile" in data
    assert "survival_rate" in data
    assert 0 <= data["mae_percentile"] <= 100
    assert 0 <= data["survival_rate"] <= 1.0

def test_chat_challenge():
    """Verify AI challenges low-confidence trade intents."""
    payload = {"message": "I want to buy XAUUSD"}
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "citations" in data
    assert len(data["citations"]) > 0
    # The response should contain reasoning (either agreement or disagreement)
    assert any(kw in data["response"].lower() for kw in ["disagree", "support", "grounded", "statistics"])

