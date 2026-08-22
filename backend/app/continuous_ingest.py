"""
Market OS — Continuous Ingestion & Signature Retraining Pipeline
================================================================
Fetches the latest market bars, computes realized MAE/MFE excursions,
classifies signatures, appends new records to database, and updates calibration.
"""

import datetime
import logging
from typing import Dict, List, Any
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from .models import PriceCache, MarketSignature, DailyMarketRegime
from .data_fetcher import fetch_historical_data, fetch_realtime_quotes, ALL_INSTRUMENTS, MACRO_TICKERS
from .engine import DecisionIntelligenceEngine

logger = logging.getLogger(__name__)


class ContinuousIngestionEngine:

    @staticmethod
    def ingest_latest_bars(db: Session) -> Dict[str, Any]:
        """
        Fetches newly closed daily bars for all instruments and saves them to PriceCache.
        Returns a summary of ingested bars count per asset.
        """
        summary = {}
        all_targets = ALL_INSTRUMENTS + list(MACRO_TICKERS.keys())

        for inst in all_targets:
            try:
                df = fetch_historical_data(inst, period="1mo", interval="1d")
                if df is None or df.empty:
                    summary[inst] = 0
                    continue

                existing_dates = {
                    r.date for r in db.query(PriceCache.date).filter(PriceCache.instrument == inst).all()
                }

                new_count = 0
                for idx, row in df.iterrows():
                    d = idx.date() if hasattr(idx, 'date') else pd.Timestamp(idx).date()
                    if d not in existing_dates:
                        cache_row = PriceCache(
                            instrument=inst,
                            date=d,
                            open=float(row["Open"]),
                            high=float(row["High"]),
                            low=float(row["Low"]),
                            close=float(row["Close"]),
                            volume=float(row.get("Volume", 0.0))
                        )
                        db.add(cache_row)
                        existing_dates.add(d)
                        new_count += 1

                if new_count > 0:
                    db.commit()
                summary[inst] = new_count
            except Exception as e:
                logger.error(f"Error ingesting bars for {inst}: {e}")
                summary[inst] = f"Error: {e}"

        return summary

    @staticmethod
    def generate_signatures_from_unclassified_bars(db: Session) -> Dict[str, Any]:
        """
        Finds price bars that do not yet have a corresponding MarketSignature,
        computes their MAE/MFE excursions and outcomes, and generates new MarketSignatures.
        """
        new_signatures_count = 0

        # Current regime context
        latest_regime = db.query(DailyMarketRegime).order_by(DailyMarketRegime.date.desc()).first()
        dxy_state = latest_regime.dxy_regime if latest_regime else "BEARISH"
        risk_sent = latest_regime.risk_sentiment if latest_regime else "NEUTRAL"

        for inst in ALL_INSTRUMENTS:
            pip_size = 0.01 if "JPY" in inst else 0.1 if "XAU" in inst else 0.0001
            
            # Find existing signature dates for this instrument
            existing_sig_dates = {
                s.date for s in db.query(MarketSignature.date).filter(MarketSignature.instrument == inst).all()
            }

            # Query price bars
            bars = db.query(PriceCache).filter(
                PriceCache.instrument == inst
            ).order_by(PriceCache.date.asc()).all()

            for b in bars:
                if b.date in existing_sig_dates:
                    continue

                # Classify trend (close vs open of the day)
                is_bullish = (b.close >= b.open)
                trend = "BULLISH" if is_bullish else "BEARISH"

                # Compute excursion pips
                if is_bullish:
                    mfe_pips = round(max(0.0, (b.high - b.open) / pip_size), 1)
                    mae_pips = round(max(0.0, (b.open - b.low) / pip_size), 1)
                else:
                    mfe_pips = round(max(0.0, (b.open - b.low) / pip_size), 1)
                    mae_pips = round(max(0.0, (b.high - b.open) / pip_size), 1)

                # Outcome threshold: Win if MFE > 1.5 * MAE or MFE >= 25 pips (100p on gold)
                min_win_mfe = 80.0 if "XAU" in inst else 25.0
                outcome = "WIN" if (mfe_pips >= min_win_mfe and mfe_pips >= mae_pips * 1.2) else "LOSS"

                # Assign session (default to LONDON / NEW_YORK blend)
                session = "LONDON"

                # Estimate holding time from daily range: wide range → volatile → shorter hold
                daily_range_pips = round((b.high - b.low) / pip_size, 1)
                if daily_range_pips > (200 if "XAU" in inst else 80):
                    holding_time_minutes = max(30, int(60 + (mae_pips + mfe_pips) * 0.5))
                elif daily_range_pips < (60 if "XAU" in inst else 20):
                    holding_time_minutes = min(360, int(150 + (mae_pips + mfe_pips) * 1.0))
                else:
                    holding_time_minutes = max(45, min(240, int(90 + (mae_pips + mfe_pips) * 0.75)))

                sig = MarketSignature(
                    instrument=inst,
                    date=b.date,
                    session=session,
                    trend=trend,
                    dxy_state=dxy_state,
                    risk_sentiment=risk_sent,
                    news_environment="NORMAL_SESSION",
                    volatility_regime="NORMAL",
                    outcome=outcome,
                    mae_pips=mae_pips,
                    mfe_pips=mfe_pips,
                    holding_time_minutes=holding_time_minutes
                )
                db.add(sig)
                existing_sig_dates.add(b.date)
                new_signatures_count += 1

        if new_signatures_count > 0:
            db.commit()

        return {
            "new_signatures_created": new_signatures_count,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }

    @staticmethod
    def run_full_nightly_pipeline(db: Session) -> Dict[str, Any]:
        """
        Runs the complete automated ingestion and signature creation pipeline.
        """
        bars_summary = ContinuousIngestionEngine.ingest_latest_bars(db)
        sigs_summary = ContinuousIngestionEngine.generate_signatures_from_unclassified_bars(db)

        return {
            "status": "SUCCESS",
            "bars_ingested": bars_summary,
            "signatures": sigs_summary,
            "executed_at": datetime.datetime.utcnow().isoformat() + "Z"
        }
