"""
PrimeEdge Video Render Router
Triggers Remotion renders for signal cards, weekly wrapped, and macro daily videos.
Returns the rendered MP4 file path or streams it directly.
"""

import datetime
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..schemas import WatchlistInstrument
from ..engine import DecisionIntelligenceEngine
from ..video_service import render_signal_card, render_weekly_wrapped, render_macro_daily

router = APIRouter(prefix="/api/v1/video", tags=["Video Render"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SignalCardRequest(BaseModel):
    symbol: str  # e.g. "XAUUSD"


class WeeklyWrappedRequest(BaseModel):
    user_name: str
    week_offset: int = 0  # 0 = current week, -1 = last week, etc.


# ---------------------------------------------------------------------------
# Helper: resolve live WatchlistInstrument data for a symbol
# ---------------------------------------------------------------------------

def _get_watchlist_data_for_symbol(symbol: str, db: Session) -> dict:
    """
    Resolves live WatchlistInstrument-equivalent data for a given symbol
    using the same logic as the main watchlist endpoint.
    """
    today = datetime.date.today()
    symbol = symbol.upper()

    dual_profiles = DecisionIntelligenceEngine.generate_dual_profiles(db, symbol, today)
    candidates = [p for p in [dual_profiles.get("long"), dual_profiles.get("short")] if p is not None]

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No active profile data found for instrument '{symbol}'. "
                   "Ensure it is on the supported watchlist.",
        )

    # Pick the most actionable, highest-confidence direction — same ranking as watchlist endpoint
    cand_order = {"READY": 0, "WAIT": 1, "NO EDGE": 2, "NO SETUP": 3, "INVALID": 4}
    candidates.sort(
        key=lambda p: (cand_order.get(p.get("status_state"), 9), -p.get("confidence_score", 0))
    )
    profile = candidates[0]

    return {
        "instrument": profile.get("instrument", symbol),
        "direction": profile.get("direction", "LONG"),
        "status_state": profile.get("status_state", "WAIT"),
        "mss_score": profile.get("confidence_score", 0.0),
        "current_regime": profile.get("current_regime", ""),
        "continuation_probability": profile.get("continuation_probability", 0.0),
        "best_session": profile.get("best_session", ""),
        "historical_sample_size": profile.get("historical_sample_size", 0),
        "evidence_strength": profile.get("evidence_strength", "Moderate"),
        "why_this_now": profile.get("why_this_now", ""),
        "acceptable_corridor": profile.get("acceptable_corridor"),
        "preferred_zone": profile.get("preferred_zone"),
        "mae_data": profile.get("mae_data"),
        "trade_thesis": profile.get("trade_thesis"),
    }


# ---------------------------------------------------------------------------
# Helper: pull weekly trade stats from DB
# ---------------------------------------------------------------------------

def _get_weekly_trade_stats(user_name: str, week_offset: int, db: Session) -> dict:
    """
    Aggregates closed trade data from the past week (offset by `week_offset`).
    week_offset=0 → current week, -1 → last week, etc.
    """
    from ..models import TradeRecord

    today = datetime.date.today()
    # Compute Monday of target week
    days_since_monday = today.weekday()  # Mon=0, Sun=6
    target_monday = today - datetime.timedelta(days=days_since_monday) + datetime.timedelta(weeks=week_offset)
    target_sunday = target_monday + datetime.timedelta(days=6)

    week_label = f"{target_monday.strftime('%b %d')} – {target_sunday.strftime('%b %d, %Y')}"

    trades = (
        db.query(TradeRecord)
        .options(joinedload(TradeRecord.setup))
        .filter(
            TradeRecord.lifecycle_state == "CLOSED",
            TradeRecord.outcome.in_(["WIN", "LOSS", "BREAKEVEN"]),
            TradeRecord.actual_entry.isnot(None),
            TradeRecord.exit_timestamp >= datetime.datetime.combine(target_monday, datetime.time.min),
            TradeRecord.exit_timestamp <= datetime.datetime.combine(target_sunday, datetime.time.max),
        )
        .order_by(TradeRecord.exit_timestamp.desc())
        .all()
    )

    def _setup_field(trade, field, default=None):
        setup = getattr(trade, "setup", None)
        return getattr(setup, field, default) if setup is not None else default

    total = len(trades)
    wins = sum(1 for t in trades if t.outcome == "WIN")
    win_rate = round(wins / total, 3) if total > 0 else 0.0
    pnl_rs = [t.pnl_r for t in trades if t.pnl_r is not None]
    pnl_pips = [t.pnl_pips for t in trades if t.pnl_pips is not None]
    avg_r = round(sum(pnl_rs) / len(pnl_rs), 3) if pnl_rs else 0.0
    total_pnl_pips = round(sum(pnl_pips), 1) if pnl_pips else 0.0
    mae_discipline = (
        round(sum(1 for t in trades if not t.mae_p90_reached) / total, 3) if total else 0.0
    )

    best_trade = {"instrument": "—", "pnl_pips": 0, "direction": "LONG"}
    if trades:
        best = max(trades, key=lambda t: (t.pnl_pips if t.pnl_pips is not None else -9999))
        best_trade = {
            "instrument": _setup_field(best, "instrument", "UNKNOWN"),
            "pnl_pips": round(best.pnl_pips or 0.0, 1),
            "direction": _setup_field(best, "direction", "LONG"),
        }

    instruments_traded = list(
        {_setup_field(t, "instrument") for t in trades if _setup_field(t, "instrument")}
    )

    return {
        "user_name": user_name,
        "week_offset": week_offset,
        "week_label": week_label,
        "total_setups": total,
        "setups_taken": total,
        "win_rate": win_rate,
        "avg_r_multiple": avg_r,
        "total_pnl_pips": total_pnl_pips,
        "best_trade": best_trade,
        "instruments_traded": instruments_traded,
        "mae_discipline": mae_discipline,
    }


# ---------------------------------------------------------------------------
# Helper: resolve current macro regime data
# ---------------------------------------------------------------------------

def _get_macro_regime_data(db: Session) -> dict:
    """Pulls the latest macro regime record for the MacroDaily composition."""
    from ..models import DailyMarketRegime

    today = datetime.date.today()
    regime = (
        db.query(DailyMarketRegime)
        .filter(DailyMarketRegime.date == today)
        .first()
    )
    if not regime:
        regime = (
            db.query(DailyMarketRegime)
            .order_by(DailyMarketRegime.date.desc())
            .first()
        )

    if not regime:
        return {
            "date_label": today.strftime("%d %b %Y"),
            "dxy_level": 104.0,
            "dxy_change_pct": 0.0,
            "vix_level": 18.0,
            "vix_change_pct": 0.0,
            "risk_sentiment": "NEUTRAL",
            "macro_headline": "Macro data not yet available.",
            "key_instruments": [],
            "session_open": "London",
        }

    from ..models import InstrumentDailyProfile

    profiles = (
        db.query(InstrumentDailyProfile)
        .filter(InstrumentDailyProfile.date == regime.date)
        .order_by(InstrumentDailyProfile.confidence_score.desc())
        .limit(5)
        .all()
    )
    key_instruments = [
        {
            "symbol": p.instrument,
            "status": "READY" if (p.confidence_score or 0) >= 0.7 else "WAIT",
            "direction": "LONG",
            "mss_score": float(p.confidence_score or 0.0),
        }
        for p in profiles
    ]

    return {
        "date_label": regime.date.strftime("%d %b %Y") if regime.date else today.strftime("%d %b %Y"),
        "dxy_level": 104.0,
        "dxy_change_pct": 0.0,
        "vix_level": 18.0,
        "vix_change_pct": 0.0,
        "risk_sentiment": regime.risk_sentiment or "NEUTRAL",
        "macro_headline": regime.macro_summary or "",
        "key_instruments": key_instruments,
        "session_open": "London",
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/signal-card")
def render_signal_card_endpoint(
    req: SignalCardRequest,
    db: Session = Depends(get_db),
):
    """
    Renders a signal card MP4 for the given instrument symbol.

    Fetches live WatchlistInstrument data from the Decision Intelligence Engine
    and passes it to the Remotion SignalCard composition.
    """
    live_data = _get_watchlist_data_for_symbol(req.symbol, db)
    output_path = render_signal_card(live_data)
    filename = os.path.basename(output_path)
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=filename,
    )


@router.post("/weekly-wrapped")
def render_weekly_wrapped_endpoint(
    req: WeeklyWrappedRequest,
    db: Session = Depends(get_db),
):
    """
    Renders a weekly-wrapped MP4 summarising closed trade performance
    for the specified week offset (0 = current week, -1 = last week, …).
    """
    stats = _get_weekly_trade_stats(req.user_name, req.week_offset, db)
    output_path = render_weekly_wrapped(stats)
    filename = os.path.basename(output_path)
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=filename,
    )


@router.get("/macro-daily")
def render_macro_daily_endpoint(db: Session = Depends(get_db)):
    """
    Renders a macro daily briefing MP4 using the current macro regime data
    (DXY, VIX, risk sentiment, etc.).  No request body required.
    """
    macro_data = _get_macro_regime_data(db)
    output_path = render_macro_daily(macro_data)
    filename = os.path.basename(output_path)
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=filename,
    )
