import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal
from .data_fetcher import fetch_realtime_quotes, fetch_macro_snapshot, ALL_INSTRUMENTS
from .models import DailyMarketRegime, InstrumentDailyProfile, PriceCache
from .signature_builder import build_daily_regime
from .engine import DecisionIntelligenceEngine, SignatureEngine

logger = logging.getLogger(__name__)

class RealtimeService:
    def __init__(self):
        self.last_refresh_time = None
        self.current_quotes = {}
        self.macro_snapshot = {}
        self.is_running = False
        self._task = None
        # Dashboard caches — computed in background, served instantly
        self.watchlist_cache = []          # List[dict] last good watchlist result
        self.csi_cache = {}                # Dict last good CSI matrix result
        self._cache_computing = False      # prevent concurrent recompute

    async def _recompute_dashboard_caches(self):
        """Recomputes watchlist + CSI in thread pool and stores results with thread-safe DB sessions."""
        if self._cache_computing:
            return
        self._cache_computing = True
        try:
            from .engine import DecisionIntelligenceEngine, CurrencyStrengthEngine
            import datetime as _dt
            today = _dt.date.today()
            instruments = ["XAUUSD", "US100", "EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "AUDJPY"]

            def _build_watchlist():
                db_t = SessionLocal()
                try:
                    watchlist = []
                    cand_order = {"READY": 0, "WAIT": 1, "NO EDGE": 2, "NO SETUP": 3, "INVALID": 4}
                    for inst in instruments:
                        try:
                            dual = DecisionIntelligenceEngine.generate_dual_profiles(db_t, inst, today)
                            candidates = [p for p in [dual.get("long"), dual.get("short")] if p is not None]
                            if candidates:
                                candidates.sort(key=lambda p: (cand_order.get(p.get("status_state"), 9), -p.get("confidence_score", 0)))
                                watchlist.append(candidates[0])
                        except Exception as e:
                            logger.error(f"[Cache] Watchlist error for {inst}: {e}", exc_info=True)
                    return watchlist
                finally:
                    db_t.close()

            def _build_csi():
                db_t = SessionLocal()
                try:
                    return CurrencyStrengthEngine.get_matrix(db_t, mode="intraday")
                except Exception as e:
                    logger.error(f"[Cache] CSI error: {e}", exc_info=True)
                    return {}
                finally:
                    db_t.close()

            wl, csi = await asyncio.gather(
                asyncio.to_thread(_build_watchlist),
                asyncio.to_thread(_build_csi),
            )
            if wl:
                self.watchlist_cache = wl
            if csi:
                self.csi_cache = csi
            logger.info(f"[Cache] Dashboard caches updated - {len(self.watchlist_cache)} watchlist items, {len(self.csi_cache)} currencies")
        except Exception as e:
            logger.error(f"[Cache] Recompute error: {e}", exc_info=True)
        finally:
            self._cache_computing = False

    async def start(self, interval_seconds: int = 300):
        """Starts the background polling task."""
        if self.is_running:
            return
        self.is_running = True
        logger.info(f"Starting realtime service, polling every {interval_seconds}s")
        self._task = asyncio.create_task(self._poll_loop(interval_seconds))

    async def stop(self):
        """Stops the background polling task."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Realtime service stopped")

    async def _poll_loop(self, interval_seconds: int):
        while self.is_running:
            try:
                await self.refresh_data()
                await self._recompute_dashboard_caches()
            except Exception as e:
                logger.error(f"Error in realtime poll: {e}")
            await asyncio.sleep(interval_seconds)

    async def refresh_data(self):
        """Forces an immediate data refresh and updates the database."""
        logger.info("Refreshing realtime market data...")
        
        # 1. Fetch latest quotes and macro data (in a thread pool to avoid blocking)
        self.current_quotes = await asyncio.to_thread(fetch_realtime_quotes, ALL_INSTRUMENTS)
        self.macro_snapshot = await asyncio.to_thread(fetch_macro_snapshot)
        self.last_refresh_time = datetime.utcnow()
        
        # 2. Update today's regime and profiles
        db = SessionLocal()
        try:
            today = datetime.utcnow().date()
            
            # Since fetch_macro_snapshot returns a dict format not DFs, 
            # we need to build regime carefully here
            dxy_data = self.macro_snapshot.get("DXY", {})
            vix_data = self.macro_snapshot.get("VIX", {})
            us10y_data = self.macro_snapshot.get("US10Y", {})
            
            # Simple regime update
            regime = db.query(DailyMarketRegime).filter(DailyMarketRegime.date == today).first()
            if regime:
                # Update existing
                if "current" in vix_data:
                    vix_val = vix_data["current"]
                    if vix_val > vix_data.get("percentile_75", 25):
                        regime.risk_sentiment = "RISK_OFF"
                    elif vix_val < vix_data.get("percentile_25", 15):
                        regime.risk_sentiment = "RISK_ON"
                    else:
                        regime.risk_sentiment = "NEUTRAL"
                        
                if "recent_closes" in dxy_data:
                    closes = dxy_data["recent_closes"]
                    if len(closes) >= 20:
                        sma_5 = sum(closes[-5:]) / 5
                        sma_20 = sum(closes[-20:]) / 20
                        diff = (sma_5 - sma_20) / sma_20 * 100
                        if diff > 0.15: regime.dxy_regime = "BULLISH"
                        elif diff < -0.15: regime.dxy_regime = "BEARISH"
                        else: regime.dxy_regime = "CONSOLIDATING"
                
                db.commit()
            
            # Update profiles with latest trends
            for inst in ALL_INSTRUMENTS:
                if inst in self.current_quotes:
                    # Append current price to cached prices to compute latest trend
                    prices = db.query(PriceCache.close).filter(
                        PriceCache.instrument == inst
                    ).order_by(PriceCache.date.desc()).limit(19).all()
                    
                    close_list = [p[0] for p in reversed(prices)]
                    close_list.append(self.current_quotes[inst]["price"])
                    
                    if len(close_list) >= 5:
                        trend = SignatureEngine.calculate_trend(close_list)
                        
                        # Re-run MSS score
                        profile_data = DecisionIntelligenceEngine.generate_daily_profile_v2(
                            db, inst, today, trend
                        )
                        
                        if profile_data:
                            profile = db.query(InstrumentDailyProfile).filter(
                                InstrumentDailyProfile.instrument == inst,
                                InstrumentDailyProfile.date == today
                            ).first()
                            
                            if not profile:
                                profile = InstrumentDailyProfile(
                                    instrument=inst,
                                    date=today,
                                    current_regime=profile_data.get("current_regime", "UNKNOWN"),
                                    similarity_score=profile_data.get("similarity_score", 70.0),
                                    continuation_probability=profile_data.get("continuation_probability", 0.60),
                                    expected_mae=profile_data.get("expected_mae", 15.0),
                                    expected_mfe=profile_data.get("expected_mfe", 30.0),
                                    expected_holding_time=profile_data.get("expected_holding_time", 120),
                                    historical_sample_size=profile_data.get("historical_sample_size", 45),
                                    best_session=profile_data.get("best_session", "LONDON"),
                                    confidence_score=profile_data.get("confidence_score", 75.0)
                                )
                                db.add(profile)
                            else:
                                profile.current_regime = profile_data.get("current_regime", profile.current_regime)
                                profile.similarity_score = profile_data.get("similarity_score", profile.similarity_score)
                                profile.continuation_probability = profile_data.get("continuation_probability", profile.continuation_probability)
                                profile.expected_mae = profile_data.get("expected_mae", profile.expected_mae)
                                profile.expected_mfe = profile_data.get("expected_mfe", profile.expected_mfe)
                                profile.expected_holding_time = profile_data.get("expected_holding_time", profile.expected_holding_time)
                                profile.historical_sample_size = profile_data.get("historical_sample_size", profile.historical_sample_size)
                                profile.best_session = profile_data.get("best_session", profile.best_session)
                                profile.confidence_score = profile_data.get("confidence_score", profile.confidence_score)
                            db.commit()

            # Update live MAE/MFE for all active trades in Auto Journal
            try:
                from .journal_service import JournalService
                JournalService.update_active_trades_with_quotes(db, self.current_quotes)
            except Exception as je:
                logger.error(f"Error updating active trade journal: {je}")

            # 3. Autonomous Execution Scanner (Zero Duplicate Guardrails & Genuine cTrader Accounts Only)
            try:
                from .models import UserBrokerAccount, TradeRecord, SetupSnapshot, ExecutionOrderQueue
                from .journal_service import JournalService
                from datetime import timedelta

                # Strict filter: ONLY active cTrader accounts with connected cTrader account IDs
                auto_accounts = db.query(UserBrokerAccount).filter(
                    UserBrokerAccount.platform == "ctrader",
                    UserBrokerAccount.is_active == True,
                    UserBrokerAccount.auto_execution_enabled == True,
                    UserBrokerAccount.ctrader_account_id != None
                ).all()

                def _dispatch_snap_to_auto_accounts(snap):
                    if not auto_accounts:
                        return
                    inst = snap.instrument
                    inst_upper = (inst or "").upper()
                    direction = snap.direction or "LONG"
                    is_index = any(idx in inst_upper for idx in ("US100", "NAS100", "USTEC", "NDX", "TECH100", "UK100", "GER40", "SPX", "US30", "AUS200"))
                    now_utc = datetime.utcnow()

                    for acc in auto_accounts:
                        try:
                            # Guard A: Check Allowed Instruments Whitelist
                            allowed = acc.allowed_instruments or []
                            if isinstance(allowed, str):
                                import json
                                try:
                                    allowed = json.loads(allowed)
                                except Exception:
                                    allowed = []
                            if allowed and inst not in allowed and "ALL" not in allowed:
                                logger.debug(f"[Auto-Execution] Instrument {inst} not in allowed list for Account #{acc.login}")
                                continue

                            # Guard B: In-Flight Queue Check ? NEVER queue duplicate if order already pending in ExecutionOrderQueue
                            in_flight_order = db.query(ExecutionOrderQueue).filter(
                                ExecutionOrderQueue.account_id == acc.id,
                                ExecutionOrderQueue.instrument == inst,
                                ExecutionOrderQueue.status.in_(["QUEUED", "DISPATCHED"])
                            ).first()
                            if in_flight_order:
                                logger.debug(f"[Auto-Execution] Order #{in_flight_order.id} for {inst} already {in_flight_order.status} in queue ? skipping duplicate")
                                continue

                            
                            # Guard B2: Snapshot-Level Per-Account Dedup
                            # Hard backstop: never create a second TradeRecord for the same
                            # (snapshot_id, account_id) pair, regardless of lifecycle state.
                            # This catches the case where a previous trade for this signal was
                            # FILLED then CLOSED, and the scanner would otherwise re-enter.
                            existing_trade_for_snap = db.query(TradeRecord).filter(
                                TradeRecord.setup_snapshot_id == snap.id,
                                TradeRecord.account_id == acc.id,
                            ).first()
                            if existing_trade_for_snap:
                                logger.debug(
                                    f"[Auto-Execution] Snapshot #{snap.id} already has Trade "
                                    f"#{existing_trade_for_snap.id} "
                                    f"(status={existing_trade_for_snap.execution_status}) "
                                    f"for Account #{acc.login} -- hard dedup block"
                                )
                                continue

# Guard C: Strict Active/Pending Trade Check on same instrument
                            has_active_or_pending = db.query(TradeRecord).join(
                                SetupSnapshot, TradeRecord.setup_snapshot_id == SetupSnapshot.id
                            ).filter(
                                TradeRecord.account_id == acc.id,
                                TradeRecord.lifecycle_state.in_(["ACTIVE", "PENDING"]),
                                TradeRecord.execution_status.in_(["QUEUED", "FILLED", "PENDING"]),
                                SetupSnapshot.instrument == inst
                            ).first()
                            if has_active_or_pending:
                                logger.debug(f"[Auto-Execution] Account #{acc.login} already has active/pending trade #{has_active_or_pending.id} on {inst} ? skipping duplicate")
                                continue

                            # Guard D: 30-Minute Cooldown on same instrument to prevent rapid-fire re-entry
                            cooldown_cutoff = now_utc - timedelta(minutes=30)
                            recent_trade = db.query(TradeRecord).join(
                                SetupSnapshot, TradeRecord.setup_snapshot_id == SetupSnapshot.id
                            ).filter(
                                TradeRecord.account_id == acc.id,
                                TradeRecord.entry_timestamp >= cooldown_cutoff,
                                SetupSnapshot.instrument == inst
                            ).first()
                            if recent_trade:
                                elapsed_mins = (now_utc - recent_trade.entry_timestamp).total_seconds() / 60
                                logger.debug(f"[Auto-Execution] Cooldown active for {inst} on Account #{acc.login} (last trade #{recent_trade.id} placed {elapsed_mins:.1f}m ago) ? skipping duplicate")
                                continue

                            # Guard D2: Session-Boundary Duplicate Prevention
                            # One trade per instrument per trading session per account.
                            # Sessions (UTC): Tokyo 00-07h, London 07-13h, NY 13-20h, After-Hours 20-24h
                            _h = now_utc.hour
                            if 0 <= _h < 7:    _cur_session = "TOKYO"
                            elif 7 <= _h < 13: _cur_session = "LONDON"
                            elif 13 <= _h < 20: _cur_session = "NEW_YORK"
                            else:              _cur_session = "AFTER_HOURS"
                            # Find start of current session
                            _session_starts = {"TOKYO": 0, "LONDON": 7, "NEW_YORK": 13, "AFTER_HOURS": 20}
                            _sess_start_h = _session_starts[_cur_session]
                            _sess_start_dt = now_utc.replace(hour=_sess_start_h, minute=0, second=0, microsecond=0)
                            session_trade = db.query(TradeRecord).join(
                                SetupSnapshot, TradeRecord.setup_snapshot_id == SetupSnapshot.id
                            ).filter(
                                TradeRecord.account_id == acc.id,
                                TradeRecord.entry_timestamp >= _sess_start_dt,
                                SetupSnapshot.instrument == inst,
                            ).first()
                            if session_trade:
                                logger.info(
                                    f"[Auto-Execution] SESSION BLOCK: {inst} trade #{session_trade.id} already placed "
                                    f"in {_cur_session} session for Account #{acc.login}. "
                                    f"Waiting for next session before re-entry."
                                )
                                continue

                            # Guard E: Check Max Concurrent Open Trades
                            # Count ACTIVE/PENDING DB records as a first-pass check.
                            # The final live-broker check happens in ctrader_copier_runner.py.
                            open_count = db.query(TradeRecord).filter(
                                TradeRecord.account_id == acc.id,
                                TradeRecord.lifecycle_state.in_(["ACTIVE", "PENDING"]),
                                TradeRecord.execution_status.in_(["QUEUED", "FILLED", "PENDING"])
                            ).count()
                            max_open = acc.max_concurrent_trades or 5
                            if open_count >= max_open:
                                logger.info(f"[Auto-Execution] Account #{acc.login} at max concurrent trades ({open_count}/{max_open}) — queuing blocked")
                                continue

                            # Guard F: Block opposite-direction trade on same instrument within same 4-hour window
                            session_cutoff = now_utc - timedelta(hours=4)
                            recent_opposite = db.query(TradeRecord).join(
                                SetupSnapshot, TradeRecord.setup_snapshot_id == SetupSnapshot.id
                            ).filter(
                                TradeRecord.account_id == acc.id,
                                TradeRecord.lifecycle_state == "CLOSED",
                                TradeRecord.exit_timestamp >= session_cutoff,
                                SetupSnapshot.instrument == inst,
                                SetupSnapshot.direction != direction
                            ).first()
                            if recent_opposite:
                                logger.info(f"[Auto-Execution] Blocking {direction} on {inst} ? opposite direction closed recently")
                                continue

                            # Determine lot size & risk geometry
                            risk_percentage = acc.risk_pct or 1.0
                            acc_balance = acc.balance if (acc.balance and acc.balance > 0) else 10000.0

                            # Pips / points multiplier
                            if "JPY" in inst_upper:
                                pip_mult = 100.0
                            elif "XAU" in inst_upper or "GOLD" in inst_upper:
                                pip_mult = 10.0
                            elif is_index:
                                pip_mult = 1.0  # Index points ? raw price units
                            else:
                                pip_mult = 10000.0  # Standard FX

                            dir_sign = 1.0 if direction == "LONG" else -1.0
                            default_sl_pts = 150.0 if is_index else (40.0 if ("XAU" in inst_upper or "GOLD" in inst_upper) else 25.0)
                            default_tp_pts = default_sl_pts * 1.5

                            actual_entry = snap.corridor_p25_price or snap.setup_ref_price or 1.0
                            if actual_entry <= 0:
                                actual_entry = 1.0

                            # Strict Geometry Verification:
                            # For LONG: SL must be strictly below entry
                            # For SHORT: SL must be strictly above entry
                            if snap.p90_invalidation and (
                                (direction == "LONG" and snap.p90_invalidation < actual_entry) or
                                (direction == "SHORT" and snap.p90_invalidation > actual_entry)
                            ):
                                actual_sl = snap.p90_invalidation
                            else:
                                actual_sl = round(actual_entry - (dir_sign * default_sl_pts / pip_mult), 5)

                            # Enforce minimum safe SL distance to prevent instant liquidation by spread
                            min_sl_dist = 25.0 if is_index else (1.5 if ("XAU" in inst_upper or "GOLD" in inst_upper) else 0.0008)
                            if abs(actual_entry - actual_sl) < min_sl_dist:
                                actual_sl = round(actual_entry - (dir_sign * min_sl_dist), 5)

                            mfe_target_pips = snap.mfe_p75_pips or snap.mfe_p50_pips or default_tp_pts
                            actual_tp = round(actual_entry + (dir_sign * mfe_target_pips / pip_mult), 5)

                            # Calculate position size
                            risk_mode = getattr(acc, "risk_mode", "DYNAMIC_RISK_PCT") or "DYNAMIC_RISK_PCT"
                            if risk_mode == "DYNAMIC_RISK_PCT":
                                risk_dist = abs(actual_entry - actual_sl)
                                risk_pips = round(risk_dist * pip_mult, 1)
                                risk_amount_usd = acc_balance * (risk_percentage / 100.0)

                                if "JPY" in inst_upper:
                                    pip_val_usd = 6.5
                                elif is_index:
                                    pip_val_usd = 1.0  # 1 pt move = $1.00 USD per 1.0 lot on cTrader index CFD
                                elif "XAU" in inst_upper or "GOLD" in inst_upper:
                                    pip_val_usd = 10.0
                                else:
                                    pip_val_usd = 10.0

                                if risk_pips > 0 and pip_val_usd > 0:
                                    calc_lots = round(risk_amount_usd / (risk_pips * pip_val_usd), 2)
                                    if is_index:
                                        size_lots = max(0.1, min(calc_lots, 5.0))
                                        size_lots = round(round(size_lots * 10) / 10, 1)
                                    else:
                                        size_lots = max(0.01, min(calc_lots, 10.0))
                                else:
                                    size_lots = 0.1 if is_index else 0.01
                                logger.info(f"?? [Auto-Execution Sizing] Account #{acc.login} DYNAMIC_RISK_PCT: balance=${acc_balance:.2f}, risk={risk_percentage}%, risk_amount=${risk_amount_usd:.2f}, risk_pips={risk_pips:.1f} -> lots={size_lots}")
                            else:
                                size_lots = acc.fixed_lot_size or (0.1 if is_index else 0.01)
                                logger.info(f"?? [Auto-Execution Sizing] Account #{acc.login} FIXED_LOT: lots={size_lots}")

                            # Queue trade ? Telegram alert is dispatched strictly post-execution on cTrader
                            JournalService.accept_setup(
                                db=db,
                                snapshot_id=snap.id,
                                actual_entry=actual_entry,
                                actual_sl=actual_sl,
                                actual_tp=actual_tp,
                                position_size_lots=size_lots,
                                risk_pct=risk_percentage,
                                account_balance=acc_balance,
                                notes=f"PrimeEdge Autonomous cTrader Execution Engine (Signal #{snap.id})",
                                account_id=acc.id,
                                user_id=acc.user_id
                            )
                            logger.info(f"?? [Auto-Execution] Queued READY signal #{snap.id} ({inst} {direction}) for cTrader Account #{acc.login} (lots={size_lots})")
                        except Exception as acc_exec_err:
                            logger.error(f"? [Auto-Execution] Error executing signal #{snap.id} for Account #{acc.id}: {acc_exec_err}", exc_info=True)
                            db.rollback()
                            continue

                # Run DUAL-HORIZON engine scan across key instruments
                instruments_to_scan = ["XAUUSD", "US100", "EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "AUDJPY"]
                for inst in instruments_to_scan:
                    try:
                        dual_profiles = DecisionIntelligenceEngine.generate_dual_profiles(db, inst, today)
                        candidates = [p for p in [dual_profiles.get("long"), dual_profiles.get("short")] if p is not None]

                        for prof_data in candidates:
                            if prof_data and prof_data.get("status_state") == "READY":
                                direction = prof_data.get("direction", "LONG")

                                existing_snap = db.query(SetupSnapshot).filter(
                                    SetupSnapshot.instrument == inst,
                                    SetupSnapshot.date == today,
                                    SetupSnapshot.snapshot_source == "AUTONOMOUS_CLOUD_ENGINE",
                                    SetupSnapshot.direction == direction,
                                    SetupSnapshot.status_at_snapshot == "READY"
                                ).order_by(SetupSnapshot.id.desc()).first()

                                if not existing_snap:
                                    logger.info(f"[Quant Engine] New READY signal detected for {inst} ({direction}) score {prof_data.get('confidence_score')}")
                                    new_snap = JournalService.create_setup_snapshot(db, inst, source="AUTONOMOUS_CLOUD_ENGINE", direction=direction)
                                    _dispatch_snap_to_auto_accounts(new_snap)
                                else:
                                    # GUARDRAIL: Never re-dispatch an existing snapshot.
                                    # Every 5-min poll re-calling _dispatch_snap_to_auto_accounts
                                    # on an already-filed signal causes duplicate trade storms
                                    # (Guard B only blocks QUEUED/DISPATCHED, not FILLED).
                                    logger.debug(
                                        f"[Quant Engine] Signal #{existing_snap.id} "
                                        f"({inst} {direction}) already dispatched today "
                                        "— skipping re-dispatch to prevent duplicate trades."
                                    )
                    except Exception as eng_err:
                        logger.error(f"[Quant Engine] Engine scan error for {inst}: {eng_err}")
            except Exception as auto_err:
                logger.error(f"Error in autonomous execution scanner: {auto_err}", exc_info=True)

            # 4. Automatic Session Close Daily Performance Digest (at or after 21:00 UTC)
            now = datetime.utcnow()
            if now.hour >= 21 and getattr(self, "_last_digest_date", None) != now.date():
                self._last_digest_date = now.date()
                try:
                    TelegramService.send_daily_digest(db)
                    logger.info("[Telegram] Automatic daily digest dispatched at session close.")
                except Exception as de:
                    logger.error(f"[Telegram] Error dispatching automatic daily digest: {de}")

            logger.info("Realtime data refresh complete")
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating DB during refresh: {e}")
        finally:
            db.close()

# Global instance
realtime_service = RealtimeService()
