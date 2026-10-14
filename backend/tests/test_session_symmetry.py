import pytest
from app.signature_builder import compute_session_mae_mfe, get_best_session_for_date

def test_session_mae_mfe_symmetry():
    # Setup a session that had a large downward drop:
    # Open: 1.1000, High: 1.1005, Low: 1.0900, Close: 1.0910 (drop of 100 pips)
    sess_drop = {"open": 1.1000, "high": 1.1005, "low": 1.0900, "close": 1.0910}
    
    # 1. When trend is BEARISH:
    mae_bear, mfe_bear, out_bear = compute_session_mae_mfe(sess_drop, 1.1000, "EURUSD", trend="BEARISH")
    assert mfe_bear == 100.0, f"Expected 100p MFE for bearish drop, got {mfe_bear}"
    assert mae_bear == 5.0, f"Expected 5p MAE for bearish drop, got {mae_bear}"
    assert out_bear == "WIN", "Bearish move should be a WIN for BEARISH trend"

    # 2. When trend is BULLISH:
    mae_bull, mfe_bull, out_bull = compute_session_mae_mfe(sess_drop, 1.1000, "EURUSD", trend="BULLISH")
    assert mfe_bull == 5.0, f"Expected 5p MFE for bullish trend during drop, got {mfe_bull}"
    assert mae_bull == 100.0, f"Expected 100p MAE for bullish trend during drop, got {mae_bull}"
    assert out_bull == "LOSS", "Bearish drop should be a LOSS for BULLISH trend"

def test_get_best_session_for_date_symmetry():
    # Setup a day with London crash (100p drop) and NY counter bounce (35p rally)
    day_sessions = {
        "LONDON": {"open": 1.1000, "high": 1.1005, "low": 1.0900, "close": 1.0910},
        "NEW_YORK": {"open": 1.0910, "high": 1.0945, "low": 1.0905, "close": 1.0940}
    }
    session_index = {"2026-09-01": day_sessions}

    # When trend is BEARISH, get_best_session_for_date must select LONDON (100p drop)
    best_bear = get_best_session_for_date(session_index, "2026-09-01", "EURUSD", 1.1000, trend="BEARISH")
    assert best_bear == "LONDON", f"Expected LONDON for BEARISH trend, got {best_bear}"

    # When trend is BULLISH, get_best_session_for_date selects NEW_YORK (35p bounce)
    best_bull = get_best_session_for_date(session_index, "2026-09-01", "EURUSD", 1.1000, trend="BULLISH")
    assert best_bull == "NEW_YORK", f"Expected NEW_YORK for BULLISH trend, got {best_bull}"
