"""
engine_validation.py
====================
Market OS — Out-of-Sample Engine Validation Suite v2.1.0

Four validation modules:
  1. Walk-Forward Backtest (Train <= 2023-12-31, Test >= 2024-01-01)
  2. Probability Calibration (Brier Score + ECE + Reliability Diagram)
  3. ATR Multiplier Sensitivity Analysis (0.25x to 0.50x)
  4. Edge Decay Monitoring (trailing 6-month vs. full-sample)

Usage:
  cd backend
  .\venv\Scripts\Activate.ps1
  python -m app.engine_validation
"""

import sys
import os
import math
import random
import statistics
from datetime import date, datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import MarketSignature, DailyMarketRegime

TRAIN_END_DATE    = date(2023, 12, 31)
TEST_START_DATE   = date(2024, 1, 1)
EDGE_DECAY_WINDOW = timedelta(days=183)
EDGE_DECAY_ALERT  = 0.05
ATR_MULTIPLIERS   = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
N_BOOTSTRAP       = 1000
BAR_WIDTH         = 72
SEP               = "-" * BAR_WIDTH


# ── Utilities ──────────────────────────────────────────────────────────────

def wilson_score_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    c = (p + z**2 / (2*n)) / (1 + z**2/n)
    m = (z / (1 + z**2/n)) * math.sqrt(p*(1-p)/n + z**2/(4*n**2))
    return (max(0.0, round(c - m, 4)), min(1.0, round(c + m, 4)))


def brier_score(preds, outcomes):
    if not preds:
        return float("nan")
    return round(sum((p - o)**2 for p, o in zip(preds, outcomes)) / len(preds), 5)


def expected_calibration_error(preds, outcomes, n_bins=10):
    if not preds:
        return float("nan")
    bins = defaultdict(lambda: {"p": [], "o": []})
    for p, o in zip(preds, outcomes):
        b = min(int(p * n_bins), n_bins - 1)
        bins[b]["p"].append(p)
        bins[b]["o"].append(o)
    n_total = len(preds)
    ece = 0.0
    for b, d in bins.items():
        nb = len(d["p"])
        if nb == 0:
            continue
        ece += (nb / n_total) * abs(statistics.mean(d["p"]) - sum(d["o"]) / nb)
    return round(ece, 5)


def _pct(v):
    return f"{v*100:.1f}%"

def _ci(ci):
    return f"[{_pct(ci[0])}, {_pct(ci[1])}]"


# ── Build Training Index ───────────────────────────────────────────────────

def build_train_index(train_sigs):
    idx = defaultdict(list)
    for s in train_sigs:
        key = (s.instrument, s.trend or "?", s.dxy_state or "?", s.risk_sentiment or "?")
        idx[key].append(1 if s.outcome == "WIN" else 0)
    return idx


def predict(s, idx):
    key = (s.instrument, s.trend or "?", s.dxy_state or "?", s.risk_sentiment or "?")
    ctx = idx.get(key)
    if not ctx or len(ctx) < 5:
        key2 = (s.instrument, s.trend or "?", s.dxy_state or "?")
        relaxed = []
        for k, v in idx.items():
            if k[:3] == key2:
                relaxed.extend(v)
        ctx = relaxed if relaxed else None
    if not ctx:
        return None
    return sum(ctx) / len(ctx)


# ── Module 1: Walk-Forward Backtest ───────────────────────────────────────

