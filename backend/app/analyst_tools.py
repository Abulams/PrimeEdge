"""
Market OS AI Analyst Tool Registry
===================================
Deterministic quantitative tools callable by the AI reasoning layer.

PRINCIPLE: ALL numbers, percentiles, probabilities, and status states are
computed by the Market OS Python engines. The LLM only receives structured
facts as context for synthesis and explanation. The LLM never independently
calculates MAE, MFE, win rates, EV, or corridor levels.
"""

import datetime
import logging
import numpy as np
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .engine import DecisionIntelligenceEngine, EntryZoneEngine
from .data_fetcher import fetch_realtime_quotes, fetch_macro_snapshot, get_pip_multiplier
from .models import DailyMarketRegime, MarketSignature, PriceCache

logger = logging.getLogger(__name__)

INSTRUMENTS = ["GBPUSD", "EURUSD", "XAUUSD", "AUDUSD", "USDJPY"]


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 — Live Market Snapshot
# ─────────────────────────────────────────────────────────────────────────────

def get_market_snapshot(db: Session) -> Dict[str, Any]:
    """
    Returns the current live market state:
    - Session (Asia/London/New York)
    - Macro regime (DXY direction, risk sentiment)
    - Live prices for all 5 instruments
    - DXY, VIX, US10Y current values
    """
    now_utc = datetime.datetime.utcnow()
    hour = now_utc.hour
    if 0 <= hour < 7:
        session = "Asia"
    elif 7 <= hour < 13:
        session = "London"
    elif 13 <= hour < 21:
        session = "New York"
    else:
        session = "End of Day"

    regime = db.query(DailyMarketRegime).order_by(DailyMarketRegime.date.desc()).first()

    try:
        quotes = fetch_realtime_quotes(INSTRUMENTS)
    except Exception:
        quotes = {}

    try:
        macro = fetch_macro_snapshot()
    except Exception:
        macro = {}

    instruments = []
    for inst in INSTRUMENTS:
        q = quotes.get(inst, {})
        instruments.append({
            "symbol": inst,
            "price": q.get("price"),
            "change": q.get("change"),
            "change_pct": q.get("change_pct"),
            "open": q.get("open"),
        })

    return {
        "timestamp_utc": now_utc.isoformat(),
        "session": session,
        "macro_regime": {
            "dxy_direction": regime.dxy_regime if regime else "UNKNOWN",
            "risk_sentiment": regime.risk_sentiment if regime else "UNKNOWN",
            "date": str(regime.date) if regime else None,
        },
        "instruments": instruments,
        "macro_indicators": {
            "DXY": macro.get("DXY", {}).get("current"),
            "VIX": macro.get("VIX", {}).get("current"),
            "US10Y": macro.get("US10Y", {}).get("current"),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 — Instrument Full Profile (V4 Corridor + Status)
# ─────────────────────────────────────────────────────────────────────────────

def get_instrument_profile(db: Session, symbol: str) -> Dict[str, Any]:
    """
    Returns full V4 state for a given instrument:
    setup_ref_price, P25/P50/P75/P90 corridor levels, status_state,
    why_this_now narrative, continuation_probability, N, MAE/MFE distribution.
    """
    symbol = symbol.upper()
    today = datetime.date.today()
    trend = DecisionIntelligenceEngine.get_current_trend(db, symbol)
    profile = DecisionIntelligenceEngine.generate_daily_profile_v2(db, symbol, today, trend)

    if not profile:
        return {"error": f"No V4 profile available for {symbol}"}

    corridor = profile.get("acceptable_corridor", {})
    preferred = profile.get("preferred_zone", {})
    deep = profile.get("deep_retracement", {})

    return {
        "symbol": symbol,
        "trend": trend,
        "direction": profile.get("direction"),
        "status_state": profile.get("status_state"),
        "why_this_now": profile.get("why_this_now"),
        "setup_ref_price": profile.get("setup_ref_price"),
        "live_price": profile.get("live_price"),
        "corridor": {
            "p25_pips": corridor.get("p25_pips"),
            "p25_price": corridor.get("p25_price"),
            "p75_pips": corridor.get("p75_pips"),
            "p75_price": corridor.get("p75_price"),
        },
        "preferred_zone": {
            "p50_pips": preferred.get("p50_pips"),
            "p50_price": preferred.get("p50_price"),
            "p75_pips": preferred.get("p75_pips"),
            "p75_price": preferred.get("p75_price"),
        },
        "deep_retracement": {
            "p75_pips": deep.get("p75_pips"),
            "p75_price": deep.get("p75_price"),
            "p90_pips": deep.get("p90_pips"),
            "p90_price": deep.get("p90_price"),
        },
        "p90_invalidation_price": profile.get("historical_adverse_boundary"),
        "continuation_probability": profile.get("continuation_probability"),
        "historical_sample_size": profile.get("historical_sample_size"),
        "expected_mae_pips": profile.get("expected_mae"),
        "expected_mfe_pips": profile.get("expected_mfe"),
        "best_session": profile.get("best_session"),
        "current_regime": profile.get("current_regime"),
        "macro_trend": profile.get("macro_trend"),
        "confidence_score": profile.get("confidence_score"),
        "failure_conditions": profile.get("historical_failure_conditions"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3 — Watchlist Rankings (same data as FIND / Radar)
# ─────────────────────────────────────────────────────────────────────────────

def get_watchlist_rankings(db: Session) -> List[Dict[str, Any]]:
    """
    Returns all instruments ranked by MSS score, win rate, EV, and status state.
    Mirrors the FIND / Radar view so the AI answers consistently with what
    the user sees on screen.
    """
    today = datetime.date.today()
    rankings = []
    for inst in INSTRUMENTS:
        trend = DecisionIntelligenceEngine.get_current_trend(db, inst)
        profile = DecisionIntelligenceEngine.generate_daily_profile_v2(db, inst, today, trend)
        if profile:
            rankings.append({
                "symbol": inst,
                "direction": profile.get("direction"),
                "status_state": profile.get("status_state"),
                "continuation_probability": profile.get("continuation_probability"),
                "confidence_score": profile.get("confidence_score"),
                "historical_sample_size": profile.get("historical_sample_size"),
                "expected_mae_pips": profile.get("expected_mae"),
                "expected_mfe_pips": profile.get("expected_mfe"),
                "best_session": profile.get("best_session"),
                "trend": trend,
            })
    # Sort by confidence score descending
    rankings.sort(key=lambda x: x.get("confidence_score") or 0, reverse=True)
    return rankings


# ─────────────────────────────────────────────────────────────────────────────
# Tool 4 — Entry Zone Analysis (Market vs Limit EV)
# ─────────────────────────────────────────────────────────────────────────────

def get_entry_zone_analysis(db: Session, symbol: str) -> Dict[str, Any]:
    """
    Returns entry zone analysis: fill probabilities, EV at each limit depth,
    market-entry vs limit-entry comparison, and optimal depth recommendation.
    """
    symbol = symbol.upper()
    today = datetime.date.today()
    trend = DecisionIntelligenceEngine.get_current_trend(db, symbol)
    profile = DecisionIntelligenceEngine.generate_daily_profile_v2(db, symbol, today, trend)

    if not profile:
        return {"error": f"No entry zone data available for {symbol}"}

    option_ab = profile.get("option_a_vs_b", {})
    waiting_cost = profile.get("waiting_cost", {})

    return {
        "symbol": symbol,
        "direction": profile.get("direction"),
        "option_a_market": {
            "label": option_ab.get("option_a", {}).get("label"),
            "fill_probability": option_ab.get("option_a", {}).get("fill_probability"),
            "target_rate": option_ab.get("option_a", {}).get("target_rate"),
            "ev": option_ab.get("option_a", {}).get("expected_ev"),
        } if option_ab.get("option_a") else None,
        "option_b_limit": {
            "label": option_ab.get("option_b", {}).get("label"),
            "fill_probability": option_ab.get("option_b", {}).get("fill_probability"),
            "target_rate_if_filled": option_ab.get("option_b", {}).get("target_rate_if_filled"),
            "ev": option_ab.get("option_b", {}).get("expected_ev"),
            "depth_pips": option_ab.get("option_b", {}).get("opt_b_pips"),
        } if option_ab.get("option_b") else None,
        "waiting_cost_description": waiting_cost.get("description"),
        "historical_fill_rate": option_ab.get("option_b", {}).get("fill_probability") if option_ab.get("option_b") else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 5 — Scenario Simulation: "What if price moves X pips?"
# ─────────────────────────────────────────────────────────────────────────────

def simulate_price_move(db: Session, symbol: str, delta_pips: float) -> Dict[str, Any]:
    """
    Evaluates a hypothetical price move against the FIXED T0 corridor levels.
    Answers: "If GBPUSD moves X pips from current price, what would the status be?"

    delta_pips: positive = favourable (toward target), negative = adverse (toward stop).
    """
    symbol = symbol.upper()
    today = datetime.date.today()
    trend = DecisionIntelligenceEngine.get_current_trend(db, symbol)
    profile = DecisionIntelligenceEngine.generate_daily_profile_v2(db, symbol, today, trend)

    if not profile:
        return {"error": f"No profile data for {symbol}"}

    pip_mult = get_pip_multiplier(symbol)
    pip_unit = 1.0 / pip_mult if pip_mult > 0 else 0.0001

    live_price = profile.get("live_price", 0.0)
    direction = profile.get("direction", "LONG")

    # Adverse move: for LONG, negative delta means price falls (adverse)
    # delta_pips negative = price falls for LONG (adverse)
    if direction == "LONG":
        hypothetical_price = round(live_price + delta_pips * pip_unit, 5)
    else:
        hypothetical_price = round(live_price - delta_pips * pip_unit, 5)

    corridor = profile.get("acceptable_corridor", {})
    deep = profile.get("deep_retracement", {})
    p25_price = corridor.get("p25_price", live_price)
    p75_price = corridor.get("p75_price", live_price)
    p90_price = profile.get("historical_adverse_boundary", live_price)

    # Evaluate status at hypothetical price
    if direction == "LONG":
        beyond_p25 = hypothetical_price < p25_price
        beyond_p75 = hypothetical_price < p75_price
        beyond_p90 = hypothetical_price < p90_price
    else:
        beyond_p25 = hypothetical_price > p25_price
        beyond_p75 = hypothetical_price > p75_price
        beyond_p90 = hypothetical_price > p90_price

    if beyond_p90:
        hypothetical_status = "INVALID"
    elif beyond_p75:
        hypothetical_status = "READY (Deep Retracement Zone — P75 to P90)"
    elif beyond_p25:
        hypothetical_status = "READY (Acceptable Corridor — P25 to P75)"
    else:
        hypothetical_status = "WAIT (Price above P25 corridor)"

    # Distance to each boundary
    def pips_away(from_price, to_price):
        return round(abs(from_price - to_price) * pip_mult, 1)

    return {
        "symbol": symbol,
        "direction": direction,
        "current_price": live_price,
        "delta_pips": delta_pips,
        "hypothetical_price": hypothetical_price,
        "hypothetical_status": hypothetical_status,
        "fixed_corridor_levels": {
            "p25_price": p25_price,
            "p75_price": p75_price,
            "p90_price": p90_price,
            "p25_pips": corridor.get("p25_pips"),
            "p75_pips": corridor.get("p75_pips"),
            "p90_pips": deep.get("p90_pips"),
        },
        "at_hypothetical_price": {
            "pips_from_p75": pips_away(hypothetical_price, p75_price),
            "pips_from_p90": pips_away(hypothetical_price, p90_price),
        },
        "setup_ref_price": profile.get("setup_ref_price"),
        "historical_sample_size": profile.get("historical_sample_size"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 6 — Historical Evidence (MAE/MFE distribution details)
# ─────────────────────────────────────────────────────────────────────────────

def get_historical_evidence(db: Session, symbol: str) -> Dict[str, Any]:
    """
    Returns the raw historical evidence backing the current V4 setup:
    N, win/loss breakdown, full MAE/MFE percentile distribution,
    best session, common failure conditions.
    """
    symbol = symbol.upper()
    regime = db.query(DailyMarketRegime).order_by(DailyMarketRegime.date.desc()).first()
    trend = DecisionIntelligenceEngine.get_current_trend(db, symbol)

    dxy_state = regime.dxy_regime if regime else "BULLISH"
    risk_sent = regime.risk_sentiment if regime else "RISK_ON"

    sigs = DecisionIntelligenceEngine.find_similar_signatures(db, symbol, trend, dxy_state, risk_sent)

    if not sigs:
        return {"symbol": symbol, "error": "No matching historical signatures found"}

    win_sigs = [s for s in sigs if s.outcome == "WIN"]
    loss_sigs = [s for s in sigs if s.outcome == "LOSS"]
    all_maes = [max(0.0, float(s.mae_pips or 0)) for s in sigs]
    all_mfes = [max(0.0, float(s.mfe_pips or 0)) for s in sigs]

    return {
        "symbol": symbol,
        "trend": trend,
        "dxy_state": dxy_state,
        "risk_sentiment": risk_sent,
        "total_signatures": len(sigs),
        "win_count": len(win_sigs),
        "loss_count": len(loss_sigs),
        "raw_win_rate": round(len(win_sigs) / len(sigs), 4) if sigs else None,
        "mae_distribution": {
            "p25": round(float(np.percentile(all_maes, 25)), 1),
            "p50": round(float(np.percentile(all_maes, 50)), 1),
            "p75": round(float(np.percentile(all_maes, 75)), 1),
            "p90": round(float(np.percentile(all_maes, 90)), 1),
            "mean": round(float(np.mean(all_maes)), 1),
            "zero_mae_count": sum(1 for m in all_maes if m == 0.0),
            "zero_mae_pct": round(sum(1 for m in all_maes if m == 0.0) / len(all_maes) * 100, 1),
        },
        "mfe_distribution": {
            "p25": round(float(np.percentile(all_mfes, 25)), 1),
            "p50": round(float(np.percentile(all_mfes, 50)), 1),
            "p75": round(float(np.percentile(all_mfes, 75)), 1),
            "p90": round(float(np.percentile(all_mfes, 90)), 1),
            "mean": round(float(np.mean(all_mfes)), 1),
        },
        "matching_conditions": {
            "instrument": symbol,
            "trend": trend,
            "dxy_direction": dxy_state,
            "risk_sentiment": risk_sent,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 7 — Methodology Documentation
# ─────────────────────────────────────────────────────────────────────────────

METHODOLOGY_DOCS = {
    "READY": (
        "READY means current price is within the P25–P90 adverse excursion corridor measured from "
        "the T0 decision price (Daily Open). The empirical distribution of comparable historical "
        "setups shows that price was at or beyond this level during the adverse phase before "
        "resolving. Being READY means the current price is inside the historically acceptable "
        "entry zone — not that the trade is guaranteed to work."
    ),
    "WAIT": (
        "WAIT means current price has not yet retraced to the P25 adverse excursion boundary. "
        "The T0 decision price is above P25, meaning entry here would be at a statistically "
        "worse level than the 25th percentile of historical entries. The setup exists, but "
        "Market OS recommends waiting for price to reach the historical entry corridor."
    ),
    "INVALID": (
        "INVALID means current price has moved beyond the P90 adverse excursion boundary. "
        "P90 is the empirical stop survival boundary: 90% of comparable historical setups "
        "that eventually succeeded did NOT experience more than P90 pips of adverse excursion. "
        "Beyond P90, the setup is statistically invalidated."
    ),
    "P25": (
        "P25 is the 25th percentile of the Maximum Adverse Excursion (MAE) distribution across "
        "all comparable historical signatures. When P25=0, it means 25% or more of comparable "
        "setups experienced ZERO adverse excursion — they moved directly to target without "
        "pulling back at all. This is not a bug; it is the correct answer for this signature. "
        "Market OS does not manufacture an artificial waiting zone."
    ),
    "P75": (
        "P75 is the 75th percentile of the MAE distribution. The P25–P75 range defines the "
        "acceptable corridor: this is where 50% of historical excursions occurred. Entries "
        "inside this corridor are historically well-positioned."
    ),
    "P90": (
        "P90 is the 90th percentile of the MAE distribution and serves as the historical "
        "adverse boundary / stop survival level. Stops placed at P90 would have survived 90% "
        "of comparable historical setups. Stops tighter than P90 risk being stopped out before "
        "the favourable move develops."
    ),
    "MAE": (
        "Maximum Adverse Excursion (MAE) measures how far price moved against the position "
        "before reaching its eventual outcome (target or stop). It is calculated from the T0 "
        "decision price (Daily Open), not from the actual entry. MAE distributions are computed "
        "across all comparable historical signatures in the Market OS database."
    ),
    "MFE": (
        "Maximum Favourable Excursion (MFE) measures the maximum profit opportunity available "
        "during the trade before it closed. It represents the largest favourable move from the "
        "T0 decision price. P50 MFE is the median target; P75 MFE is a conservative target; "
        "P90 MFE is the maximum historically available."
    ),
    "acceptable_corridor": (
        "The Acceptable Corridor is the P25–P75 MAE zone. It represents the most historically "
        "common range of adverse excursion for comparable setups. An entry inside this corridor "
        "is within the normal pullback range for this type of setup."
    ),
    "preferred_zone": (
        "The Preferred Zone is the P50–P75 MAE zone. This is the historically most efficient "
        "entry area — deep enough to capture meaningful price improvement, shallow enough that "
        "fill probability remains high."
    ),
    "deep_retracement": (
        "The Deep Retracement Zone is P75–P90 MAE. Entries here are still technically within "
        "the setup's historical survival range, but represent the more extreme adverse excursions. "
        "Market OS flags deep retracement entries with a caution: only 10% of comparable setups "
        "went deeper than P90 and survived."
    ),
    "T0": (
        "T0 is the decision timestamp — the Daily Open price at which the Market OS setup is "
        "identified. All corridor levels (P25, P75, P90) are calculated as fixed price levels "
        "relative to T0. This means the corridor does NOT move with live price. Live price "
        "moves through the static corridor; the corridor does not chase the price."
    ),
    "MSS": (
        "The Market Signature Score (MSS) is a composite confidence score combining continuation "
        "probability, sample size quality, regime alignment, session strength, and volatility "
        "regime. It is not a prediction — it is a measure of the evidence quality behind the setup."
    ),
    "NO_EDGE": (
        "NO EDGE means the historical evidence is present but the quantitative criteria for a "
        "statistically justified setup are not met. This could be due to low sample size, "
        "low win rate, or adverse risk/reward characteristics."
    ),
    "NO_SETUP": (
        "NO SETUP means Market OS found insufficient comparable historical signatures to generate "
        "any statistically meaningful evidence. The system will not produce corridor levels or "
        "directional guidance without adequate historical grounding."
    ),
}

def get_methodology_doc(topic: str) -> Dict[str, str]:
    """
    Returns the authoritative Market OS V4 methodology definition for a given topic.
    Topics: READY, WAIT, INVALID, P25, P75, P90, MAE, MFE, T0, MSS,
            acceptable_corridor, preferred_zone, deep_retracement, NO_EDGE, NO_SETUP.
    """
    key = topic.upper().replace(" ", "_").replace("-", "_")
    # Try exact match first, then partial
    doc = METHODOLOGY_DOCS.get(key)
    if not doc:
        for k, v in METHODOLOGY_DOCS.items():
            if key in k or k in key:
                doc = v
                break
    if not doc:
        return {
            "topic": topic,
            "definition": (
                f"No specific methodology documentation found for '{topic}'. "
                f"Available topics: {', '.join(METHODOLOGY_DOCS.keys())}"
            )
        }
    return {"topic": topic, "definition": doc}
