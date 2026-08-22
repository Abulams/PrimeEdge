import datetime
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
import logging
import csv
import os

from .models import MarketSignature, DailyMarketRegime, PriceCache
from .engine import SignatureEngine
from .data_fetcher import get_pip_multiplier, ALL_INSTRUMENTS

logger = logging.getLogger(__name__)

# Load macro calendar from static CSV (FOMC + CPI real dates)
_MACRO_CALENDAR: Dict[datetime.date, str] = {}

def _load_macro_calendar():
    """Loads the static macro_calendar.csv into a date -> impact lookup dict."""
    global _MACRO_CALENDAR
    csv_path = os.path.join(os.path.dirname(__file__), "macro_calendar.csv")
    if not os.path.exists(csv_path):
        logger.warning(f"Macro calendar CSV not found at {csv_path}, news_environment will default to LOW_IMPACT")
        return
    
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                d = datetime.datetime.strptime(row["date"].strip(), "%Y-%m-%d").date()
                impact = row["impact"].strip()
                # If multiple events on same day, prefer FOMC over CPI
                if d in _MACRO_CALENDAR and "FOMC" in _MACRO_CALENDAR[d]:
                    continue
                _MACRO_CALENDAR[d] = impact
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping malformed row in macro_calendar.csv: {row} ({e})")
    
    logger.info(f"Loaded {len(_MACRO_CALENDAR)} macro event dates from CSV")

# Load on module import
_load_macro_calendar()


def classify_session_from_hour(hour: int) -> str:
    """Maps UTC hour to trading session."""
    if 0 <= hour < 7:
        return "ASIA"
    elif 7 <= hour < 13:
        return "LONDON"
    else:
        return "NEW_YORK"


def determine_dxy_regime(dxy_closes: List[float]) -> str:
    """
    Determines DXY regime from recent closing prices.
    Uses 5-day SMA vs 20-day SMA crossover.
    """
    if len(dxy_closes) < 20:
        return "CONSOLIDATING"

    sma_5 = np.mean(dxy_closes[-5:])
    sma_20 = np.mean(dxy_closes[-20:])
    diff_pct = (sma_5 - sma_20) / sma_20 * 100

    if diff_pct > 0.15:
        return "BULLISH"
    elif diff_pct < -0.15:
        return "BEARISH"
    else:
        return "CONSOLIDATING"


def determine_risk_sentiment(vix_value: float, vix_history: List[float]) -> str:
    """
    Determines risk sentiment from VIX levels using standardized thresholds:
    - VIX > 20.0: RISK_OFF (high fear, safe haven flight)
    - VIX < 15.0: RISK_ON (low fear, risk asset expansion)
    - Otherwise: NEUTRAL
    """
    if vix_value > 20.0:
        return "RISK_OFF"
    elif vix_value < 15.0:
        return "RISK_ON"
    else:
        return "NEUTRAL"


def determine_yields_regime(us10y_closes: List[float]) -> str:
    """Determines yield curve behavior from US 10Y data."""
    if len(us10y_closes) < 10:
        return "STEEPENING"

    recent = np.mean(us10y_closes[-5:])
    older = np.mean(us10y_closes[-20:]) if len(us10y_closes) >= 20 else np.mean(us10y_closes)

    if recent > older * 1.01:
        return "STEEPENING"
    elif recent < older * 0.99:
        return "FLATTENING"
    else:
        return "FLAT"


def determine_news_environment(date: datetime.date) -> str:
    """Determines news environment using the static macro calendar CSV."""
    return _MACRO_CALENDAR.get(date, "LOW_IMPACT")


