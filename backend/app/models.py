import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    """Multi-tenant user account."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="trader", nullable=False)   # "trader" | "admin"
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    current_tier_id = Column(Integer, ForeignKey("subscription_tiers.id"), nullable=True)  # Current active tier
    trial_used = Column(Boolean, default=False, nullable=False)  # Whether user has used their trial
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class DailyMarketRegime(Base):
    __tablename__ = "daily_market_regimes"

    date = Column(Date, primary_key=True, index=True)
    dxy_regime = Column(String, nullable=False)
    yields_regime = Column(String, nullable=False)
    risk_sentiment = Column(String, nullable=False)
    no_trade_zones = Column(JSON, nullable=True)  # List of dicts: [{"reason": "FOMC", "session": "NEW_YORK"}]
    macro_summary = Column(String, nullable=True)
    overall_confidence_score = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    instrument_profiles = relationship("InstrumentDailyProfile", back_populates="daily_regime")

class MarketSignature(Base):
    __tablename__ = "market_signatures"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instrument = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    session = Column(String, nullable=False)
    trend = Column(String, nullable=False)
    dxy_state = Column(String, nullable=False)
    risk_sentiment = Column(String, nullable=False)
    news_environment = Column(String, nullable=False)
    volatility_regime = Column(String, nullable=False)
    continuation_or_reversal = Column(String, nullable=False)
    mae_pips = Column(Float, nullable=False)
    mfe_pips = Column(Float, nullable=False)
    holding_time_minutes = Column(Integer, nullable=False)
    outcome = Column(String, nullable=False)
    supporting_macro_conditions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class InstrumentDailyProfile(Base):
    __tablename__ = "instrument_daily_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instrument = Column(String, nullable=False, index=True)
    date = Column(Date, ForeignKey("daily_market_regimes.date"), nullable=False, index=True)
    current_regime = Column(String, nullable=False)
    similarity_score = Column(Float, nullable=False)
    continuation_probability = Column(Float, nullable=False)
    expected_mae = Column(Float, nullable=False)
    expected_mfe = Column(Float, nullable=False)
    expected_holding_time = Column(Integer, nullable=False)
    historical_sample_size = Column(Integer, nullable=False)
    best_session = Column(String, nullable=False)
    historical_failure_conditions = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=False)
    supporting_explanation = Column(String, nullable=True)
    mss_decomposition = Column(JSON, nullable=True)
    similarity_decomposition = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    daily_regime = relationship("DailyMarketRegime", back_populates="instrument_profiles")

class TradePlannerLog(Base):
    __tablename__ = "trade_planner_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instrument = Column(String, nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    trade_quality_score = Column(Float, nullable=False)
    probability_win = Column(Float, nullable=False)
    expected_mae = Column(Float, nullable=False)
    expected_mfe = Column(Float, nullable=False)
    position_size = Column(Float, nullable=False)
    risk_amount = Column(Float, nullable=False)
    warnings = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    journal_entry = relationship("TradingJournal", back_populates="trade_planner", uselist=False)

class TradingJournal(Base):
    __tablename__ = "trading_journal"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trade_planner_log_id = Column(Integer, ForeignKey("trade_planner_logs.id"), nullable=True)
    instrument = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    session = Column(String, nullable=False)
    market_regime = Column(String, nullable=False)
    news_environment = Column(String, nullable=False)
    mss_score = Column(Float, nullable=False)
    mae_actual = Column(Float, nullable=False)
    mfe_actual = Column(Float, nullable=False)
    execution_quality = Column(String, nullable=False)
    risk_quality = Column(String, nullable=False)
    outcome = Column(String, nullable=False)
    lessons = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    trade_planner = relationship("TradePlannerLog", back_populates="journal_entry")

class PriceCache(Base):
    __tablename__ = "price_cache"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instrument = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)

class SetupSnapshot(Base):
    __tablename__ = "setup_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instrument = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    direction = Column(String, nullable=False)
    trend = Column(String, nullable=False)
    status_at_snapshot = Column(String, nullable=False)
    setup_ref_price = Column(Float, nullable=False)
    live_price_at_snap = Column(Float, nullable=True)

    mae_p25_pips = Column(Float, nullable=True)
    mae_p50_pips = Column(Float, nullable=True)
    mae_p75_pips = Column(Float, nullable=True)
    mae_p90_pips = Column(Float, nullable=True)

    mfe_p25_pips = Column(Float, nullable=True)
    mfe_p50_pips = Column(Float, nullable=True)
    mfe_p75_pips = Column(Float, nullable=True)
    mfe_p90_pips = Column(Float, nullable=True)

    corridor_p25_price = Column(Float, nullable=True)
    corridor_p75_price = Column(Float, nullable=True)
    p90_invalidation = Column(Float, nullable=True)
    preferred_entry_low = Column(Float, nullable=True)
    preferred_entry_high = Column(Float, nullable=True)

    dxy_regime = Column(String, nullable=True)
    risk_sentiment = Column(String, nullable=True)
    session = Column(String, nullable=True)
    historical_n = Column(Integer, nullable=True)
    continuation_prob = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    market_entry_ev = Column(Float, nullable=True)
    limit_entry_ev = Column(Float, nullable=True)
    system_preference = Column(String, nullable=True)
    setup_thesis = Column(String, nullable=True)

    snapshot_source = Column(String, nullable=False, default="AUTO")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    trades = relationship("TradeRecord", back_populates="setup")

class TradeRecord(Base):
    __tablename__ = "trade_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    setup_snapshot_id = Column(Integer, ForeignKey("setup_snapshots.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    account_id = Column(Integer, ForeignKey("user_broker_accounts.id"), nullable=True, index=True)

    lifecycle_state = Column(String, nullable=False, default="PENDING")
    execution_status = Column(String, nullable=False, default="QUEUED")  # QUEUED, FILLED, REJECTED, CLOSED
    broker_ticket = Column(String, nullable=True, index=True)

    decision_at = Column(DateTime, nullable=True)
    decision_type = Column(String, nullable=True)

    actual_entry = Column(Float, nullable=True)
    entry_timestamp = Column(DateTime, nullable=True)
    entry_type = Column(String, nullable=True)
    entry_in_corridor = Column(String, nullable=True)
    entry_deviation_pips = Column(Float, nullable=True)

    actual_sl = Column(Float, nullable=True)
    actual_tp = Column(Float, nullable=True)
    system_suggested_sl = Column(Float, nullable=True)
    system_suggested_tp = Column(Float, nullable=True)
    sl_deviation_pips = Column(Float, nullable=True)
    tp_deviation_pips = Column(Float, nullable=True)

    position_size_lots = Column(Float, nullable=True)
    risk_pct = Column(Float, nullable=True)
    account_balance = Column(Float, nullable=True)

    max_mae_pips = Column(Float, nullable=True, default=0.0)
    max_mfe_pips = Column(Float, nullable=True, default=0.0)

    mae_p25_reached = Column(Integer, nullable=True, default=0)
    mae_p50_reached = Column(Integer, nullable=True, default=0)
    mae_p75_reached = Column(Integer, nullable=True, default=0)
    mae_p90_reached = Column(Integer, nullable=True, default=0)
    mfe_p25_reached = Column(Integer, nullable=True, default=0)
    mfe_p50_reached = Column(Integer, nullable=True, default=0)
    mfe_p75_reached = Column(Integer, nullable=True, default=0)
    mfe_p90_reached = Column(Integer, nullable=True, default=0)

    exit_price = Column(Float, nullable=True)
    exit_timestamp = Column(DateTime, nullable=True)
    exit_reason = Column(String, nullable=True)
    outcome = Column(String, nullable=True)
    pnl_pips = Column(Float, nullable=True)
    pnl_r = Column(Float, nullable=True)

    setup_outcome = Column(String, nullable=True)
    execution_outcome = Column(String, nullable=True)
    max_mfe_percentile = Column(Float, nullable=True)
    max_mae_percentile = Column(Float, nullable=True)

    notes = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    setup = relationship("SetupSnapshot", back_populates="trades")


# --- Replay / Simulation Environment Models ---

class ReplayBatch(Base):
    __tablename__ = "replay_batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    instruments = Column(JSON, nullable=False)  # ["GBPUSD", "EURUSD", ...]
    execution_policy = Column(String, nullable=False, default="STRICT_V4_LIMIT")
    friction_pips = Column(Float, nullable=False, default=2.5)  # 1.5 spread + 1.0 slippage

    total_setups_evaluated = Column(Integer, default=0)
    total_trades_taken = Column(Integer, default=0)
    total_setups_passed = Column(Integer, default=0)
    status = Column(String, default="RUNNING")  # RUNNING, COMPLETED, FAILED

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    snapshots = relationship("ReplaySetupSnapshot", back_populates="batch", cascade="all, delete-orphan")


class ReplaySetupSnapshot(Base):
    __tablename__ = "replay_setup_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("replay_batches.id"), nullable=False, index=True)
    instrument = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    direction = Column(String, nullable=False)
    trend = Column(String, nullable=False)
    status_at_snapshot = Column(String, nullable=False)
    setup_ref_price = Column(Float, nullable=False)
    live_price_at_snap = Column(Float, nullable=True)

    # Frozen T0 Entry/SL/TP Levels
    frozen_entry = Column(Float, nullable=True)
    frozen_sl = Column(Float, nullable=True)
    frozen_tp = Column(Float, nullable=True)

    mae_p25_pips = Column(Float, nullable=True)
    mae_p50_pips = Column(Float, nullable=True)
    mae_p75_pips = Column(Float, nullable=True)
    mae_p90_pips = Column(Float, nullable=True)

    mfe_p25_pips = Column(Float, nullable=True)
    mfe_p50_pips = Column(Float, nullable=True)
    mfe_p75_pips = Column(Float, nullable=True)
    mfe_p90_pips = Column(Float, nullable=True)

    corridor_p25_price = Column(Float, nullable=True)
    corridor_p75_price = Column(Float, nullable=True)
    p90_invalidation = Column(Float, nullable=True)
    preferred_entry_low = Column(Float, nullable=True)
    preferred_entry_high = Column(Float, nullable=True)

    dxy_regime = Column(String, nullable=True)
    risk_sentiment = Column(String, nullable=True)
    session = Column(String, nullable=True)
    historical_n = Column(Integer, nullable=True)
    continuation_prob = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    market_entry_ev = Column(Float, nullable=True)
    limit_entry_ev = Column(Float, nullable=True)
    system_preference = Column(String, nullable=True)
    setup_thesis = Column(String, nullable=True)

    # Opportunity Outcome for Passed & Unfilled Setups (Without creating a TradeRecord)
    opportunity_outcome = Column(String, nullable=True)  # MISSED_WIN, SAVED_LOSS, EXPIRED_NEUTRAL, UNFILLED_MISSED_OPPORTUNITY
    opportunity_max_mfe = Column(Float, nullable=True)
    opportunity_max_mae = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    batch = relationship("ReplayBatch", back_populates="snapshots")
    trades = relationship("ReplayTradeRecord", back_populates="setup", cascade="all, delete-orphan")


class ReplayTradeRecord(Base):
    __tablename__ = "replay_trade_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    replay_snapshot_id = Column(Integer, ForeignKey("replay_setup_snapshots.id"), nullable=False, index=True)

    lifecycle_state = Column(String, nullable=False, default="PENDING")  # PENDING, ACTIVE, CLOSED, PASSED, UNFILLED

    decision_at = Column(DateTime, nullable=True)
    decision_type = Column(String, nullable=True)  # ACCEPTED, PASSED

    actual_entry = Column(Float, nullable=True)
    entry_timestamp = Column(DateTime, nullable=True)
    entry_type = Column(String, nullable=True)  # MARKET, LIMIT
    entry_in_corridor = Column(String, nullable=True)
    entry_deviation_pips = Column(Float, nullable=True)

    actual_sl = Column(Float, nullable=True)
    actual_tp = Column(Float, nullable=True)
    system_suggested_sl = Column(Float, nullable=True)
    system_suggested_tp = Column(Float, nullable=True)
    sl_deviation_pips = Column(Float, nullable=True)
    tp_deviation_pips = Column(Float, nullable=True)

    position_size_lots = Column(Float, nullable=True)
    risk_pct = Column(Float, nullable=True)

    max_mae_pips = Column(Float, nullable=True, default=0.0)
    max_mfe_pips = Column(Float, nullable=True, default=0.0)

    mae_p25_reached = Column(Integer, nullable=True, default=0)
    mae_p50_reached = Column(Integer, nullable=True, default=0)
    mae_p75_reached = Column(Integer, nullable=True, default=0)
    mae_p90_reached = Column(Integer, nullable=True, default=0)
    mfe_p25_reached = Column(Integer, nullable=True, default=0)
    mfe_p50_reached = Column(Integer, nullable=True, default=0)
    mfe_p75_reached = Column(Integer, nullable=True, default=0)
    mfe_p90_reached = Column(Integer, nullable=True, default=0)

    # Time-ordered trajectory milestone timestamps
    mfe_p25_time = Column(DateTime, nullable=True)
    mfe_p50_time = Column(DateTime, nullable=True)
    mfe_p75_time = Column(DateTime, nullable=True)
    mfe_p90_time = Column(DateTime, nullable=True)
    mae_p25_time = Column(DateTime, nullable=True)
    mae_p50_time = Column(DateTime, nullable=True)
    mae_p75_time = Column(DateTime, nullable=True)
    mae_p90_time = Column(DateTime, nullable=True)
    first_milestone = Column(String, nullable=True)  # MFE_FIRST, MAE_FIRST

    exit_price = Column(Float, nullable=True)
    exit_timestamp = Column(DateTime, nullable=True)
    exit_reason = Column(String, nullable=True)  # STOP_LOSS, TAKE_PROFIT, EOD_EXPIRE, UNFILLED
    outcome = Column(String, nullable=True)  # WIN, LOSS, BREAKEVEN, UNFILLED
    pnl_pips = Column(Float, nullable=True)
    pnl_r = Column(Float, nullable=True)

    setup_outcome = Column(String, nullable=True)
    execution_outcome = Column(String, nullable=True)
    max_mfe_percentile = Column(Float, nullable=True)
    max_mae_percentile = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    setup = relationship("ReplaySetupSnapshot", back_populates="trades")


# ---------------------------------------------------------------------------
# Cloud MT5 Execution Bridge Models (Zero-Install Multi-Tenant)
# ---------------------------------------------------------------------------

class UserBrokerAccount(Base):
    """Customer MT5 broker connection binding (credentials encrypted at rest)."""
    __tablename__ = "user_broker_accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    broker_server = Column(String, nullable=False)
    login = Column(Integer, nullable=False)
    encrypted_password = Column(String, nullable=False)
    platform_type = Column(String, default="MT5_CLOUD", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    auto_execution_enabled = Column(Boolean, default=True, nullable=False)
    allocated_worker_id = Column(String, default="worker-default-1", nullable=False)

    balance = Column(Float, default=100000.0)
    equity = Column(Float, default=100000.0)
    currency = Column(String, default="USD")
    leverage = Column(Integer, default=100)
    ping_ms = Column(Float, default=4.0)

    # Risk & Asset Sizing Preferences (Prop Desk Model)
    risk_mode = Column(String, default="FIXED_LOT", nullable=False)  # "FIXED_LOT" or "DYNAMIC_RISK_PCT"
    risk_pct = Column(Float, default=1.0, nullable=False)  # 0.25 to 2.0%
    fixed_lot_size = Column(Float, default=0.01, nullable=False)  # 0.01 to 2.0 lots
    allowed_instruments = Column(JSON, default=lambda: ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US100", "USDCHF"], nullable=False)
    max_concurrent_trades = Column(Integer, default=3, nullable=False)
    max_daily_loss_pct = Column(Float, default=3.0, nullable=False)

    last_heartbeat = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class WorkerNode(Base):
    """Registered Windows VPS worker executing isolated MT5 terminal sessions."""
    __tablename__ = "worker_nodes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    worker_id = Column(String, unique=True, index=True, nullable=False)
    hostname = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    status = Column(String, default="ONLINE", nullable=False)  # ONLINE, OFFLINE, DEGRADED
    cpu_pct = Column(Float, default=0.0)
    ram_pct = Column(Float, default=0.0)
    active_terminals = Column(Integer, default=0)
    max_terminals = Column(Integer, default=10)
    last_heartbeat = Column(DateTime, nullable=True)
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)


class ExecutionAuditLog(Base):
    """Comprehensive execution audit trail for all order dispatches and fills."""
    __tablename__ = "execution_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    worker_id = Column(String, nullable=False)
    ticket_id = Column(String, index=True, nullable=False)
    signal_id = Column(String, index=True, nullable=False)
    trade_id = Column(Integer, nullable=True, index=True)
    instrument = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    order_type = Column(String, default="MARKET", nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    sl = Column(Float, nullable=False)
    tp = Column(Float, nullable=False)
    volume = Column(Float, default=0.1, nullable=False)
    status = Column(String, default="FILLED", nullable=False)  # FILLED, CLOSED, REJECTED
    exit_reason = Column(String, nullable=True)  # EARLY_INVALIDATION_MAE, TAKE_PROFIT, MANUAL
    pnl_r = Column(Float, nullable=True)
    latency_ms = Column(Float, default=0.0)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class ExecutionOrderQueue(Base):
    """
    Durable Transactional Outbox for cloud order dispatch.
    Persisted to SQLite so restarts, reboots, and network blips NEVER drop orders.
    """
    __tablename__ = "execution_orders_queue"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    signal_id = Column(String, unique=True, index=True, nullable=False)
    trade_id = Column(Integer, ForeignKey("trade_records.id"), nullable=True, index=True)
    account_id = Column(Integer, ForeignKey("user_broker_accounts.id"), nullable=False, index=True)
    action_type = Column(String, default="OPEN", nullable=False)  # "OPEN" or "CLOSE"
    ticket_id = Column(String, nullable=True)  # for CLOSE actions
    instrument = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # "LONG" or "SHORT"
    order_type = Column(String, default="MARKET", nullable=False)
    entry_reference_price = Column(Float, nullable=False, default=0.0)
    stop_loss = Column(Float, nullable=False, default=0.0)
    take_profit = Column(Float, nullable=False, default=0.0)
    position_size_lots = Column(Float, nullable=False, default=0.01)
    risk_pct = Column(Float, nullable=False, default=1.0)
    account_balance = Column(Float, nullable=False, default=10000.0)
    status = Column(String, default="QUEUED", index=True, nullable=False)  # "QUEUED", "DISPATCHED", "FILLED", "REJECTED", "EXPIRED"
    error_comment = Column(String, nullable=True)
    retcode = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    dispatched_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class BetaFeedback(Base):
    """Direct user feedback submitted from the web UI during closed beta."""
    __tablename__ = "beta_feedbacks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String, nullable=True)
    category = Column(String, default="GENERAL", nullable=False)  # BUG, FEATURE, EXECUTION, UI_UX, GENERAL
    rating = Column(Integer, default=5, nullable=True)             # 1-5 rating
    active_tab = Column(String, nullable=True)                     # find, plan, execution, journal, why, replay, chat
    selected_instrument = Column(String, nullable=True)            # XAUUSD, GBPUSD, etc.
    message = Column(String, nullable=False)
    system_info = Column(JSON, nullable=True)                      # Browser, viewport, OS
    status = Column(String, default="NEW", nullable=False)         # NEW, REVIEWED, RESOLVED
    admin_notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class WaitlistLead(Base):
    """Exclusive Early Access Waitlist Cohort for 20 traders."""
    __tablename__ = "waitlist_leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    email = Column(String, index=True, nullable=False, unique=True)
    broker_platform = Column(String, nullable=True)       # MT5, OANDA, FTMO, etc.
    contact_method = Column(String, nullable=True)         # Email, Telegram, Discord, WhatsApp
    why_interested = Column(String, nullable=True)         # Qualitative feedback
    consent_given = Column(Boolean, default=True, nullable=False)
    status = Column(String, default="PENDING", nullable=False) # PENDING, INVITED, ONBOARDED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SubscriptionTier(Base):
    """Subscription pricing tiers: Starter, Pro, Premium."""
    __tablename__ = "subscription_tiers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)  # "starter", "pro", "premium"
    display_name = Column(String, nullable=False)  # "Starter", "Pro", "Premium"
    description = Column(String, nullable=True)
    price_monthly = Column(Float, nullable=False)  # Monthly price in USD
    price_yearly = Column(Float, nullable=True)   # Yearly price in USD (optional)
    stripe_price_id_monthly = Column(String, nullable=True)  # Stripe Price ID for monthly
    stripe_price_id_yearly = Column(String, nullable=True)   # Stripe Price ID for yearly
    price_monthly_ngn = Column(Float, nullable=True, default=0.0)  # Monthly price in NGN
    paystack_plan_id_monthly = Column(String, nullable=True)  # Paystack Plan Code for monthly
    features = Column(JSON, nullable=True)  # List of features: ["Auto-execution", "Real-time signals", etc.]
    max_accounts = Column(Integer, default=1)  # Max accounts allowed
    auto_execution_enabled = Column(Boolean, default=False)  # Whether tier has auto-execution access
    api_access_enabled = Column(Boolean, default=False)  # Whether tier has API access
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class UserSubscription(Base):
    """User subscription tracking."""
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tier_id = Column(Integer, ForeignKey("subscription_tiers.id"), nullable=False, index=True)
    payment_provider = Column(String, default="stripe", nullable=True)  # "stripe" or "paystack"
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    paystack_customer_code = Column(String, nullable=True, index=True)
    paystack_subscription_code = Column(String, nullable=True, index=True)
    paystack_reference = Column(String, nullable=True, index=True)
    status = Column(String, default="active", nullable=False)  # "active", "canceled", "past_due", "trialing"
    billing_interval = Column(String, nullable=True)  # "month" or "year"
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    trial_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", backref="subscriptions")
    tier = relationship("SubscriptionTier")


class StripeWebhookEvent(Base):
    """Log of Stripe webhook events for debugging and reconciliation."""
    __tablename__ = "stripe_webhook_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    stripe_event_id = Column(String, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)  # "customer.subscription.created", etc.
    processed = Column(Boolean, default=False, nullable=False)
    payload = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)