def run_walk_forward_backtest(db):
    print("\n[1/4] Walk-Forward Backtest ...")
    all_sigs = db.query(MarketSignature).all()
    train = [s for s in all_sigs if s.date <= TRAIN_END_DATE]
    test  = [s for s in all_sigs if s.date >= TEST_START_DATE]

    print(f"  Train: {len(train):,}  |  Test: {len(test):,}")
    if len(test) < 10:
        return {"status": "INSUFFICIENT_DATA", "n_train": len(train), "n_test": len(test)}

    idx = build_train_index(train)
    preds, outcomes = [], []
    no_ctx = 0
    per_inst  = defaultdict(lambda: {"p":[], "o":[]})
    per_sess  = defaultdict(lambda: {"p":[], "o":[]})

    # Fit Isotonic Calibrator strictly on training signatures
    from app.engine import IsotonicCalibrator
    calibrator = IsotonicCalibrator().fit(db, train_cutoff_date=TRAIN_END_DATE)

    for s in test:
        p_raw = predict(s, idx)
        if p_raw is None:
            no_ctx += 1
            continue
        p = calibrator.calibrate(p_raw) if calibrator.is_fitted else p_raw
        o = 1 if s.outcome == "WIN" else 0
        preds.append(p); outcomes.append(o)
        per_inst[s.instrument]["p"].append(p)
        per_inst[s.instrument]["o"].append(o)
        per_sess[s.session or "?"]["p"].append(p)
        per_sess[s.session or "?"]["o"].append(o)

    n = len(preds)
    mp = round(statistics.mean(preds), 4) if preds else 0.0
    ma = round(sum(outcomes)/n, 4)         if n else 0.0
    bias = round(mp - ma, 4)
    bs  = brier_score(preds, outcomes)
    ece = expected_calibration_error(preds, outcomes)

    inst_bd = {}
    for inst, d in per_inst.items():
        ni = len(d["p"])
        wi = sum(d["o"])
        inst_bd[inst] = {
            "n": ni,
            "predicted_win_rate": round(statistics.mean(d["p"]), 3),
            "actual_win_rate":    round(wi/ni, 3) if ni else 0,
            "bias":               round(statistics.mean(d["p"]) - wi/ni, 3) if ni else 0,
            "ci_95":              wilson_score_ci(wi, ni),
        }

    sess_bd = {}
    for sess, d in per_sess.items():
        ni = len(d["p"])
        wi = sum(d["o"])
        sess_bd[sess] = {
            "n": ni,
            "predicted_win_rate": round(statistics.mean(d["p"]), 3) if d["p"] else 0,
            "actual_win_rate":    round(wi/ni, 3) if ni else 0,
        }

    return {
        "status": "COMPLETE",
        "n_train": len(train), "n_test": len(test),
        "n_evaluated": n, "n_no_context": no_ctx,
        "mean_predicted_win_rate": mp, "mean_actual_win_rate": ma,
        "prediction_bias": bias,
        "brier_score": bs, "expected_calibration_error": ece,
        "per_instrument": inst_bd, "per_session": sess_bd,
    }


# ── Module 2: Probability Calibration ─────────────────────────────────────

def run_probability_calibration(db):
    print("\n[2/4] Probability Calibration ...")
    all_sigs = db.query(MarketSignature).all()
    train = [s for s in all_sigs if s.date <= TRAIN_END_DATE]
    test  = [s for s in all_sigs if s.date >= TEST_START_DATE]
    if len(test) < 10:
        return {"status": "INSUFFICIENT_DATA"}

    idx = build_train_index(train)
    buckets = {
        "50-60%": {"p":[], "o":[]}, "60-70%": {"p":[], "o":[]},
        "70-80%": {"p":[], "o":[]}, "80-90%": {"p":[], "o":[]},
        "90-100%": {"p":[], "o":[]},
    }

    def get_bucket(p):
        if 0.50 <= p < 0.60: return "50-60%"
        if 0.60 <= p < 0.70: return "60-70%"
        if 0.70 <= p < 0.80: return "70-80%"
        if 0.80 <= p < 0.90: return "80-90%"
        if 0.90 <= p <= 1.0:  return "90-100%"
        return None

    from app.engine import IsotonicCalibrator
    calibrator = IsotonicCalibrator().fit(db, train_cutoff_date=TRAIN_END_DATE)

    for s in test:
        p_raw = predict(s, idx)
        if p_raw is None: continue
        p = calibrator.calibrate(p_raw) if calibrator.is_fitted else p_raw
        bkt = get_bucket(p)
        if bkt is None: continue
        buckets[bkt]["p"].append(p)
        buckets[bkt]["o"].append(1 if s.outcome == "WIN" else 0)

    cal_table = {}
    all_p, all_o = [], []
    for label, d in buckets.items():
        n = len(d["p"])
        if n == 0:
            cal_table[label] = {"n": 0, "status": "NO_DATA"}; continue
        w = sum(d["o"])
        mp = statistics.mean(d["p"])
        ar = w / n
        gap = round(ar - mp, 4)
        ci  = wilson_score_ci(w, n)
        cal_table[label] = {
            "n": n, "mean_predicted": round(mp, 4), "actual_win_rate": round(ar, 4),
            "calibration_gap": gap, "ci_95": ci,
            "status": "WELL_CALIBRATED" if abs(gap) <= 0.05
                       else ("OVERCONFIDENT" if gap < 0 else "UNDERCONFIDENT"),
        }
        all_p.extend(d["p"]); all_o.extend(d["o"])

    return {
        "status": "COMPLETE",
        "brier_score": brier_score(all_p, all_o),
        "expected_calibration_error": expected_calibration_error(all_p, all_o),
        "calibration_table": cal_table,
    }