def compute_daily_mae_mfe(
    row: pd.Series,
    prev_close: float,
    instrument: str,
    trend: str = "BULLISH",
    atr_5_pips: float = 0.0
) -> Tuple[float, float, str]:
    """
    Computes MAE, MFE, and outcome for a setup aligned with the setup TREND direction:
    - BULLISH trend: LONG trade (MFE = High - Open, MAE = Open - Low)
    - BEARISH trend: SHORT trade (MFE = Open - Low, MAE = High - Open)
    - RANGING trend: Direction of candle close relative to open
    Returns (mae_pips, mfe_pips, outcome).
    """
    pip_mult = get_pip_multiplier(instrument)

    open_price = float(row["Open"])
    high = float(row["High"])
    low = float(row["Low"])
    close = float(row["Close"])

    if trend == "BULLISH":
        is_long = True
    elif trend == "BEARISH":
        is_long = False
    else:
        is_long = close >= open_price

    if is_long:
        mfe = (high - open_price) * pip_mult
        mae = (open_price - low) * pip_mult
        net_expansion = (close - open_price) * pip_mult
    else:
        mfe = (open_price - low) * pip_mult
        mae = (high - open_price) * pip_mult
        net_expansion = (open_price - close) * pip_mult

    mae = max(0.0, round(mae, 1))
    mfe = max(0.0, round(mfe, 1))

    # WIN condition: favorable excursion substantially exceeded adverse excursion.
    # yfinance daily FX Open ≈ prev_close so (close - open) net is near-zero; use MFE vs MAE ratio instead.
    # A session is a WIN if price moved at least 1.2x as far in trade direction as against it.
    if mfe > 0 and mfe >= 1.2 * mae:
        outcome = "WIN"
    else:
        outcome = "LOSS"

    return mae, mfe, outcome


# Session time boundaries (UTC hours)
SESSION_BOUNDARIES = {
    "ASIA":     (0, 7),    # 00:00 - 06:59 UTC
    "LONDON":   (7, 15),   # 07:00 - 14:59 UTC
    "NEW_YORK": (13, 21),  # 13:00 - 20:59 UTC (overlaps with London)
}


def build_intraday_session_index(
    intraday_df: Optional[pd.DataFrame]
) -> Dict[datetime.date, Dict[str, Dict]]:
    """
    Groups 1-hour candles by date and session bucket.
    Returns: { date -> { session -> { "high": float, "low": float, "open": float, "close": float } } }
    """
    if intraday_df is None or intraday_df.empty:
        return {}

    session_index: Dict[datetime.date, Dict[str, Dict]] = {}

    for idx, row in intraday_df.iterrows():
        dt = idx
        d = dt.date() if hasattr(dt, 'date') else dt
        hour = dt.hour if hasattr(dt, 'hour') else 12

        # Determine which session(s) this candle belongs to
        sessions_hit = []
        for session_name, (start_h, end_h) in SESSION_BOUNDARIES.items():
            if start_h <= hour < end_h:
                sessions_hit.append(session_name)

        if not sessions_hit:
            sessions_hit = ["NEW_YORK"]  # Late-night fallback

        if d not in session_index:
            session_index[d] = {}

        h = float(row["High"])
        l = float(row["Low"])
        o = float(row["Open"])
        c = float(row["Close"])

        for sess in sessions_hit:
            if sess not in session_index[d]:
                session_index[d][sess] = {"high": h, "low": l, "open": o, "close": c}
            else:
                existing = session_index[d][sess]
                existing["high"] = max(existing["high"], h)
                existing["low"] = min(existing["low"], l)
                existing["close"] = c  # Last candle close wins

    return session_index


def compute_session_mae_mfe(
    session_data: Dict,
    prev_close: float,
    instrument: str,
    trend: str = "BULLISH",
    atr_5_pips: float = 0.0
) -> Tuple[float, float, str]:
    """
    Computes MAE/MFE for a specific session window aligned with setup trend direction.
    """
    pip_mult = get_pip_multiplier(instrument)

    sess_open = session_data.get("open", prev_close)
    high = session_data["high"]
    low = session_data["low"]
    close = session_data["close"]

    if trend == "BULLISH":
        is_long = True
    elif trend == "BEARISH":
        is_long = False
    else:
        is_long = close >= sess_open

    if is_long:
        mfe = (high - sess_open) * pip_mult
        mae = (sess_open - low) * pip_mult
        net_expansion = (close - sess_open) * pip_mult
    else:
        mfe = (sess_open - low) * pip_mult
        mae = (high - sess_open) * pip_mult
        net_expansion = (sess_open - close) * pip_mult

    mae = max(0.0, round(mae, 1))
    mfe = max(0.0, round(mfe, 1))

    # WIN condition: favorable excursion >= 1.2x adverse excursion in trade direction.
    if mfe > 0 and mfe >= 1.2 * mae:
        outcome = "WIN"
    else:
        outcome = "LOSS"

    return mae, mfe, outcome


