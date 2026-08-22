import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Ticker mapping: internal name -> yfinance symbol
TICKER_MAP = {
    "GBPUSD": "GBPUSD=X",
    "EURUSD": "EURUSD=X",
    "XAUUSD": "GC=F",
    "AUDUSD": "AUDUSD=X",
    "USDJPY": "USDJPY=X",
}

MACRO_TICKERS = {
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "US10Y": "^TNX",
}

ALL_INSTRUMENTS = list(TICKER_MAP.keys())


def fetch_historical_data(instrument: str, period: str = "6y", interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    Downloads historical OHLCV data for a single instrument.
    Falls back to explicit date range if period parameter returns no data (handles system clock offsets).
    """
    ticker_symbol = TICKER_MAP.get(instrument) or MACRO_TICKERS.get(instrument)
    if not ticker_symbol:
        logger.error(f"Unknown instrument: {instrument}")
        return None
    
    try:
        logger.info(f"Fetching {period} of {interval} data for {instrument} ({ticker_symbol})...")
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period, interval=interval)
        
        # Fallback if period fails (e.g. future system clock year)
        if df is None or df.empty:
            logger.info(f"  Period query empty, falling back to explicit start date for {instrument}...")
            # Calculate start date ~6 years ago relative to real time (e.g., 2019)
            df = ticker.history(start="2019-01-01", end="2025-12-31", interval=interval)
        
        if df is None or df.empty:
            logger.warning(f"No data returned for {instrument}")
            return None
        
        df = df.dropna(subset=["Close"])
        
        for col in ["Open", "High", "Low", "Close"]:
            if col not in df.columns:
                logger.error(f"Missing column {col} for {instrument}")
                return None
        
        logger.info(f"  -> Got {len(df)} bars for {instrument} from {df.index[0].date()} to {df.index[-1].date()}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {instrument}: {e}")
        return None


def fetch_intraday_data(instrument: str, period: str = "730d", interval: str = "1h") -> Optional[pd.DataFrame]:
    """
    Downloads intraday OHLCV data (1-hour candles) for a single instrument.
    Falls back to explicit start date if period query returns empty.
    """
    ticker_symbol = TICKER_MAP.get(instrument)
    if not ticker_symbol:
        logger.error(f"Unknown instrument for intraday: {instrument}")
        return None
    
    try:
        logger.info(f"Fetching {period} of {interval} intraday data for {instrument} ({ticker_symbol})...")
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df is None or df.empty:
            logger.info(f"  Intraday period query empty, trying explicit start date for {instrument}...")
            df = ticker.history(start="2024-06-01", end="2025-12-31", interval=interval)
        
        if df is None or df.empty:
            logger.warning(f"No intraday data returned for {instrument}")
            return None
        
        df = df.dropna(subset=["Close"])
        
        for col in ["Open", "High", "Low", "Close"]:
            if col not in df.columns:
                logger.error(f"Missing column {col} for intraday {instrument}")
                return None
        
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC")
        
        logger.info(f"  -> Got {len(df)} intraday bars for {instrument} from {df.index[0]} to {df.index[-1]}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching intraday data for {instrument}: {e}")
        return None


def fetch_all_historical(period: str = "6y") -> Dict[str, pd.DataFrame]:
    """
    Downloads historical daily data for all instruments + macro indicators.
    Returns dict mapping instrument name -> DataFrame.
    """
    all_data = {}
    
    # Fetch forex pairs
    for instrument in ALL_INSTRUMENTS:
        df = fetch_historical_data(instrument, period=period)
        if df is not None and not df.empty:
            all_data[instrument] = df
    
    # Fetch macro indicators
    for name in MACRO_TICKERS:
        df = fetch_historical_data(name, period=period)
        if df is not None and not df.empty:
            all_data[name] = df
    
    return all_data


def fetch_realtime_quotes(instruments: Optional[List[str]] = None) -> Dict[str, Dict]:
    """
    Gets latest price snapshot for instruments.
    Returns dict mapping instrument -> {price, change, change_pct, high, low, timestamp}.
    """
    if instruments is None:
        instruments = ALL_INSTRUMENTS
    
    quotes = {}
    for instrument in instruments:
        ticker_symbol = TICKER_MAP.get(instrument)
        if not ticker_symbol:
            continue
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Get latest 5 days to compute change reliably across weekend / bank holidays
            hist = ticker.history(period="5d", interval="1d")
            if hist.empty or len(hist) < 1:
                continue
            
            latest = hist.iloc[-1]
            prev_close = hist.iloc[-2]["Close"] if len(hist) >= 2 else latest["Close"]
            change = latest["Close"] - prev_close
            change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
            
            quotes[instrument] = {
                "price": round(float(latest["Close"]), 5),
                "open": round(float(latest["Open"]), 5),
                "high": round(float(latest["High"]), 5),
                "low": round(float(latest["Low"]), 5),
                "change": round(float(change), 5),
                "change_pct": round(float(change_pct), 3),
                "timestamp": hist.index[-1].isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching realtime quote for {instrument}: {e}")
    
    return quotes


def fetch_macro_snapshot() -> Dict[str, Dict]:
    """
    Gets current values for DXY, VIX, and US10Y.
    Returns dict with current values and recent history for regime detection.
    """
    snapshot = {}
    for name, ticker_symbol in MACRO_TICKERS.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="1mo", interval="1d")
            if hist.empty:
                continue
            
            latest = hist.iloc[-1]
            closes = hist["Close"].tolist()
            
            snapshot[name] = {
                "current": round(float(latest["Close"]), 4),
                "high_52w": round(float(hist["Close"].max()), 4),
                "low_52w": round(float(hist["Close"].min()), 4),
                "sma_5": round(float(hist["Close"].tail(5).mean()), 4),
                "sma_20": round(float(hist["Close"].tail(20).mean()), 4),
                "recent_closes": closes[-20:],  # Last 20 for trend computation
                "percentile_75": round(float(np.percentile(closes, 75)), 4),
                "percentile_25": round(float(np.percentile(closes, 25)), 4),
            }
        except Exception as e:
            logger.error(f"Error fetching macro data for {name}: {e}")
    
    return snapshot


def get_pip_size(instrument: str) -> float:
    """Returns the pip size for the instrument (used for MAE/MFE calculations)."""
    if "JPY" in instrument:
        return 0.01   # JPY pairs: 2 decimal places
    elif "XAU" in instrument or "GOLD" in instrument:
        return 0.1    # Gold: 1 decimal place movement = 1 pip
    else:
        return 0.0001  # Standard FX: 4 decimal places


def get_pip_multiplier(instrument: str) -> float:
    """Returns multiplier to convert price difference to pips."""
    return 1.0 / get_pip_size(instrument)
