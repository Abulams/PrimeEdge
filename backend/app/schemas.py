from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import datetime

# --- Dashboard Schemas ---
class MacroRegimeResponse(BaseModel):
    date: datetime.date
    dxy_regime: str
    yields_regime: str
    risk_sentiment: str
    no_trade_zones: List[Dict[str, Any]]
    macro_summary: str
    overall_confidence_score: float

class WatchlistInstrument(BaseModel):
    instrument: str
    direction: str = "LONG"
    status_state: str = "WAIT"  # READY, WAIT, INVALID, NO EDGE, NO SETUP
    why_this_now: str = ""
    evidence_strength: str = "Moderate"  # Strong, Moderate, Weak
    mss_score: float
    current_regime: str
    continuation_probability: float
    best_session: str
    historical_sample_size: int
    supporting_explanation: str
    acceptable_corridor: Optional[Dict[str, Any]] = None
    preferred_zone: Optional[Dict[str, Any]] = None
    historical_adverse_boundary: Optional[float] = None
    waiting_cost: Optional[Dict[str, Any]] = None
    trade_thesis: Optional[str] = None
    option_a_vs_b: Optional[Dict[str, Any]] = None
    mss_decomposition: Optional[Dict[str, float]] = None

# --- Trade Planner Schemas ---
class TradePlanRequest(BaseModel):
    instrument: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_pct: Optional[float] = 1.0
    account_balance: Optional[float] = 10000.0

class TradePlannerInput(BaseModel):
    instrument: str
    direction: Optional[str] = "BUY"
    timeframe: Optional[str] = "15M"
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_pct: Optional[float] = 1.0
    account_balance: Optional[float] = 10000.0
    session_name: Optional[str] = None

class TradePlanResponse(BaseModel):
    instrument: str
    risk_pips: float
    reward_pips: float
    risk_reward_ratio: float
    position_size_lots: float
    risk_amount_usd: float
    win_probability: float
    expected_mae_pips: float
    expected_mfe_pips: float
    mae_percentile: float
    survival_rate: float
    trade_quality_score: float
    warnings: List[str]

# --- Journal Schemas ---
class JournalCreate(BaseModel):
    trade_planner_log_id: Optional[int] = None
    instrument: str
    date: datetime.date
    session: str
    market_regime: str
    news_environment: str
    mss_score: float
    mae_actual: float
    mfe_actual: float
    execution_quality: str
    risk_quality: str
    outcome: str
    lessons: Optional[str] = None

class JournalResponseModel(BaseModel):
    id: int
    trade_planner_log_id: Optional[int]
    instrument: str
    date: datetime.date
    session: str
    market_regime: str
    news_environment: str
    mss_score: float
    mae_actual: float
    mfe_actual: float
    execution_quality: str
    risk_quality: str
    outcome: str
    lessons: Optional[str]
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Auto Journal Schemas ---
class SetupSnapshotCreate(BaseModel):
    instrument: str
    source: Optional[str] = "MANUAL"
    direction: Optional[str] = None

class SetupSnapshotResponse(BaseModel):
    id: int
    instrument: str
    date: datetime.date
    direction: str
    trend: str
    status_at_snapshot: str
    setup_ref_price: float
    live_price_at_snap: Optional[float]

    mae_p25_pips: Optional[float]
    mae_p50_pips: Optional[float]
    mae_p75_pips: Optional[float]
    mae_p90_pips: Optional[float]

    mfe_p25_pips: Optional[float]
    mfe_p50_pips: Optional[float]
    mfe_p75_pips: Optional[float]
    mfe_p90_pips: Optional[float]

    corridor_p25_price: Optional[float]
    corridor_p75_price: Optional[float]
    p90_invalidation: Optional[float]
    preferred_entry_low: Optional[float]
    preferred_entry_high: Optional[float]

    dxy_regime: Optional[str]
    risk_sentiment: Optional[str]
    session: Optional[str]
    historical_n: Optional[int]
    continuation_prob: Optional[float]
    confidence_score: Optional[float]
    system_preference: Optional[str]
    setup_thesis: Optional[str]
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class AcceptSetupRequest(BaseModel):
    snapshot_id: int
    actual_entry: float
    actual_sl: float
    actual_tp: float
    entry_type: Optional[str] = "MARKET"
    position_size_lots: Optional[float] = 0.1
    risk_pct: Optional[float] = 1.0
    account_balance: Optional[float] = 10000.0
    notes: Optional[str] = None

