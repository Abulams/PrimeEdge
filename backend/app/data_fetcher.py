import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
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
    "US100":  "NQ=F",
    "AUDJPY": "AUDJPY=X",
}

MACRO_TICKERS = {
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "US10Y": "^TNX",
}

ALL_INSTRUMENTS = list(TICKER_MAP.keys())



import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# In-memory TTL cache: key -> (timestamp, data)
_CACHE: Dict[str, Tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()

def _get_from_cache(key: str, ttl_seconds: float) -> Optional[Any]:
    with _CACHE_LOCK:
        if key in _CACHE:
            ts, val = _CACHE[key]
            if time.time() - ts < ttl_seconds:
                return val
    return None

def _set_in_cache(key: str, val: Any) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (time.time(), val)


def fetch_historical_data(instrument: str, period: str = "6y", interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    Downloads historical OHLCV data for a single instrument with 1-hour TTL cache.
    Falls back to explicit date range if period parameter returns no data.
    """
    cache_key = f"hist_{instrument}_{period}_{interval}"
    cached = _get_from_cache(cache_key, ttl_seconds=3600)
    if cached is not None:
        return cached

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
        _set_in_cache(cache_key, df)
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {instrument}: {e}")
        return None


def fetch_intraday_data(instrument: str, period: str = "730d", interval: str = "1h") -> Optional[pd.DataFrame]:
    """
    Downloads intraday OHLCV data (1-hour candles) with 10-minute TTL cache.
    """
    cache_key = f"intraday_{instrument}_{period}_{interval}"
    cached = _get_from_cache(cache_key, ttl_seconds=600)
    if cached is not None:
        return cached

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
        _set_in_cache(cache_key, df)
        return df
        
    except Exception as e:
        logger.error(f"Error fetching intraday data for {instrument}: {e}")
        return None


def fetch_all_historical(period: str = "6y") -> Dict[str, pd.DataFrame]:
    """
    Downloads historical daily data in parallel across all instruments + macro indicators.
    """
    all_targets = ALL_INSTRUMENTS + list(MACRO_TICKERS.keys())
    all_data = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_inst = {
            executor.submit(fetch_historical_data, inst, period): inst
            for inst in all_targets
        }
        for future in as_completed(future_to_inst):
            inst = future_to_inst[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    all_data[inst] = df
            except Exception as e:
                logger.error(f"Parallel history fetch failed for {inst}: {e}")

    return all_data


def _fetch_single_quote(instrument: str) -> Optional[Tuple[str, Dict]]:
    ticker_symbol = TICKER_MAP.get(instrument)
    if not ticker_symbol:
        return None
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Primary: fast_info provides real-time tick price matching TradingView
        fast = getattr(ticker, "fast_info", None)
        if fast is not None:
            try:
                last_p = float(fast.last_price)
                if last_p > 0:
                    prev_c = float(fast.previous_close) if getattr(fast, "previous_close", None) else last_p
                    open_p = float(fast.open) if getattr(fast, "open", None) else last_p
                    day_h = float(fast.day_high) if getattr(fast, "day_high", None) else last_p
                    day_l = float(fast.day_low) if getattr(fast, "day_low", None) else last_p
                    change = last_p - prev_c
                    change_pct = (change / prev_c) * 100 if prev_c != 0 else 0.0

                    return instrument, {
                        "price": round(last_p, 5),
                        "open": round(open_p, 5),
                        "high": round(day_h, 5),
                        "low": round(day_l, 5),
                        "change": round(change, 5),
                        "change_pct": round(change_pct, 3),
                        "timestamp": datetime.utcnow().isoformat()
                    }
            except Exception:
                pass

        # Fallback: 1d 1m history
        hist = ticker.history(period="1d", interval="1m")
        if hist.empty:
            hist = ticker.history(period="5d", interval="1d")
        if hist.empty or len(hist) < 1:
            return None
        
        latest = hist.iloc[-1]
        prev_close = hist.iloc[-2]["Close"] if len(hist) >= 2 else latest["Close"]
        change = latest["Close"] - prev_close
        change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
        
        return instrument, {
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
        return None


def fetch_realtime_quotes(instruments: Optional[List[str]] = None) -> Dict[str, Dict]:
    """
    Gets latest price snapshot in parallel for instruments with 5s TTL cache.
    """
    if instruments is None:
        instruments = ALL_INSTRUMENTS

    inst_key = "_".join(sorted(instruments))
    cache_key = f"quotes_{inst_key}"
    cached = _get_from_cache(cache_key, ttl_seconds=5)
    if cached is not None:
        return cached


    quotes = {}
    with ThreadPoolExecutor(max_workers=min(len(instruments), 8)) as executor:
        futures = [executor.submit(_fetch_single_quote, inst) for inst in instruments]
        for future in as_completed(futures):
            res = future.result()
            if res:
                inst, data = res
                quotes[inst] = data

    if quotes:
        _set_in_cache(cache_key, quotes)
    return quotes


def _fetch_single_macro(name: str, ticker_symbol: str) -> Optional[Tuple[str, Dict]]:
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1mo", interval="1d")
        if hist.empty:
            return None
        
        latest = hist.iloc[-1]
        closes = hist["Close"].tolist()
        
        return name, {
            "current": round(float(latest["Close"]), 4),
            "high_52w": round(float(hist["Close"].max()), 4),
            "low_52w": round(float(hist["Close"].min()), 4),
            "sma_5": round(float(hist["Close"].tail(5).mean()), 4),
            "sma_20": round(float(hist["Close"].tail(20).mean()), 4),
            "recent_closes": closes[-20:],
            "percentile_75": round(float(np.percentile(closes, 75)), 4),
            "percentile_25": round(float(np.percentile(closes, 25)), 4),
        }
    except Exception as e:
        logger.error(f"Error fetching macro data for {name}: {e}")
        return None


def fetch_macro_snapshot() -> Dict[str, Dict]:
    """
    Gets current values for DXY, VIX, and US10Y in parallel with 60s TTL cache.
    """
    cache_key = "macro_snapshot"
    cached = _get_from_cache(cache_key, ttl_seconds=60)
    if cached is not None:
        return cached

    snapshot = {}
    with ThreadPoolExecutor(max_workers=len(MACRO_TICKERS)) as executor:
        futures = [
            executor.submit(_fetch_single_macro, name, sym)
            for name, sym in MACRO_TICKERS.items()
        ]
        for future in as_completed(futures):
            res = future.result()
            if res:
                name, data = res
                snapshot[name] = data

    if snapshot:
        _set_in_cache(cache_key, snapshot)
    return snapshot



def get_pip_size(instrument: str) -> float:
    """Returns the pip size for the instrument (used for MAE/MFE calculations)."""
    if "US100" in instrument or "NAS100" in instrument:
        return 1.0    # Index point = 1.0
    elif "JPY" in instrument:
        return 0.01   # JPY pairs: 2 decimal places
    elif "XAU" in instrument or "GOLD" in instrument:
        return 0.1    # Gold: 1 decimal place movement = 1 pip
    else:
        return 0.0001  # Standard FX: 4 decimal places


def get_pip_multiplier(instrument: str) -> float:
    """Returns multiplier to convert price difference to pips."""
    return 1.0 / get_pip_size(instrument)