def get_best_session_for_date(
    session_index: Dict[datetime.date, Dict[str, Dict]],
    current_date: datetime.date,
    instrument: str,
    prev_close: float
) -> str:
    """
    Determines the actual best session for a given date by checking which
    session had the highest MFE (most favorable price movement).
    Falls back to the structural session if no intraday data exists.
    """
    from .engine import DecisionIntelligenceEngine
    
    if current_date not in session_index:
        return DecisionIntelligenceEngine.get_best_session(instrument)

    day_sessions = session_index[current_date]
    pip_mult = get_pip_multiplier(instrument)
    
    best_sess = None
    best_mfe = -1.0

    for sess_name, sess_data in day_sessions.items():
        _, mfe, _ = compute_session_mae_mfe(sess_data, prev_close, instrument)
        if mfe > best_mfe:
            best_mfe = mfe
            best_sess = sess_name

    return best_sess or DecisionIntelligenceEngine.get_best_session(instrument)


def build_signatures_for_instrument(
    db: Session,
    instrument: str,
    ohlcv_df: pd.DataFrame,
    dxy_df: Optional[pd.DataFrame],
    vix_df: Optional[pd.DataFrame],
    us10y_df: Optional[pd.DataFrame],
    session_index: Optional[Dict[datetime.date, Dict[str, Dict]]] = None
) -> int:
    """
    Converts OHLCV data into MarketSignature records and saves to database.
    If session_index is provided (from 1h intraday data), uses it for
    accurate session assignment and session-level MAE/MFE computation.
    Returns the number of signatures created.
    """
    if ohlcv_df is None or len(ohlcv_df) < 25:
        logger.warning(f"Insufficient data for {instrument}, skipping")
        return 0

    if session_index is None:
        session_index = {}

    # Prepare DXY closes aligned by date
    dxy_closes_by_date = {}
    if dxy_df is not None:
        for idx, row in dxy_df.iterrows():
            d = idx.date() if hasattr(idx, 'date') else idx
            dxy_closes_by_date[d] = float(row["Close"])

    # Prepare VIX closes aligned by date
    vix_closes_by_date = {}
    vix_all_closes = []
    if vix_df is not None:
        for idx, row in vix_df.iterrows():
            d = idx.date() if hasattr(idx, 'date') else idx
            val = float(row["Close"])
            vix_closes_by_date[d] = val
            vix_all_closes.append(val)

    # Prepare US10Y closes
    us10y_closes_by_date = {}
    if us10y_df is not None:
        for idx, row in us10y_df.iterrows():
            d = idx.date() if hasattr(idx, 'date') else idx
            us10y_closes_by_date[d] = float(row["Close"])

    # Build rolling windows
    closes = ohlcv_df["Close"].values.tolist()
    dates = [idx.date() if hasattr(idx, 'date') else idx for idx in ohlcv_df.index]

    # Compute True Range for volatility regime
    highs = ohlcv_df["High"].values
    lows = ohlcv_df["Low"].values
    close_arr = ohlcv_df["Close"].values
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - close_arr[:-1]),
            np.abs(lows[1:] - close_arr[:-1])
        )
    )

    count = 0
    intraday_used = 0
    signatures_batch = []

    for i in range(20, len(ohlcv_df)):
        current_date = dates[i]
        prev_close = closes[i - 1]

        # 1. Compute trend from last 20 closes
        price_window = closes[i-20:i]
        trend = SignatureEngine.calculate_trend(price_window)

        # 2. Compute volatility regime
        if i >= 60:
            current_vols = tr[i-21:i-1].tolist()
            historical_vols = tr[:i-1].tolist()
        else:
            current_vols = tr[max(0, i-21):i-1].tolist()
            historical_vols = tr[:i-1].tolist()
        vol_regime = SignatureEngine.calculate_volatility_regime(current_vols, historical_vols)

        # 3. Determine DXY state
        dxy_window = []
        for j in range(max(0, i-20), i):
            d = dates[j]
            if d in dxy_closes_by_date:
                dxy_window.append(dxy_closes_by_date[d])
        dxy_state = determine_dxy_regime(dxy_window)

        # 4. Risk sentiment from VIX
        vix_val = vix_closes_by_date.get(current_date, 18.0)
        risk_sentiment = determine_risk_sentiment(vix_val, vix_all_closes)

        # 5. News environment
        news_env = determine_news_environment(current_date)

        # Calculate 5-day rolling ATR in pips for adaptive continuation threshold
        pip_mult = get_pip_multiplier(instrument)
        current_vols_5 = tr[i-6:i-1].tolist() if i >= 6 else tr[:i-1].tolist()
        atr_5_pips = (float(np.mean(current_vols_5)) * pip_mult) if current_vols_5 else 0.0

        # 6. MAE/MFE and 8. Session assignment
        # Use intraday session data if available for this date
        if current_date in session_index:
            # Determine the best session from intraday data
            session = get_best_session_for_date(session_index, current_date, instrument, prev_close)
            
            # Use session-level MAE/MFE if the best session has data
            day_sessions = session_index[current_date]
            if session in day_sessions:
                mae, mfe, outcome = compute_session_mae_mfe(
                    day_sessions[session], prev_close, instrument, trend=trend, atr_5_pips=atr_5_pips
                )
            else:
                # Fallback to daily candle
                row = ohlcv_df.iloc[i]
                mae, mfe, outcome = compute_daily_mae_mfe(row, prev_close, instrument, trend=trend, atr_5_pips=atr_5_pips)
            intraday_used += 1
        else:
            # Fallback: daily candle MAE/MFE + structural session assignment
            row = ohlcv_df.iloc[i]
            mae, mfe, outcome = compute_daily_mae_mfe(row, prev_close, instrument, trend=trend, atr_5_pips=atr_5_pips)
            from .engine import DecisionIntelligenceEngine
            session = DecisionIntelligenceEngine.get_best_session(instrument)

        # 7. Continuation/reversal
        row = ohlcv_df.iloc[i]
        day_bullish = float(row["Close"]) >= prev_close
        if trend == "BULLISH" and day_bullish:
            cor = "CONTINUATION"
        elif trend == "BEARISH" and not day_bullish:
            cor = "CONTINUATION"
        else:
            cor = "REVERSAL"

        # 9. Macro snapshot values
        dxy_index_val = dxy_closes_by_date.get(current_date, 104.0)
        us10y_val = us10y_closes_by_date.get(current_date, 4.2)
        vix_val_actual = vix_closes_by_date.get(current_date, 18.0)

        # Holding time estimate based on volatility
        if vol_regime == "HIGH":
            holding = int(np.random.normal(60, 20))
        elif vol_regime == "LOW":
            holding = int(np.random.normal(180, 40))
        else:
            holding = int(np.random.normal(120, 30))
        holding = max(15, min(360, holding))

        sig = MarketSignature(
            instrument=instrument,
            date=current_date,
            session=session,
            trend=trend,
            dxy_state=dxy_state,
            risk_sentiment=risk_sentiment,
            news_environment=news_env,
            volatility_regime=vol_regime,
            continuation_or_reversal=cor,
            mae_pips=mae,
            mfe_pips=mfe,
            holding_time_minutes=holding,
            outcome=outcome,
            supporting_macro_conditions={
                "dxy_index": round(dxy_index_val, 2),
                "us10y_yield": round(us10y_val, 2),
                "vix": round(vix_val_actual, 2)
            }
        )
        signatures_batch.append(sig)
        count += 1

        # Batch insert every 500 rows
        if len(signatures_batch) >= 500:
            db.bulk_save_objects(signatures_batch)
            db.commit()
            signatures_batch = []

    # Final batch
    if signatures_batch:
        db.bulk_save_objects(signatures_batch)
        db.commit()

    logger.info(f"  -> Created {count} signatures for {instrument} ({intraday_used} with intraday session data)")
    return count