# ── Module 3: ATR Sensitivity ──────────────────────────────────────────────

def run_atr_sensitivity(db):
    print("\n[3/4] ATR Multiplier Sensitivity ...")
    all_sigs = db.query(MarketSignature).all()
    if not all_sigs:
        return {"status": "NO_DATA"}

    by_inst = defaultdict(list)
    for s in all_sigs:
        by_inst[s.instrument].append(s)

    results = {}
    for mult in ATR_MULTIPLIERS:
        label = f"{mult:.2f}x"
        per_inst = {}
        for inst, sigs in by_inst.items():
            ranges = sorted(s.mae_pips + s.mfe_pips for s in sigs)
            if not ranges: continue
            med = ranges[len(ranges)//2]
            atr_est = med * 0.5
            base = 10.0 if "XAU" in inst else 25.0
            thresh = max(base, mult * atr_est)
            conts = [s for s in sigs if s.mfe_pips >= thresh]
            nc = len(conts)
            na = len(sigs)
            wr = len([s for s in conts if s.outcome == "WIN"]) / nc if nc else 0.0
            ci = wilson_score_ci(len([s for s in conts if s.outcome == "WIN"]), nc)
            per_inst[inst] = {"threshold_pips": round(thresh,1), "n_continuations": nc,
                              "continuation_rate": round(nc/na,4) if na else 0,
                              "win_rate": round(wr,4), "ci_95": ci}
        wrs = [v["win_rate"] for v in per_inst.values() if v["n_continuations"] >= 10]
        std = round(statistics.stdev(wrs), 4) if len(wrs) >= 2 else float("nan")
        results[label] = {"multiplier": mult, "per_instrument": per_inst,
                          "cross_instrument_win_rate_std": std}

    valid = {k: v for k, v in results.items() if not math.isnan(v["cross_instrument_win_rate_std"])}
    opt = min(valid, key=lambda k: valid[k]["cross_instrument_win_rate_std"]) if valid else "0.40x"
    prod = "0.40x"
    return {
        "status": "COMPLETE",
        "optimal_multiplier": opt,
        "current_production_multiplier": prod,
        "recommendation": ("Current 0.40x is OPTIMAL" if opt == prod
                           else f"Consider switching to {opt}"),
        "sensitivity_table": results,
    }


# ── Module 4: Edge Decay ───────────────────────────────────────────────────

def run_edge_decay_monitoring(db):
    print("\n[4/4] Edge Decay Monitoring ...")
    all_sigs = db.query(MarketSignature).all()
    if not all_sigs:
        return {"status": "NO_DATA"}

    cutoff = date.today() - EDGE_DECAY_WINDOW
    by_inst = defaultdict(list)
    for s in all_sigs:
        by_inst[s.instrument].append(s)

    decay_results = {}
    any_decay = False

    for inst, sigs in sorted(by_inst.items()):
        wf  = [s for s in sigs if s.outcome == "WIN"]
        st  = [s for s in sigs if s.date >= cutoff]
        wt  = [s for s in st   if s.outcome == "WIN"]
        nf, nt = len(sigs), len(st)
        wrf = round(len(wf)/nf, 4) if nf else 0.0
        wrt = round(len(wt)/nt, 4) if nt else 0.0
        delta = round(wrt - wrf, 4)
        flag = abs(delta) > EDGE_DECAY_ALERT and nt >= 20
        if flag: any_decay = True
        status = ("[!!] SIGNAL DECAY" if (flag and delta < 0)
                  else ("[UP] IMPROVING" if (flag and delta > 0) else "[OK] STABLE"))
        decay_results[inst] = {
            "full_sample": {"n": nf, "win_rate": wrf, "ci_95": wilson_score_ci(len(wf), nf)},
            "trailing_6m": {"n": nt, "win_rate": wrt, "ci_95": wilson_score_ci(len(wt), nt)},
            "delta": delta, "decay_flag": flag, "status": status,
        }

    return {
        "status": "COMPLETE",
        "trailing_window_days": EDGE_DECAY_WINDOW.days,
        "any_decay_detected": any_decay,
        "per_instrument": decay_results,
    }


# ── Report Printer ─────────────────────────────────────────────────────────

def print_report(bt, cal, sens, decay):
    print(f"\n{'='*BAR_WIDTH}")
    print(f"  MARKET OS — ENGINE VALIDATION REPORT  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*BAR_WIDTH}")

    # 1. Backtest
    print(f"\n1. WALK-FORWARD BACKTEST  (Train <= {TRAIN_END_DATE}, Test >= {TEST_START_DATE})")
    print(SEP)
    if bt.get("status") == "INSUFFICIENT_DATA":
        n_train = bt.get("n_train", 0)
        n_test  = bt.get("n_test", 0)
        print(f"  Train: {n_train:,}  |  Test: {n_test:,}")
        print(f"  NOTE: All signatures are in the training window (pre-2024).")
        print(f"  The engine has no out-of-sample data yet. This is expected for a")
        print(f"  freshly seeded database. Validation will activate once live data")
        print(f"  accumulates past {TEST_START_DATE}.")
    else:
        print(f"  Train: {bt['n_train']:,}  |  Test: {bt['n_test']:,}  |  Eval: {bt['n_evaluated']:,}  |  No-ctx: {bt['n_no_context']:,}")
        bias = bt["prediction_bias"]
        bias_tag = "OVERESTIMATING" if bias > 0.02 else ("UNDERESTIMATING" if bias < -0.02 else "WELL-ALIGNED")
        print(f"  Mean Pred WR : {_pct(bt['mean_predicted_win_rate'])}  |  Actual WR: {_pct(bt['mean_actual_win_rate'])}  |  Bias: {bias:+.4f}  ({bias_tag})")
        print(f"  Brier Score  : {bt['brier_score']:.5f}  (< 0.20 = excellent)")
        print(f"  ECE          : {bt['expected_calibration_error']:.5f}  (< 0.08 = acceptable)")
        print(f"\n  Per-Instrument:")
        print(f"  {'Instrument':<12} {'N':>6} {'Pred WR':>9} {'Actual WR':>10} {'Bias':>8}  95% CI")
        print(f"  {'-'*62}")
        for inst, d in sorted(bt["per_instrument"].items()):
            print(f"  {inst:<12} {d['n']:>6} {_pct(d['predicted_win_rate']):>9} "
                  f"{_pct(d['actual_win_rate']):>10} {d['bias']:>+8.3f}  {_ci(d['ci_95'])}")
        print(f"\n  Per-Session:")
        print(f"  {'Session':<14} {'N':>6} {'Pred WR':>9} {'Actual WR':>10}")
        for sess, d in sorted(bt["per_session"].items()):
            print(f"  {sess:<14} {d['n']:>6} {_pct(d['predicted_win_rate']):>9} {_pct(d['actual_win_rate']):>10}")

    # 2. Calibration
    print(f"\n2. PROBABILITY CALIBRATION")
    print(SEP)
    if cal.get("status") == "INSUFFICIENT_DATA":
        print("  No out-of-sample data yet. Calibration will activate once 2024+ data is accumulated.")
    else:
        bs_g  = "EXCELLENT" if cal["brier_score"] < 0.18 else ("GOOD" if cal["brier_score"] < 0.22 else "POOR")
        ece_g = "EXCELLENT" if cal["expected_calibration_error"] < 0.03 else ("ACCEPTABLE" if cal["expected_calibration_error"] < 0.08 else "POORLY CALIBRATED")
        print(f"  Brier Score : {cal['brier_score']:.5f}  ({bs_g})")
        print(f"  ECE         : {cal['expected_calibration_error']:.5f}  ({ece_g})")
        print(f"\n  {'Bucket':<12} {'N':>6} {'Mean Pred':>10} {'Actual WR':>10} {'Gap':>8}  Status")
        print(f"  {'-'*60}")
        for label, d in cal["calibration_table"].items():
            if d.get("status") == "NO_DATA":
                print(f"  {label:<12} {'—':>6}")
            else:
                print(f"  {label:<12} {d['n']:>6} {_pct(d['mean_predicted']):>10} "
                      f"{_pct(d['actual_win_rate']):>10} {d['calibration_gap']:>+8.4f}  {d['status']}")

    # 3. Sensitivity
    print(f"\n3. ATR MULTIPLIER SENSITIVITY")
    print(SEP)
    if sens.get("status") == "NO_DATA":
        print("  No data.")
    else:
        print(f"  Production: {sens['current_production_multiplier']}  |  Optimal: {sens['optimal_multiplier']}")
        print(f"  {sens['recommendation']}")
        print(f"\n  {'Multiplier':<12} {'Cross-Inst sigma(WR)':>22}")
        print(f"  {'-'*36}")
        for label, d in sorted(sens["sensitivity_table"].items(), key=lambda x: x[1]["multiplier"]):
            std = d["cross_instrument_win_rate_std"]
            tag = " <-- PRODUCTION" if label == sens["current_production_multiplier"] else ""
            print(f"  {label:<12} {std:>22.4f}{tag}" if not math.isnan(std) else f"  {label:<12} {'N/A':>22}{tag}")

    # 4. Edge Decay
    print(f"\n4. EDGE DECAY MONITORING  (trailing {decay.get('trailing_window_days',183)} days)")
    print(SEP)
    if decay.get("status") == "NO_DATA":
        print("  No data.")
    else:
        print("  [!!] DECAY DETECTED" if decay["any_decay_detected"] else "  [OK] All instruments STABLE")
        print(f"\n  {'Instrument':<12} {'Full WR':>8} {'Trail WR':>10} {'Delta':>8}  Status")
        print(f"  {'-'*56}")
        for inst, d in sorted(decay["per_instrument"].items()):
            print(f"  {inst:<12} {_pct(d['full_sample']['win_rate']):>8} "
                  f"{_pct(d['trailing_6m']['win_rate']):>10} "
                  f"{d['delta']:>+8.4f}  {d['status']}")

    print(f"\n{'='*BAR_WIDTH}")
    print(f"  VALIDATION COMPLETE  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*BAR_WIDTH}\n")


# ── Entry Point ────────────────────────────────────────────────────────────

def main():
    random.seed(42)
    print("Market OS — Engine Validation Suite v2.1.0")
    db = SessionLocal()
    try:
        n = db.query(MarketSignature).count()
        print(f"Database: {n:,} Market Signatures loaded.")
        if n == 0:
            print("ERROR: Database empty. Run seed.py first."); return
        bt    = run_walk_forward_backtest(db)
        cal   = run_probability_calibration(db)
        sens  = run_atr_sensitivity(db)
        decay = run_edge_decay_monitoring(db)
        print_report(bt, cal, sens, decay)
    finally:
        db.close()


if __name__ == "__main__":
    main()