class PassSetupRequest(BaseModel):
    snapshot_id: int
    notes: Optional[str] = None

class CloseTradeRequest(BaseModel):
    trade_id: int
    exit_price: float
    exit_reason: Optional[str] = "MANUAL"

class TradeRecordResponse(BaseModel):
    id: int
    setup_snapshot_id: int
    lifecycle_state: str
    execution_status: Optional[str] = "QUEUED"
    broker_ticket: Optional[str] = None
    decision_at: Optional[datetime.datetime]
    decision_type: Optional[str]

    actual_entry: Optional[float]
    entry_timestamp: Optional[datetime.datetime]
    entry_type: Optional[str]
    entry_in_corridor: Optional[str]
    entry_deviation_pips: Optional[float]

    actual_sl: Optional[float]
    actual_tp: Optional[float]
    system_suggested_sl: Optional[float]
    system_suggested_tp: Optional[float]
    sl_deviation_pips: Optional[float]
    tp_deviation_pips: Optional[float]

    position_size_lots: Optional[float]
    risk_pct: Optional[float]

    max_mae_pips: Optional[float]
    max_mfe_pips: Optional[float]

    mae_p25_reached: Optional[int]
    mae_p50_reached: Optional[int]
    mae_p75_reached: Optional[int]
    mae_p90_reached: Optional[int]
    mfe_p25_reached: Optional[int]
    mfe_p50_reached: Optional[int]
    mfe_p75_reached: Optional[int]
    mfe_p90_reached: Optional[int]

    exit_price: Optional[float]
    exit_timestamp: Optional[datetime.datetime]
    exit_reason: Optional[str]
    outcome: Optional[str]
    pnl_pips: Optional[float]
    pnl_r: Optional[float]

    setup_outcome: Optional[str]
    execution_outcome: Optional[str]
    max_mfe_percentile: Optional[float]
    max_mae_percentile: Optional[float]
    notes: Optional[str]

    setup: Optional[SetupSnapshotResponse] = None

    class Config:
        from_attributes = True

class AutoJournalPerformanceResponse(BaseModel):
    total_trades_logged: int
    total_passed_setups: int
    trader_win_rate: float
    setup_success_rate: float
    average_r_multiple: float
    average_mae_endured_pips: float
    average_mfe_captured_pips: float
    avoidable_losses_from_poor_execution: int
    win_count: int
    loss_count: int


# --- Chat & Analyst Schemas ---
class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    response: str
    citations: List[Dict[str, Any]]

class AnalystQueryRequest(BaseModel):
    query: str
    symbol: Optional[str] = None                                 # UI context: currently selected pair
    conversation_history: Optional[List[Dict[str, str]]] = []   # Multi-turn memory: [{role, content}, ...]

class AnalystQueryResponse(BaseModel):
    query: str
    answer: str
    evidence: List[Dict[str, Any]]
    suggested_followups: List[str]
    intent: Optional[str] = None    # Detected intent for UI routing
    symbol: Optional[str] = None    # Resolved instrument


# --- Replay / Simulation Environment Schemas ---

class ReplayRunRequest(BaseModel):
    batch_name: Optional[str] = "Historical Control Group Audit"
    start_date: datetime.date
    end_date: datetime.date
    instruments: Optional[List[str]] = ["GBPUSD", "EURUSD", "XAUUSD", "AUDUSD", "USDJPY"]
    execution_policy: Optional[str] = "MARKET_ENTRY"  # Canonical institutional standard: Market Entry
    friction_pips: Optional[float] = 2.5  # 1.5 spread + 1.0 slippage

