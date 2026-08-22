"""
Market OS — Dataset/Accounting Reconciliation & P90 Invalidation Audit Script
================================================================---------------
Performs strict mathematical population reconciliation, denominator isolation,
deterministic setup population hashing, row-by-row same-setup policy comparison,
and comprehensive P90 breach breakdown across all supported instruments and policies.
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))
import datetime
import json
import hashlib
from typing import Dict, Any, List
import numpy as np
from sqlalchemy.orm import sessionmaker

from app.database import Base, engine as db_engine
from app.models import PriceCache, ReplayBatch, ReplaySetupSnapshot, ReplayTradeRecord
from app.replay_service import ReplayService
from app.replay_engine import ReplayEngine
from app.data_fetcher import get_pip_multiplier

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


def run_reconciliation_audit() -> Dict[str, Any]:
    db = SessionLocal()
    print("=" * 90)
    print("         MARKET OS — DATASET / ACCOUNTING RECONCILIATION & P90 AUDIT         ")
    print("=" * 90)

    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date(2024, 6, 1)
    instruments = ["GBPUSD", "EURUSD", "XAUUSD", "USDJPY", "AUDUSD"]

    # 1. Clean Replay Tables
    ReplayService.reset_replay_data(db)

    # 2. Run Policy Batches Sequentially
    print("\n[STEP 1] Running Replay Batches for Policy A, B, C...")
    b_strict = ReplayService.create_batch(db, start_date, end_date, instruments, "Batch Strict", "STRICT_V4_LIMIT", 2.5)
    ReplayService.run_batch(db, b_strict.id)

    b_market = ReplayService.create_batch(db, start_date, end_date, instruments, "Batch Market", "MARKET_ENTRY", 2.5)
    ReplayService.run_batch(db, b_market.id)

    b_dev = ReplayService.create_batch(db, start_date, end_date, instruments, "Batch Deviation", "EXECUTION_DEVIATION", 2.5)
    ReplayService.run_batch(db, b_dev.id)

    # 3. Retrieve Analytics scoped strictly to each Batch ID
    print("[STEP 2] Scoping Analytics strictly to Batch IDs...")
    strict_analytics = ReplayService.get_control_group_analytics(db, b_strict.id)
    market_analytics = ReplayService.get_control_group_analytics(db, b_market.id)
    dev_analytics = ReplayService.get_control_group_analytics(db, b_dev.id)

    # 4. Population Checksum Hash Audit
    hash_strict = strict_analytics["population_checksum_hash"]
    hash_market = market_analytics["population_checksum_hash"]
    hash_dev = dev_analytics["population_checksum_hash"]

    hash_match = (hash_strict == hash_market == hash_dev)

    print(f"\n[PILLAR C: POPULATION HASH AUDIT]")
    print(f"  -> STRICT Policy Hash:    {hash_strict[:16]}...")
    print(f"  -> MARKET Policy Hash:    {hash_market[:16]}...")
    print(f"  -> DEVIATION Policy Hash: {hash_dev[:16]}...")
    print(f"  -> Population Hash Match: {'PASS (100% Identical T0 Setups)' if hash_match else 'FAIL'}")

    # 5. Denominator Reconciliation Invariants Audit
    reconciliation_results = []
    for analytics, name in [(strict_analytics, "STRICT_V4_LIMIT"), (market_analytics, "MARKET_ENTRY"), (dev_analytics, "EXECUTION_DEVIATION")]:
        n_eval = analytics["total_setups_evaluated"]
        status_dist = analytics["status_distribution"]
        n_taken = analytics["total_trades_taken"]
        n_passed = analytics["total_setups_passed"]
        n_unfilled = analytics["total_unfilled_missed"]
        n_missed_wins = analytics["opportunity_missed_wins"]
        n_saved_losses = analytics["opportunity_saved_losses"]
        n_expired = analytics["opportunity_expired_neutral"]

        inv_status = (sum(status_dist.values()) == n_eval)
        inv_decision = (n_taken + n_passed == n_eval)
        inv_opportunity = (n_missed_wins + n_saved_losses + n_expired == n_passed + n_unfilled)

        reconciliation_results.append({
            "policy": name,
            "n_evaluated": n_eval,
            "status_population_check": f"{sum(status_dist.values())}/{n_eval} ({'PASS' if inv_status else 'FAIL'})",
            "decision_population_check": f"{n_taken}+{n_passed}={n_eval} ({'PASS' if inv_decision else 'FAIL'})",
            "opportunity_population_check": f"{n_missed_wins}+{n_saved_losses}+{n_expired}={n_passed+n_unfilled} ({'PASS' if inv_opportunity else 'FAIL'})"
        })

    # 6. P90 Invalidation Deep Audit (No Tuning)
    print("\n[PILLAR F: P90 INVALIDATION AUDIT]")
    snapshots_market = db.query(ReplaySetupSnapshot).filter(ReplaySetupSnapshot.batch_id == b_market.id).all()
    trades_market = db.query(ReplayTradeRecord).join(ReplaySetupSnapshot).filter(ReplaySetupSnapshot.batch_id == b_market.id).all()

    p90_by_instrument = {}
    p90_by_direction = {}
    p90_by_regime = {}

    for t in trades_market:
        inst = t.setup.instrument
        dirn = t.setup.direction
        regime_str = t.setup.dxy_regime or "UNKNOWN"

        if inst not in p90_by_instrument:
            p90_by_instrument[inst] = {"total": 0, "breached": 0, "realized_maes": []}
        if dirn not in p90_by_direction:
            p90_by_direction[dirn] = {"total": 0, "breached": 0}
        if regime_str not in p90_by_regime:
            p90_by_regime[regime_str] = {"total": 0, "breached": 0}

        p90_by_instrument[inst]["total"] += 1
        p90_by_direction[dirn]["total"] += 1
        p90_by_regime[regime_str]["total"] += 1

        p90_by_instrument[inst]["realized_maes"].append(t.max_mae_pips or 0.0)

        if (t.mae_p90_reached or 0) > 0:
            p90_by_instrument[inst]["breached"] += 1
            p90_by_direction[dirn]["breached"] += 1
            p90_by_regime[regime_str]["breached"] += 1

    p90_instrument_report = {}
    for inst, data in p90_by_instrument.items():
        tot = data["total"]
        brk = data["breached"]
        rate = round(brk / tot * 100, 1) if tot > 0 else 0.0
        avg_realized_mae = round(float(np.mean(data["realized_maes"])), 1) if data["realized_maes"] else 0.0
        p90_instrument_report[inst] = {
            "fraction": f"{brk}/{tot}",
            "breach_rate": f"{rate}%",
            "avg_realized_mae_pips": avg_realized_mae
        }

    p90_direction_report = {}
    for dirn, data in p90_by_direction.items():
        tot = data["total"]
        brk = data["breached"]
        rate = round(brk / tot * 100, 1) if tot > 0 else 0.0
        p90_direction_report[dirn] = {
            "fraction": f"{brk}/{tot}",
            "breach_rate": f"{rate}%"
        }

    p90_regime_report = {}
    for reg, data in p90_by_regime.items():
        tot = data["total"]
        brk = data["breached"]
        rate = round(brk / tot * 100, 1) if tot > 0 else 0.0
        p90_regime_report[reg] = {
            "fraction": f"{brk}/{tot}",
            "breach_rate": f"{rate}%"
        }

    # 7. Row-by-Row Same-Setup Policy Comparison Sample Matrix
    print("\n[PILLAR G: ROW-BY-ROW POLICY MATRIX]")
    # Map setup (date, inst) -> result under each policy
    snaps_strict_map = {(s.date, s.instrument): s for s in db.query(ReplaySetupSnapshot).filter(ReplaySetupSnapshot.batch_id == b_strict.id).all()}
    snaps_market_map = {(s.date, s.instrument): s for s in db.query(ReplaySetupSnapshot).filter(ReplaySetupSnapshot.batch_id == b_market.id).all()}
    snaps_dev_map = {(s.date, s.instrument): s for s in db.query(ReplaySetupSnapshot).filter(ReplaySetupSnapshot.batch_id == b_dev.id).all()}

    sample_keys = list(snaps_strict_map.keys())[:10]
    row_matrix = []

    for k in sample_keys:
        s_str = snaps_strict_map[k]
        s_mkt = snaps_market_map[k]
        s_dev = snaps_dev_map[k]

        t_str = s_str.trades[0] if s_str.trades else None
        t_mkt = s_mkt.trades[0] if s_mkt.trades else None
        t_dev = s_dev.trades[0] if s_dev.trades else None

        row_matrix.append({
            "date": str(k[0]),
            "instrument": k[1],
            "direction": s_str.direction,
            "status": s_str.status_at_snapshot,
            "ref_price": s_str.setup_ref_price,
            "STRICT_result": t_str.outcome if t_str else s_str.opportunity_outcome,
            "MARKET_result": t_mkt.outcome if t_mkt else s_mkt.opportunity_outcome,
            "DEVIATION_result": t_dev.outcome if t_dev else s_dev.opportunity_outcome
        })

    report = {
        "population_hash_audit": {
            "status": "PASS" if hash_match else "FAIL",
            "hash_strict": hash_strict,
            "hash_market": hash_market,
            "hash_dev": hash_dev
        },
        "reconciliation_invariants": reconciliation_results,
        "policy_comparison_scoped": {
            "STRICT_V4_LIMIT": strict_analytics,
            "MARKET_ENTRY": market_analytics,
            "EXECUTION_DEVIATION": dev_analytics
        },
        "p90_invalidation_audit": {
            "by_instrument": p90_instrument_report,
            "by_direction": p90_direction_report,
            "by_regime": p90_regime_report
        },
        "sample_row_matrix": row_matrix
    }

    db.close()
    return report


if __name__ == "__main__":
    rep = run_reconciliation_audit()
    print("\n" + "=" * 90)
    print("                 RECONCILIATION AUDIT REPORT SUMMARY                    ")
    print("=" * 90)
    print(json.dumps(rep, indent=2))
