"""
Phase 3: Market OS Signal Performance Around Transitions
Analyze how Market OS signals performed around recent effective regime changes
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = r"C:\Market-OS\backend\market_os.db"

def get_market_os_signals_around_date(target_date, days_before=7, days_after=7):
    """Get Market OS signals around a specific date"""
    conn = sqlite3.connect(DB_PATH)
    
    start_date = (pd.to_datetime(target_date) - timedelta(days=days_before)).strftime('%Y-%m-%d')
    end_date = (pd.to_datetime(target_date) + timedelta(days=days_after)).strftime('%Y-%m-%d')
    
    query = f"""
    SELECT instrument, date, direction, status_at_snapshot, dxy_regime, 
           risk_sentiment, trend, session, created_at,
           setup_ref_price, live_price_at_snap,
           mae_p50_pips, mfe_p50_pips, continuation_prob, historical_n
    FROM setup_snapshots
    WHERE date BETWEEN '{start_date}' AND '{end_date}'
    AND instrument IN ('XAUUSD', 'GBPUSD', 'EURUSD')
    ORDER BY date ASC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

def get_regime_context_around_date(target_date, days_before=10, days_after=10):
    """Get regime context around a specific date"""
    conn = sqlite3.connect(DB_PATH)
    
    start_date = (pd.to_datetime(target_date) - timedelta(days=days_before)).strftime('%Y-%m-%d')
    end_date = (pd.to_datetime(target_date) + timedelta(days=days_after)).strftime('%Y-%m-%d')
    
    query = f"""
    SELECT date, dxy_regime, risk_sentiment, macro_summary
    FROM daily_market_regimes
    WHERE date BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY date ASC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

def analyze_signal_timing_relative_to_transition(signals_df, transition_date, transition_type):
    """Analyze signal timing relative to transition"""
    analysis = []
    
    transition_dt = pd.to_datetime(transition_date)
    
    for _, signal in signals_df.iterrows():
        signal_dt = pd.to_datetime(signal['date'])
        days_from_transition = (signal_dt - transition_dt).days
        
        analysis.append({
            'signal_date': signal['date'],
            'days_from_transition': days_from_transition,
            'period': classify_period(days_from_transition),
            'instrument': signal['instrument'],
            'direction': signal['direction'],
            'dxy_regime': signal['dxy_regime'],
            'status': signal['status_at_snapshot'],
            'continuation_prob': signal['continuation_prob'],
            'transition_type': transition_type
        })
    
    return pd.DataFrame(analysis)

def classify_period(days_from_transition):
    """Classify signal period relative to transition"""
    if days_from_transition < -7:
        return "BEFORE_TRANSITION"
    elif days_from_transition < 0:
        return "PRE_TRANSITION"
    elif days_from_transition == 0:
        return "TRANSITION_DAY"
    elif days_from_transition <= 7:
        return "POST_TRANSITION"
    else:
        return "AFTER_TRANSITION"

print("=" * 80)
print("PHASE 3: MARKET OS SIGNAL PERFORMANCE AROUND TRANSITIONS")
print("=" * 80)

# Load the effective transition catalog
transition_catalog = pd.read_csv(r"C:\Market-OS\effective_transition_catalog.csv")

# Focus on recent transitions (2025-2026)
recent_transitions = transition_catalog[transition_catalog['transition_date'] >= '2025-01-01']

print(f"\nAnalyzing {len(recent_transitions)} recent transitions (2025-2026)")

# Analyze the most recent transition (most relevant to current signals)
most_recent = recent_transitions.iloc[-1]
print(f"\nFOCUS: Most recent transition")
print(f"Date: {most_recent['transition_date']}")
print(f"Type: {most_recent['from_regime']} to {most_recent['to_regime']}")
print(f"Duration: {most_recent['previous_duration_days']} days")
print(f"Classification: {most_recent['classified_type']}")

transition_date = most_recent['transition_date']

# Get regime context
print("\n1. REGIME CONTEXT AROUND TRANSITION")
print("=" * 80)
regime_context = get_regime_context_around_date(transition_date, days_before=10, days_after=10)
print(regime_context.to_string(index=False))

# Get Market OS signals
print("\n2. MARKET OS SIGNALS AROUND TRANSITION")
print("=" * 80)
signals_around = get_market_os_signals_around_date(transition_date, days_before=7, days_after=7)

print(f"Signals found: {len(signals_around)}")

if len(signals_around) > 0:
    print("\nSignal breakdown by date:")
    print(signals_around['date'].value_counts().sort_index())
    
    print("\nSignal breakdown by status:")
    print(signals_around['status_at_snapshot'].value_counts())
    
    print("\nSignal breakdown by direction:")
    print(signals_around['direction'].value_counts())
    
    # Analyze timing relative to transition
    print("\n3. SIGNAL TIMING RELATIVE TO TRANSITION")
    print("=" * 80)
    timing_analysis = analyze_signal_timing_relative_to_transition(
        signals_around, transition_date, most_recent['classified_type']
    )
    
    print("Signals by period relative to transition:")
    print(timing_analysis['period'].value_counts())
    
    print("\nDetailed signal timing:")
    for _, row in timing_analysis.iterrows():
        print(f"{row['signal_date']} ({row['days_from_transition']}d): {row['instrument']} {row['direction']} | {row['period']} | DXY: {row['dxy_regime']} | Status: {row['status']}")
    
    # Analyze signal characteristics by period
    print("\n4. SIGNAL CHARACTERISTICS BY PERIOD")
    print("=" * 80)
    
    for period in timing_analysis['period'].unique():
        period_data = timing_analysis[timing_analysis['period'] == period]
        print(f"\n{period}: {len(period_data)} signals")
        
        if len(period_data) > 0:
            print(f"  Average continuation probability: {period_data['continuation_prob'].mean():.2f}")
            print(f"  Direction breakdown: {period_data['direction'].value_counts().to_dict()}")
            print(f"  Status breakdown: {period_data['status_at_snapshot'].value_counts().to_dict()}")
    
    # Check for evidence of stale macro state
    print("\n5. STALE MACRO STATE ANALYSIS")
    print("=" * 80)
    
    # Look for signals that might be using stale macro state
    # Example: LONG signals during transition from BULLISH to BEARISH
    if most_recent['from_regime'] == 'BULLISH' and most_recent['to_regime'] == 'BEARISH':
        stale_signals = timing_analysis[
            (timing_analysis['days_from_transition'] >= 0) &  # After transition
            (timing_analysis['direction'] == 'LONG') &  # Still going LONG
            (timing_analysis['dxy_regime'] == 'BEARISH')  # New regime is BEARISH
        ]
        
        print(f"Potential stale macro state signals: {len(stale_signals)}")
        if len(stale_signals) > 0:
            print("\nSignals continuing LONG direction after BULLISH->BEARISH transition:")
            for _, row in stale_signals.iterrows():
                print(f"  {row['signal_date']}: {row['instrument']} LONG | {row['days_from_transition']}d post-transition | Continuation prob: {row['continuation_prob']:.2f}")
    
    # Compare pre/post transition signal characteristics
    print("\n6. PRE VS POST TRANSITION COMPARISON")
    print("=" * 80)
    
    pre_transition = timing_analysis[timing_analysis['period'] == 'PRE_TRANSITION']
    post_transition = timing_analysis[timing_analysis['period'] == 'POST_TRANSITION']
    
    if len(pre_transition) > 0 and len(post_transition) > 0:
        print(f"Pre-transition signals: {len(pre_transition)}")
        print(f"  Avg continuation probability: {pre_transition['continuation_prob'].mean():.2f}")
        print(f"  Direction distribution: {pre_transition['direction'].value_counts().to_dict()}")
        
        print(f"\nPost-transition signals: {len(post_transition)}")
        print(f"  Avg continuation probability: {post_transition['continuation_prob'].mean():.2f}")
        print(f"  Direction distribution: {post_transition['direction'].value_counts().to_dict()}")
        
        # Check if direction changed appropriately
        pre_long_pct = (pre_transition['direction'] == 'LONG').sum() / len(pre_transition) * 100
        post_long_pct = (post_transition['direction'] == 'LONG').sum() / len(post_transition) * 100
        
        print(f"\nLONG signal percentage:")
        print(f"  Pre-transition: {pre_long_pct:.1f}%")
        print(f"  Post-transition: {post_long_pct:.1f}%")
        
        if most_recent['from_regime'] == 'BULLISH' and most_recent['to_regime'] == 'BEARISH':
            if post_long_pct > 50:
                print(f"  WARNING: System still generating {post_long_pct:.1f}% LONG signals after BULLISH->BEARISH transition")
                print(f"  This suggests potential stale macro state - system not adapting to new regime")
    
else:
    print("No Market OS signals found around this transition period")

# Analyze a few more recent transitions for pattern
print("\n7. ANALYZING ADDITIONAL RECENT TRANSITIONS")
print("=" * 80)

for i in range(min(3, len(recent_transitions)-1)):
    transition = recent_transitions.iloc[-(i+2)]  # Skip the most recent one we already analyzed
    trans_date = transition['transition_date']
    
    print(f"\nTransition: {trans_date} ({transition['from_regime']} to {transition['to_regime']}, {transition['classified_type']})")
    
    signals = get_market_os_signals_around_date(trans_date, days_before=5, days_after=5)
    print(f"  Signals around transition: {len(signals)}")
    
    if len(signals) > 0:
        # Check direction alignment
        if transition['from_regime'] == 'BULLISH' and transition['to_regime'] == 'BEARISH':
            post_signals = signals[signals['date'] > trans_date]
            if len(post_signals) > 0:
                post_long_pct = (post_signals['direction'] == 'LONG').sum() / len(post_signals) * 100
                print(f"  Post-transition LONG signals: {post_long_pct:.1f}%")
                if post_long_pct > 50:
                    print(f"  WARNING: Continued LONG bias after BULLISH->BEARISH transition")

print("\n" + "=" * 80)
print("PHASE 3 COMPLETE")
print("=" * 80)