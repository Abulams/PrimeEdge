import os
import sys
import json
import datetime

sys.path.insert(0, 'C:/Users/qsoft/.gemini/antigravity/scratch/market-os/backend')
from app.database import SessionLocal, engine, Base
from app.replay_service import ReplayService
import app.models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

start_date = datetime.date(2021, 1, 1)
end_date = datetime.date(2025, 12, 31)
instruments = ['EURUSD', 'GBPUSD', 'AUDUSD', 'USDJPY', 'XAUUSD']
results = {}

print('=== STARTING FULL SCIENTIFIC MARKET OS REPLAY SUITE ===', flush=True)
for inst in instruments:
    name = inst + ' Strict Audit (2021-2025)'
    print(f'\nExecuting Replay Batch for {inst} (2021-2025, 2.5p friction)...', flush=True)
    batch = ReplayService.create_batch(db, start_date, end_date, [inst], name, 'MARKET_ENTRY', 2.5)
    batch_id = batch.id
    print(f'  -> Batch ID {batch_id} created. Running ReplayEngine...', flush=True)
    ReplayService.run_batch(db, batch_id)
    analytics = ReplayService.get_control_group_analytics(db, batch_id)
    integrity = ReplayService.run_replay_integrity_checksum(db, batch_id)
    results[inst] = {'batch_id': batch_id, 'analytics': analytics, 'integrity': integrity}
    print(f'  -> Results for {inst}:', flush=True)
    print('     Evaluated:', analytics.get('total_setups_evaluated'), flush=True)
    print('     Trades Taken:', analytics.get('total_trades_taken'), flush=True)
    print('     Passed:', analytics.get('total_setups_passed'), '(Saved Losses:', analytics.get('opportunity_saved_losses'), ')', flush=True)
    print('     Win Rate:', analytics.get('simulated_trader_win_rate'), '%', flush=True)
    print('     Avg Winner: +', analytics.get('average_winner_r'), 'R', flush=True)
    print('     Avg Loser:', analytics.get('average_loser_r'), 'R', flush=True)
    print('     Profit Factor:', analytics.get('profit_factor'), flush=True)
    print('     Expectancy: +', analytics.get('expectancy_r'), 'R/trade', flush=True)
    print('     Net R: +', analytics.get('net_r'), 'R', flush=True)
    print('     Integrity:', integrity.get('status'), flush=True)

with open('full_backtest_audit_results.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)

print('\n=== ALL REPLAY BATCHES COMPLETED AND RECONCILED ===', flush=True)
