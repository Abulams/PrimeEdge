"""
Phase 3 (Revised): August 23-28 Signals in Transition Context
Analyze current Market OS signals in context of recent regime transitions
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = r"C:\Market-OS\backend\market_os.db"

def get_august_signals():
    """Get all Market OS signals from August 23-28, 2026"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT instrument, date, direction, status_at_snapshot, dxy_regime, 
           risk_sentiment, trend, session, created_at,
           setup_ref_price, live_price_at_snap,
           mae_p50_pips, mfe_p50_pips, continuation_prob, historical_n
    FROM setup_snapshots
    WHERE date BETWEEN '2026-08-23' AND '2026-08-28'
    AND instrument IN ('XAUUSD', 'GBPUSD', 'EURUSD')
    ORDER BY date ASC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

def get_regime_context_august():
    """Get regime context for August 2026"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT date, dxy_regime, risk_sentiment, macro_summary
    FROM daily_market_regimes
    WHERE date BETWEEN '2026-08-01' AND '2026-08-29'
    ORDER BY date ASC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

def get_recent_transitions():
    """Get recent transitions relevant to August period"""
    transition_catalog = pd.read_csv(r"C:\Market-OS\effective_transition_catalog.csv")
    
    # Get transitions in 2026 that could affect August signals
    recent_transitions = transition_catalog[
        (transition_catalog['transition_date'] >= '2026-01-01') & 
        (transition_catalog['transition_date'] <= '2026-08-28')
    ]
    
    return recent_transitions

print("=" * 80)
print("PHASE 3 (REVISED): AUGUST 23-28 SIGNALS IN TRANSITION CONTEXT")
print("=" * 80)

# Step 1: Get August 23-28 signals
print("\n1. AUGUST 23-28 SIGNALS")
print("=" * 80)
august_signals = get_august_signals()

print(f"Total signals: {len(august_signals)}")

if len(august_signals) > 0:
    print("\nSignal breakdown by date:")
    print(august_signals['date'].value_counts().sort_index())
    
    print("\nSignal breakdown by instrument:")
    print(august_signals['instrument'].value_counts())
    
    print("\nSignal breakdown by status:")
    print(august_signals['status_at_snapshot'].value_counts())
    
    print("\nSignal breakdown by direction:")
    print(august_signals['direction'].value_counts())
    
    print("\nDetailed signals:")
    for _, signal in august_signals.iterrows():
        print(f"{signal['date']}: {signal['instrument']} {signal['direction']} | {signal['status_at_snapshot']} | DXY: {signal['dxy_regime']} | Continuation prob: {signal['continuation_prob']:.2f}")

# Step 2: Get regime context for August
print("\n2. AUGUST 2026 REGIME CONTEXT")
print("=" * 80)
august_regime = get_regime_context_august()

print(august_regime.to_string(index=False))

# Step 3: Get recent transitions
print("\n3. RECENT TRANSITIONS RELEVANT TO AUGUST")
print("=" * 80)
recent_transitions = get_recent_transitions()

print(f"Transitions in 2026: {len(recent_transitions)}")

for _, transition in recent_transitions.iterrows():
    print(f"{transition['transition_date']}: {transition['from_regime']} to {transition['to_regime']} ({transition['classified_type']}, {transition['previous_duration_days']} days)")

# Step 4: Analyze August signals in transition context
print("\n4. AUGUST SIGNALS IN TRANSITION CONTEXT")
print("=" * 80)

if len(august_signals) > 0:
    # Find the most recent transition before August 23
    aug_23 = pd.to_datetime('2026-08-23')
    
    transitions_before_august = recent_transitions[
        pd.to_datetime(recent_transitions['transition_date']) < aug_23
    ]
    
    if len(transitions_before_august) > 0:
        most_recent_before_august = transitions_before_august.iloc[-1]
        transition_date = pd.to_datetime(most_recent_before_august['transition_date'])
        days_since_transition = (aug_23 - transition_date).days
        
        print(f"Most recent transition before August 23:")
        print(f"  Date: {most_recent_before_august['transition_date']}")
        print(f"  Type: {most_recent_before_august['from_regime']} to {most_recent_before_august['to_regime']}")
        print(f"  Classification: {most_recent_before_august['classified_type']}")
        print(f"  Days before August 23: {days_since_transition}")
        
        # Analyze if signals align with post-transition regime
        print(f"\nRegime alignment analysis:")
        print(f"  Transition result: {most_recent_before_august['to_regime']}")
        print(f"  August signals DXY regime: {august_signals['dxy_regime'].iloc[0] if len(august_signals) > 0 else 'N/A'}")
        
        if len(august_signals) > 0:
            august_dxy = august_signals['dxy_regime'].iloc[0]
            transition_result = most_recent_before_august['to_regime']
            
            if august_dxy == transition_result:
                print(f"  Alignment: CORRECT - August signals reflect post-transition regime")
            else:
                print(f"  Alignment: INCORRECT - August signals don't reflect post-transition regime")
                print(f"  This suggests potential stale macro state")
        
        # Check if signal direction is appropriate for the regime
        print(f"\nSignal direction vs regime analysis:")
        
        if len(august_signals) > 0:
            signal_direction = august_signals['direction'].iloc[0]
            dxy_regime = august_signals['dxy_regime'].iloc[0]
            
            if dxy_regime == 'BEARISH' and signal_direction == 'LONG':
                print(f"  Regime: BEARISH (USD weakness)")
                print(f"  Signal direction: LONG")
                print(f"  Analysis: APPROPRIATE - LONG during BEARISH-DXY is fundamentally consistent")
                print(f"  (USD weakness should support LONG on USD pairs)")
            elif dxy_regime == 'BULLISH' and signal_direction == 'LONG':
                print(f"  Regime: BULLISH (USD strength)")
                print(f"  Signal direction: LONG")
                print(f"  Analysis: CONTRADICTORY - LONG during BULLISH-DXY conflicts with USD strength")
            else:
                print(f"  Regime: {dxy_regime}")
                print(f"  Signal direction: {signal_direction}")
                print(f"  Analysis: Needs further analysis")
    
    else:
        print("No transitions found before August 23, 2026")

# Step 5: Check for consolidation periods
print("\n5. CONSOLIDATION PERIOD ANALYSIS")
print("=" * 80)

# Check if there were consolidation periods before August signals
consolidation_periods = august_regime[august_regime['dxy_regime'] == 'CONSOLIDATING']

if len(consolidation_periods) > 0:
    print(f"Consolidation periods in August: {len(consolidation_periods)}")
    print(consolidation_periods[['date', 'dxy_regime', 'risk_sentiment']].to_string(index=False))
else:
    print("No consolidation periods in August regime data")

# Step 6: Signal freshness analysis
print("\n6. SIGNAL FRESHNESS ANALYSIS")
print("=" * 80)

if len(august_signals) > 0:
    # Check when the current regime started
    current_regime = august_signals['dxy_regime'].iloc[0]
    
    # Find when this regime started
    regime_start_dates = august_regime[august_regime['dxy_regime'] == current_regime]['date']
    
    if len(regime_start_dates) > 0:
        regime_start = regime_start_dates.iloc[0]
        regime_duration = (pd.to_datetime('2026-08-28') - pd.to_datetime(regime_start)).days
        
        print(f"Current regime: {current_regime}")
        print(f"Regime start date: {regime_start}")
        print(f"Regime duration as of August 28: {regime_duration} days")
        
        if regime_duration > 30:
            print(f"Analysis: Established regime ({regime_duration} days) - signals should be stable")
        elif regime_duration > 7:
            print(f"Analysis: Recent regime ({regime_duration} days) - signals should be adapting")
        else:
            print(f"Analysis: Very recent regime ({regime_duration} days) - potential transition period")

print("\n" + "=" * 80)
print("PHASE 3 (REVISED) COMPLETE")
print("=" * 80)