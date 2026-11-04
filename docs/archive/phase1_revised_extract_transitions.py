"""
Phase 1 (Revised): Historical DXY Regime Identification
Include CONSOLIDATING transitions as intermediate states for adequate sample size
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = r"C:\Market-OS\backend\market_os.db"

def extract_historical_dxy_regimes():
    """Extract all historical DXY regime data"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT date, dxy_regime, risk_sentiment, macro_summary
    FROM daily_market_regimes
    ORDER BY date ASC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

def identify_effective_regime_changes(regime_df):
    """
    Identify effective regime changes including CONSOLIDATING as intermediate states
    BEARISH -> CONSOLIDATING -> BULLISH = Effective BEARISH -> BULLISH transition
    """
    effective_transitions = []
    
    # Track the last non-consolidating regime
    last_non_consolidating = None
    last_non_consolidating_date = None
    
    for i, row in regime_df.iterrows():
        current_regime = row['dxy_regime']
        current_date = row['date']
        
        # Initialize first non-consolidating regime
        if last_non_consolidating is None and current_regime != 'CONSOLIDATING':
            last_non_consolidating = current_regime
            last_non_consolidating_date = current_date
            continue
        
        # Detect effective regime change
        if current_regime != 'CONSOLIDATING' and current_regime != last_non_consolidating:
            # This is an effective regime change
            duration_days = (pd.to_datetime(current_date) - pd.to_datetime(last_non_consolidating_date)).days
            
            effective_transitions.append({
                'transition_date': current_date,
                'from_regime': last_non_consolidating,
                'to_regime': current_regime,
                'transition_type': f"{last_non_consolidating}_TO_{current_regime}",
                'previous_duration_days': duration_days,
                'intermediate_consolidating': True,
                'risk_sentiment_change': True  # Will be calculated more precisely
            })
            
            last_non_consolidating = current_regime
            last_non_consolidating_date = current_date
        
        # Update when we enter/exit consolidating
        elif current_regime != 'CONSOLIDATING':
            if last_non_consolidating != current_regime:
                last_non_consolidating = current_regime
                last_non_consolidating_date = current_date
    
    return effective_transitions

def classify_transition_type_revised(transition):
    """
    Revised classification for effective transitions
    """
    duration = transition['previous_duration_days']
    
    if duration <= 7:
        return "TYPE_1_NOISE_REVERSAL"
    elif duration <= 30:
        return "TYPE_2_GRADUAL_TRANSITION"
    elif duration <= 90:
        return "TYPE_3_ABRUPT_TRANSITION"
    else:
        return "TYPE_4_STRUCTURAL_TRANSITION"

print("=" * 80)
print("PHASE 1 (REVISED): EFFECTIVE REGIME CHANGE IDENTIFICATION")
print("Including CONSOLIDATING as intermediate states")
print("=" * 80)

# Step 1: Extract historical DXY regimes
print("\n1. EXTRACTING HISTORICAL DXY REGIMES")
print("=" * 80)
regime_df = extract_historical_dxy_regimes()

print(f"Total historical records: {len(regime_df)}")
print(f"Date range: {regime_df['date'].min()} to {regime_df['date'].max()}")

print("\nRegime distribution:")
print(regime_df['dxy_regime'].value_counts())

# Step 2: Identify effective regime changes
print("\n2. IDENTIFYING EFFECTIVE REGIME CHANGES")
print("=" * 80)
effective_transitions = identify_effective_regime_changes(regime_df)

print(f"Total effective regime changes identified: {len(effective_transitions)}")

if len(effective_transitions) > 0:
    print("\nEffective transition breakdown:")
    transition_types = [t['transition_type'] for t in effective_transitions]
    from collections import Counter
    for trans_type, count in Counter(transition_types).items():
        print(f"  {trans_type}: {count}")
    
    print("\nAll effective transitions:")
    for i, trans in enumerate(effective_transitions, 1):
        print(f"{i}. {trans['transition_date']}: {trans['from_regime']} to {trans['to_regime']} (duration: {trans['previous_duration_days']} days)")
    
    # Step 3: Apply revised transition taxonomy
    print("\n3. APPLYING REVISED TRANSITION TAXONOMY")
    print("=" * 80)
    
    for transition in effective_transitions:
        transition_type = classify_transition_type_revised(transition)
        transition['classified_type'] = transition_type
    
    print("Transition classification:")
    from collections import Counter
    classified_types = [t['classified_type'] for t in effective_transitions]
    for trans_type, count in Counter(classified_types).items():
        print(f"  {trans_type}: {count}")
    
    # Step 4: Focus on recent transitions (2025-2026)
    print("\n4. RECENT TRANSITIONS (2025-2026)")
    print("=" * 80)
    
    recent_transitions = [t for t in effective_transitions if t['transition_date'] >= '2025-01-01']
    print(f"Recent transitions: {len(recent_transitions)}")
    
    for i, trans in enumerate(recent_transitions, 1):
        print(f"{i}. {trans['transition_date']}: {trans['from_regime']} to {trans['to_regime']} (duration: {trans['previous_duration_days']} days, type: {trans['classified_type']})")
    
    # Step 5: Save results
    print("\n5. SAVING REVISED TRANSITION CATALOG")
    print("=" * 80)
    
    transition_catalog = []
    for transition in effective_transitions:
        catalog_entry = {
            'transition_date': transition['transition_date'],
            'from_regime': transition['from_regime'],
            'to_regime': transition['to_regime'],
            'transition_type': transition['transition_type'],
            'previous_duration_days': transition['previous_duration_days'],
            'classified_type': transition['classified_type'],
            'intermediate_consolidating': transition['intermediate_consolidating']
        }
        transition_catalog.append(catalog_entry)
    
    catalog_df = pd.DataFrame(transition_catalog)
    catalog_file = r"C:\Market-OS\effective_transition_catalog.csv"
    catalog_df.to_csv(catalog_file, index=False)
    print(f"Effective transition catalog saved to: {catalog_file}")
    
    print("\nEffective transition catalog summary:")
    print(catalog_df.to_string(index=False))
    
else:
    print("No effective regime changes found in the data.")

print("\n" + "=" * 80)
print("PHASE 1 (REVISED) COMPLETE")
print("=" * 80)