class ReplayBatchResponse(BaseModel):
    id: int
    batch_name: str
    start_date: datetime.date
    end_date: datetime.date
    instruments: List[str]
    execution_policy: str
    friction_pips: float
    total_setups_evaluated: int
    total_trades_taken: int
    total_setups_passed: int
    status: str
    created_at: datetime.datetime
    completed_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True

class ReplaySetupSnapshotResponse(BaseModel):
    id: int
    batch_id: int
    instrument: str
    date: datetime.date
    direction: str
    trend: str
    status_at_snapshot: str
    setup_ref_price: float
    live_price_at_snap: Optional[float]

    frozen_entry: Optional[float]
    frozen_sl: Optional[float]
    frozen_tp: Optional[float]

    mae_p25_pips: Optional[float]
    mae_p75_pips: Optional[float]
    mae_p90_pips: Optional[float]
    mfe_p50_pips: Optional[float]
    mfe_p75_pips: Optional[float]
    corridor_p25_price: Optional[float]
    p90_invalidation: Optional[float]
    historical_n: Optional[int]
    continuation_prob: Optional[float]
    confidence_score: Optional[float]

    opportunity_outcome: Optional[str]
    opportunity_max_mfe: Optional[float]
    opportunity_max_mae: Optional[float]

    created_at: datetime.datetime

    class Config:
        from_attributes = True

class ReplayTradeRecordResponse(BaseModel):
    id: int
    replay_snapshot_id: int
    lifecycle_state: str
    decision_type: Optional[str]
    actual_entry: Optional[float]
    actual_sl: Optional[float]
    actual_tp: Optional[float]
    entry_type: Optional[str]
    entry_in_corridor: Optional[str]
    entry_deviation_pips: Optional[float]
    max_mae_pips: Optional[float]
    max_mfe_pips: Optional[float]
    mae_p25_reached: Optional[int]
    mae_p50_reached: Optional[int]
    mae_p75_reached: Optional[int]
    mae_p90_reached: Optional[int]
    mfe_p25_reached: Optional[int]
    mfe_p50_reached: Optional[int]
    mfe_p75_reached: Optional[int]
    mfe_p90_reached: Optional[int]

    mfe_p25_time: Optional[datetime.datetime]
    mfe_p50_time: Optional[datetime.datetime]
    mfe_p75_time: Optional[datetime.datetime]
    mfe_p90_time: Optional[datetime.datetime]
    mae_p25_time: Optional[datetime.datetime]
    mae_p50_time: Optional[datetime.datetime]
    mae_p75_time: Optional[datetime.datetime]
    mae_p90_time: Optional[datetime.datetime]
    first_milestone: Optional[str]

    exit_price: Optional[float]
    exit_reason: Optional[str]
    outcome: Optional[str]
    pnl_pips: Optional[float]
    pnl_r: Optional[float]
    setup_outcome: Optional[str]
    execution_outcome: Optional[str]
    setup: Optional[ReplaySetupSnapshotResponse] = None

    class Config:
        from_attributes = True

class ReplayAnalyticsResponse(BaseModel):
    total_setups_evaluated: int
    total_trades_taken: int
    total_setups_passed: int
    total_unfilled_missed: int
    simulated_trader_win_rate: float
    predicted_vs_actual_win_rate_delta: float
    setup_success_rate: float
    p90_invalidation_survival_rate: float
    p90_survival_winning_trades: float
    average_r_multiple: float
    average_mae_pips: float
    average_mfe_pips: float
    opportunity_missed_wins: int
    opportunity_saved_losses: int
    status_distribution: Dict[str, int]
    trajectory_milestones: Dict[str, int]
    sl_first_pessimistic_exits: int
    friction_pips_applied: float
    integrity_checksum: Dict[str, Any]


