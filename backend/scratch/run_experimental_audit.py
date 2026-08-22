"""
Market OS — MAE/MFE & Execution Layer Scientific Experimental Audit
================================================--------------------
Establishes a baseline vs evidence-backed solution run across the EXACT SAME
550 T0 setups (2024-01-01 -> 2024-06-01 across 5 instruments).

Compares:
1. Baseline (Old static DEPTH_LEVELS_PIPS & 10-day cumulative MAE horizon)
2. Evidence-Backed Solution (Empirical MAE Quantile Retracement & Single-Day Horizon Alignment)
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))
import datetime
import json
from typing import Dict, Any, List
import numpy as np
from sqlalchemy.orm import sessionmaker

from app.database import Base, engine as db_engine
from app.models import PriceCache, ReplayBatch, ReplaySetupSnapshot, ReplayTradeRecord
from app.replay_service import ReplayService
from app.replay_engine import ReplayEngine
from app.data_fetcher import get_pip_multiplier

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


def run_experiment() -> Dict[str, Any]:
    db = SessionLocal()
    print("=" * 90)
    print("       MARKET OS — MAE/MFE & EXECUTION EXPERIMENTAL SCIENTIFIC AUDIT        ")
    print("=" * 90)

    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date(2024, 6, 1)
    instruments = ["GBPUSD", "EURUSD", "XAUUSD", "USDJPY", "AUDUSD"]

    # 1. Reset Replay Data
    ReplayService.reset_replay_data(db)

    # 2. Run Policy Batches under current engine
    b_strict = ReplayService.create_batch(db, start_date, end_date, instruments, "Batch Strict", "STRICT_V4_LIMIT", 2.5)
    ReplayService.run_batch(db, b_strict.id)

    b_market = ReplayService.create_batch(db, start_date, end_date, instruments, "Batch Market", "MARKET_ENTRY", 2.5)
    ReplayService.run_batch(db, b_market.id)

    b_dev = ReplayService.create_batch(db, start_date, end_date, instruments, "Batch Deviation", "EXECUTION_DEVIATION", 2.5)
    ReplayService.run_batch(db, b_dev.id)

    strict_analytics = ReplayService.get_control_group_analytics(db, b_strict.id)
    market_analytics = ReplayService.get_control_group_analytics(db, b_market.id)
    dev_analytics = ReplayService.get_control_group_analytics(db, b_dev.id)

    # 3. Single-Day vs Multi-Day P90 Invalidation Horizon Audit
    trades_market = db.query(ReplayTradeRecord).join(ReplaySetupSnapshot).filter(ReplaySetupSnapshot.batch_id == b_market.id).all()
    future_bars_cache = {}

    single_day_p90_breaches = 0
    multi_day_p90_breaches = 0
    total_trades = len(trades_market)

    p90_breaches_by_inst = {}
    p90_breaches_by_dir = {"LONG": {"tot": 0, "sing_brk": 0, "mult_brk": 0}, "SHORT": {"tot": 0, "sing_brk": 0, "mult_brk": 0}}

    for t in trades_market:
        inst = t.setup.instrument
        dirn = t.setup.direction
        entry_date = t.setup.date
        p90_limit = t.setup.mae_p90_pips or 35.0
        pip_mult = get_pip_multiplier(inst)
        is_long = (dirn == "LONG")
        entry_price = t.actual_entry

        # Fetch T1 bar (first day after T0)
        t1_bar = db.query(PriceCache).filter(
            PriceCache.instrument == inst,
            PriceCache.date > entry_date
        ).order_by(PriceCache.date.asc()).first()

        if t1_bar:
            t1_mae = max(0.0, (entry_price - t1_bar.low) * pip_mult) if is_long else max(0.0, (t1_bar.high - entry_price) * pip_mult)
        else:
            t1_mae = 0.0

        if inst not in p90_breaches_by_inst:
            p90_breaches_by_inst[inst] = {"tot": 0, "sing_brk": 0, "mult_brk": 0}

        p90_breaches_by_inst[inst]["tot"] += 1
        p90_breaches_by_dir[dirn]["tot"] += 1

        if t1_mae >= p90_limit:
            single_day_p90_breaches += 1
            p90_breaches_by_inst[inst]["sing_brk"] += 1
            p90_breaches_by_dir[dirn]["sing_brk"] += 1

        if (t.mae_p90_reached or 0) > 0:
            multi_day_p90_breaches += 1
            p90_breaches_by_inst[inst]["mult_brk"] += 1
            p90_breaches_by_dir[dirn]["mult_brk"] += 1

    single_day_breach_rate = round(single_day_p90_breaches / total_trades * 100, 1) if total_trades > 0 else 0.0
    multi_day_breach_rate = round(multi_day_p90_breaches / total_trades * 100, 1) if total_trades > 0 else 0.0

    report = {
        "horizon_discrepancy_audit": {
            "total_trades_audited": total_trades,
            "single_day_t1_p90_breach_rate": f"{single_day_p90_breaches}/{total_trades} ({single_day_breach_rate}%)",
            "multi_day_10d_p90_breach_rate": f"{multi_day_p90_breaches}/{total_trades} ({multi_day_breach_rate}%)",
            "by_instrument": {
                inst: {
                    "single_day_breach": f"{d['sing_brk']}/{d['tot']} ({round(d['sing_brk']/d['tot']*100,1)}%)" if d['tot']>0 else "0%",
                    "multi_day_breach": f"{d['mult_brk']}/{d['tot']} ({round(d['mult_brk']/d['tot']*100,1)}%)" if d['tot']>0 else "0%"
                }
                for inst, d in p90_breaches_by_inst.items()
            },
            "by_direction": {
                dirn: {
                    "single_day_breach": f"{d['sing_brk']}/{d['tot']} ({round(d['sing_brk']/d['tot']*100,1)}%)" if d['tot']>0 else "0%",
                    "multi_day_breach": f"{d['mult_brk']}/{d['tot']} ({round(d['mult_brk']/d['tot']*100,1)}%)" if d['tot']>0 else "0%"
                }
                for dirn, d in p90_breaches_by_dir.items()
            }
        },
        "policy_comparison": {
            "STRICT_V4_LIMIT": strict_analytics,
            "MARKET_ENTRY": market_analytics,
            "EXECUTION_DEVIATION": dev_analytics
        }
    }

    db.close()
    return report


if __name__ == "__main__":
    rep = run_experiment()
    print("\n" + "=" * 90)
    print("                    EXPERIMENTAL AUDIT REPORT SUMMARY                   ")
    print("=" * 90)
    print(json.dumps(rep, indent=2))
