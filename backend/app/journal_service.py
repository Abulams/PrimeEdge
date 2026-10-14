"""
Market OS Auto Journal Service Layer
====================================
Manages the lifecycle of Market OS setup snapshots and trade records:
- Snapshot creation (immutable T₀ grounding)
- Trader decision (Accept vs Pass)
- Execution tracking & deviation logging
- Live MAE/MFE trajectory monitoring
- Outcome classification (Setup Outcome vs Trader Execution Outcome)
- Performance analytics & learning metrics
"""

import datetime
import logging
import re
from typing import Any, Dict, List, Optional
import numpy as np
from sqlalchemy.orm import Session, joinedload

from .models import SetupSnapshot, TradeRecord, DailyMarketRegime
from .engine import DecisionIntelligenceEngine
from .data_fetcher import fetch_realtime_quotes, get_pip_multiplier

logger = logging.getLogger(__name__)


class JournalService:

    @staticmethod
    def create_setup_snapshot(db: Session, instrument: str, source: str = "MANUAL", user_id: Optional[int] = None, direction: Optional[str] = None) -> SetupSnapshot:
        """
        Captures an immutable setup snapshot grounded at T₀ (Daily Open).
        Preserves all V4 corridor levels, percentiles, regime data, and setup thesis.
        """
        inst_upper = instrument.upper()
        today = datetime.date.today()
        if direction:
            req = direction.upper()
            trend = "BULLISH" if req in ["BUY", "LONG", "BULLISH"] else "BEARISH"
        else:
            dual = DecisionIntelligenceEngine.generate_dual_profiles(db, inst_upper, today)
            candidates = [p for p in [dual.get("long"), dual.get("short")] if p is not None]
            cand_order = {"READY": 0, "WAIT": 1, "NO EDGE": 2, "NO SETUP": 3, "INVALID": 4}
            if candidates:
                candidates.sort(key=lambda p: (cand_order.get(p.get("status_state"), 9), -p.get("confidence_score", 0)))
                winning_dir = candidates[0].get("direction", "LONG")
                trend = "BULLISH" if winning_dir == "LONG" else "BEARISH"
            else:
                trend = DecisionIntelligenceEngine.get_current_trend(db, inst_upper)

        profile = DecisionIntelligenceEngine.generate_daily_profile_v2(db, inst_upper, today, trend)

        if not profile:
            raise ValueError(f"Could not generate profile for {inst_upper}")

        regime = db.query(DailyMarketRegime).order_by(DailyMarketRegime.date.desc()).first()

        corridor = profile.get("acceptable_corridor") or {}
        preferred = profile.get("preferred_zone") or {}
        deep = profile.get("deep_retracement") or {}
        option_ab = profile.get("option_a_vs_b") or {}

        snapshot = SetupSnapshot(
            instrument=inst_upper,
            date=today,
            direction=profile.get("direction", "LONG"),
            trend=trend,
            status_at_snapshot=profile.get("status_state", "WAIT"),
            setup_ref_price=profile.get("setup_ref_price", 0.0),
            live_price_at_snap=profile.get("live_price", 0.0),

            mae_p25_pips=corridor.get("p25_pips"),
            mae_p50_pips=preferred.get("p50_pips"),
            mae_p75_pips=corridor.get("p75_pips"),
            mae_p90_pips=deep.get("p90_pips"),

            mfe_p25_pips=None, # Derived from signature distribution if available
            mfe_p50_pips=profile.get("expected_mfe"),
            mfe_p75_pips=round(profile.get("expected_mfe", 0) * 1.4, 1),
            mfe_p90_pips=round(profile.get("expected_mfe", 0) * 2.0, 1),

            corridor_p25_price=corridor.get("p25_price"),
            corridor_p75_price=corridor.get("p75_price"),
            p90_invalidation=profile.get("historical_adverse_boundary"),
            preferred_entry_low=preferred.get("p50_price"),
            preferred_entry_high=preferred.get("p75_price"),

            dxy_regime=regime.dxy_regime if regime else "UNKNOWN",
            risk_sentiment=regime.risk_sentiment if regime else "UNKNOWN",
            session=profile.get("best_session", "ANY"),
            historical_n=profile.get("historical_sample_size", 0),
            continuation_prob=profile.get("continuation_probability", 0.0),
            confidence_score=profile.get("confidence_score", 0.0),

            market_entry_ev=option_ab.get("option_a", {}).get("expected_ev") if option_ab else None,
            limit_entry_ev=option_ab.get("option_b", {}).get("expected_ev") if option_ab else None,
            system_preference=option_ab.get("system_preference") if option_ab else "MARKET",
            setup_thesis=profile.get("trade_thesis") or profile.get("why_this_now"),

            snapshot_source=source,
            user_id=user_id,
            created_at=datetime.datetime.utcnow()
        )

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    @staticmethod
    def accept_setup(
        db: Session,
        snapshot_id: int,
        actual_entry: float,
        actual_sl: float,
        actual_tp: float,
        entry_type: str = "MARKET",
        position_size_lots: float = 0.1,
        risk_pct: float = 1.0,
        account_balance: float = 10000.0,
        notes: Optional[str] = None,
        account_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> TradeRecord:
        """
        Records that the trader accepted a Market OS setup and executed a trade.
        Calculates execution deviations from the system's recommended boundaries.
        """
        snapshot = db.query(SetupSnapshot).filter(SetupSnapshot.id == snapshot_id).first()
        if not snapshot:
            raise ValueError(f"Snapshot ID {snapshot_id} not found")

        pip_mult = get_pip_multiplier(snapshot.instrument)

        # Recommended boundaries
        rec_entry = snapshot.corridor_p25_price or snapshot.setup_ref_price
        rec_sl = snapshot.p90_invalidation or snapshot.setup_ref_price
        rec_tp = round(snapshot.setup_ref_price + (1.0 if snapshot.direction == "LONG" else -1.0) * (snapshot.mfe_p75_pips or 20.0) / pip_mult, 5)

        # Deviations in pips
        entry_dev = round(abs(actual_entry - rec_entry) * pip_mult, 1)
        sl_dev = round(abs(actual_sl - rec_sl) * pip_mult, 1)
        tp_dev = round(abs(actual_tp - rec_tp) * pip_mult, 1)

        # Evaluate corridor positioning
        p25 = snapshot.corridor_p25_price
        p75 = snapshot.corridor_p75_price
        p90 = snapshot.p90_invalidation

        entry_corridor = "OUTSIDE"
        if p25 and p75:
            high_bound = max(p25, p75)
            low_bound = min(p25, p75)
            if low_bound <= actual_entry <= high_bound:
                entry_corridor = "INSIDE_ACCEPTED_CORRIDOR"
            elif p90 and (min(low_bound, p90) <= actual_entry <= max(high_bound, p90)):
                entry_corridor = "DEEP_RETRACEMENT_ZONE"

        now = datetime.datetime.utcnow()
        trade = TradeRecord(
            setup_snapshot_id=snapshot.id,
            user_id=user_id,
            account_id=account_id,
            lifecycle_state="ACTIVE",
            execution_status="QUEUED",
            broker_ticket=None,
            decision_at=now,
            decision_type="ACCEPTED",

            actual_entry=actual_entry,
            entry_timestamp=now,
            entry_type=entry_type.upper(),
            entry_in_corridor=entry_corridor,
            entry_deviation_pips=entry_dev,

            actual_sl=actual_sl,
            actual_tp=actual_tp,
            system_suggested_sl=rec_sl,
            system_suggested_tp=rec_tp,
            sl_deviation_pips=sl_dev,
            tp_deviation_pips=tp_dev,

            position_size_lots=position_size_lots,
            risk_pct=risk_pct,
            account_balance=account_balance,

            max_mae_pips=0.0,
            max_mfe_pips=0.0,

            notes=notes,
            created_at=now,
            updated_at=now
        )

        db.add(trade)
        db.commit()
        db.refresh(trade)

        # Dispatch to 24/7 Cloud MT5 Execution Bridge via Durable DB Queue (Transactional Outbox)
        try:
            from .models import ExecutionOrderQueue
            from .routers.execution_cloud_router import cloud_router
            from .stripe_service import StripeService
            
            target_acc_id = account_id
            
            # Check if user has Premium tier for auto-execution
            if user_id and not StripeService.check_auto_execution_access(db, user_id):
                logger.warning(f"User {user_id} attempted auto-execution without Premium tier. Order not dispatched.")
                trade.execution_status = "BLOCKED"
                trade.lifecycle_state = "CLOSED"
                trade.exit_reason = "TIER_RESTRICTION"
                trade.exit_timestamp = datetime.datetime.utcnow()
                trade.outcome = "REJECTED"
                db.commit()
                return trade
            
            if target_acc_id and cloud_router.is_execution_allowed(target_acc_id):
                signal_id = f"SNAP-{snapshot.id}-TR-{trade.id}"
                # Validate signal_id format to prevent downstream trade lookup failures
                if not re.match(r'^SNAP-\d+-TR-\d+$', signal_id):
                    raise ValueError(f"Invalid signal_id format: {signal_id}. Expected format: SNAP-{{snapshot_id}}-TR-{{trade_id}}")
                db_order = ExecutionOrderQueue(
                    signal_id=signal_id,
                    trade_id=trade.id,
                    account_id=target_acc_id,
                    action_type="OPEN",
                    ticket_id=None,
                    instrument=snapshot.instrument,
                    direction=snapshot.direction,
                    order_type=entry_type.upper(),
                    entry_reference_price=actual_entry,
                    stop_loss=actual_sl,
                    take_profit=actual_tp,
                    position_size_lots=position_size_lots,
                    risk_pct=risk_pct,
                    account_balance=account_balance,
                    status="QUEUED"
                )
                db.add(db_order)
                db.commit()
                logger.info(f"💾 [Durable Outbox] Queued order {signal_id} ({snapshot.instrument} {snapshot.direction}) for Account ID {target_acc_id}")
        except Exception as e:
            logger.error(f"Error persisting durable execution order: {e}")

        return trade

    @staticmethod
    def pass_setup(db: Session, snapshot_id: int, notes: Optional[str] = None, user_id: Optional[int] = None) -> TradeRecord:
        """
        Records that the trader explicitly passed on a Market OS setup.
        Allows post-session counterfactual analysis of passed setups.
        """
        snapshot = db.query(SetupSnapshot).filter(SetupSnapshot.id == snapshot_id).first()
        if not snapshot:
            raise ValueError(f"Snapshot ID {snapshot_id} not found")

        now = datetime.datetime.utcnow()
        trade = TradeRecord(
            setup_snapshot_id=snapshot.id,
            user_id=user_id,
            lifecycle_state="PASSED",
            decision_at=now,
            decision_type="PASSED",
            notes=notes,
            created_at=now,
            updated_at=now
        )

        db.add(trade)
        db.commit()
        db.refresh(trade)
        return trade

    @staticmethod
    def update_active_trades_with_quotes(db: Session, quotes: Dict[str, Dict[str, Any]]) -> List[TradeRecord]:
        """
        Updates live MAE/MFE and checks SL/TP breaches for all ACTIVE trades.
        Called by RealtimeService on every polling cycle.
        """
        active_trades = db.query(TradeRecord).options(joinedload(TradeRecord.setup)).filter(TradeRecord.lifecycle_state == "ACTIVE").all()
        updated_trades = []

        for trade in active_trades:
            if trade.execution_status == "QUEUED":
                continue  # Allow worker to fill trade before evaluating quote excursions

            setup = trade.setup
            if not setup:
                continue

            symbol = setup.instrument
            quote = quotes.get(symbol)
            if not quote or not quote.get("price"):
                continue

            current_price = float(quote["price"])
            high_price = float(quote.get("high", current_price))
            low_price = float(quote.get("low", current_price))
            pip_mult = get_pip_multiplier(symbol)
            entry = trade.actual_entry or setup.setup_ref_price

            # Calculate live excursion from entry
            if setup.direction == "LONG":
                adverse_dist = max(0.0, entry - low_price)
                favorable_dist = max(0.0, high_price - entry)
            else:
                adverse_dist = max(0.0, high_price - entry)
                favorable_dist = max(0.0, entry - low_price)

            mae_pips = round(adverse_dist * pip_mult, 1)
            mfe_pips = round(favorable_dist * pip_mult, 1)

            trade.max_mae_pips = max(trade.max_mae_pips or 0.0, mae_pips)
            trade.max_mfe_pips = max(trade.max_mfe_pips or 0.0, mfe_pips)

            # Update percentile threshold flags
            if setup.mae_p25_pips and trade.max_mae_pips >= setup.mae_p25_pips:
                trade.mae_p25_reached = 1
            if setup.mae_p50_pips and trade.max_mae_pips >= setup.mae_p50_pips:
                trade.mae_p50_reached = 1
            if setup.mae_p75_pips and trade.max_mae_pips >= setup.mae_p75_pips:
                trade.mae_p75_reached = 1
            if setup.mae_p90_pips and trade.max_mae_pips >= setup.mae_p90_pips:
                trade.mae_p90_reached = 1

            if setup.mfe_p25_pips and trade.max_mfe_pips >= setup.mfe_p25_pips:
                trade.mfe_p25_reached = 1
            if setup.mfe_p50_pips and trade.max_mfe_pips >= setup.mfe_p50_pips:
                trade.mfe_p50_reached = 1
            if setup.mfe_p75_pips and trade.max_mfe_pips >= setup.mfe_p75_pips:
                trade.mfe_p75_reached = 1
            if setup.mfe_p90_pips and trade.max_mfe_pips >= setup.mfe_p90_pips:
                trade.mfe_p90_reached = 1

            # Calculate risk parameters for dynamic early invalidation
            min_floor = 15.0 if ("XAU" in symbol or "US100" in symbol) else 6.0
            risk_dist = abs(entry - trade.actual_sl) if trade.actual_sl else (setup.mae_p90_pips / pip_mult if setup and setup.mae_p90_pips else 0.0035)
            risk_pips = max(1.0, risk_dist * pip_mult)
            early_inval_r = 0.35
            early_inval_pips = max(min_floor, early_inval_r * risk_pips)

            # Auto-close check on Early Invalidation / SL / TP breach
            should_close = False
            exit_reason = None
            exit_price = current_price

            # Grace period check: allow at least 45 seconds for position to absorb initial spread noise
            elapsed_sec = (datetime.datetime.utcnow() - (trade.entry_timestamp or datetime.datetime.utcnow())).total_seconds()
            grace_passed = elapsed_sec >= 45.0

            # Directive: MAE_FIRST Early Invalidation Check (-0.35R MAE before +0.35R MFE)
            # If MFE achieves +0.35R first, the early invalidation rule is disarmed
            early_inval_disarmed = (trade.max_mfe_pips or 0.0) >= early_inval_pips
            if grace_passed and not early_inval_disarmed and (trade.max_mae_pips or 0.0) >= early_inval_pips:
                should_close = True
                exit_reason = "EARLY_INVALIDATION_MAE"
                exit_price = (entry - early_inval_r * risk_dist) if setup.direction == "LONG" else (entry + early_inval_r * risk_dist)

            if not should_close and trade.actual_sl:
                if setup.direction == "LONG" and low_price <= trade.actual_sl:
                    should_close = True
                    exit_reason = "STOP_LOSS"
                    exit_price = trade.actual_sl
                elif setup.direction == "SHORT" and high_price >= trade.actual_sl:
                    should_close = True
                    exit_reason = "STOP_LOSS"
                    exit_price = trade.actual_sl

            # Take Profit: only trigger if actual_tp is positioned in the PROFITABLE direction relative to entry
            if not should_close and trade.actual_tp:
                if setup.direction == "LONG" and trade.actual_tp > entry and high_price >= trade.actual_tp:
                    should_close = True
                    exit_reason = "TAKE_PROFIT"
                    exit_price = trade.actual_tp
                elif setup.direction == "SHORT" and trade.actual_tp < entry and low_price <= trade.actual_tp:
                    should_close = True
                    exit_reason = "TAKE_PROFIT"
                    exit_price = trade.actual_tp

            if should_close:
                JournalService._finalize_trade(trade, exit_price, exit_reason)
                # Bidirectional dispatch: if position has an active MT5 ticket, queue close command to worker!
                if trade.broker_ticket and trade.account_id and setup:
                    try:
                        from .routers.execution_cloud_router import cloud_router
                        cloud_router.queue_close_order_for_account(
                            account_id=trade.account_id,
                            ticket_id=trade.broker_ticket,
                            instrument=setup.instrument,
                            reason=exit_reason
                        )
                        logger.info(f"Auto-dispatched MT5 CLOSE order for Ticket #{trade.broker_ticket} ({setup.instrument}) on Account ID {trade.account_id}")
                    except Exception as ce:
                        logger.error(f"Error dispatching auto-close to MT5: {ce}")

            trade.updated_at = datetime.datetime.utcnow()
            updated_trades.append(trade)

        db.commit()
        return updated_trades

    @staticmethod
    def close_trade(db: Session, trade_id: int, exit_price: float, exit_reason: str = "MANUAL") -> TradeRecord:
        """
        Manually closes an active trade. Computes PnL, outcomes, and distribution percentiles.
        Dispatches immediate CLOSE command to MT5 execution bridge if broker ticket exists.
        """
        trade = db.query(TradeRecord).options(joinedload(TradeRecord.setup)).filter(TradeRecord.id == trade_id).first()
        if not trade:
            raise ValueError(f"Trade ID {trade_id} not found")

        JournalService._finalize_trade(trade, exit_price, exit_reason)
        db.commit()
        db.refresh(trade)

        # Bidirectional dispatch: If this trade has an MT5 broker ticket, dispatch CLOSE to MT5 worker!
        if trade.broker_ticket and trade.account_id and trade.setup:
            try:
                from .routers.execution_cloud_router import cloud_router
                cloud_router.queue_close_order_for_account(
                    account_id=trade.account_id,
                    ticket_id=trade.broker_ticket,
                    instrument=trade.setup.instrument,
                    reason=exit_reason
                )
                logger.info(f"Dispatched MT5 CLOSE order for Ticket #{trade.broker_ticket} ({trade.setup.instrument}) on Account ID {trade.account_id}")
            except Exception as e:
                logger.error(f"Error dispatching MT5 close order: {e}")

        return trade

    @staticmethod
    def _finalize_trade(trade: TradeRecord, exit_price: float, exit_reason: str):
        """Helper to calculate PnL and classify outcomes on trade close."""
        setup = trade.setup
        pip_mult = get_pip_multiplier(setup.instrument if setup else "GBPUSD")
        entry = trade.actual_entry or (setup.setup_ref_price if setup else exit_price)
        direction = setup.direction if setup else "LONG"

        if direction == "LONG":
            pnl_pips = round((exit_price - entry) * pip_mult, 1)
        else:
            pnl_pips = round((entry - exit_price) * pip_mult, 1)

        risk_dist = abs(entry - trade.actual_sl) if trade.actual_sl else (setup.mae_p90_pips / pip_mult if setup and setup.mae_p90_pips else 0.0020)
        risk_pips = max(1.0, risk_dist * pip_mult)
        pnl_r = round(pnl_pips / risk_pips, 2)

        outcome = "WIN" if pnl_pips > 1.0 else ("LOSS" if pnl_pips < -1.0 else "BREAKEVEN")

        # Setup outcome vs Trader Execution outcome
        mfe_target = setup.mfe_p50_pips or 15.0 if setup else 15.0
        setup_outcome = "SUCCESSFUL" if (trade.max_mfe_pips or 0.0) >= mfe_target else "FAILED"

        if outcome == "WIN" and (trade.entry_deviation_pips or 0) <= 5.0:
            exec_outcome = "EXCELLENT_EXECUTION"
        elif outcome == "WIN":
            exec_outcome = "WIN_WITH_DEVIATION"
        elif setup_outcome == "SUCCESSFUL" and outcome == "LOSS":
            exec_outcome = "POOR_EXECUTION_SETUP_WORKED"
        else:
            exec_outcome = "SYSTEM_LOSS"

        trade.lifecycle_state = "CLOSED"
        trade.execution_status = "CLOSED"
        trade.exit_price = exit_price
        trade.exit_timestamp = datetime.datetime.utcnow()
        trade.exit_reason = exit_reason
        trade.outcome = outcome
        trade.pnl_pips = pnl_pips
        trade.pnl_r = pnl_r
        trade.setup_outcome = setup_outcome
        trade.execution_outcome = exec_outcome

        if setup and setup.mfe_p90_pips and setup.mfe_p90_pips > 0:
            trade.max_mfe_percentile = round(min(1.0, (trade.max_mfe_pips or 0.0) / setup.mfe_p90_pips) * 90.0, 1)
        if setup and setup.mae_p90_pips and setup.mae_p90_pips > 0:
            trade.max_mae_percentile = round(min(1.0, (trade.max_mae_pips or 0.0) / setup.mae_p90_pips) * 90.0, 1)

    @staticmethod
    def get_performance_summary(db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generates aggregated performance stats comparing Market OS expectations vs actual trader execution specifically for a user.
        """
        q_closed = db.query(TradeRecord).filter(TradeRecord.lifecycle_state == "CLOSED")
        q_passed = db.query(TradeRecord).filter(TradeRecord.lifecycle_state == "PASSED")

        if user_id is not None:
            q_closed = q_closed.filter(TradeRecord.user_id == user_id)
            q_passed = q_passed.filter(TradeRecord.user_id == user_id)

        closed_trades = q_closed.all()
        passed_trades = q_passed.all()

        # Only evaluate genuine executed/filled trades that reached a completed outcome
        # Exclude unfilled/rejected/expired orders that never executed on a broker
        executed_trades = [
            t for t in closed_trades
            if t.outcome in ["WIN", "LOSS", "BREAKEVEN"] and t.actual_entry is not None
        ]

        total_executed = len(executed_trades)
        wins = [t for t in executed_trades if t.outcome == "WIN"]
        losses = [t for t in executed_trades if t.outcome == "LOSS"]

        win_rate = round(len(wins) / total_executed * 100, 1) if total_executed > 0 else 0.0
        avg_r = round(float(np.mean([t.pnl_r for t in executed_trades if t.pnl_r is not None])), 2) if total_executed > 0 else 0.0
        avg_mae = round(float(np.mean([t.max_mae_pips for t in executed_trades if t.max_mae_pips is not None])), 1) if total_executed > 0 else 0.0
        avg_mfe = round(float(np.mean([t.max_mfe_pips for t in executed_trades if t.max_mfe_pips is not None])), 1) if total_executed > 0 else 0.0

        # Setup vs Execution
        setup_worked_count = sum(1 for t in executed_trades if t.setup_outcome == "SUCCESSFUL")
        setup_success_rate = round(setup_worked_count / total_executed * 100, 1) if total_executed > 0 else 0.0

        # Execution deviation impact
        poor_exec_losses = sum(1 for t in executed_trades if t.execution_outcome == "POOR_EXECUTION_SETUP_WORKED")

        return {
            "total_trades_logged": total_executed,
            "total_passed_setups": len(passed_trades),
            "trader_win_rate": win_rate,
            "setup_success_rate": setup_success_rate,
            "average_r_multiple": avg_r,
            "average_mae_endured_pips": avg_mae,
            "average_mfe_captured_pips": avg_mfe,
            "avoidable_losses_from_poor_execution": poor_exec_losses,
            "win_count": len(wins),
            "loss_count": len(losses),
        }
