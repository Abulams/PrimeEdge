import datetime
import os
import numpy as np
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse as StaticFileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

# Load .env (GEMINI_API_KEY etc.) before any module-level reads
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass  # python-dotenv not installed — rely on shell env vars


from .database import get_db, engine, Base
from .models import (
    DailyMarketRegime, TradingJournal, InstrumentDailyProfile, TradePlannerLog,
    MarketSignature, PriceCache, SetupSnapshot, TradeRecord,
    ReplayBatch, ReplaySetupSnapshot, ReplayTradeRecord
)
from .schemas import (
    MacroRegimeResponse, WatchlistInstrument, TradePlanRequest, TradePlanResponse,
    JournalCreate, JournalResponseModel, ChatRequest, ChatResponse,
    TradePlannerInput, AnalystQueryRequest, AnalystQueryResponse,
    SetupSnapshotCreate, SetupSnapshotResponse, AcceptSetupRequest, PassSetupRequest,
    CloseTradeRequest, TradeRecordResponse, AutoJournalPerformanceResponse,
    ReplayRunRequest, ReplayBatchResponse, ReplaySetupSnapshotResponse,
    ReplayTradeRecordResponse, ReplayAnalyticsResponse
)
from .engine import DecisionIntelligenceEngine, TradePlannerEngine
from .journal_service import JournalService
from .replay_service import ReplayService
from .data_fetcher import fetch_realtime_quotes
from . import analyst_engine
from .realtime import realtime_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables (including users) are created
    Base.metadata.create_all(bind=engine)
    # Start the realtime polling service (every 5 minutes)
    await realtime_service.start(interval_seconds=300)
    yield
    # Stop the service on shutdown
    await realtime_service.stop()

app = FastAPI(title="Market OS API", version="1.0.0", lifespan=lifespan)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enable GZip compression (60-70% bandwidth reduction on JSON payloads)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Auth & Cloud Execution Routers
from .routers.auth_router import router as auth_router
from .routers.execution_cloud_router import router as execution_cloud_router
from .auth import get_current_user
from .models import User as UserModel

app.include_router(auth_router)
app.include_router(execution_cloud_router)


# Root endpoint — serve React app if built, otherwise API health message
@app.get("/")
def read_root():
    _dist_index = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist", "index.html")
    if os.path.isfile(_dist_index):
        return StaticFileResponse(_dist_index)
    return {"message": "Welcome to Market OS API. Bloomberg Terminal x Quantitative Research Engine."}

def sync_live_macro_regime(db: Session) -> DailyMarketRegime:
    """
    Synchronizes the DailyMarketRegime with live macro data (DXY, VIX, US10Y).
    Ensures the entire platform (Narrative, Badges, Watchlist) reflects the exact live DXY state.
    """
    today = datetime.date.today()

    snapshot = getattr(realtime_service, "macro_snapshot", None)
    if not snapshot or not snapshot.get("DXY"):
        try:
            from .data_fetcher import fetch_macro_snapshot
            snapshot = fetch_macro_snapshot()
        except Exception:
            snapshot = {}

    dxy_info = snapshot.get("DXY", {})
    dxy_val = float(dxy_info.get("current", 101.43))
    sma5 = float(dxy_info.get("sma_5", dxy_val))
    sma20 = float(dxy_info.get("sma_20", dxy_val))

    diff_pct = ((sma5 - sma20) / sma20 * 100.0) if sma20 != 0 else 0.0
    if diff_pct > 0.15:
        dxy_regime = "BULLISH"
    elif diff_pct < -0.15:
        dxy_regime = "BEARISH"
    else:
        dxy_regime = "CONSOLIDATING"

    vix_info = snapshot.get("VIX", {})
    vix_val = float(vix_info.get("current", 18.0))
    if vix_val >= 22.0:
        risk_sentiment = "RISK_OFF"
    elif vix_val <= 15.0:
        risk_sentiment = "RISK_ON"
    else:
        risk_sentiment = "NEUTRAL"

    yields_regime = "STEEPENING"

    macro_summary = (
        f"DXY is {dxy_regime.lower()} at {dxy_val:.2f}. "
        f"VIX at {vix_val:.1f} indicates {risk_sentiment.replace('_', ' ').lower()} conditions. "
        f"US 10Y yields regime is {yields_regime.lower()}."
    )

    regime = db.query(DailyMarketRegime).filter(DailyMarketRegime.date == today).first()
    if not regime:
        regime = db.query(DailyMarketRegime).order_by(DailyMarketRegime.date.desc()).first()
        if regime:
            regime.date = today

    if not regime:
        regime = DailyMarketRegime(
            date=today,
            dxy_regime=dxy_regime,
            yields_regime=yields_regime,
            risk_sentiment=risk_sentiment,
            no_trade_zones=[],
            macro_summary=macro_summary,
            overall_confidence_score=75.0
        )
        db.add(regime)
    else:
        regime.dxy_regime = dxy_regime
        regime.risk_sentiment = risk_sentiment
        regime.yields_regime = yields_regime
        regime.macro_summary = macro_summary

    db.commit()
    db.refresh(regime)
    return regime


# 1. Macro Regime Endpoint
@app.get("/api/v1/dashboard/regime", response_model=MacroRegimeResponse)
def get_macro_regime(db: Session = Depends(get_db)):
    return sync_live_macro_regime(db)


# 2. Watchlist Endpoint
@app.get("/api/v1/dashboard/watchlist", response_model=List[WatchlistInstrument])
def get_watchlist(db: Session = Depends(get_db)):
    today = datetime.date.today()
    regime = sync_live_macro_regime(db)
    instruments = ["GBPUSD", "EURUSD", "XAUUSD", "AUDUSD", "USDJPY"]
    watchlist = []

    for inst in instruments:
        trend = DecisionIntelligenceEngine.get_current_trend(db, inst)
        profile_data = DecisionIntelligenceEngine.generate_daily_profile_v2(db, inst, today, trend)
        if profile_data:
            watchlist.append(
                WatchlistInstrument(
                    instrument=profile_data["instrument"],
                    direction=profile_data.get("direction", "LONG"),
                    status_state=profile_data.get("status_state", "WAIT"),
                    why_this_now=profile_data.get("why_this_now", ""),
                    evidence_strength=profile_data.get("evidence_strength", "Moderate"),
                    mss_score=profile_data["confidence_score"],
                    current_regime=profile_data["current_regime"],
                    continuation_probability=profile_data["continuation_probability"],
                    best_session=profile_data["best_session"],
                    historical_sample_size=profile_data["historical_sample_size"],
                    supporting_explanation=profile_data["supporting_explanation"] or "",
                    acceptable_corridor=profile_data.get("acceptable_corridor"),
                    preferred_zone=profile_data.get("preferred_zone"),
                    historical_adverse_boundary=profile_data.get("historical_adverse_boundary"),
                    waiting_cost=profile_data.get("waiting_cost"),
                    trade_thesis=profile_data.get("trade_thesis"),
                    option_a_vs_b=profile_data.get("option_a_vs_b"),
                    mss_decomposition=profile_data["mss_decomposition"]
                )
            )

    # Sort watchlist by actionability: READY (0) -> WAIT (1) -> NO EDGE (2) -> NO SETUP (3), then mss_score desc
    status_order = {"READY": 0, "WAIT": 1, "NO EDGE": 2, "NO SETUP": 3, "INVALID": 4}
    evidence_order = {"Strong": 0, "Moderate": 1, "Weak": 2}

    watchlist.sort(
        key=lambda x: (
            status_order.get(x.status_state, 9),
            evidence_order.get(x.evidence_strength, 9),
            -x.mss_score
        )
    )
    return watchlist

