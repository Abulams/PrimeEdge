"""
Market OS -- Full 7-Instrument Reconciled Backtest Suite
=========================================================
Instruments : EURUSD, GBPUSD, AUDUSD, USDJPY, XAUUSD, US100, AUDJPY
Period       : 2021-01-01  ->  2025-12-31
Rules        : MARKET_ENTRY, 2.5-pip friction, strict -0.35R MAE invalidation,
               +0.35R MFE disarm, hostile SL-first adverse resolution.
               Point-in-time only -- zero look-ahead.
"""
import sys, os, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.replay_service import ReplayService

START = datetime.date(2021, 1, 1)
END   = datetime.date(2025, 12, 31)
INSTRUMENTS   = ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "XAUUSD", "US100", "AUDJPY"]
FRICTION_PIPS = 2.5
POLICY        = "MARKET_ENTRY"

results = {}
portfolio_trades = 0
portfolio_net_r  = 0.0
portfolio_saved  = 0

print("=" * 70)
print("  MARKET OS -- FULL 7-INSTRUMENT RECONCILED BACKTEST (2021-2025)")
print("  Rules: -0.35R MAE cut | 2.5p friction | SL-first hostile resolution")
print("=" * 70)

db = SessionLocal()

for inst in INSTRUMENTS:
    name  = f"{inst} Strict Audit v2 (2021-2025)"
    print(f"\nExecuting Replay Batch for {inst} (2021-2025, {FRICTION_PIPS}p friction)...", flush=True)
    batch = ReplayService.create_batch(db, START, END, [inst], name, POLICY, FRICTION_PIPS)
    bid   = batch.id
    print(f"  -> Batch ID {bid} created. Running ReplayEngine...", flush=True)

    ReplayService.run_batch(db, bid)
    analytics = ReplayService.get_control_group_analytics(db, bid)
    integrity = ReplayService.run_replay_integrity_checksum(db, bid)

    evaluated = analytics.get("total_setups_evaluated", 0)
    taken     = analytics.get("total_trades_taken", 0)
    passed    = analytics.get("total_setups_passed", 0)
    saved     = analytics.get("opportunity_saved_losses", 0)
    wr        = analytics.get("simulated_trader_win_rate", 0)
    avg_w     = analytics.get("average_winner_r", 0)
    avg_l     = analytics.get("average_loser_r", 0)
    pf        = analytics.get("profit_factor", 0)
    exp       = analytics.get("expectancy_r", 0)
    net_r     = analytics.get("net_r", 0)
    integ     = integrity.get("status", "UNKNOWN")

    results[inst] = {"batch_id": bid, "analytics": analytics, "integrity": integrity}

    portfolio_trades += taken
    portfolio_net_r  += net_r
    portfolio_saved  += saved

    print(f"  -> Results for {inst}:")
    print(f"     Evaluated:     {evaluated}")
    print(f"     Trades Taken:  {taken}")
    print(f"     Passed:        {passed}  (Saved Losses: {saved})")
    print(f"     Win Rate:      {wr} %")
    print(f"     Avg Winner:   +{avg_w} R")
    print(f"     Avg Loser:     {avg_l} R")
    print(f"     Profit Factor: {pf}")
    print(f"     Expectancy:   +{exp} R/trade")
    print(f"     Net R:        +{net_r} R")
    print(f"     Integrity:     {integ}", flush=True)

db.close()

print("\n" + "=" * 70)
print(f"  PORTFOLIO SUMMARY  ({len(INSTRUMENTS)} instruments)")
print(f"  Total Trades Taken : {portfolio_trades}")
print(f"  Total Saved Losses : {portfolio_saved}")
print(f"  Total Net R        : +{round(portfolio_net_r, 2)} R")
print("=" * 70)
print("\n=== ALL REPLAY BATCHES COMPLETED AND RECONCILED ===")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "full_backtest_7inst_results.json")
with open(out_path, "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"Full audit JSON saved to: {out_path}")
