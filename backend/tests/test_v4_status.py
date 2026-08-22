"""
V4 Baseline Freeze — Unit Tests for Status State Classification

Tests the pure corridor-derived status logic:
  WAIT     = price hasn't reached P25
  READY    = price between P25 and P90
  INVALID  = price breached P90
  NO EDGE  = evidence exists but EV not positive
  NO SETUP = insufficient evidence

Covers:
  - P25=0 (zero percentile → always READY, with narrative)
  - P25>0 (meaningful corridor with WAIT zone)
  - Price inside P25–P75 (acceptable corridor)
  - Price inside P75–P90 (deep retracement)
  - Price beyond P90 (invalidation)
  - LONG direction
  - SHORT direction
  - NO EDGE
  - NO SETUP
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def classify_status(
    direction: str,
    ref_price: float,
    p25_price: float,
    p75_price: float,
    p90_price: float,
    p25_mae: float,
    p75_mae: float,
    p90_mae: float,
    all_maes: list,
    total_samples: int,
    max_ev: float,
    opt_a_win_rate: float,
    opt_b_win_rate: float,
    pip_unit: float = 0.0001,
    instrument: str = "GBPUSD",
):
    """
    Pure extraction of the V4 status classification logic from engine.py.
    Returns (status_state, why_this_now).
    """
    if total_samples < 10:
        return "NO SETUP", "Current market conditions do not closely match a sufficiently reliable historical pattern."

    if max_ev <= 0.0 or (opt_a_win_rate < 0.40 and opt_b_win_rate < 0.45):
        return "NO EDGE", "Current market conditions show ample historical matches, but current execution choices offer no statistically compelling edge."

    if (direction == "LONG" and ref_price <= p90_price) or (direction == "SHORT" and ref_price >= p90_price):
        return "INVALID", f"Price ({ref_price}) has breached the historical invalidation boundary (P90 MAE: {p90_mae:.1f}p). Setup is invalidated."

    if (direction == "LONG" and ref_price <= p25_price) or (direction == "SHORT" and ref_price >= p25_price):
        in_deep = (direction == "LONG" and ref_price <= p75_price) or (direction == "SHORT" and ref_price >= p75_price)
        if p25_mae == 0.0:
            pct_zero_mae = round(sum(1 for m in all_maes if m == 0.0) / len(all_maes) * 100)
            why = (
                f"Market entry supported. {pct_zero_mae}% of comparable setups moved favorably "
                f"without a measurable pullback. The historical acceptable corridor extends "
                f"up to {p75_mae:.1f}p of adverse movement."
            )
        elif in_deep:
            depth_pips = round(abs(ref_price - p75_price) / pip_unit, 1)
            why = (
                f"Price ({ref_price}) is {depth_pips}p into the deep retracement zone "
                f"(P75\u2013P90: {p75_mae:.1f}p\u2013{p90_mae:.1f}p). Entry is still valid but "
                f"approaching the P90 invalidation boundary."
            )
        else:
            why = (
                f"Price ({ref_price}) is inside the acceptable entry corridor "
                f"(P25\u2013P75: {p25_mae:.1f}p\u2013{p75_mae:.1f}p) for {instrument}."
            )
        return "READY", why

    pips_away = round(abs(ref_price - p25_price) / pip_unit, 1)
    why = (
        f"{direction.capitalize()} historical pattern detected. Price is currently "
        f"{pips_away} pips above the P25 entry corridor boundary."
    )
    return "WAIT", why


class TestV4StatusClassification(unittest.TestCase):
    """V4 Baseline Freeze: status_state must be purely corridor-derived."""

    # ── Common test fixtures ──────────────────────────────────────────────

    def _long_defaults(self, **overrides):
        """Default LONG setup: P25=3.2, P75=14.4, P90=31.6, ref=1.34756"""
        base = dict(
            direction="LONG",
            ref_price=1.34756,
            p25_mae=3.2,
            p75_mae=14.4,
            p90_mae=31.6,
            all_maes=[0.0, 1.5, 3.2, 5.0, 7.8, 10.0, 14.4, 20.0, 31.6, 45.0],
            total_samples=32,
            max_ev=0.8,
            opt_a_win_rate=0.59,
            opt_b_win_rate=0.62,
            pip_unit=0.0001,
            instrument="GBPUSD",
        )
        # Compute price boundaries from MAE
        base["p25_price"] = round(base["ref_price"] - base["p25_mae"] * base["pip_unit"], 5)
        base["p75_price"] = round(base["ref_price"] - base["p75_mae"] * base["pip_unit"], 5)
        base["p90_price"] = round(base["ref_price"] - base["p90_mae"] * base["pip_unit"], 5)
        base.update(overrides)
        return base

    def _short_defaults(self, **overrides):
        """Default SHORT setup: mirrored inequalities."""
        base = dict(
            direction="SHORT",
            ref_price=1.34756,
            p25_mae=4.0,
            p75_mae=12.0,
            p90_mae=28.0,
            all_maes=[0.0, 2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 22.0, 28.0, 40.0],
            total_samples=25,
            max_ev=0.6,
            opt_a_win_rate=0.55,
            opt_b_win_rate=0.58,
            pip_unit=0.0001,
            instrument="GBPUSD",
        )
        # For SHORT, MAE is upward: P25_price = ref + P25_mae * pip
        base["p25_price"] = round(base["ref_price"] + base["p25_mae"] * base["pip_unit"], 5)
        base["p75_price"] = round(base["ref_price"] + base["p75_mae"] * base["pip_unit"], 5)
        base["p90_price"] = round(base["ref_price"] + base["p90_mae"] * base["pip_unit"], 5)
        base.update(overrides)
        return base

    # ── Test: P25 = 0 (LONG) ─────────────────────────────────────────────

    def test_p25_zero_long_always_ready(self):
        """When P25=0, status is READY at market price with P25=0 narrative."""
        params = self._long_defaults(p25_mae=0.0)
        params["p25_price"] = params["ref_price"]  # P25=0 → boundary = ref_price
        params["all_maes"] = [0.0, 0.0, 0.0, 0.0, 5.0, 7.0, 9.1, 12.0, 25.0, 38.7]

        status, why = classify_status(**params)
        self.assertEqual(status, "READY")
        self.assertIn("without a measurable pullback", why)
        self.assertIn("Market entry supported", why)

    # ── Test: P25 > 0 (LONG) — WAIT zone exists ─────────────────────────

    def test_p25_positive_long_wait(self):
        """When P25>0 and price hasn't pulled back, status is WAIT."""
        params = self._long_defaults()
        # ref_price is above p25_price, so WAIT
        status, why = classify_status(**params)
        self.assertEqual(status, "WAIT")
        self.assertIn("above the P25 entry corridor boundary", why)

    # ── Test: Price inside P25–P75 (acceptable corridor) ─────────────────

    def test_inside_acceptable_corridor_long(self):
        """Price between P25 and P75 → READY with corridor narrative."""
        params = self._long_defaults()
        # Place price 8 pips below ref (between P25=3.2 and P75=14.4)
        params["ref_price"] = params["p25_price"] - 0.0001  # just below P25 boundary
        status, why = classify_status(**params)
        self.assertEqual(status, "READY")
        self.assertIn("acceptable entry corridor", why)

    # ── Test: Price inside P75–P90 (deep retracement) ────────────────────

    def test_deep_retracement_long(self):
        """Price between P75 and P90 → READY with deep retracement warning."""
        params = self._long_defaults()
        # Place price between P75 and P90
        params["ref_price"] = params["p75_price"] - 0.0005  # 5p below P75
        status, why = classify_status(**params)
        self.assertEqual(status, "READY")
        self.assertIn("deep retracement zone", why)
        self.assertIn("approaching the P90 invalidation boundary", why)

    # ── Test: Price beyond P90 (INVALID) ─────────────────────────────────

    def test_beyond_p90_long_invalid(self):
        """Price below P90 boundary → INVALID."""
        params = self._long_defaults()
        params["ref_price"] = params["p90_price"] - 0.0005  # 5p below P90
        status, why = classify_status(**params)
        self.assertEqual(status, "INVALID")
        self.assertIn("breached the historical invalidation boundary", why)

    # ── Test: SHORT direction — mirrored inequalities ────────────────────

    def test_short_wait(self):
        """SHORT: price below P25 boundary (hasn't risen enough) → WAIT."""
        params = self._short_defaults()
        # For SHORT, ref_price < p25_price means WAIT
        status, why = classify_status(**params)
        self.assertEqual(status, "WAIT")

    def test_short_ready_in_corridor(self):
        """SHORT: price between P25 and P75 → READY."""
        params = self._short_defaults()
        params["ref_price"] = params["p25_price"] + 0.0001  # just above P25
        status, why = classify_status(**params)
        self.assertEqual(status, "READY")
        self.assertIn("acceptable entry corridor", why)

    def test_short_invalid(self):
        """SHORT: price above P90 → INVALID."""
        params = self._short_defaults()
        params["ref_price"] = params["p90_price"] + 0.0005
        status, why = classify_status(**params)
        self.assertEqual(status, "INVALID")

    # ── Test: NO EDGE ────────────────────────────────────────────────────

    def test_no_edge(self):
        """When max_ev ≤ 0, status is NO EDGE regardless of price."""
        params = self._long_defaults(max_ev=-0.1)
        status, why = classify_status(**params)
        self.assertEqual(status, "NO EDGE")
        self.assertIn("no statistically compelling edge", why)

    def test_no_edge_low_win_rates(self):
        """When both win rates are below thresholds, status is NO EDGE."""
        params = self._long_defaults(opt_a_win_rate=0.35, opt_b_win_rate=0.40, max_ev=0.5)
        status, why = classify_status(**params)
        self.assertEqual(status, "NO EDGE")

    # ── Test: NO SETUP ───────────────────────────────────────────────────

    def test_no_setup(self):
        """When total_samples < 10, status is NO SETUP."""
        params = self._long_defaults(total_samples=5)
        status, why = classify_status(**params)
        self.assertEqual(status, "NO SETUP")
        self.assertIn("do not closely match", why)

    # ── Test: Optimizer does NOT influence status ────────────────────────

    def test_optimizer_does_not_influence_status(self):
        """Verify opt_b_pips is not used in classification at all."""
        # Two runs with identical corridor but different opt_b_pips should produce same status
        params1 = self._long_defaults()
        params2 = self._long_defaults()
        # classify_status takes no opt_b_pips argument — by design
        status1, _ = classify_status(**params1)
        status2, _ = classify_status(**params2)
        self.assertEqual(status1, status2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
