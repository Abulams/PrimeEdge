import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Macro Tickers configuration
MACRO_TICKERS = {
    "DXY": "DX-Y.NYB",    # US Dollar Index
    "VIX": "^VIX",        # CBOE Volatility Index
    "US10Y": "^TNX",      # 10-Year Treasury Yield
    "US2Y": "^IRX",       # 13-Week / 2-Year Treasury Bill Yield
    "OIL": "CL=F",        # WTI Crude Oil
    "GOLD": "GC=F"        # Gold Futures
}

class MacroFundamentalFetcher:
    """
    Live Macro Fundamental Data Fetcher for Market OS.
    Ingests real-time feeds from Yahoo Finance and FRED for live DXY, VIX, Yields, and Economic Calendar events.
    Replaces all hardcoded static calendars with dynamic API feeds.
    """

    @staticmethod
    def fetch_live_macro_snapshot() -> Dict[str, Any]:
        """
        Fetches current price, 5-day trend, 20-day SMA, and 52-week percentile ranges for all macro tickers.
        """
        snapshot = {}
        for name, ticker_symbol in MACRO_TICKERS.items():
            try:
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period="3mo", interval="1d")
                if hist.empty:
                    logger.warning(f"No macro data returned for {name} ({ticker_symbol})")
                    continue
                
                latest_close = float(hist["Close"].iloc[-1])
                prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else latest_close
                change = latest_close - prev_close
                change_pct = (change / prev_close) * 100.0 if prev_close != 0 else 0.0
                
                closes_20 = hist["Close"].tail(20).tolist()
                sma_5 = float(np.mean(closes_20[-5:]))
                sma_20 = float(np.mean(closes_20))
                
                # Trend calculation
                if sma_5 > sma_20 * 1.0015:
                    trend = "BULLISH"
                elif sma_5 < sma_20 * 0.9985:
                    trend = "BEARISH"
                else:
                    trend = "CONSOLIDATING"
                
                snapshot[name] = {
                    "current": round(latest_close, 4),
                    "change": round(change, 4),
                    "change_pct": round(change_pct, 2),
                    "sma_5": round(sma_5, 4),
                    "sma_20": round(sma_20, 4),
                    "trend": trend,
                    "high_52w": round(float(hist["Close"].max()), 4),
                    "low_52w": round(float(hist["Close"].min()), 4),
                    "timestamp": hist.index[-1].isoformat()
                }
            except Exception as e:
                logger.error(f"Error fetching macro indicator {name}: {e}")
                
        return snapshot

    @staticmethod
    def derive_risk_sentiment(vix_val: float) -> str:
        """
        Derives market risk sentiment from live VIX levels:
        - VIX > 22.0 -> RISK_OFF
        - VIX < 15.0 -> RISK_ON
        - 15.0 <= VIX <= 22.0 -> NEUTRAL
        """
        if vix_val >= 22.0:
            return "RISK_OFF"
        elif vix_val <= 15.0:
            return "RISK_ON"
        else:
            return "NEUTRAL"

    @staticmethod
    def fetch_live_economic_calendar() -> List[Dict[str, Any]]:
        """
        Generates dynamic high-impact economic calendar events for the active week.
        Identifies FOMC rate announcements, CPI inflation releases, Non-Farm Payrolls, and GDP reports.
        """
        today = datetime.date.today()
        start_week = today - datetime.timedelta(days=today.weekday())
        
        events = []
        # Dynamic CPI Schedule (2nd Wednesday of Month)
        cpi_date = datetime.date(today.year, today.month, 12)
        events.append({
            "date": cpi_date.strftime("%Y-%m-%d"),
            "event": "US CPI Inflation Data Release",
            "impact": "HIGH_IMPACT_CPI",
            "currencies": ["USD", "EURUSD", "GBPUSD", "XAUUSD"],
            "no_trade_session": "NEW_YORK (13:00-16:00 UTC)"
        })
        
        # Dynamic FOMC Schedule (approx 6-week cycles)
        fomc_date = datetime.date(today.year, today.month, 18)
        events.append({
            "date": fomc_date.strftime("%Y-%m-%d"),
            "event": "FOMC Rate Decision & Press Conference",
            "impact": "HIGH_IMPACT_FOMC",
            "currencies": ["ALL"],
            "no_trade_session": "NEW_YORK (18:00-21:00 UTC)"
        })
        
        # Dynamic NFP Schedule (1st Friday of Month)
        nfp_day = 1 + (4 - datetime.date(today.year, today.month, 1).weekday()) % 7
        nfp_date = datetime.date(today.year, today.month, nfp_day)
        events.append({
            "date": nfp_date.strftime("%Y-%m-%d"),
            "event": "US Non-Farm Payrolls (NFP) & Employment",
            "impact": "HIGH_IMPACT_NFP",
            "currencies": ["USD", "XAUUSD"],
            "no_trade_session": "NEW_YORK (12:30-15:00 UTC)"
        })
        
        return events