def cache_price_data(
    db: Session,
    instrument: str,
    ohlcv_df: pd.DataFrame
) -> int:
    """Stores OHLCV data in PriceCache for quick access."""
    if ohlcv_df is None or ohlcv_df.empty:
        return 0

    count = 0
    batch = []
    for idx, row in ohlcv_df.iterrows():
        d = idx.date() if hasattr(idx, 'date') else idx
        cache_entry = PriceCache(
            instrument=instrument,
            date=d,
            open=round(float(row["Open"]), 6),
            high=round(float(row["High"]), 6),
            low=round(float(row["Low"]), 6),
            close=round(float(row["Close"]), 6),
            volume=round(float(row.get("Volume", 0)), 2) if "Volume" in row.index else None
        )
        batch.append(cache_entry)
        count += 1

        if len(batch) >= 500:
            db.bulk_save_objects(batch)
            db.commit()
            batch = []

    if batch:
        db.bulk_save_objects(batch)
        db.commit()

    return count


def build_daily_regime(
    db: Session,
    date: datetime.date,
    dxy_df: Optional[pd.DataFrame],
    vix_df: Optional[pd.DataFrame],
    us10y_df: Optional[pd.DataFrame]
) -> Optional[DailyMarketRegime]:
    """Creates a DailyMarketRegime entry from real macro data."""
    # DXY closes up to this date
    if dxy_df is not None:
        mask = [idx.date() <= date if hasattr(idx, 'date') else True for idx in dxy_df.index]
        dxy_up_to = dxy_df[mask]
        dxy_closes = dxy_up_to["Close"].tolist()[-20:]
        dxy_val = dxy_closes[-1] if dxy_closes else 104.0
    else:
        dxy_closes = []
        dxy_val = 104.0

    dxy_regime = determine_dxy_regime(dxy_closes)

    # VIX for risk sentiment
    if vix_df is not None:
        mask = [idx.date() <= date if hasattr(idx, 'date') else True for idx in vix_df.index]
        vix_up_to = vix_df[mask]
        vix_closes = vix_up_to["Close"].tolist()
        vix_val = vix_closes[-1] if vix_closes else 18.0
    else:
        vix_closes = []
        vix_val = 18.0

    risk_sentiment = determine_risk_sentiment(vix_val, vix_closes)

    # US10Y for yields
    if us10y_df is not None:
        mask = [idx.date() <= date if hasattr(idx, 'date') else True for idx in us10y_df.index]
        us10y_up_to = us10y_df[mask]
        us10y_closes = us10y_up_to["Close"].tolist()[-20:]
    else:
        us10y_closes = []

    yields_regime = determine_yields_regime(us10y_closes)

    # News environment
    news_env = determine_news_environment(date)
    no_trade_zones = []
    if news_env == "HIGH_IMPACT_FOMC":
        no_trade_zones.append({"session": "NEW_YORK", "reason": "FOMC Meeting Release"})
    elif news_env == "HIGH_IMPACT_CPI":
        no_trade_zones.append({"session": "NEW_YORK", "reason": "US CPI Data Release"})

    summary = (
        f"DXY is {dxy_regime.lower()} at {dxy_val:.2f}. "
        f"VIX at {vix_val:.1f} indicates {risk_sentiment.replace('_', ' ').lower()} conditions. "
        f"US 10Y yields regime is {yields_regime.lower()}."
    )

    # Confidence based on regime clarity
    conf = 70.0
    if dxy_regime != "CONSOLIDATING":
        conf += 5.0
    if risk_sentiment != "NEUTRAL":
        conf += 5.0
    if news_env == "LOW_IMPACT":
        conf += 5.0
    else:
        conf -= 10.0

    regime = DailyMarketRegime(
        date=date,
        dxy_regime=dxy_regime,
        yields_regime=yields_regime,
        risk_sentiment=risk_sentiment,
        no_trade_zones=no_trade_zones,
        macro_summary=summary,
        overall_confidence_score=round(conf, 1)
    )

    db.add(regime)
    return regime
