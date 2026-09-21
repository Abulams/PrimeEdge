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

            # 3. Autonomous Execution Scanner for Auto-Execution Enabled Accounts
            try:
                from .models import UserBrokerAccount, TradeRecord, SetupSnapshot
                from .journal_service import JournalService

                auto_accounts = db.query(UserBrokerAccount).filter(
                    UserBrokerAccount.is_active == True,
                    UserBrokerAccount.auto_execution_enabled == True
                ).all()

                if auto_accounts:
                    instruments_to_scan = ["XAUUSD", "US100", "EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "AUDJPY"]
                    for inst in instruments_to_scan:
                        trend = DecisionIntelligenceEngine.get_current_trend(db, inst)
                        prof_data = DecisionIntelligenceEngine.generate_daily_profile_v2(db, inst, today, trend)

                        if prof_data and prof_data.get("status_state") == "READY":
                            direction = prof_data.get("direction", "LONG")
                            ref_price = prof_data.get("setup_ref_price", 0.0)
                            session_name = prof_data.get("best_session", "ANY")

                            # Retrieve existing autonomous SetupSnapshot for this exact READY signal instance, or create one
                            snap = db.query(SetupSnapshot).filter(
                                SetupSnapshot.instrument == inst,
                                SetupSnapshot.date == today,
                                SetupSnapshot.snapshot_source == "AUTONOMOUS_CLOUD_ENGINE",
                                SetupSnapshot.direction == direction,
                                SetupSnapshot.setup_ref_price == ref_price,
                                SetupSnapshot.status_at_snapshot == "READY",
                                SetupSnapshot.session == session_name
                            ).order_by(SetupSnapshot.id.desc()).first()

                            if not snap:
                                snap = JournalService.create_setup_snapshot(
                                    db, inst, source="AUTONOMOUS_CLOUD_ENGINE"
                                )

                            for acc in auto_accounts:
                                try:
                                    # Guard A: Check Allowed Instruments Whitelist
                                    allowed = acc.allowed_instruments or []
                                    if allowed and inst not in allowed:
                                        logger.debug(f"[Auto-Execution] Instrument {inst} not in allowed list {allowed} for Account #{acc.login} (ID {acc.id})")
                                        continue

                                    # Guard B: Check Max Concurrent Open Trades
                                    open_count = db.query(TradeRecord).filter(
                                        TradeRecord.account_id == acc.id,
                                        TradeRecord.lifecycle_state == "ACTIVE"
                                    ).count()
                                    max_open = acc.max_concurrent_trades or 3
                                    if open_count >= max_open:
                                        logger.debug(f"[Auto-Execution] Account #{acc.login} (ID {acc.id}) at max trades limit ({open_count}/{max_open})")
                                        continue

                                    # Guard C: STRICT 1-TRADE PER DISTINCT READY SIGNAL INSTANCE PER ACCOUNT
                                    already_executed_signal = db.query(TradeRecord).filter(
                                        TradeRecord.account_id == acc.id,
                                        TradeRecord.setup_snapshot_id == snap.id
                                    ).first()

                                    if already_executed_signal:
                                        continue  # Already executed this signal instance

                                    # Determine lot size & risk from user preferences
                                    size_lots = acc.fixed_lot_size or 0.01
                                    risk_percentage = acc.risk_pct or 1.0
                                    acc_balance = acc.balance if (acc.balance and acc.balance > 0) else 10000.0

                                    pip_mult = 100.0 if "JPY" in inst else (10.0 if "XAU" in inst else 10000.0)
                                    dir_sign = 1.0 if direction == "LONG" else -1.0
                                    mfe_target_pips = snap.mfe_p75_pips or snap.mfe_p50_pips or 30.0

                                    actual_entry = snap.corridor_p25_price or snap.setup_ref_price or 1.0
                                    actual_sl = snap.p90_invalidation or round(actual_entry - (dir_sign * 25.0 / pip_mult), 5)
                                    actual_tp = round(actual_entry + (dir_sign * mfe_target_pips / pip_mult), 5)

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
                                    logger.info(f"🤖 [Auto-Execution] Successfully queued READY signal #{snap.id} for {inst} on Account #{acc.login} (User {acc.user_id}, Acc ID {acc.id})")
                                except Exception as acc_exec_err:
                                    logger.error(f"❌ [Auto-Execution] Error executing signal #{snap.id} for Account #{acc.id} ({acc.login}): {acc_exec_err}", exc_info=True)
                                    db.rollback()
                                    continue
            except Exception as auto_err:
                logger.error(f"Error in autonomous execution scanner: {auto_err}", exc_info=True)

            logger.info("Realtime data refresh complete")
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating DB during refresh: {e}")
        finally:
            db.close()

# Global instance
realtime_service = RealtimeService()
