import datetime
import pytest
from unittest.mock import MagicMock, patch
from app.main import get_active_instrument_direction

def test_get_active_instrument_direction_explicit():
    db = MagicMock()
    today = datetime.date.today()
    assert get_active_instrument_direction(db, "AUDUSD", today, "LONG") == "BULLISH"
    assert get_active_instrument_direction(db, "AUDUSD", today, "BUY") == "BULLISH"
    assert get_active_instrument_direction(db, "AUDUSD", today, "SHORT") == "BEARISH"
    assert get_active_instrument_direction(db, "AUDUSD", today, "SELL") == "BEARISH"

def test_get_active_instrument_direction_fallback_to_watchlist_winner():
    db = MagicMock()
    today = datetime.date.today()
    
    # Mock dual profiles where short is READY and long is WAIT
    mock_dual = {
        "long": {
            "instrument": "AUDUSD",
            "direction": "LONG",
            "status_state": "WAIT",
            "confidence_score": 55.0
        },
        "short": {
            "instrument": "AUDUSD",
            "direction": "SHORT",
            "status_state": "READY",
            "confidence_score": 70.0
        }
    }
    
    with patch("app.main.DecisionIntelligenceEngine.generate_dual_profiles", return_value=mock_dual):
        # Without explicit direction, it should pick SHORT (READY > WAIT) -> BEARISH
        result = get_active_instrument_direction(db, "AUDUSD", today, None)
        assert result == "BEARISH"