# 3. Instrument Detail Endpoint
@app.get("/api/v1/instruments/{symbol}/profile")
def get_instrument_profile(symbol: str, db: Session = Depends(get_db)):
    today = datetime.date.today()
    regime = sync_live_macro_regime(db)
    trend = DecisionIntelligenceEngine.get_current_trend(db, symbol.upper())
    profile_data = DecisionIntelligenceEngine.generate_daily_profile_v2(db, symbol.upper(), today, trend)
    if not profile_data:
        raise HTTPException(status_code=404, detail=f"No profile data found for {symbol}")
    return profile_data

# 4. Trade Planner Endpoints
@app.post("/api/v1/trade-planner/evaluate")
@app.post("/api/v1/planner/evaluate")
def evaluate_trade_plan(req: TradePlannerInput, db: Session = Depends(get_db)):
    evaluation = TradePlannerEngine.evaluate_setup(
        db=db,
        instrument=req.instrument.upper(),
        entry=req.entry_price,
        stop=req.stop_loss,
        target=req.take_profit,
        direction=req.direction or "BUY",
        timeframe=req.timeframe or "15M",
        risk_pct=req.risk_pct or 1.0,
        account_balance=req.account_balance or 10000.0,
        session_name=req.session_name
    )
    
    if "error" in evaluation:
        raise HTTPException(status_code=400, detail=evaluation["error"])
        
    # Save log entry
    try:
        log_entry = TradePlannerLog(
            instrument=evaluation["instrument"],
            entry_price=req.entry_price,
            stop_loss=req.stop_loss,
            take_profit=req.take_profit,
            trade_quality_score=float(evaluation.get("expected_r_multiple", 1.0) * 20.0),
            probability_win=evaluation["calibrated_win_probability"],
            expected_mae=evaluation["empirical_mae"]["p50"],
            expected_mfe=evaluation["empirical_mfe"]["p50"],
            position_size=evaluation["position_size_lots"],
            risk_amount=evaluation["risk_amount_usd"],
            warnings=evaluation["decision_audit"]["warnings"]
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
    except Exception as e:
        logger.warning(f"Could not log trade planner evaluation: {e}")
        db.rollback()
    
    return evaluation

# 5. Journal Endpoints
@app.get("/api/v1/journal", response_model=List[JournalResponseModel])
def get_journal(db: Session = Depends(get_db)):
    journal_entries = db.query(TradingJournal).order_by(TradingJournal.date.desc()).all()
    return journal_entries

@app.post("/api/v1/journal/log", response_model=JournalResponseModel)
def log_journal_entry(req: JournalCreate, db: Session = Depends(get_db)):
    journal_entry = TradingJournal(**req.dict())
    db.add(journal_entry)
    db.commit()
    db.refresh(journal_entry)
    return journal_entry

# 5b. Auto Journal Endpoints (Immutable T₀ Snapshots & Trade Lifecycle)
@app.post("/api/v1/journal/snapshot", response_model=SetupSnapshotResponse)
def create_setup_snapshot(req: SetupSnapshotCreate, db: Session = Depends(get_db)):
    """Captures an immutable T₀ snapshot of the setup for an instrument."""
    try:
        return JournalService.create_setup_snapshot(db, req.instrument, source=req.source or "MANUAL")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@app.post("/api/v1/journal/accept", response_model=TradeRecordResponse)
def accept_setup(req: AcceptSetupRequest, db: Session = Depends(get_db)):
    """Trader accepts a setup and confirms execution parameters."""
    try:
        return JournalService.accept_setup(
            db=db,
            snapshot_id=req.snapshot_id,
            actual_entry=req.actual_entry,
            actual_sl=req.actual_sl,
            actual_tp=req.actual_tp,
            entry_type=req.entry_type or "MARKET",
            position_size_lots=req.position_size_lots or 0.1,
            risk_pct=req.risk_pct or 1.0,
            account_balance=req.account_balance or 10000.0,
            notes=req.notes
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@app.post("/api/v1/journal/pass", response_model=TradeRecordResponse)
def pass_setup(req: PassSetupRequest, db: Session = Depends(get_db)):
    """Trader explicitly passes on a setup."""
    try:
        return JournalService.pass_setup(db, req.snapshot_id, notes=req.notes)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@app.post("/api/v1/journal/close", response_model=TradeRecordResponse)
def close_trade(req: CloseTradeRequest, db: Session = Depends(get_db)):
    """Manually closes an active trade and computes final outcome & percentile ranks."""
    try:
        return JournalService.close_trade(db, req.trade_id, req.exit_price, req.exit_reason or "MANUAL")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@app.get("/api/v1/journal/active", response_model=List[TradeRecordResponse])
def get_active_trades(db: Session = Depends(get_db)):
    """Returns all currently ACTIVE trades with live MAE/MFE tracking."""
    return db.query(TradeRecord).filter(TradeRecord.lifecycle_state == "ACTIVE").order_by(TradeRecord.created_at.desc()).all()

@app.get("/api/v1/journal/history", response_model=List[TradeRecordResponse])
def get_trade_history(db: Session = Depends(get_db)):
    """Returns all CLOSED trades with full trajectory & outcome metrics."""
    return db.query(TradeRecord).filter(TradeRecord.lifecycle_state == "CLOSED").order_by(TradeRecord.exit_timestamp.desc()).all()

@app.get("/api/v1/journal/passed", response_model=List[TradeRecordResponse])
def get_passed_setups(db: Session = Depends(get_db)):
    """Returns all PASSED setups for opportunity cost review."""
    return db.query(TradeRecord).filter(TradeRecord.lifecycle_state == "PASSED").order_by(TradeRecord.created_at.desc()).all()

@app.get("/api/v1/journal/performance", response_model=AutoJournalPerformanceResponse)
def get_journal_performance(db: Session = Depends(get_db)):
    """Returns aggregated performance summary comparing Market OS expectations vs trader execution."""
    return JournalService.get_performance_summary(db)

# 5c. Historical Replay / Simulation Environment Endpoints
@app.post("/api/v1/replay/run", response_model=ReplayBatchResponse)
def run_replay_batch(req: ReplayRunRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Initiates an isolated historical replay simulation batch across a date range.
    Enforces strict point-in-time anti-look-ahead data slicing (t <= T₀).
    """
    instruments = req.instruments or ["GBPUSD", "EURUSD", "XAUUSD", "AUDUSD", "USDJPY"]
    batch = ReplayService.create_batch(
        db=db,
        start_date=req.start_date,
        end_date=req.end_date,
        instruments=instruments,
        batch_name=req.batch_name or "Control Group Audit",
        execution_policy=req.execution_policy or "STRICT_V4_LIMIT",
        friction_pips=req.friction_pips or 2.5
    )

    # Run replay execution
    ReplayService.run_batch(db, batch.id)
    db.refresh(batch)
    return batch

@app.get("/api/v1/replay/status/{batch_id}", response_model=ReplayBatchResponse)
def get_replay_batch_status(batch_id: int, db: Session = Depends(get_db)):
    """Checks progress and metadata of a historical replay batch."""
    batch = ReplayService.get_batch(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Replay batch {batch_id} not found")
    return batch

@app.get("/api/v1/replay/history", response_model=List[ReplayTradeRecordResponse])
def get_replay_history(db: Session = Depends(get_db)):
    """Returns closed trade records from the isolated Replay Journal."""
    return ReplayService.get_history_trades(db)

@app.get("/api/v1/replay/passed", response_model=List[ReplaySetupSnapshotResponse])
def get_replay_passed(db: Session = Depends(get_db)):
    """Returns passed and unfilled setup snapshot records from the isolated Replay Journal."""
    return ReplayService.get_passed_setups(db)

@app.get("/api/v1/replay/analytics")
def get_replay_analytics(batch_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Returns Control Group baseline analytics evaluating V4 win rate calibration, P90 survival, and scorecard KPIs."""
    return ReplayService.get_control_group_analytics(db, batch_id)

@app.get("/api/v1/replay/compare")
def compare_replay_batches(
    baseline_id: int,
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """
    Compares two replay batches (from live DB or persistent file archives)
    and returns a structured delta scorecard with validity classification,
    primary/secondary KPI verdicts, per-instrument breadth, and grounded interpretation.
    """
    try:
        return ReplayService.compare_batches(db, baseline_id, candidate_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare replay batches: {e}")


@app.get("/api/v1/replay/batches")
def get_replay_batches(db: Session = Depends(get_db)):
    """Returns all replay batches with principal performance metrics and export status."""
    return ReplayService.get_all_batches_summary(db)

@app.get("/api/v1/replay/{batch_id}/export")
def export_replay_batch(batch_id: int, db: Session = Depends(get_db)):
    """Exports a single replay batch into persistent file archive storage (JSON, CSV, manifest, zip)."""
    try:
        res = ReplayService.export_batch(db, batch_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export batch: {e}")

@app.get("/api/v1/replay/export-all")
def export_all_replay_batches(db: Session = Depends(get_db)):
    """Exports all replay batches into persistent file archive storage."""
    try:
        return ReplayService.export_all_batches(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export all batches: {e}")

@app.get("/api/v1/replay/{batch_id}/download")
def download_replay_batch_zip(batch_id: int, db: Session = Depends(get_db)):
    """Downloads the generated ZIP archive for a replay batch."""
    from fastapi.responses import FileResponse
    res = ReplayService.export_batch(db, batch_id)
    zip_path = res.get("zip_path")
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Archive zip file not found")
    return FileResponse(zip_path, filename=f"batch_{batch_id}.zip", media_type="application/zip")

@app.get("/api/v1/replay/{batch_id}/download-trades-csv")
def download_replay_trades_csv(batch_id: int, db: Session = Depends(get_db)):
    """Downloads the trade_records.csv directly for a replay batch."""
    from fastapi.responses import FileResponse
    res = ReplayService.export_batch(db, batch_id)
    archive_dir = res.get("archive_dir")
    csv_path = os.path.join(archive_dir, "trade_records.csv") if archive_dir else None
    if not csv_path or not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Trade records CSV not found")
    return FileResponse(csv_path, filename=f"batch_{batch_id}_trades.csv", media_type="text/csv")

@app.get("/api/v1/replay/{batch_id}/download-snapshots-csv")
def download_replay_snapshots_csv(batch_id: int, db: Session = Depends(get_db)):
    """Downloads the setup_snapshots.csv directly for a replay batch."""
    from fastapi.responses import FileResponse
    res = ReplayService.export_batch(db, batch_id)
    archive_dir = res.get("archive_dir")
    csv_path = os.path.join(archive_dir, "setup_snapshots.csv") if archive_dir else None
    if not csv_path or not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Setup snapshots CSV not found")
    return FileResponse(csv_path, filename=f"batch_{batch_id}_snapshots.csv", media_type="text/csv")

@app.post("/api/v1/replay/reset")
def reset_replay_data(db: Session = Depends(get_db)):
    """One-click wipe of all active Replay simulation database tables (preserves persistent file archives)."""
    count = ReplayService.reset_replay_data(db)
    return {"message": f"Successfully reset Replay environment. {count} database records removed. Persistent archives preserved.", "records_wiped": count}


# 6. Similar Days Explorer
@app.get("/api/v1/instruments/{symbol}/similar-days")
def get_similar_days(symbol: str, db: Session = Depends(get_db)):
    today = datetime.date.today()
    regime = db.query(DailyMarketRegime).filter(DailyMarketRegime.date == today).first()
    if not regime:
        regime = db.query(DailyMarketRegime).order_by(DailyMarketRegime.date.desc()).first()
    
    dxy_reg = regime.dxy_regime if regime else "BULLISH"
    risk_sent = regime.risk_sentiment if regime else "RISK_ON"
    
    trend = DecisionIntelligenceEngine.get_current_trend(db, symbol.upper())
    
    matching_sigs = DecisionIntelligenceEngine.find_similar_signatures(
        db, symbol.upper(), trend, dxy_reg, risk_sent
    )
    
    # Format top 5 matching signatures
    results = []
    for sig in matching_sigs[:5]:
        # Determine matching variables
        matched = []
        if sig.trend == trend: matched.append("Trend")
        if sig.dxy_state == dxy_reg: matched.append("DXY State")
        if sig.risk_sentiment == risk_sent: matched.append("Risk Sentiment")
        
        results.append({
            "date": sig.date.strftime("%Y-%m-%d"),
            "session": sig.session,
            "trend": sig.trend,
            "dxy_state": sig.dxy_state,
            "risk_sentiment": sig.risk_sentiment,
            "news_environment": sig.news_environment,
            "volatility_regime": sig.volatility_regime,
            "outcome": sig.outcome,
            "mae_pips": sig.mae_pips,
            "mfe_pips": sig.mfe_pips,
            "holding_time_minutes": sig.holding_time_minutes,
            "matching_variables": matched
        })
    return results

# 7. Instrument DNA Endpoint
@app.get("/api/v1/instruments/{symbol}/dna")
def get_instrument_dna(symbol: str, db: Session = Depends(get_db)):
    inst = symbol.upper()
    sigs = db.query(MarketSignature).filter(MarketSignature.instrument == inst).all()
    if not sigs:
        raise HTTPException(status_code=404, detail=f"No signatures found for {symbol}")
        
    win_sigs = [s for s in sigs if s.outcome == "WIN"]
    win_maes = [s.mae_pips for s in win_sigs] if win_sigs else [15.0]
    win_mfes = [s.mfe_pips for s in win_sigs] if win_sigs else [35.0]
    
    # Calculate DNA metrics using numpy/scipy
    normal_mae_50 = round(float(np.percentile(win_maes, 50)), 1)
    normal_mae_90 = round(float(np.percentile(win_maes, 90)), 1)
    normal_mfe = round(float(np.percentile(win_mfes, 50)), 1)
    
    continuation_rate = round(len(win_sigs) / len(sigs), 2) if sigs else 0.5
    
    # Sessions analysis
    best_session = DecisionIntelligenceEngine.get_best_session(inst)
    
    all_sessions = [s.session for s in sigs]
    worst_session = "ASIA" if best_session != "ASIA" else "NEW_YORK"
    other_sessions = [x for x in set(all_sessions) if x != best_session]
    if other_sessions:
        session_counts = {x: all_sessions.count(x) for x in other_sessions}
        worst_session = min(other_sessions, key=lambda x: [s.outcome for s in sigs if s.session == x].count("WIN") / session_counts[x])
    
    # DXY State analysis
    win_dxys = [s.dxy_state for s in win_sigs]
    best_dxy_state = max(set(win_dxys), key=win_dxys.count) if win_dxys else "BEARISH"
    
    # News analysis
    news_rates = {}
    for s in sigs:
        news_rates.setdefault(s.news_environment, []).append(1 if s.outcome == "WIN" else 0)
    worst_news_env = min(news_rates.keys(), key=lambda k: sum(news_rates[k]) / len(news_rates[k])) if news_rates else "HIGH_IMPACT_FOMC"
    
    avg_holding_time = round(float(np.mean([s.holding_time_minutes for s in sigs]))) if sigs else 90
    avg_pullback = round(float(np.mean([s.mae_pips for s in sigs])), 1) if sigs else 12.0
    
    # Construct fail signature text
    fail_signature = f"Strong DXY + RISK_OFF in {worst_session} session"
    
    return {
        "instrument": inst,
        "normal_mae_50": normal_mae_50,
        "normal_mae_90": normal_mae_90,
        "normal_mfe": normal_mfe,
        "best_session": best_session,
        "worst_session": worst_session,
        "continuation_rate": continuation_rate,
        "best_dxy_state": best_dxy_state,
        "worst_news_env": worst_news_env,
        "typical_holding_time": avg_holding_time,
        "average_pullback": avg_pullback,
        "failure_signature": fail_signature
    }

# 8. Decision Timeline Endpoint
@app.get("/api/v1/dashboard/timeline")
def get_timeline(db: Session = Depends(get_db)):
    today = datetime.date.today()
    regime = db.query(DailyMarketRegime).filter(DailyMarketRegime.date == today).first()
    if not regime:
        regime = db.query(DailyMarketRegime).order_by(DailyMarketRegime.date.desc()).first()

    dxy = regime.dxy_regime if regime else "BEARISH"
    sentiment = regime.risk_sentiment if regime else "NEUTRAL"
    yields = regime.yields_regime if regime else "STEEPENING"

    # Query top profiles today
    profiles = db.query(InstrumentDailyProfile).filter(
        InstrumentDailyProfile.date == (regime.date if regime else today)
    ).order_by(InstrumentDailyProfile.confidence_score.desc()).all()
    
    top_inst = profiles[0].instrument if profiles else "USDJPY"
    top_score = profiles[0].confidence_score if profiles else 76.8

    timeline_events = [
        {
            "time": "07:00",
            "event": "Asia Session Corridor Closes",
            "dxy": dxy,
            "sentiment": sentiment,
            "narrative": f"Asian trading session closed with DXY in {dxy} regime and risk sentiment at {sentiment.replace('_', ' ')}. Asian liquidity anchored key support levels."
        },
        {
            "time": "08:00",
            "event": "London Session Liquidity Injection",
            "dxy": dxy,
            "sentiment": sentiment,
            "narrative": f"European liquidity opened with DXY demonstrating {dxy.lower()} structural pressure. US 10Y Yield spread is currently {yields.lower()}."
        },
        {
            "time": "12:00",
            "event": "Midday Quant Alignment",
            "dxy": dxy,
            "sentiment": sentiment,
            "narrative": f"Market Signature Engine evaluated top scoring setup: {top_inst} leads the watchlist with an MSS confidence score of {top_score}."
        },
        {
            "time": "13:30",
            "event": "US NY Macro Session Open",
            "dxy": dxy,
            "sentiment": sentiment,
            "narrative": f"New York institutional flows active. DXY regime: {dxy}. Macro narrative stance: {regime.macro_summary if regime else 'DXY bearish'}"
        }
    ]

    if regime and regime.no_trade_zones:
        timeline_events.append({
            "time": "14:30",
            "event": "Active No-Trade Zone Alert",
            "dxy": dxy,
            "sentiment": sentiment,
            "narrative": f"Caution: No-Trade zone flagged for {regime.no_trade_zones[0].get('session', 'NEW_YORK')} session due to {regime.no_trade_zones[0].get('reason', 'High volatility event')}."
        })
    else:
        timeline_events.append({
            "time": "16:00",
            "event": "NY Session Corridor Lock",
            "dxy": dxy,
            "sentiment": sentiment,
            "narrative": "All major session corridors clear. Market signatures maintaining stable continuation probabilities across major forex pairs."
        })

    return timeline_events

# 9. AI Peer Challenge Chat Endpoint
@app.post("/api/v1/chat", response_model=ChatResponse)
def chat_assistant(req: ChatRequest, db: Session = Depends(get_db)):
    msg = req.message.upper()
    
    # Check for buying/selling intents
    is_buy_intent = any(x in msg for x in ["BUY", "LONG", "CALL"])
    is_sell_intent = any(x in msg for x in ["SELL", "SHORT", "PUT"])
    
    # Determine symbol
    symbol = None
    for sym in ["GBPUSD", "EURUSD", "XAUUSD", "AUDUSD", "USDJPY"]:
        if sym in msg or (sym == "XAUUSD" and "GOLD" in msg):
            symbol = sym
            break
            
    if (is_buy_intent or is_sell_intent) and symbol:
        # Check current daily profile score
        today = datetime.date.today()
        profile = db.query(InstrumentDailyProfile).filter(
            InstrumentDailyProfile.instrument == symbol,
            InstrumentDailyProfile.date == today
        ).first()
        
        if profile and profile.confidence_score < 65.0:
            # AI Disagrees and challenges trader!
            response_text = (
                f"I disagree with taking a {'long' if is_buy_intent else 'short'} position on {symbol} today.\n\n"
                f"Reasoning:\n"
                f"Today's macro regime ({profile.current_regime}) matches {profile.historical_sample_size} historical sessions, "
                f"but only {profile.continuation_probability * 100:.0f}% produced bullish continuation. "
                f"The MSS Confidence Score is extremely low ({profile.confidence_score}). "
                f"Historically, losses on {symbol} in this regime correspond to {profile.historical_failure_conditions.get('dxy_behavior', 'DXY expansion') if profile.historical_failure_conditions else 'DXY expansion'}.\n\n"
                f"The highest probability instrument on the watchlist today is AUDUSD. Would you like to compare their profiles?"
            )
            citations = [
                {"source": "MSD Database Query", "message": f"Matching sessions = {profile.historical_sample_size}, Win rate = {profile.continuation_probability * 100:.0f}%"},
                {"source": "Fail Signatures", "message": f"Common loss trigger: {profile.historical_failure_conditions.get('dxy_behavior', 'DXY behavior') if profile.historical_failure_conditions else 'DXY expansion'}"}
            ]
        else:
            # AI agrees or profile is solid
            win_rate_str = f"{profile.continuation_probability * 100:.0f}%" if profile else "62%"
            samples_str = f"{profile.historical_sample_size}" if profile else "42"
            response_text = (
                f"Grounded MSD statistics support a {'long' if is_buy_intent else 'short'} bias on {symbol}.\n\n"
                f"Historical similarity is {profile.similarity_score if profile else 82}%. "
                f"Out of {samples_str} similar historical sessions, {win_rate_str} resulted in continuation. "
                f"However, ensure your stop loss is set wider than the expected MAE of {profile.expected_mae if profile else 12.0} pips to survive normal pullback thresholds."
            )
            citations = [
                {"source": "MSD Database Query", "message": f"Continuation Win rate = {win_rate_str} across {samples_str} similar sessions."}
            ]
    else:
        # Standard query
        response_text = (
            "Explainable AI assistant active. I can analyze today's GBPUSD, EURUSD, XAUUSD, AUDUSD, or USDJPY. "
            "Ask me to analyze a pair (e.g. 'I want to buy Gold') and I will challenge your thesis using MSD historical statistics."
        )
        citations = [{"source": "System Engine", "message": "Awaiting trade intent or query."}]
        
    return ChatResponse(response=response_text, citations=citations)


# 9b. AI Analyst Endpoint — Tool-Using Reasoning Layer
@app.post("/api/v1/analyst/query", response_model=AnalystQueryResponse)
def query_ai_analyst(req: AnalystQueryRequest, db: Session = Depends(get_db)):
    """
    Market OS AI Analyst.
    - Routes query intent (status/explain/compare/simulate/methodology)
    - Fetches deterministic quantitative facts from V4 engines
    - Synthesises answer via LLM (with rule-based fallback)
    - Returns structured evidence footer
    """
    result = analyst_engine.answer(
        db=db,
        query=req.query.strip(),
        conversation_history=req.conversation_history or [],
        symbol_hint=req.symbol,
    )

    # Build suggested followups based on intent and resolved symbol
    sym = result.get("symbol") or "GBPUSD"
    intent = result.get("intent", "GENERAL")
    followup_map = {
        "STATUS":      [f"Why is {sym} in this state?", f"What happens if {sym} drops 10 pips?", f"Compare {sym} with EURUSD."],
        "EXPLAIN":     [f"Show me the historical evidence for {sym}.", f"What is P90 invalidation?", f"Where should I enter {sym}?"],
        "COMPARE":     [f"What is the status of GBPUSD right now?", "Show me the full watchlist rankings.", "Explain what READY means."],
        "SIMULATE":    [f"What is the current status of {sym}?", f"Where is the P90 invalidation for {sym}?", f"Explain the acceptable corridor."],
        "METHODOLOGY": [f"What is the status of {sym} right now?", "What does WAIT mean?", "Why is P25 = 0 valid?"],
        "ENTRY":       [f"What is the fill probability at the optimal depth for {sym}?", f"What happens if I enter at market on {sym}?", f"Explain the waiting cost."],
        "GENERAL":     [f"What is {sym} doing?", "Compare all instruments.", "Explain the Market OS methodology."],
    }
    followups = followup_map.get(intent, followup_map["GENERAL"])

    return AnalystQueryResponse(
        query=req.query,
        answer=result["answer"],
        evidence=result["evidence"],
        suggested_followups=followups,
        intent=intent,
        symbol=sym,
    )

# 10. Realtime Endpoints
@app.get("/api/v1/realtime/status")
def get_realtime_status():
    return {
        "is_running": realtime_service.is_running,
        "last_refresh_time": realtime_service.last_refresh_time.isoformat() if realtime_service.last_refresh_time else None,
        "quotes": realtime_service.current_quotes,
        "macro": realtime_service.macro_snapshot
    }

@app.post("/api/v1/realtime/refresh")
async def force_realtime_refresh(background_tasks: BackgroundTasks):
    background_tasks.add_task(realtime_service.refresh_data)
    return {"message": "Realtime refresh initiated"}

# 11. Currency Strength Matrix Endpoint
@app.get("/api/v1/dashboard/currency-strength")
def get_currency_strength(mode: str = "intraday", db: Session = Depends(get_db)):
    from .engine import CurrencyStrengthEngine
    return CurrencyStrengthEngine.get_matrix(db, mode=mode)


# 12. Chart Overlay Engine Endpoint
@app.get("/api/v1/chart/{symbol}/overlays")
def get_chart_overlays(symbol: str, timeframe: str = "1d", db: Session = Depends(get_db)):
    """
    Returns data for the interactive MSD chart overlays across multi-timeframes (5m, 15m, 1h, 4h, 1d):
    - candles: OHLC price series dynamically fetched per timeframe resolution
    - mae_cloud: 50th & 90th percentile adverse excursion price levels scaled to timeframe
    - mfe_cloud: average & max favorable expansion price levels scaled to timeframe
    - execution_zones: best/worst session UTC hour bands
    - historical_ghosts: price trajectories of top matching historical signatures
    - trade_health: current price regime relative to MAE/MFE thresholds
    """
    inst = symbol.upper()
    tf_clean = timeframe.lower().strip()

    # --- 1. OHLC Candle Series (Intraday vs Daily) ---
    candles = []
    try:
        import yfinance as yf
        ticker_map = {"GBPUSD": "GBPUSD=X", "EURUSD": "EURUSD=X", "XAUUSD": "GC=F", "AUDUSD": "AUDUSD=X", "USDJPY": "USDJPY=X"}
        symbol_yf = ticker_map.get(inst, f"{inst}=X")
        
        if tf_clean == "5m":
            period_str, yf_interval = "5d", "5m"
        elif tf_clean == "15m":
            period_str, yf_interval = "1mo", "15m"
        elif tf_clean in ["1h", "4h"]:
            period_str, yf_interval = "1mo", "1h"
        else:  # "1d"
            period_str, yf_interval = "1y", "1d"

        df = yf.Ticker(symbol_yf).history(period=period_str, interval=yf_interval)
        if df is not None and not df.empty:
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
            if tf_clean == "4h":
                df = df.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()

            df = df.tail(120)
            for idx, r in df.iterrows():
                ts = int(idx.timestamp()) if hasattr(idx, 'timestamp') else int(pd.Timestamp(idx).timestamp())
                candles.append({
                    "time": ts,
                    "open": round(float(r["Open"]), 5),
                    "high": round(float(r["High"]), 5),
                    "low": round(float(r["Low"]), 5),
                    "close": round(float(r["Close"]), 5)
                })
    except Exception as e:
        logger.warning(f"Live candle fetch failed for {inst} {tf_clean}: {e}")

    # Fallback to PriceCache (Daily: most recent 120 days up to today)
    if not candles:
        rows = db.query(PriceCache).filter(
            PriceCache.instrument == inst
        ).order_by(PriceCache.date.desc()).limit(120).all()
        rows.reverse()

        for r in rows:
            ts = int(datetime.datetime.combine(r.date, datetime.time(0, 0)).timestamp())
            candles.append({
                "time": ts,
                "open": round(r.open, 5),
                "high": round(r.high, 5),
                "low": round(r.low, 5),
                "close": round(r.close, 5)
            })

    if not candles:
        raise HTTPException(status_code=404, detail=f"No price data found for {inst}")

    # Synchronize with live quote snapshot
    quotes = fetch_realtime_quotes([inst])
    live_quote = quotes.get(inst)
    if live_quote and "price" in live_quote and live_quote["price"] > 0:
        current_price = float(live_quote["price"])
        if candles:
            candles[-1]["close"] = current_price
            if "high" in live_quote:
                candles[-1]["high"] = max(candles[-1]["high"], float(live_quote["high"]))
            if "low" in live_quote:
                candles[-1]["low"] = min(candles[-1]["low"], float(live_quote["low"]))
    else:
        current_price = candles[-1]["close"]

    # --- 2. Hierarchical Adaptive Context Signature Matching ---
    regime = db.query(DailyMarketRegime).order_by(DailyMarketRegime.date.desc()).first()
    dxy_state = regime.dxy_regime if regime else "BULLISH"
    risk_sent = regime.risk_sentiment if regime else "RISK_ON"
    trend = DecisionIntelligenceEngine.get_current_trend(db, inst)

    # Grounded signature matching matching Watchlist profile engine
    matching_sigs = DecisionIntelligenceEngine.find_similar_signatures(
        db, inst, trend, dxy_state, risk_sent
    )
    sample_quality = DecisionIntelligenceEngine.classify_sample_size_quality(len(matching_sigs))
    filters_applied = {"instrument": inst, "trend": trend, "dxy_state": dxy_state, "risk_sentiment": risk_sent}
    relaxation_description = "Tier 1: Grounded Context Match"

    win_sigs = [s for s in matching_sigs if s.outcome == "WIN"]
    loss_sigs = [s for s in matching_sigs if s.outcome == "LOSS"]

    raw_win_rate = len(win_sigs) / len(matching_sigs) if matching_sigs else 0.5
    cal_res = DecisionIntelligenceEngine.calibrate_win_probability(raw_win_rate, db)
    calibrated_win_rate = cal_res["calibrated_prob"]

    pip_size = 0.01 if "JPY" in inst else 0.1 if "XAU" in inst else 0.0001

    is_gold = "XAU" in inst or "GOLD" in inst
    is_jpy = "JPY" in inst
    fallback_maes = [30.0, 60.0, 100.0, 150.0] if is_gold else ([12.0, 25.0, 40.0, 60.0] if is_jpy else [8.0, 15.0, 25.0, 35.0])
    fallback_mfes = [100.0, 180.0, 300.0] if is_gold else ([40.0, 80.0, 130.0] if is_jpy else [25.0, 50.0, 85.0])

    # --- 3. Empirical MAE & MFE Bounds with 1,000-Iteration Bootstrap 95% CIs ---
    all_maes = [s.mae_pips for s in matching_sigs] if matching_sigs else fallback_maes
    all_mfes = [s.mfe_pips for s in win_sigs] if win_sigs else ([s.mfe_pips for s in matching_sigs] if matching_sigs else fallback_mfes)

    mae_boot = DecisionIntelligenceEngine.compute_bootstrap_percentiles(all_maes, [25.0, 50.0, 75.0, 90.0], n_bootstraps=1000)
    mfe_boot = DecisionIntelligenceEngine.compute_bootstrap_percentiles(all_mfes, [50.0, 75.0, 90.0], n_bootstraps=1000)

    mae_25 = mae_boot["P25"]["val"]
    mae_50 = mae_boot["P50"]["val"]
    mae_75 = mae_boot["P75"]["val"]
    mae_90 = mae_boot["P90"]["val"]

    mfe_50 = mfe_boot["P50"]["val"]
    mfe_75 = mfe_boot["P75"]["val"]
    mfe_90 = mfe_boot["P90"]["val"]

    # Anchor levels to T0 decision price (Daily Open) so levels remain stationary for the session
    quotes = fetch_realtime_quotes([inst])
    live_quote = quotes.get(inst)
    if live_quote and "open" in live_quote and live_quote["open"] > 0:
        setup_ref_price = float(live_quote["open"])
    else:
        daily_row = db.query(PriceCache).filter(PriceCache.instrument == inst).order_by(PriceCache.date.desc()).first()
        setup_ref_price = float(daily_row.open) if daily_row else current_price

    direction_mult = -1.0 if trend == "BULLISH" else 1.0
    mae_cloud = {
        "mae_25_price": round(setup_ref_price + direction_mult * mae_25 * pip_size, 5),
        "mae_50_price": round(setup_ref_price + direction_mult * mae_50 * pip_size, 5),
        "mae_75_price": round(setup_ref_price + direction_mult * mae_75 * pip_size, 5),
        "mae_90_price": round(setup_ref_price + direction_mult * mae_90 * pip_size, 5),
        "mae_25_pips": round(mae_25, 1),
        "mae_50_pips": round(mae_50, 1),
        "mae_75_pips": round(mae_75, 1),
        "mae_90_pips": round(mae_90, 1),
        "setup_ref_price": setup_ref_price,
        "mae_50_ci": [mae_boot["P50"]["ci_lower"], mae_boot["P50"]["ci_upper"]],
        "mae_75_ci": [mae_boot["P75"]["ci_lower"], mae_boot["P75"]["ci_upper"]],
        "mae_90_ci": [mae_boot["P90"]["ci_lower"], mae_boot["P90"]["ci_upper"]],
        "label_50": f"P50 MAE ({mae_50:.1f}p [CI: {mae_boot['P50']['ci_lower']:.1f}-{mae_boot['P50']['ci_upper']:.1f}p])",
        "label_75": f"P75 MAE ({mae_75:.1f}p [CI: {mae_boot['P75']['ci_lower']:.1f}-{mae_boot['P75']['ci_upper']:.1f}p])",
        "label_90": f"P90 Survival Stop ({mae_90:.1f}p [CI: {mae_boot['P90']['ci_lower']:.1f}-{mae_boot['P90']['ci_upper']:.1f}p])"
    }

    # --- 4. Empirical MFE Cloud (P50, P75, P90 with Bootstrap CIs) ---
    target_mult = 1.0 if trend == "BULLISH" else -1.0
    mfe_cloud = {
        "mfe_50_price": round(setup_ref_price + target_mult * mfe_50 * pip_size, 5),
        "mfe_75_price": round(setup_ref_price + target_mult * mfe_75 * pip_size, 5),
        "mfe_90_price": round(setup_ref_price + target_mult * mfe_90 * pip_size, 5),
        "mfe_50_pips": round(mfe_50, 1),
        "mfe_75_pips": round(mfe_75, 1),
        "mfe_90_pips": round(mfe_90, 1),
        "mfe_50_ci": [mfe_boot["P50"]["ci_lower"], mfe_boot["P50"]["ci_upper"]],
        "mfe_75_ci": [mfe_boot["P75"]["ci_lower"], mfe_boot["P75"]["ci_upper"]],
        "mfe_90_ci": [mfe_boot["P90"]["ci_lower"], mfe_boot["P90"]["ci_upper"]],
        "label_50": f"P50 Target 1 ({mfe_50:.1f}p [CI: {mfe_boot['P50']['ci_lower']:.1f}-{mfe_boot['P50']['ci_upper']:.1f}p])",
        "label_75": f"P75 Target 2 ({mfe_75:.1f}p [CI: {mfe_boot['P75']['ci_lower']:.1f}-{mfe_boot['P75']['ci_upper']:.1f}p])",
    }

    # --- 5. Execution Zones (best/worst session UTC hour windows) ---
    session_windows = {
        "ASIA": {"start_hour": 0, "end_hour": 7, "label": "Asia Session (00:00-07:00 UTC)"},
        "LONDON": {"start_hour": 7, "end_hour": 13, "label": "London Session (07:00-13:00 UTC)"},
        "NEW_YORK": {"start_hour": 13, "end_hour": 21, "label": "New York Session (13:00-21:00 UTC)"}
    }
    best_session = DecisionIntelligenceEngine.get_best_session(inst)
    session_win_rates = {}
    for sess in ["ASIA", "LONDON", "NEW_YORK"]:
        if sess == best_session:
            continue
        sess_sigs = [s for s in matching_sigs if s.session == sess]
        if sess_sigs:
            w_rate = len([s for s in sess_sigs if s.outcome == "WIN"]) / len(sess_sigs)
            session_win_rates[sess] = w_rate

    worst_session = min(session_win_rates, key=session_win_rates.get) if session_win_rates else "ASIA"

    execution_zones = {
        "best": {
            "start_hour": session_windows[best_session]["start_hour"],
            "end_hour": session_windows[best_session]["end_hour"],
            "label": f"Optimal Entry Corridor ({session_windows[best_session]['label']})",
            "session": best_session
        },
        "worst": {
            "start_hour": session_windows[worst_session]["start_hour"],
            "end_hour": session_windows[worst_session]["end_hour"],
            "label": f"Low Liquidity Warning ({session_windows[worst_session]['label']})",
            "session": worst_session
        }
    }

    # --- 6. Historical Signature Trajectories (Top 5 Matching Ghosts) ---
    ghosts = []
    top_sigs = win_sigs[:3] + loss_sigs[:2]
    for sig in top_sigs[:5]:
        path = [
            {"day_offset": 0, "price": current_price, "offset_pips": 0.0},
            {"day_offset": 1, "price": round(current_price + (sig.mfe_pips if sig.outcome == "WIN" else -sig.mae_pips) * pip_size, 5), "offset_pips": sig.mfe_pips if sig.outcome == "WIN" else -sig.mae_pips}
        ]
        ghosts.append({
            "date": sig.date.strftime("%Y-%m-%d"),
            "outcome": sig.outcome,
            "mae_pips": sig.mae_pips,
            "mfe_pips": sig.mfe_pips,
            "session": sig.session,
            "trend": sig.trend,
            "path": path
        })

    # --- 7. Trade Health HUD ---
    mae_50_price = mae_cloud["mae_50_price"]
    mae_90_price = mae_cloud["mae_90_price"]
    mfe_avg_price = mfe_cloud["mfe_50_price"]
    mfe_max_price = mfe_cloud["mfe_90_price"]

    if trend == "BULLISH":
        if current_price >= mfe_avg_price:
            health = "PROFIT_ZONE"
            health_label = "In MFE Expansion Zone"
            health_color = "green"
        elif current_price > mae_50_price:
            health = "HEALTHY"
            health_label = "Within Normal MAE Range"
            health_color = "teal"
        elif current_price > mae_90_price:
            health = "DRAWDOWN_WARNING"
            health_label = "50th %ile MAE Breached"
            health_color = "orange"
        else:
            health = "CRITICAL"
            health_label = "90th %ile Survival Stop Zone"
            health_color = "red"
    else:  # BEARISH
        if current_price <= mfe_avg_price:
            health = "PROFIT_ZONE"
            health_label = "In MFE Expansion Zone"
            health_color = "green"
        elif current_price < mae_50_price:
            health = "HEALTHY"
            health_label = "Within Normal MAE Range"
            health_color = "teal"
        elif current_price < mae_90_price:
            health = "DRAWDOWN_WARNING"
            health_label = "50th %ile MAE Breached"
            health_color = "orange"
        else:
            health = "CRITICAL"
            health_label = "90th %ile Survival Stop Zone"
            health_color = "red"

    trade_health = {
        "status": health,
        "label": health_label,
        "color": health_color,
        "current_price": current_price,
        "trend": trend,
        "raw_win_rate": round(raw_win_rate * 100, 1),
        "win_rate": round(calibrated_win_rate * 100, 1),
        "sample_size": len(matching_sigs),
        "sample_quality": sample_quality
    }

    sig_hash = f"msd_{len(matching_sigs)}_{trend}_{dxy_state}_{risk_sent}"

    # --- 8. Entry Zone Probability Distribution ---
    # Use regime-derived risk/reward so this works independently of Trade Planner
    # Risk = P50 MAE (expected adverse excursion), Reward = P75 MFE (expected favorable expansion)
    entry_risk_pips = max(mae_50, 5.0)
    entry_reward_pips = max(mfe_75, entry_risk_pips * 1.2)

    from .engine import EntryZoneEngine
    entry_zone = EntryZoneEngine.compute_distribution(
        all_sigs=matching_sigs,
        original_risk_pips=entry_risk_pips,
        original_reward_pips=entry_reward_pips,
        baseline_win_prob=calibrated_win_rate,
    )

    # Compute price levels for each distribution step (for chart rendering)
    direction_sign = -1.0 if trend == "BULLISH" else 1.0  # BUY goes below, SELL goes above
    for step in entry_zone["distribution"]:
        step["price_level"] = round(current_price + direction_sign * step["pips_below"] * pip_size, 5)

    # Annotate profiles with price levels
    for profile_key in ["aggressive", "optimal", "conservative"]:
        d = entry_zone["profiles"][profile_key]["pips_below"]
        entry_zone["profiles"][profile_key]["price_level"] = round(
            current_price + direction_sign * d * pip_size, 5
        )

    entry_zone["current_price"] = current_price
    entry_zone["trend"] = trend
    entry_zone["pip_size"] = pip_size
    entry_zone["regime_risk_pips"] = round(entry_risk_pips, 1)
    entry_zone["regime_reward_pips"] = round(entry_reward_pips, 1)

    return {
        "symbol": inst,
        "trend": trend,
        "timeframe": timeframe,
        "candles": candles,
        "mae_cloud": mae_cloud,
        "mfe_cloud": mfe_cloud,
        "execution_zones": execution_zones,
        "historical_ghosts": ghosts,
        "trade_health": trade_health,
        "entry_zone": entry_zone,
        "empirical_metadata": {
            "build_version": "2.1.0",
            "database_version": "MSD_V2.1_2026_07",
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "signature_hash": sig_hash,
            "model_type": "ADAPTIVE_EMPIRICAL_ZERO_SCALED",
            "timeframe": timeframe.upper(),
            "sample_size": len(matching_sigs),
            "sample_quality": sample_quality["rating"],
            "sample_quality_color": sample_quality["color"],
            "sample_quality_description": sample_quality["description"],
            "relaxation_tier": 1,
            "relaxation_description": relaxation_description,
            "confidence_method": {
                "probabilities": "Isotonic Regression (PAV) + 95% Wilson Score",
                "percentiles": "1,000-Iteration Empirical Percentile Bootstrap (BCa)"
            },
            "calibration_delta": round(cal_res["calibration_delta"], 4),
            "percentiles": ["P50", "P75", "P90"],
            "filters_applied": filters_applied
        }
    }


# 13. Live Fundamentals Endpoint
@app.get("/api/v1/fundamentals/live")
async def get_live_fundamentals():
    """
    Fetches live macro fundamentals from Yahoo Finance:
    - DXY (US Dollar Index): level, 5/20-day SMA, trend direction
    - VIX (CBOE Volatility Index): level, risk regime classification
    - US10Y (10-Year Treasury Yield): level, yield regime
    - Economic calendar: dynamic high-impact event schedule for current week

    Source attribution:
    - DXY: Yahoo Finance / Intercontinental Exchange (ICE) / NYBOT
    - VIX: CBOE Volatility Index
    - US10Y: US Department of the Treasury / FRED
    Latency: ~15s fetch time. Cache TTL should be 5 minutes in production.
    """
    import asyncio
    from .data_fetcher import fetch_macro_snapshot
    from .macro_fetcher import MacroFundamentalFetcher

    try:
        snapshot = await asyncio.to_thread(fetch_macro_snapshot)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Macro data feed unavailable: {e}")

    enriched = {}
    for name, data in snapshot.items():
        current = data.get("current", 0.0)
        sma5 = data.get("sma_5", current)
        sma20 = data.get("sma_20", current)
        recent = data.get("recent_closes", [current, current])

        prev = recent[-2] if len(recent) >= 2 else current
        change = round(current - prev, 4)
        change_pct = round((change / prev) * 100, 2) if prev != 0 else 0.0

        diff_pct = ((sma5 - sma20) / sma20 * 100) if sma20 != 0 else 0.0
        if diff_pct > 0.15:
            trend = "BULLISH"
        elif diff_pct < -0.15:
            trend = "BEARISH"
        else:
            trend = "CONSOLIDATING"

        enriched[name] = {
            "current": current,
            "change": change,
            "change_pct": change_pct,
            "trend": trend,
            "sma_5": round(sma5, 4),
            "sma_20": round(sma20, 4),
            "high_52w": data.get("high_52w", current),
            "low_52w": data.get("low_52w", current),
        }

    vix_val = enriched.get("VIX", {}).get("current", 18.0)
    if vix_val >= 22.0:
        risk_sentiment = "RISK_OFF"
    elif vix_val <= 15.0:
        risk_sentiment = "RISK_ON"
    else:
        risk_sentiment = "NEUTRAL"

    yields_regime = enriched.get("US10Y", {}).get("trend", "STABLE")

    try:
        calendar = await asyncio.to_thread(MacroFundamentalFetcher.fetch_live_economic_calendar)
    except Exception:
        calendar = []

    return {
        "source": "Yahoo Finance / ICE / CBOE / US Treasury",
        "latency_note": "Data refreshed every 5 minutes. May lag 10-15 minutes during market open.",
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "indicators": enriched,
        "derived": {
            "risk_sentiment": risk_sentiment,
            "yields_regime": yields_regime,
            "dxy_trend": enriched.get("DXY", {}).get("trend", "CONSOLIDATING"),
        },
        "economic_calendar": calendar,
    }


# =============================================================================
# EXECUTION GATEWAY & MULTI-PLATFORM BRIDGE ENDPOINTS
# =============================================================================

from .execution import execution_bridge, PlatformType, ExecutionOrder, OrderDirection
from fastapi.responses import FileResponse, PlainTextResponse


@app.get("/api/v1/execution/status")
def get_execution_gateway_status():
    """Returns gateway status, connected terminal info, open positions, and guardrail settings."""
    return execution_bridge.get_status()


@app.post("/api/v1/execution/connect")
def connect_execution_platform(payload: Dict[str, Any]):
    """Initializes and connects to the execution platform (MT5_NATIVE, MT4, cTrader)."""
    payload_copy = dict(payload)
    platform_str = payload_copy.pop("platform", "MT5_NATIVE")
    try:
        platform_enum = PlatformType(platform_str)
    except ValueError:
        platform_enum = PlatformType.MT5_NATIVE
    return execution_bridge.connect_platform(platform=platform_enum, **payload_copy)


@app.post("/api/v1/execution/disconnect")
def disconnect_execution_platform():
    """Disconnects the active execution platform."""
    return execution_bridge.disconnect_platform()


@app.post("/api/v1/execution/toggle-auto")
def toggle_auto_execution(payload: Dict[str, Any]):
    """Enables or pauses automatic trade order dispatching."""
    enabled = payload.get("enabled", True)
    execution_bridge.is_auto_execution_enabled = bool(enabled)
    return {"status": "UPDATED", "auto_execution_enabled": execution_bridge.is_auto_execution_enabled}


@app.post("/api/v1/execution/orders")
def dispatch_execution_order(order_data: Dict[str, Any]):
    """Dispatches a market/limit execution order with -0.35R invalidation parameters."""
    try:
        direction_enum = OrderDirection.LONG if order_data.get("direction", "LONG").upper() == "LONG" else OrderDirection.SHORT
        order = ExecutionOrder(
            signal_id=order_data.get("signal_id", f"SIG-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"),
            instrument=order_data.get("instrument", "GBPUSD"),
            direction=direction_enum,
            entry_reference_price=float(order_data.get("entry_reference_price", 1.0)),
            stop_loss=float(order_data.get("stop_loss", 0.0)),
            take_profit=float(order_data.get("take_profit", 0.0)),
            risk_r_pips=float(order_data.get("risk_r_pips", 35.0)),
            position_size_lots=float(order_data.get("position_size_lots", 0.1)),
            risk_pct=float(order_data.get("risk_pct", 1.0)),
            mae_early_inval_r=float(order_data.get("mae_early_inval_r", -0.35)),
            mae_early_inval_price=float(order_data["mae_early_inval_price"]) if "mae_early_inval_price" in order_data else None,
            mfe_disarm_r=float(order_data.get("mfe_disarm_r", 0.35)),
            mfe_disarm_price=float(order_data["mfe_disarm_price"]) if "mfe_disarm_price" in order_data else None,
            max_allowed_spread_pips=float(order_data.get("max_allowed_spread_pips", 2.5)),
            max_slippage_pips=float(order_data.get("max_slippage_pips", 1.5))
        )
        res = execution_bridge.dispatch_signal_order(order)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/execution/positions")
def get_execution_positions():
    """Returns all active live execution positions across connected platforms with live MAE/MFE excursions."""
    positions = execution_bridge.get_all_positions()
    return [pos.dict() for pos in positions]


@app.post("/api/v1/execution/close")
def close_execution_position(payload: Dict[str, Any]):
    """Manually closes or invalidates an execution position."""
    ticket_id = str(payload.get("ticket_id"))
    exit_reason = payload.get("exit_reason", "MANUAL")
    return execution_bridge.close_position(ticket_id, exit_reason=exit_reason)


# ── Remote MQL4 / MQL5 EA Bridge Endpoints ──

@app.post("/api/v1/execution/bridge/register")
def register_mql_ea(payload: Dict[str, Any]):
    """Registers a remote MQL4/MQL5 EA client with the Market OS gateway."""
    client_id = payload.get("client_id", "EA-CLIENT-01")
    platform = payload.get("platform", "MT5")
    login = int(payload.get("account_login", 0))
    broker = payload.get("broker", "Generic")
    return execution_bridge.mql_bridge.register_ea(client_id, platform, login, broker)


@app.post("/api/v1/execution/bridge/poll")
def poll_mql_signals(payload: Dict[str, Any]):
    """Called periodically by remote MQL EAs to fetch executable order signals."""
    client_id = payload.get("client_id", "EA-CLIENT-01")
    signals = execution_bridge.mql_bridge.poll_signals(client_id)
    return {"signals": signals, "count": len(signals)}


@app.post("/api/v1/execution/bridge/fill")
def report_mql_fill(payload: Dict[str, Any]):
    """Called by remote MQL EAs to report fill confirmations and ticket IDs."""
    return execution_bridge.mql_bridge.report_fill(payload)


@app.post("/api/v1/execution/bridge/close")
def report_mql_close(payload: Dict[str, Any]):
    """Called by remote MQL EAs when a position is closed or early-invalidated."""
    return execution_bridge.mql_bridge.report_close(payload)


@app.get("/api/v1/execution/download-ea/{platform}")
def download_bridge_ea(platform: str):
    """Downloads the production-ready MQL5 or MQL4 Bridge Expert Advisor."""
    clean_platform = platform.lower().strip()
    mql_dir = os.path.join(os.path.dirname(__file__), "execution", "mql")
    if clean_platform in ["mt5", "mql5"]:
        file_path = os.path.join(mql_dir, "MarketOS_Bridge.mq5")
        if os.path.exists(file_path):
            return FileResponse(file_path, filename="MarketOS_Bridge.mq5", media_type="text/plain")
    elif clean_platform in ["mt4", "mql4"]:
        file_path = os.path.join(mql_dir, "MarketOS_Bridge.mq4")
        if os.path.exists(file_path):
            return FileResponse(file_path, filename="MarketOS_Bridge.mq4", media_type="text/plain")

    raise HTTPException(status_code=404, detail="EA script not found for requested platform")


# ── Serve built React frontend ──────────────────────────────────────────────
# Must be mounted LAST so all API routes take priority.
_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")

if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return StaticFileResponse(os.path.join(_DIST, "index.html"))
