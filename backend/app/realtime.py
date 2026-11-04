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

            # 3. Autonomous Execution Scanner & Telegram Signal Dispatcher
            try:
                from .models import UserBrokerAccount, TradeRecord, SetupSnapshot
                from .journal_service import JournalService
                from .telegram_service import TelegramService

                # Maintain an in-memory set of alerted snapshot IDs on the realtime service
                if not hasattr(self, "_alerted_snapshot_ids"):
                    from datetime import timedelta
                    cutoff = datetime.utcnow() - timedelta(minutes=15)
                    try:
                        older_snaps = db.query(SetupSnapshot.id).filter(
                            SetupSnapshot.date == today,
                            SetupSnapshot.created_at < cutoff
                        ).all()
                        self._alerted_snapshot_ids = {s[0] for s in older_snaps}
                    except Exception:
                        self._alerted_snapshot_ids = set()

                def _dispatch_telegram_alert(snap):
                    if not snap or not getattr(snap, "id", None):
                        return
                    if snap.id in self._alerted_snapshot_ids:
                        return
                    self._alerted_snapshot_ids.add(snap.id)

                    # Capture exact live tick quote price from memory
                    inst_quote = self.current_quotes.get(snap.instrument)
                    live_tick = None
                    if inst_quote and isinstance(inst_quote, dict):
                        live_tick = inst_quote.get("price")

                    TelegramService.send_setup_alert(snap, current_live_price=live_tick)
                    logger.info(f"ðŸ“£ [Telegram Alert] Dispatched READY signal #{snap.id} ({snap.instrument} {snap.direction}) with live tick {live_tick}")

                auto_accounts = db.query(UserBrokerAccount).filter(
                    UserBrokerAccount.is_active == True,
                    UserBrokerAccount.auto_execution_enabled == True
                ).all()

                def _dispatch_snap_to_auto_accounts(snap):
                    if not auto_accounts:
                        return
                    inst = snap.instrument
                    direction = snap.direction or "LONG"
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

                            # Guard B: Check Max Concurrent Open Trades
                            open_count = db.query(TradeRecord).filter(
                                TradeRecord.account_id == acc.id,
                                TradeRecord.lifecycle_state == "ACTIVE"
                            ).count()
                            max_open = acc.max_concurrent_trades or 5
                            if open_count >= max_open:
                                logger.debug(f"[Auto-Execution] Account #{acc.login} at max trades ({open_count}/{max_open})")
                                continue

                            # Guard C: STRICT 1-TRADE PER DISTINCT READY SIGNAL INSTANCE PER ACCOUNT
                            already_executed_signal = db.query(TradeRecord).filter(
                                TradeRecord.account_id == acc.id,
                                TradeRecord.setup_snapshot_id == snap.id
                            ).first()

                            if already_executed_signal:
                                continue  # Already executed this signal instance

                            # Guard D: Prevent duplicate active trades on the same instrument
                            has_active_trade = db.query(TradeRecord).join(
                                SetupSnapshot, TradeRecord.setup_snapshot_id == SetupSnapshot.id
                            ).filter(
                                TradeRecord.account_id == acc.id,
                                TradeRecord.lifecycle_state == "ACTIVE",
                                SetupSnapshot.instrument == inst
                            ).first()
                            if has_active_trade:
                                logger.debug(f"[Auto-Execution] Account #{acc.login} already has active trade #{has_active_trade.id} on {inst} - skipping duplicate")
                                continue

                            # Guard E: Block opposite-direction trade on same instrument within same session
                            # A "session" = last 4 hours. Prevents noise-chasing by flipping direction.
                            from datetime import timedelta
                            session_cutoff = datetime.utcnow() - timedelta(hours=4)
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
                                mins_ago = (datetime.utcnow() - recent_opposite.exit_timestamp).total_seconds() / 60
                                logger.info(
                                    f"[Auto-Execution] BLOCKING {direction} on {inst} -- "
                                    f"opposite direction closed {mins_ago:.0f}min ago. No same-session direction flip."
                                )
                                continue

                            # Guard F: Cooldown after early invalidation (30 min minimum before re-entry)
                            recent_early_inval = db.query(TradeRecord).join(
                                SetupSnapshot, TradeRecord.setup_snapshot_id == SetupSnapshot.id
                            ).filter(
                                TradeRecord.account_id == acc.id,
                                TradeRecord.lifecycle_state == "CLOSED",
                                TradeRecord.exit_reason == "EARLY_INVALIDATION_MAE",
                                TradeRecord.exit_timestamp >= datetime.utcnow() - timedelta(minutes=30),
                                SetupSnapshot.instrument == inst
                            ).first()
                            if recent_early_inval:
                                elapsed = (datetime.utcnow() - recent_early_inval.exit_timestamp).total_seconds() / 60
                                logger.info(
                                    f"[Auto-Execution] COOLDOWN active for {inst} -- "
                                    f"early invalidation {elapsed:.0f}min ago. Skipping new entry."
                                )
                                continue

                            # Determine lot size & risk from user preferences
                            risk_percentage = acc.risk_pct or 1.0
                            acc_balance = acc.balance if (acc.balance and acc.balance > 0) else 10000.0

                            # pip_mult: per-instrument correct values
                            # Indices (US100, NAS100, USTEC, etc.) trade in index points, not pip fractions
                            if "JPY" in inst:
                                pip_mult = 100.0
                            elif "XAU" in inst or "GOLD" in inst:
                                pip_mult = 10.0
                            elif any(idx in inst for idx in ("US100", "NAS100", "USTEC", "UK100", "GER40", "SPX", "US30", "AUS200")):
                                pip_mult = 1.0  # Index points -- TP/SL in raw price units
                            else:
                                pip_mult = 10000.0  # Standard FX (4-decimal pairs)
                            dir_sign = 1.0 if direction == "LONG" else -1.0
                            mfe_target_pips = snap.mfe_p75_pips or snap.mfe_p50_pips or 30.0

                            actual_entry = snap.corridor_p25_price or snap.setup_ref_price or 1.0
                            actual_sl = snap.p90_invalidation or round(actual_entry - (dir_sign * 25.0 / pip_mult), 5)
                            actual_tp = round(actual_entry + (dir_sign * mfe_target_pips / pip_mult), 5)

                            # Calculate position size based on user's configured risk mode
                            risk_mode = getattr(acc, "risk_mode", "FIXED_LOT") or "FIXED_LOT"
                            if risk_mode == "DYNAMIC_RISK_PCT":
                                risk_dist = abs(actual_entry - actual_sl)
                                risk_pips = round(risk_dist * pip_mult, 1)
                                risk_amount_usd = acc_balance * (risk_percentage / 100.0)

                                if "JPY" in inst:
                                    pip_val_usd = 6.5
                                elif "US100" in inst:
                                    pip_val_usd = 20.0
                                else:
                                    pip_val_usd = 10.0

                                if risk_pips > 0 and pip_val_usd > 0:
                                    calc_lots = round(risk_amount_usd / (risk_pips * pip_val_usd), 2)
                                    size_lots = max(0.01, min(calc_lots, 50.0))
                                else:
                                    size_lots = 0.01
                                logger.info(f"ðŸ“Š [Auto-Execution Sizing] Account #{acc.login} DYNAMIC_RISK_PCT: balance=${acc_balance:.2f}, risk={risk_percentage}%, risk_amount=${risk_amount_usd:.2f}, risk_pips={risk_pips:.1f} -> lots={size_lots}")
                            else:
                                size_lots = acc.fixed_lot_size or 0.01
                                logger.info(f"ðŸ“Š [Auto-Execution Sizing] Account #{acc.login} FIXED_LOT: lots={size_lots}")

                            # Accept trade tied to user and account
                            JournalService.accept_setup(
                                db=db,
                                snapshot_id=snap.id,
                                actual_entry=actual_entry,
                                actual_sl=actual_sl,
                                actual_tp=actual_tp,
                                position_size_lots=size_lots,
                                risk_pct=risk_percentage,
                                account_balance=acc_balance,
                                notes=f"Market OS Autonomous Execution Engine (Signal #{snap.id})",
                                account_id=acc.id,
                                user_id=acc.user_id
                            )
                            logger.info(f"ðŸ¤– [Auto-Execution] Queued READY signal #{snap.id} ({inst} {direction}) for Account #{acc.login} (Acc ID {acc.id})")
                        except Exception as acc_exec_err:
                            logger.error(f"âŒ [Auto-Execution] Error executing signal #{snap.id} for Account #{acc.id}: {acc_exec_err}", exc_info=True)
                            db.rollback()
                            continue

                # 1. Run DUAL-HORIZON engine scan across key instruments to detect ANY NEW READY setups and dispatch IMMEDIATELY
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
                                    logger.info(f"ðŸš€ [Quant Engine] New READY signal detected for {inst} ({direction}) score {prof_data.get('confidence_score')} â€” creating snapshot and alerting")
                                    new_snap = JournalService.create_setup_snapshot(db, inst, source="AUTONOMOUS_CLOUD_ENGINE", direction=direction)
                                    _dispatch_telegram_alert(new_snap)
                                    _dispatch_snap_to_auto_accounts(new_snap)
                                else:
                                    _dispatch_telegram_alert(existing_snap)
                                    _dispatch_snap_to_auto_accounts(existing_snap)
                    except Exception as eng_err:
                        logger.error(f"[Quant Engine] Engine scan error for {inst}: {eng_err}")

                # 2. Also sweep any existing READY snaps for today
                ready_snaps = db.query(SetupSnapshot).filter(
                    SetupSnapshot.date == today,
                    SetupSnapshot.status_at_snapshot == "READY",
                    SetupSnapshot.snapshot_source == "AUTONOMOUS_CLOUD_ENGINE"
                ).all()

                for snap in ready_snaps:
                    _dispatch_telegram_alert(snap)
                    _dispatch_snap_to_auto_accounts(snap)
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
