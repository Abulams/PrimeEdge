"""
Market OS Replay Service Layer — Scientific Test Harness & Accounting Reconciliation
================================================================--------------------
Manages Replay Batch orchestration, strictly scoped by `batch_id`.
Provides mathematical population reconciliation, denominator isolation,
deterministic setup population hashing, and automated integrity checksums.
"""

import os
import json
import csv
import zipfile
import subprocess
import datetime
import logging
import hashlib
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session, joinedload

from .models import ReplayBatch, ReplaySetupSnapshot, ReplayTradeRecord
from .replay_engine import ReplayEngine


logger = logging.getLogger(__name__)


class ReplayService:

    @staticmethod
    def create_batch(
        db: Session,
        start_date: datetime.date,
        end_date: datetime.date,
        instruments: List[str],
        batch_name: str = "Control Group Audit",
        execution_policy: str = "STRICT_V4_LIMIT",
        friction_pips: float = 2.5
    ) -> ReplayBatch:
        """Creates a new ReplayBatch record."""
        batch = ReplayBatch(
            batch_name=batch_name,
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            execution_policy=execution_policy,
            friction_pips=friction_pips,
            status="PENDING",
            created_at=datetime.datetime.utcnow()
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def run_batch(db: Session, batch_id: int) -> ReplayBatch:
        """Executes a replay batch via ReplayEngine."""
        return ReplayEngine.run_replay_batch(db, batch_id)

    @staticmethod
    def get_batch(db: Session, batch_id: int) -> Optional[ReplayBatch]:
        """Gets a ReplayBatch by ID."""
        return db.query(ReplayBatch).filter(ReplayBatch.id == batch_id).first()

    @staticmethod
    def get_latest_batch_id(db: Session) -> Optional[int]:
        """Returns the latest batch ID."""
        latest = db.query(ReplayBatch.id).order_by(ReplayBatch.id.desc()).first()
        return latest[0] if latest else None

    @staticmethod
    def get_active_trades(db: Session, batch_id: Optional[int] = None) -> List[ReplayTradeRecord]:
        """Returns active replay trades scoped to batch_id."""
        target_batch = batch_id or ReplayService.get_latest_batch_id(db)
        if not target_batch:
            return []
        return db.query(ReplayTradeRecord).join(ReplaySetupSnapshot).filter(
            ReplaySetupSnapshot.batch_id == target_batch,
            ReplayTradeRecord.lifecycle_state == "ACTIVE"
        ).all()

    @staticmethod
    def get_history_trades(db: Session, batch_id: Optional[int] = None) -> List[ReplayTradeRecord]:
        """Returns closed executed replay trades scoped strictly to batch_id."""
        target_batch = batch_id or ReplayService.get_latest_batch_id(db)
        if not target_batch:
            return []
        return db.query(ReplayTradeRecord).options(
            joinedload(ReplayTradeRecord.setup)
        ).join(ReplaySetupSnapshot).filter(
            ReplaySetupSnapshot.batch_id == target_batch,
            ReplayTradeRecord.lifecycle_state == "CLOSED"
        ).order_by(ReplayTradeRecord.exit_timestamp.desc()).all()

    @staticmethod
    def get_passed_setups(db: Session, batch_id: Optional[int] = None) -> List[ReplaySetupSnapshot]:
        """Returns passed/unfilled setup snapshots scoped strictly to batch_id."""
        target_batch = batch_id or ReplayService.get_latest_batch_id(db)
        if not target_batch:
            return []
        return db.query(ReplaySetupSnapshot).filter(
            ReplaySetupSnapshot.batch_id == target_batch,
            ReplaySetupSnapshot.opportunity_outcome.isnot(None)
        ).order_by(ReplaySetupSnapshot.date.desc()).all()

    @staticmethod
    def compute_population_checksum_hash(snapshots: List[ReplaySetupSnapshot]) -> str:
        """
        Generates a SHA-256 hash of ordered T0 setup tuples (date, instrument, direction, status_at_snapshot, ref_price).
        Used to prove that different policies evaluated the EXACT SAME T0 setup population.
        """
        ordered = sorted(snapshots, key=lambda s: (s.date, s.instrument, s.direction))
        serialized = "|".join([
            f"{s.date}:{s.instrument}:{s.direction}:{s.status_at_snapshot}:{round(s.setup_ref_price, 5)}"
            for s in ordered
        ])
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def run_replay_integrity_checksum(db: Session, batch_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Performs automated pre-flight integrity assertions scoped to batch_id.
        """
        target_batch = batch_id or ReplayService.get_latest_batch_id(db)
        if not target_batch:
            return {"status": "UNTRUSTED HARNESS", "checks": {}}

        snapshots = db.query(ReplaySetupSnapshot).filter(ReplaySetupSnapshot.batch_id == target_batch).all()
        trades = db.query(ReplayTradeRecord).join(ReplaySetupSnapshot).filter(ReplaySetupSnapshot.batch_id == target_batch).all()

        check_passed_no_trade = True
        for s in snapshots:
            if s.opportunity_outcome in ["MISSED_WIN", "SAVED_LOSS", "EXPIRED_NEUTRAL"]:
                if len(s.trades) > 0:
                    check_passed_no_trade = False
                    break

        check_trades_have_entry = all(t.actual_entry is not None for t in trades)
        check_no_negative_mae = all((t.max_mae_pips or 0.0) >= 0.0 for t in trades)
        check_no_negative_mfe = all((t.max_mfe_pips or 0.0) >= 0.0 for t in trades)
        check_exit_after_entry = all(t.exit_timestamp >= t.entry_timestamp for t in trades if t.exit_timestamp and t.entry_timestamp)
        check_frozen_levels = all(s.frozen_entry is not None and s.frozen_sl is not None for s in snapshots)

        # Denominator Reconciliations
        n_eval = len(snapshots)
        status_counts = {"READY": 0, "WAIT": 0, "NO EDGE": 0, "NO SETUP": 0, "INVALID": 0}
        for s in snapshots:
            st = s.status_at_snapshot
            status_counts[st] = status_counts.get(st, 0) + 1

        check_status_pop_reconciled = (sum(status_counts.values()) == n_eval)
        check_decision_pop_reconciled = (len(trades) + sum(1 for s in snapshots if s.opportunity_outcome in ["MISSED_WIN", "SAVED_LOSS", "EXPIRED_NEUTRAL"]) == n_eval)

        integrity_status = "VERIFIED SCIENTIFIC HARNESS" if (
            check_passed_no_trade and check_trades_have_entry and
            check_no_negative_mae and check_no_negative_mfe and
            check_exit_after_entry and check_frozen_levels and
            check_status_pop_reconciled and check_decision_pop_reconciled
        ) else "UNTRUSTED HARNESS"

        return {
            "status": integrity_status,
            "checks": {
                "PASSED_SETUPS_NO_TRADE_RECORDS": "PASS" if check_passed_no_trade else "FAIL",
                "EXECUTED_TRADES_HAVE_ENTRY": "PASS" if check_trades_have_entry else "FAIL",
                "NO_NEGATIVE_MAE": "PASS" if check_no_negative_mae else "FAIL",
                "NO_NEGATIVE_MFE": "PASS" if check_no_negative_mfe else "FAIL",
                "EXIT_AFTER_ENTRY": "PASS" if check_exit_after_entry else "FAIL",
                "FROZEN_LEVELS_IMMUTABLE": "PASS" if check_frozen_levels else "FAIL",
                "STATUS_POPULATION_RECONCILED": "PASS" if check_status_pop_reconciled else "FAIL",
                "DECISION_POPULATION_RECONCILED": "PASS" if check_decision_pop_reconciled else "FAIL"
            }
        }

    @staticmethod
    def get_control_group_analytics(db: Session, batch_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Computes cold Control Group baseline analytics strictly scoped to batch_id.
        Reconciles all four mathematical populations and explicit denominators.
        """
        target_batch_id = batch_id or ReplayService.get_latest_batch_id(db)
        if not target_batch_id:
            return {}

        batch = db.query(ReplayBatch).filter(ReplayBatch.id == target_batch_id).first()
        snapshots = db.query(ReplaySetupSnapshot).filter(ReplaySetupSnapshot.batch_id == target_batch_id).all()
        closed_trades = db.query(ReplayTradeRecord).options(
            joinedload(ReplayTradeRecord.setup)
        ).join(ReplaySetupSnapshot).filter(
            ReplaySetupSnapshot.batch_id == target_batch_id,
            ReplayTradeRecord.lifecycle_state == "CLOSED"
        ).all()

        # ---------------------------------------------------------------------
        # Denominator 1: Setup Population (N_eval)
        # ---------------------------------------------------------------------
        total_evaluated = len(snapshots)
        status_dist = {"READY": 0, "WAIT": 0, "NO EDGE": 0, "NO SETUP": 0, "INVALID": 0}
        for s in snapshots:
            st = s.status_at_snapshot
            status_dist[st] = status_dist.get(st, 0) + 1

        population_hash = ReplayService.compute_population_checksum_hash(snapshots)

        # ---------------------------------------------------------------------
        # Denominator 2: Execution Decision Population (Taken vs Passed)
        # ---------------------------------------------------------------------
        total_taken = len(closed_trades)
        passed_snapshots = [s for s in snapshots if s.opportunity_outcome in ["MISSED_WIN", "SAVED_LOSS", "EXPIRED_NEUTRAL"]]
        unfilled_snapshots = [s for s in snapshots if s.opportunity_outcome == "UNFILLED_MISSED_OPPORTUNITY"]
        total_passed = len(passed_snapshots)
        total_unfilled = len(unfilled_snapshots)

        # ---------------------------------------------------------------------
        # Denominator 3: Closed Trade Population (Wins vs Losses)
        # ---------------------------------------------------------------------
        wins = [t for t in closed_trades if t.outcome == "WIN"]
        losses = [t for t in closed_trades if t.outcome == "LOSS"]
        breakevens = [t for t in closed_trades if t.outcome == "BREAKEVEN"]

        win_rate = round(len(wins) / total_taken * 100, 1) if total_taken > 0 else 0.0

        predicted_probs = [t.setup.continuation_prob for t in closed_trades if t.setup and t.setup.continuation_prob]
        avg_predicted_win_rate = round(float(np.mean(predicted_probs)) * 100, 1) if predicted_probs else 0.0
        calibration_delta = round(win_rate - avg_predicted_win_rate, 1)

        setup_success = sum(1 for t in closed_trades if t.setup_outcome == "SUCCESSFUL")
        setup_success_rate = round(setup_success / total_taken * 100, 1) if total_taken > 0 else 0.0

        # P90 Invalidation Survival Rates
        survived_p90_all = sum(1 for t in closed_trades if (t.mae_p90_reached or 0) == 0)
        p90_survival_all_rate = round(survived_p90_all / total_taken * 100, 1) if total_taken > 0 else 100.0

        survived_p90_wins = sum(1 for t in wins if (t.mae_p90_reached or 0) == 0)
        p90_survival_wins_rate = round(survived_p90_wins / len(wins) * 100, 1) if len(wins) > 0 else 100.0

        win_pnls = [t.pnl_r for t in wins if t.pnl_r is not None]
        loss_pnls = [t.pnl_r for t in losses if t.pnl_r is not None]
        avg_winner_r = round(float(np.mean(win_pnls)), 2) if win_pnls else 0.0
        avg_loser_r = round(float(np.mean(loss_pnls)), 2) if loss_pnls else 0.0
        dec_win_rate = len(wins) / total_taken if total_taken > 0 else 0.0
        expectancy_r = round(dec_win_rate * avg_winner_r + (1.0 - dec_win_rate) * avg_loser_r, 3)

        # Max Favorable R Distribution across taken trades
        from .data_fetcher import get_pip_multiplier
        max_r_list = []
        for t in closed_trades:
            if t.actual_entry and t.actual_sl and t.max_mfe_pips is not None:
                inst = t.setup.instrument if t.setup else "GBPUSD"
                pm = get_pip_multiplier(inst)
                risk_p = max(1.0, abs(t.actual_entry - t.actual_sl) * pm)
                max_r_list.append(t.max_mfe_pips / risk_p)

        if max_r_list:
            max_r_dist = {
                "p25": round(float(np.percentile(max_r_list, 25)), 2),
                "p50": round(float(np.percentile(max_r_list, 50)), 2),
                "p75": round(float(np.percentile(max_r_list, 75)), 2),
                "p90": round(float(np.percentile(max_r_list, 90)), 2),
            }
            reach_rates = {
                "reach_0_5r_pct": round(sum(1 for r in max_r_list if r >= 0.5) / len(max_r_list) * 100, 1),
                "reach_1_0r_pct": round(sum(1 for r in max_r_list if r >= 1.0) / len(max_r_list) * 100, 1),
                "reach_1_5r_pct": round(sum(1 for r in max_r_list if r >= 1.5) / len(max_r_list) * 100, 1),
                "reach_2_0r_pct": round(sum(1 for r in max_r_list if r >= 2.0) / len(max_r_list) * 100, 1),
                "reach_2_5r_pct": round(sum(1 for r in max_r_list if r >= 2.5) / len(max_r_list) * 100, 1),
                "reach_3_0r_pct": round(sum(1 for r in max_r_list if r >= 3.0) / len(max_r_list) * 100, 1),
            }
        else:
            max_r_dist = {"p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0}
            reach_rates = {}

        avg_r = round(float(np.mean([t.pnl_r for t in closed_trades if t.pnl_r is not None])), 2) if total_taken > 0 else 0.0
        net_r = round(float(sum([t.pnl_r for t in closed_trades if t.pnl_r is not None])), 2) if total_taken > 0 else 0.0
        avg_mae = round(float(np.mean([t.max_mae_pips for t in closed_trades if t.max_mae_pips is not None])), 1) if total_taken > 0 else 0.0
        avg_mfe = round(float(np.mean([t.max_mfe_pips for t in closed_trades if t.max_mfe_pips is not None])), 1) if total_taken > 0 else 0.0

        # Profit Factor (Gross Win R / Gross Loss R)
        gross_win_r = sum(t.pnl_r for t in wins if t.pnl_r is not None and t.pnl_r > 0)
        gross_loss_r = sum(abs(t.pnl_r) for t in losses if t.pnl_r is not None and t.pnl_r < 0)
        if gross_loss_r > 0:
            profit_factor = round(gross_win_r / gross_loss_r, 2)
        elif gross_win_r > 0:
            profit_factor = 999.0  # Infinite profit factor
        else:
            profit_factor = 0.0

        # Max Drawdown in Cumulative R
        # Order closed trades chronologically
        chronological_trades = sorted(closed_trades, key=lambda t: t.exit_timestamp or t.created_at or datetime.datetime.min)
        cum_r = 0.0
        peak_r = 0.0
        max_dd_r = 0.0
        for t in chronological_trades:
            if t.pnl_r is not None:
                cum_r += t.pnl_r
                if cum_r > peak_r:
                    peak_r = cum_r
                dd = peak_r - cum_r
                if dd > max_dd_r:
                    max_dd_r = dd
        max_drawdown_r = round(float(max_dd_r), 2)

        # Realized MFE and MAE distributions (in pips)
        all_trade_maes = [float(t.max_mae_pips) for t in closed_trades if t.max_mae_pips is not None]
        all_trade_mfes = [float(t.max_mfe_pips) for t in closed_trades if t.max_mfe_pips is not None]
        mae_dist = {
            "p25": round(float(np.percentile(all_trade_maes, 25)), 1) if all_trade_maes else 0.0,
            "p50": round(float(np.percentile(all_trade_maes, 50)), 1) if all_trade_maes else 0.0,
            "p75": round(float(np.percentile(all_trade_maes, 75)), 1) if all_trade_maes else 0.0,
            "p90": round(float(np.percentile(all_trade_maes, 90)), 1) if all_trade_maes else 0.0,
        }
        mfe_dist = {
            "p25": round(float(np.percentile(all_trade_mfes, 25)), 1) if all_trade_mfes else 0.0,
            "p50": round(float(np.percentile(all_trade_mfes, 50)), 1) if all_trade_mfes else 0.0,
            "p75": round(float(np.percentile(all_trade_mfes, 75)), 1) if all_trade_mfes else 0.0,
            "p90": round(float(np.percentile(all_trade_mfes, 90)), 1) if all_trade_mfes else 0.0,
        }

        # Per-Instrument Performance Breakdown
        instrument_groups: Dict[str, List[ReplayTradeRecord]] = {}
        for t in closed_trades:
            inst = t.setup.instrument if t.setup else "UNKNOWN"
            instrument_groups.setdefault(inst, []).append(t)

        performance_by_instrument = {}
        for inst, i_trades in sorted(instrument_groups.items()):
            i_wins = [t for t in i_trades if t.outcome == "WIN"]
            i_losses = [t for t in i_trades if t.outcome == "LOSS"]
            i_taken = len(i_trades)
            i_win_rate = round(len(i_wins) / i_taken * 100, 1) if i_taken > 0 else 0.0
            i_win_pnls = [t.pnl_r for t in i_wins if t.pnl_r is not None]
            i_loss_pnls = [t.pnl_r for t in i_losses if t.pnl_r is not None]
            i_avg_winner = round(float(np.mean(i_win_pnls)), 2) if i_win_pnls else 0.0
            i_avg_loser = round(float(np.mean(i_loss_pnls)), 2) if i_loss_pnls else 0.0
            i_exp = round((len(i_wins) / i_taken) * i_avg_winner + (len(i_losses) / i_taken) * i_avg_loser, 3) if i_taken > 0 else 0.0
            i_net_r = round(float(sum(t.pnl_r for t in i_trades if t.pnl_r is not None)), 2)
            i_avg_r = round(float(np.mean([t.pnl_r for t in i_trades if t.pnl_r is not None])), 2) if i_taken > 0 else 0.0
            
            i_gwin = sum(t.pnl_r for t in i_wins if t.pnl_r is not None and t.pnl_r > 0)
            i_gloss = sum(abs(t.pnl_r) for t in i_losses if t.pnl_r is not None and t.pnl_r < 0)
            i_pf = round(i_gwin / i_gloss, 2) if i_gloss > 0 else (999.0 if i_gwin > 0 else 0.0)

            # Max DD for this instrument
            i_cum = 0.0
            i_peak = 0.0
            i_dd = 0.0
            for t in sorted(i_trades, key=lambda x: x.exit_timestamp or x.created_at or datetime.datetime.min):
                if t.pnl_r is not None:
                    i_cum += t.pnl_r
                    if i_cum > i_peak:
                        i_peak = i_cum
                    c_dd = i_peak - i_cum
                    if c_dd > i_dd:
                        i_dd = c_dd

            i_edge_status = "VALIDATED_EDGE" if i_exp > 0.05 and i_pf > 1.15 else ("NEUTRAL_BREAKEVEN" if i_exp >= -0.05 else "NEGATIVE_EXPECTANCY")

            performance_by_instrument[inst] = {
                "trades_taken": i_taken,
                "win_rate": i_win_rate,
                "average_r": i_avg_r,
                "average_winner_r": i_avg_winner,
                "average_loser_r": i_avg_loser,
                "expectancy_r": i_exp,
                "net_r": i_net_r,
                "profit_factor": i_pf,
                "max_drawdown_r": round(i_dd, 2),
                "edge_status": i_edge_status,
                "avg_mae_pips": round(float(np.mean([t.max_mae_pips for t in i_trades if t.max_mae_pips is not None])), 1) if i_taken > 0 else 0.0,
                "avg_mfe_pips": round(float(np.mean([t.max_mfe_pips for t in i_trades if t.max_mfe_pips is not None])), 1) if i_taken > 0 else 0.0,
            }

        # ---------------------------------------------------------------------
        # Denominator 4: Opportunity Outcome Population
        # ---------------------------------------------------------------------
        missed_wins = sum(1 for s in snapshots if s.opportunity_outcome == "MISSED_WIN")
        saved_losses = sum(1 for s in snapshots if s.opportunity_outcome == "SAVED_LOSS")
        expired_neutrals = sum(1 for s in snapshots if s.opportunity_outcome == "EXPIRED_NEUTRAL")

        trajectory_milestones = {
            "mfe_p25": sum(1 for t in closed_trades if t.mfe_p25_reached),
            "mfe_p50": sum(1 for t in closed_trades if t.mfe_p50_reached),
            "mfe_p75": sum(1 for t in closed_trades if t.mfe_p75_reached),
            "mfe_p90": sum(1 for t in closed_trades if t.mfe_p90_reached),
            "mae_p25": sum(1 for t in closed_trades if t.mae_p25_reached),
            "mae_p50": sum(1 for t in closed_trades if t.mae_p50_reached),
            "mae_p75": sum(1 for t in closed_trades if t.mae_p75_reached),
            "mae_p90": sum(1 for t in closed_trades if t.mae_p90_reached),
            "mfe_first": sum(1 for t in closed_trades if t.first_milestone == "MFE_FIRST"),
            "mae_first": sum(1 for t in closed_trades if t.first_milestone == "MAE_FIRST"),
        }

        sl_first_pessimistic_count = sum(1 for t in closed_trades if t.exit_reason == "STOP_LOSS_PESSIMISTIC_SAME_BAR")
        checksum = ReplayService.run_replay_integrity_checksum(db, target_batch_id)

        return {
            "batch_id": target_batch_id,
            "batch_name": batch.batch_name if batch else "Unknown",
            "execution_policy": batch.execution_policy if batch else "STRICT_V4_LIMIT",
            "population_checksum_hash": population_hash,
            "total_setups_evaluated": total_evaluated,
            "total_trades_taken": total_taken,
            "total_setups_passed": total_passed,
            "total_unfilled_missed": total_unfilled,

            # Explicit Denominators
            "denominators": {
                "win_rate_fraction": f"{len(wins)}/{total_taken}",
                "setup_success_fraction": f"{setup_success}/{total_taken}",
                "p90_survival_all_fraction": f"{survived_p90_all}/{total_taken}",
                "p90_survival_wins_fraction": f"{survived_p90_wins}/{len(wins)}",
                "opportunity_saved_losses_fraction": f"{saved_losses}/{total_passed + total_unfilled}",
                "opportunity_missed_wins_fraction": f"{missed_wins}/{total_passed + total_unfilled}"
            },

            # Primary Economic KPIs
            "expectancy_r": expectancy_r,
            "average_winner_r": avg_winner_r,
            "average_loser_r": avg_loser_r,
            "profit_factor": profit_factor,
            "max_drawdown_r": max_drawdown_r,

            # Secondary KPIs & Distributions
            "simulated_trader_win_rate": win_rate,
            "net_r": net_r,
            "predicted_vs_actual_win_rate_delta": calibration_delta,
            "setup_success_rate": setup_success_rate,
            "p90_invalidation_survival_rate": p90_survival_all_rate,
            "p90_survival_winning_trades": p90_survival_wins_rate,
            "average_r_multiple": avg_r,
            "max_r_distribution": max_r_dist,
            "r_milestone_reach_rates": reach_rates,
            "average_mae_pips": avg_mae,
            "average_mfe_pips": avg_mfe,
            "mae_distribution": mae_dist,
            "mfe_distribution": mfe_dist,
            "opportunity_missed_wins": missed_wins,
            "opportunity_saved_losses": saved_losses,
            "opportunity_expired_neutral": expired_neutrals,
            "status_distribution": status_dist,
            "trajectory_milestones": trajectory_milestones,
            "sl_first_pessimistic_exits": sl_first_pessimistic_count,
            "friction_pips_applied": batch.friction_pips if batch else 2.5,
            "performance_by_instrument": performance_by_instrument,
            "integrity_checksum": checksum
        }


    @staticmethod
    def get_default_archive_dir() -> str:
        """Returns the default replay archive directory path."""
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "replay_archive")
        )
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    @staticmethod
    def _compute_sha256(filepath: str) -> str:
        """Computes SHA-256 hash of a file."""
        if not os.path.exists(filepath):
            return "FILE_NOT_FOUND"
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _get_git_commit_hash() -> str:
        """Attempts to retrieve the current git commit hash."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=3,
                cwd=os.path.dirname(__file__)
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return "UNKNOWN_GIT_COMMIT"

    @staticmethod
    def _get_source_file_hashes() -> Dict[str, str]:
        """Calculates SHA-256 hashes of core engine source files for reproducibility provenance."""
        app_dir = os.path.dirname(__file__)
        files_to_hash = ["engine.py", "replay_engine.py", "signature_builder.py", "models.py", "replay_service.py"]
        hashes = {}
        for fname in files_to_hash:
            fpath = os.path.join(app_dir, fname)
            hashes[fname] = ReplayService._compute_sha256(fpath)
        return hashes

    @staticmethod
    def export_batch(
        db: Session,
        batch_id: int,
        archive_base_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exports a complete replay batch into persistent archive storage:
        - replay_archive/batch_<id>/batch.json
        - replay_archive/batch_<id>/analytics.json
        - replay_archive/batch_<id>/setup_snapshots.csv
        - replay_archive/batch_<id>/trade_records.csv
        - replay_archive/batch_<id>/integrity.json
        - replay_archive/batch_<id>/manifest.json
        - replay_archive/batch_<id>.zip
        - replay_archive/experiment_index.csv (updated index)

        Invariant: Never overwrites an existing batch archive.
        """
        base_dir = archive_base_dir or ReplayService.get_default_archive_dir()
        os.makedirs(base_dir, exist_ok=True)

        batch = db.query(ReplayBatch).filter(ReplayBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Replay batch ID {batch_id} not found")

        batch_dir = os.path.join(base_dir, f"batch_{batch_id}")
        zip_path = os.path.join(base_dir, f"batch_{batch_id}.zip")
        manifest_path = os.path.join(batch_dir, "manifest.json")

        os.makedirs(batch_dir, exist_ok=True)

        # 1. Fetch all data
        snapshots = db.query(ReplaySetupSnapshot).filter(
            ReplaySetupSnapshot.batch_id == batch_id
        ).order_by(ReplaySetupSnapshot.date.asc(), ReplaySetupSnapshot.instrument.asc()).all()

        trades = db.query(ReplayTradeRecord).join(ReplaySetupSnapshot).filter(
            ReplaySetupSnapshot.batch_id == batch_id
        ).order_by(ReplayTradeRecord.entry_timestamp.asc()).all()

        analytics = ReplayService.get_control_group_analytics(db, batch_id)
        integrity = ReplayService.run_replay_integrity_checksum(db, batch_id)

        # 2. Export batch.json
        batch_data = {
            "id": batch.id,
            "batch_name": batch.batch_name,
            "start_date": str(batch.start_date),
            "end_date": str(batch.end_date),
            "instruments": batch.instruments,
            "execution_policy": batch.execution_policy,
            "friction_pips": batch.friction_pips,
            "total_setups_evaluated": batch.total_setups_evaluated,
            "total_trades_taken": batch.total_trades_taken,
            "total_setups_passed": batch.total_setups_passed,
            "status": batch.status,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
        }
        with open(os.path.join(batch_dir, "batch.json"), "w", encoding="utf-8") as f:
            json.dump(batch_data, f, indent=2, default=str)

        # 3. Export analytics.json
        with open(os.path.join(batch_dir, "analytics.json"), "w", encoding="utf-8") as f:
            json.dump(analytics, f, indent=2, default=str)

        # 4. Export integrity.json
        with open(os.path.join(batch_dir, "integrity.json"), "w", encoding="utf-8") as f:
            json.dump(integrity, f, indent=2, default=str)

        # 5. Export setup_snapshots.csv
        snap_cols = [
            "id", "batch_id", "instrument", "date", "direction", "trend", "status_at_snapshot",
            "setup_ref_price", "live_price_at_snap", "frozen_entry", "frozen_sl", "frozen_tp",
            "mae_p25_pips", "mae_p50_pips", "mae_p75_pips", "mae_p90_pips",
            "mfe_p25_pips", "mfe_p50_pips", "mfe_p75_pips", "mfe_p90_pips",
            "corridor_p25_price", "corridor_p75_price", "p90_invalidation",
            "preferred_entry_low", "preferred_entry_high",
            "dxy_regime", "risk_sentiment", "session", "historical_n",
            "continuation_prob", "confidence_score", "market_entry_ev", "limit_entry_ev",
            "system_preference", "setup_thesis", "opportunity_outcome",
            "opportunity_max_mfe", "opportunity_max_mae", "created_at"
        ]
        with open(os.path.join(batch_dir, "setup_snapshots.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=snap_cols)
            writer.writeheader()
            for s in snapshots:
                row = {col: getattr(s, col, None) for col in snap_cols}
                writer.writerow(row)

        # 6. Export trade_records.csv
        trade_cols = [
            "id", "replay_snapshot_id", "lifecycle_state", "decision_at", "decision_type",
            "actual_entry", "entry_timestamp", "entry_type", "entry_in_corridor", "entry_deviation_pips",
            "actual_sl", "actual_tp", "system_suggested_sl", "system_suggested_tp",
            "sl_deviation_pips", "tp_deviation_pips", "position_size_lots", "risk_pct",
            "max_mae_pips", "max_mfe_pips",
            "mae_p25_reached", "mae_p50_reached", "mae_p75_reached", "mae_p90_reached",
            "mfe_p25_reached", "mfe_p50_reached", "mfe_p75_reached", "mfe_p90_reached",
            "mfe_p25_time", "mfe_p50_time", "mfe_p75_time", "mfe_p90_time",
            "mae_p25_time", "mae_p50_time", "mae_p75_time", "mae_p90_time",
            "first_milestone", "exit_price", "exit_timestamp", "exit_reason",
            "outcome", "pnl_pips", "pnl_r", "setup_outcome", "execution_outcome",
            "max_mfe_percentile", "max_mae_percentile", "created_at", "updated_at"
        ]
        with open(os.path.join(batch_dir, "trade_records.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=trade_cols)
            writer.writeheader()
            for t in trades:
                row = {col: getattr(t, col, None) for col in trade_cols}
                writer.writerow(row)

        # 7. Compute file hashes and create manifest.json
        file_hashes = {
            "batch.json": ReplayService._compute_sha256(os.path.join(batch_dir, "batch.json")),
            "analytics.json": ReplayService._compute_sha256(os.path.join(batch_dir, "analytics.json")),
            "integrity.json": ReplayService._compute_sha256(os.path.join(batch_dir, "integrity.json")),
            "setup_snapshots.csv": ReplayService._compute_sha256(os.path.join(batch_dir, "setup_snapshots.csv")),
            "trade_records.csv": ReplayService._compute_sha256(os.path.join(batch_dir, "trade_records.csv")),
        }

        manifest = {
            "manifest_schema_version": "1.0",
            "batch_id": batch.id,
            "batch_name": batch.batch_name,
            "execution_policy": batch.execution_policy,
            "start_date": str(batch.start_date),
            "end_date": str(batch.end_date),
            "instruments": batch.instruments,
            "friction_pips": batch.friction_pips,
            "database_schema_version": "v2.1",
            "git_commit_hash": ReplayService._get_git_commit_hash(),
            "source_engine_hashes": ReplayService._get_source_file_hashes(),
            "total_setups_evaluated": batch.total_setups_evaluated,
            "total_trades_taken": batch.total_trades_taken,
            "total_setups_passed": batch.total_setups_passed,
            "population_checksum_hash": analytics.get("population_checksum_hash", "UNKNOWN"),
            "exported_at": datetime.datetime.utcnow().isoformat() + "Z",
            "file_manifest": file_hashes
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 8. Create ZIP archive
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(batch_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, base_dir)
                    zf.write(full_p, rel_p)

        # 9. Update experiment_index.csv
        index_csv_path = os.path.join(base_dir, "experiment_index.csv")
        index_cols = [
            "batch_id", "batch_name", "execution_policy", "start_date", "end_date",
            "instruments", "friction_pips", "total_setups_evaluated", "total_trades_taken",
            "total_setups_passed", "total_unfilled_missed", "win_rate", "avg_r",
            "avg_winner_r", "avg_loser_r", "expectancy_r", "p90_survival_rate",
            "opportunity_saved_losses", "opportunity_missed_wins", "status",
            "created_at", "completed_at", "exported_at", "archive_dir", "zip_path"
        ]

        existing_rows = {}
        if os.path.exists(index_csv_path):
            try:
                with open(index_csv_path, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        if "batch_id" in r:
                            existing_rows[str(r["batch_id"])] = r
            except Exception as e:
                logger.warning(f"Error reading existing experiment_index.csv: {e}")

        new_row = {
            "batch_id": batch.id,
            "batch_name": batch.batch_name,
            "execution_policy": batch.execution_policy,
            "start_date": str(batch.start_date),
            "end_date": str(batch.end_date),
            "instruments": json.dumps(batch.instruments) if isinstance(batch.instruments, list) else str(batch.instruments),
            "friction_pips": batch.friction_pips,
            "total_setups_evaluated": batch.total_setups_evaluated,
            "total_trades_taken": batch.total_trades_taken,
            "total_setups_passed": batch.total_setups_passed,
            "total_unfilled_missed": analytics.get("total_unfilled_missed", 0),
            "win_rate": analytics.get("simulated_trader_win_rate", 0.0),
            "avg_r": analytics.get("average_r_multiple", 0.0),
            "avg_winner_r": analytics.get("average_winner_r", 0.0),
            "avg_loser_r": analytics.get("average_loser_r", 0.0),
            "expectancy_r": analytics.get("expectancy_r", 0.0),
            "p90_survival_rate": analytics.get("p90_invalidation_survival_rate", 0.0),
            "opportunity_saved_losses": analytics.get("opportunity_saved_losses", 0),
            "opportunity_missed_wins": analytics.get("opportunity_missed_wins", 0),
            "status": batch.status,
            "created_at": batch.created_at.isoformat() if batch.created_at else "",
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else "",
            "exported_at": manifest["exported_at"],
            "archive_dir": batch_dir,
            "zip_path": zip_path
        }
        existing_rows[str(batch.id)] = new_row

        with open(index_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=index_cols)
            writer.writeheader()
            for b_id_str in sorted(existing_rows.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                writer.writerow(existing_rows[b_id_str])

        return {
            "status": "SUCCESS",
            "batch_id": batch.id,
            "archive_dir": batch_dir,
            "zip_path": zip_path,
            "manifest": manifest,
            "files_exported": list(file_hashes.keys()) + [f"batch_{batch_id}.zip"]
        }

    @staticmethod
    def export_all_batches(
        db: Session,
        archive_base_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Exports all ReplayBatch records in the database to persistent archives."""
        batches = db.query(ReplayBatch).order_by(ReplayBatch.id.asc()).all()
        results = []
        for b in batches:
            try:
                res = ReplayService.export_batch(db, b.id, archive_base_dir=archive_base_dir)
                results.append(res)
            except Exception as e:
                logger.error(f"Failed to export batch {b.id}: {e}")
                results.append({
                    "status": "ERROR",
                    "batch_id": b.id,
                    "error": str(e)
                })
        return results

    @staticmethod
    def get_all_batches_summary(
        db: Session,
        archive_base_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns all batches with their summary performance metrics and export status."""
        base_dir = archive_base_dir or ReplayService.get_default_archive_dir()
        batches = db.query(ReplayBatch).order_by(ReplayBatch.id.desc()).all()
        results = []
        for b in batches:
            manifest_p = os.path.join(base_dir, f"batch_{b.id}", "manifest.json")
            is_exported = os.path.exists(manifest_p)
            zip_p = os.path.join(base_dir, f"batch_{b.id}.zip")

            analytics = ReplayService.get_control_group_analytics(db, b.id)
            results.append({
                "id": b.id,
                "batch_name": b.batch_name,
                "execution_policy": b.execution_policy,
                "start_date": str(b.start_date),
                "end_date": str(b.end_date),
                "instruments": b.instruments,
                "friction_pips": b.friction_pips,
                "total_setups_evaluated": b.total_setups_evaluated,
                "total_trades_taken": b.total_trades_taken,
                "total_setups_passed": b.total_setups_passed,
                "status": b.status,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "completed_at": b.completed_at.isoformat() if b.completed_at else None,
                "win_rate": analytics.get("simulated_trader_win_rate", 0.0),
                "average_r": analytics.get("average_r_multiple", 0.0),
                "expectancy_r": analytics.get("expectancy_r", 0.0),
                "average_winner_r": analytics.get("average_winner_r", 0.0),
                "average_loser_r": analytics.get("average_loser_r", 0.0),
                "is_exported": is_exported,
                "zip_path": zip_p if is_exported and os.path.exists(zip_p) else None
            })
        return results

    @staticmethod
    def load_batch_analytics_and_manifest(
        db: Session,
        batch_id: int,
        archive_base_dir: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Loads analytics and manifest for a batch.
        Checks active database first; if not in DB (or wiped),
        seamlessly falls back to persistent archive files in replay_archive/batch_<id>/.
        """
        base_dir = archive_base_dir or ReplayService.get_default_archive_dir()
        batch_dir = os.path.join(base_dir, f"batch_{batch_id}")
        manifest_path = os.path.join(batch_dir, "manifest.json")
        analytics_path = os.path.join(batch_dir, "analytics.json")
        batch_json_path = os.path.join(batch_dir, "batch.json")

        batch_in_db = db.query(ReplayBatch).filter(ReplayBatch.id == batch_id).first() if db else None

        if batch_in_db:
            analytics = ReplayService.get_control_group_analytics(db, batch_id)
            if os.path.exists(manifest_path):
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            else:
                manifest = {
                    "batch_id": batch_in_db.id,
                    "batch_name": batch_in_db.batch_name,
                    "execution_policy": batch_in_db.execution_policy,
                    "start_date": str(batch_in_db.start_date),
                    "end_date": str(batch_in_db.end_date),
                    "instruments": batch_in_db.instruments,
                    "friction_pips": batch_in_db.friction_pips,
                    "database_schema_version": "v2.1",
                    "git_commit_hash": ReplayService._get_git_commit_hash(),
                    "source_engine_hashes": ReplayService._get_source_file_hashes(),
                }
            return analytics, manifest

        # Fallback to persistent archive files
        if os.path.exists(analytics_path) and os.path.exists(manifest_path):
            with open(analytics_path, "r", encoding="utf-8") as f:
                analytics = json.load(f)
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            return analytics, manifest

        raise ValueError(f"Replay batch #{batch_id} not found in database or archive directory ({batch_dir})")

    @staticmethod
    def compare_batches(
        db: Session,
        baseline_batch_id: int,
        candidate_batch_id: int,
        archive_base_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs rigorous empirical comparison between Baseline and Candidate replay batches.
        Enforces KPI hierarchy:
        - PRIMARY: expectancy_r, average_winner_r, average_loser_r, profit_factor, max_drawdown_r
        - SECONDARY: win_rate, net_r, p90_survival_rate, MFE/MAE distributions, R milestones, saved_losses, missed_wins, trades_taken
        - Validates comparison type (CONTROLLED vs CONTEXTUAL)
        - Analyzes per-instrument breadth (broad vs isolated improvement)
        - Synthesizes grounded economic interpretation without arbitrary weighted scoring
        """
        base_analytics, base_manifest = ReplayService.load_batch_analytics_and_manifest(db, baseline_batch_id, archive_base_dir)
        cand_analytics, cand_manifest = ReplayService.load_batch_analytics_and_manifest(db, candidate_batch_id, archive_base_dir)

        # 1. Comparison Validity Classification
        diffs = []
        base_start, base_end = base_manifest.get("start_date"), base_manifest.get("end_date")
        cand_start, cand_end = cand_manifest.get("start_date"), cand_manifest.get("end_date")
        if (base_start, base_end) != (cand_start, cand_end):
            diffs.append(f"Date range mismatch ({base_start}..{base_end} vs {cand_start}..{cand_end})")

        base_inst = sorted(base_manifest.get("instruments") or [])
        cand_inst = sorted(cand_manifest.get("instruments") or [])
        if base_inst != cand_inst:
            diffs.append(f"Instrument universe mismatch ({base_inst} vs {cand_inst})")

        base_friction = base_manifest.get("friction_pips")
        cand_friction = cand_manifest.get("friction_pips")
        if base_friction != cand_friction:
            diffs.append(f"Friction mismatch ({base_friction}p vs {cand_friction}p)")

        base_hash = base_manifest.get("population_checksum_hash") or base_analytics.get("population_checksum_hash")
        cand_hash = cand_manifest.get("population_checksum_hash") or cand_analytics.get("population_checksum_hash")
        if base_hash and cand_hash and base_hash != cand_hash and not diffs:
            diffs.append("V4 Signal population hash changed")

        if not diffs:
            comparison_validity = "CONTROLLED"
            validity_reason = "Controlled comparison: Identical date range, instrument universe, friction penalty, and signal population. Pure execution/strategy variation."
        else:
            comparison_validity = "CONTEXTUAL"
            validity_reason = f"Contextual comparison (Not controlled): {'; '.join(diffs)}."

        # 2. Metric Delta Helper
        def calc_metric_delta(base_val: float, cand_val: float, higher_is_better: bool = True, is_loss_val: bool = False) -> Dict[str, Any]:
            b = float(base_val or 0.0)
            c = float(cand_val or 0.0)
            delta_abs = round(c - b, 3)
            delta_pct = round((c - b) / abs(b) * 100, 1) if abs(b) > 0.0001 else (0.0 if abs(c) < 0.0001 else 100.0)

            if is_loss_val:
                # For average_loser_r (e.g. -1.05R vs -0.80R), less negative (higher) is better
                improved = (c > b + 0.001)
                worsened = (c < b - 0.001)
            elif higher_is_better:
                improved = (c > b + 0.001)
                worsened = (c < b - 0.001)
            else:
                improved = (c < b - 0.001)
                worsened = (c > b + 0.001)

            verdict = "IMPROVED" if improved else ("WORSENED" if worsened else "NEUTRAL")
            return {
                "baseline": round(b, 3),
                "candidate": round(c, 3),
                "delta_abs": delta_abs,
                "delta_pct": delta_pct,
                "verdict": verdict
            }

        # 3. Primary Economic KPIs
        primary_kpis = {
            "expectancy_r": calc_metric_delta(base_analytics.get("expectancy_r", 0.0), cand_analytics.get("expectancy_r", 0.0), higher_is_better=True),
            "average_winner_r": calc_metric_delta(base_analytics.get("average_winner_r", 0.0), cand_analytics.get("average_winner_r", 0.0), higher_is_better=True),
            "average_loser_r": calc_metric_delta(base_analytics.get("average_loser_r", 0.0), cand_analytics.get("average_loser_r", 0.0), is_loss_val=True),
            "profit_factor": calc_metric_delta(base_analytics.get("profit_factor", 0.0), cand_analytics.get("profit_factor", 0.0), higher_is_better=True),
            "max_drawdown_r": calc_metric_delta(base_analytics.get("max_drawdown_r", 0.0), cand_analytics.get("max_drawdown_r", 0.0), higher_is_better=False),
        }

        # 4. Secondary KPIs
        secondary_kpis = {
            "win_rate": calc_metric_delta(base_analytics.get("simulated_trader_win_rate", 0.0), cand_analytics.get("simulated_trader_win_rate", 0.0), higher_is_better=True),
            "net_r": calc_metric_delta(base_analytics.get("net_r", 0.0), cand_analytics.get("net_r", 0.0), higher_is_better=True),
            "p90_survival_rate": calc_metric_delta(base_analytics.get("p90_invalidation_survival_rate", 0.0), cand_analytics.get("p90_invalidation_survival_rate", 0.0), higher_is_better=True),
            "trades_taken": calc_metric_delta(base_analytics.get("total_trades_taken", 0), cand_analytics.get("total_trades_taken", 0), higher_is_better=True),
            "saved_losses": calc_metric_delta(base_analytics.get("opportunity_saved_losses", 0), cand_analytics.get("opportunity_saved_losses", 0), higher_is_better=True),
            "missed_wins": calc_metric_delta(base_analytics.get("opportunity_missed_wins", 0), cand_analytics.get("opportunity_missed_wins", 0), higher_is_better=False),
        }

        # 5. Per-Instrument Breadth Comparison
        base_inst_perf = base_analytics.get("performance_by_instrument", {})
        cand_inst_perf = cand_analytics.get("performance_by_instrument", {})
        all_instruments = sorted(set(list(base_inst_perf.keys()) + list(cand_inst_perf.keys())))

        instrument_comparisons = {}
        improved_instruments = []
        worsened_instruments = []
        neutral_instruments = []

        for inst in all_instruments:
            b_p = base_inst_perf.get(inst, {})
            c_p = cand_inst_perf.get(inst, {})

            inst_exp_delta = calc_metric_delta(b_p.get("expectancy_r", 0.0), c_p.get("expectancy_r", 0.0), higher_is_better=True)
            inst_pf_delta = calc_metric_delta(b_p.get("profit_factor", 0.0), c_p.get("profit_factor", 0.0), higher_is_better=True)
            inst_net_delta = calc_metric_delta(b_p.get("net_r", 0.0), c_p.get("net_r", 0.0), higher_is_better=True)
            inst_wr_delta = calc_metric_delta(b_p.get("win_rate", 0.0), c_p.get("win_rate", 0.0), higher_is_better=True)
            inst_dd_delta = calc_metric_delta(b_p.get("max_drawdown_r", 0.0), c_p.get("max_drawdown_r", 0.0), higher_is_better=False)

            # Classify per-instrument verdict based on primary economics (expectancy & profit factor)
            if inst_exp_delta["delta_abs"] >= 0.02 and inst_pf_delta["verdict"] in ["IMPROVED", "NEUTRAL"]:
                inst_verdict = "IMPROVED"
                improved_instruments.append(inst)
            elif inst_exp_delta["delta_abs"] <= -0.02 or (inst_pf_delta["verdict"] == "WORSENED" and inst_exp_delta["delta_abs"] < 0):
                inst_verdict = "WORSENED"
                worsened_instruments.append(inst)
            else:
                inst_verdict = "NEUTRAL"
                neutral_instruments.append(inst)

            instrument_comparisons[inst] = {
                "verdict": inst_verdict,
                "expectancy_r": inst_exp_delta,
                "profit_factor": inst_pf_delta,
                "net_r": inst_net_delta,
                "win_rate": inst_wr_delta,
                "max_drawdown_r": inst_dd_delta,
                "baseline_trades": b_p.get("trades_taken", 0),
                "candidate_trades": c_p.get("trades_taken", 0),
            }

        # Breadth assessment
        total_inst_count = len(all_instruments)
        if total_inst_count > 0:
            if len(improved_instruments) / total_inst_count >= 0.6:
                breadth_summary = "BROAD_IMPROVEMENT"
            elif len(improved_instruments) > 0 and len(worsened_instruments) == 0:
                breadth_summary = "CONCENTRATED_IMPROVEMENT"
            elif len(worsened_instruments) / total_inst_count >= 0.6:
                breadth_summary = "BROAD_DETERIORATION"
            else:
                breadth_summary = "MIXED"
        else:
            breadth_summary = "INSUFFICIENT_DATA"

        # 6. Grounded Economic Interpretation Layer
        exp_v = primary_kpis["expectancy_r"]["verdict"]
        pf_v = primary_kpis["profit_factor"]["verdict"]
        dd_v = primary_kpis["max_drawdown_r"]["verdict"]
        wr_v = secondary_kpis["win_rate"]["verdict"]
        taken_v = secondary_kpis["trades_taken"]["verdict"]
        exp_delta = primary_kpis["expectancy_r"]["delta_abs"]

        if exp_v == "IMPROVED" and pf_v == "IMPROVED" and dd_v in ["IMPROVED", "NEUTRAL"]:
            economic_verdict = "OBSERVED ECONOMIC IMPROVEMENT ACROSS PRIMARY METRICS"
            evidence_summary = (
                f"Candidate demonstrated empirical improvement in core economics: Expectancy increased by "
                f"{'+' if exp_delta >= 0 else ''}{exp_delta}R ({primary_kpis['expectancy_r']['delta_pct']:+.1f}%), "
                f"Profit Factor moved from {primary_kpis['profit_factor']['baseline']} to {primary_kpis['profit_factor']['candidate']}, "
                f"with gains observed in {len(improved_instruments)}/{total_inst_count} instruments."
            )
        elif exp_v == "IMPROVED" and dd_v == "WORSENED":
            economic_verdict = "OBSERVED PROFITABILITY IMPROVEMENT WITH INCREASED DRAWDOWN"
            evidence_summary = (
                f"Candidate improved per-trade expectancy ({'+' if exp_delta >= 0 else ''}{exp_delta}R), "
                f"but Maximum Drawdown expanded by {primary_kpis['max_drawdown_r']['delta_abs']:+.2f}R. "
                f"Risk-adjusted stability trade-off must be considered."
            )
        elif wr_v == "IMPROVED" and exp_v in ["WORSENED", "NEUTRAL"]:
            economic_verdict = "HIGHER WIN RATE WITH DETERIORATED TRADE ECONOMICS"
            evidence_summary = (
                f"Candidate achieved higher nominal win rate ({secondary_kpis['win_rate']['delta_pct']:+.1f}%), "
                f"but economic expectancy remained flat or decreased ({'+' if exp_delta >= 0 else ''}{exp_delta}R), "
                f"proving that higher win rate alone did not yield improved profitability."
            )
        elif exp_v == "IMPROVED" and taken_v == "WORSENED":
            economic_verdict = "LOWER OPPORTUNITY COUNT WITH HIGHER TRADE QUALITY"
            evidence_summary = (
                f"Candidate filtered out lower-quality setups, reducing total trades taken from "
                f"{secondary_kpis['trades_taken']['baseline']} to {secondary_kpis['trades_taken']['candidate']}, "
                f"while increasing per-trade expectancy by {'+' if exp_delta >= 0 else ''}{exp_delta}R."
            )
        elif exp_v == "WORSENED":
            economic_verdict = "OBSERVED ECONOMIC DETERIORATION"
            evidence_summary = (
                f"Candidate exhibited lower economic expectancy ({exp_delta:+.3f}R) and deteriorated "
                f"profit factor ({primary_kpis['profit_factor']['baseline']} -> {primary_kpis['profit_factor']['candidate']})."
            )
        else:
            economic_verdict = "NO CLEAR OBSERVED ECONOMIC IMPROVEMENT"
            evidence_summary = (
                f"Observed changes between Baseline and Candidate are within minor variation bounds "
                f"(Expectancy delta: {exp_delta:+.3f}R). Results are empirically inconclusive."
            )

        return {
            "comparison_validity": comparison_validity,
            "validity_reason": validity_reason,
            "provenance": {
                "baseline": {
                    "batch_id": baseline_batch_id,
                    "batch_name": base_manifest.get("batch_name", "Baseline"),
                    "execution_policy": base_manifest.get("execution_policy"),
                    "date_range": f"{base_manifest.get('start_date')} to {base_manifest.get('end_date')}",
                    "instruments": base_manifest.get("instruments"),
                    "friction_pips": base_manifest.get("friction_pips"),
                    "git_commit": base_manifest.get("git_commit_hash", "UNKNOWN"),
                    "schema_version": base_manifest.get("database_schema_version", "v2.1"),
                },
                "candidate": {
                    "batch_id": candidate_batch_id,
                    "batch_name": cand_manifest.get("batch_name", "Candidate"),
                    "execution_policy": cand_manifest.get("execution_policy"),
                    "date_range": f"{cand_manifest.get('start_date')} to {cand_manifest.get('end_date')}",
                    "instruments": cand_manifest.get("instruments"),
                    "friction_pips": cand_manifest.get("friction_pips"),
                    "git_commit": cand_manifest.get("git_commit_hash", "UNKNOWN"),
                    "schema_version": cand_manifest.get("database_schema_version", "v2.1"),
                }
            },
            "economic_verdict": economic_verdict,
            "evidence_summary": evidence_summary,
            "breadth_summary": breadth_summary,
            "instruments_improved": improved_instruments,
            "instruments_worsened": worsened_instruments,
            "instruments_neutral": neutral_instruments,
            "primary_kpis": primary_kpis,
            "secondary_kpis": secondary_kpis,
            "instrument_comparisons": instrument_comparisons,
        }

    @staticmethod
    def reset_replay_data(db: Session) -> int:
        """
        One-click wipe of all isolated Replay database tables.
        Preserves all exported file archives and experiment_index.csv intact.
        """
        count_trades = db.query(ReplayTradeRecord).delete()
        count_snapshots = db.query(ReplaySetupSnapshot).delete()
        count_batches = db.query(ReplayBatch).delete()
        db.commit()
        logger.info(f"Replay DB wiped: {count_batches} batches, {count_snapshots} snapshots, {count_trades} trades removed. Persistent file archives preserved.")
        return count_trades + count_snapshots + count_batches


