"""
Phase 1: Historical DXY Regime Identification
Extract historical DXY regime data and identify transitions with dual timestamp system
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

def identify_regime_transitions(regime_df):
    """Identify DXY regime transitions with dual timestamp system"""
    transitions = []
    
    for i in range(1, len(regime_df)):
        current_row = regime_df.iloc[i]
        previous_row = regime_df.iloc[i-1]
        
        current_regime = current_row['dxy_regime']
        previous_regime = previous_row['dxy_regime']
        
        # Check for regime change
        if current_regime != previous_regime:
            transitions.append({
                'transition_date': current_row['date'],
                'from_regime': previous_regime,
                'to_regime': current_regime,
                'transition_type': f"{previous_regime}_TO_{current_regime}",
                'previous_duration_days': i,  # Days in previous regime
                'risk_sentiment_change': previous_row['risk_sentiment'] != current_row['risk_sentiment']
            })
    
    return transitions

def classify_transition_type(transition, price_data=None):
    """
    Classify transition type based on duration and characteristics
    Type 1: Noise reversal (brief, returns to original regime)
    Type 2: Gradual transition (progressive change over sessions)
    Type 3: Abrupt transition (rapid, event-driven)
    Type 4: Structural transition (new persistent regime)
    """
    # This is a preliminary classification - will be refined with price data analysis
    duration = transition['previous_duration_days']
    
    # Focus on direct BULLISH/BEARISH transitions for this research
    # Filter out CONSOLIDATING transitions as they are intermediate states
    if 'CONSOLIDATING' in transition['from_regime'] or 'CONSOLIDATING' in transition['to_regime']:
        return "INTERMEDIATE_CONSOLIDATION"
    
    if duration <= 3:
        return "TYPE_1_NOISE_REVERSAL"
    elif duration <= 10:
        return "TYPE_2_GRADUAL_TRANSITION"
    elif duration <= 20:
        return "TYPE_3_ABRUPT_TRANSITION"
    else:
        return "TYPE_4_STRUCTURAL_TRANSITION"

print("=" * 80)
print("PHASE 1: HISTORICAL DXY REGIME IDENTIFICATION")
print("=" * 80)

# Step 1: Extract historical DXY regimes
print("\n1. EXTRACTING HISTORICAL DXY REGIMES")
print("=" * 80)
regime_df = extract_historical_dxy_regimes()

print(f"Total historical records: {len(regime_df)}")
print(f"Date range: {regime_df['date'].min()} to {regime_df['date'].max()}")

print("\nRegime distribution:")
print(regime_df['dxy_regime'].value_counts())

print("\nRecent regimes (last 10):")
print(regime_df.tail(10)[['date', 'dxy_regime', 'risk_sentiment']].to_string(index=False))

# Step 2: Identify regime transitions
print("\n2. IDENTIFYING REGIME TRANSITIONS")
print("=" * 80)
transitions = identify_regime_transitions(regime_df)

print(f"Total regime transitions identified: {len(transitions)}")

if len(transitions) > 0:
    print("\nTransition breakdown:")
    transition_types = [t['transition_type'] for t in transitions]
    from collections import Counter
    for trans_type, count in Counter(transition_types).items():
        print(f"  {trans_type}: {count}")
    
    # Focus on direct BULLISH/BEARISH transitions for this research
    direct_transitions = [t for t in transitions if 
                        ('CONSOLIDATING' not in t['from_regime'] and 'CONSOLIDATING' not in t['to_regime'])]
    
    print(f"\nDirect BULLISH/BEARISH transitions (research focus): {len(direct_transitions)}")
    print("\nDirect transitions:")
    for i, trans in enumerate(direct_transitions, 1):
        print(f"{i}. {trans['transition_date']}: {trans['from_regime']} to {trans['to_regime']} (duration: {trans['previous_duration_days']} days)")
    
    # Use direct transitions for the rest of the analysis
    transitions = direct_transitions

if len(transitions) > 0:
    # Step 3: Get price context
    print("\n3. GETTING PRICE CONTEXT FOR T0 IDENTIFICATION")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    transitions_with_prices = []
    
    for transition in transitions:
        transition_date = transition['transition_date']
        
        # Get price data for window around transition (7 days before, 7 days after)
        start_date = (pd.to_datetime(transition_date) - timedelta(days=10)).strftime('%Y-%m-%d')
        end_date = (pd.to_datetime(transition_date) + timedelta(days=10)).strftime('%Y-%m-%d')
        
        # Try to get DXY price data from price_cache
        query = f"""
        SELECT date, open, high, low, close
        FROM price_cache
        WHERE instrument = 'DXY'
        AND date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY date ASC
        """
        
        try:
            price_df = pd.read_sql_query(query, conn)
            transition['price_data'] = price_df if len(price_df) > 0 else None
        except Exception as e:
            transition['price_data'] = None
        
        transitions_with_prices.append(transition)
    
    conn.close()
    
    transitions_with_price_data = [t for t in transitions_with_prices if t['price_data'] is not None]
    print(f"Transitions with price data available: {len(transitions_with_price_data)}")
    
    # Step 4: Apply transition taxonomy
    print("\n4. APPLYING TRANSITION TAXONOMY")
    print("=" * 80)
    
    for transition in transitions_with_prices:
        transition_type = classify_transition_type(transition, transition.get('price_data'))
        transition['classified_type'] = transition_type
    
    print("Transition classification:")
    from collections import Counter
    classified_types = [t['classified_type'] for t in transitions_with_prices]
    for trans_type, count in Counter(classified_types).items():
        print(f"  {trans_type}: {count}")
    
    # Step 5: Save results
    print("\n5. SAVING TRANSITION CATALOG")
    print("=" * 80)
    
    # Create detailed transition catalog
    transition_catalog = []
    for transition in transitions_with_prices:
        catalog_entry = {
            'transition_date': transition['transition_date'],
            'from_regime': transition['from_regime'],
            'to_regime': transition['to_regime'],
            'transition_type': transition['transition_type'],
            'previous_duration_days': transition['previous_duration_days'],
            'classified_type': transition['classified_type'],
            'risk_sentiment_change': transition['risk_sentiment_change'],
            'has_price_data': transition['price_data'] is not None
        }
        transition_catalog.append(catalog_entry)
    
    catalog_df = pd.DataFrame(transition_catalog)
    catalog_file = r"C:\Market-OS\transition_catalog.csv"
    catalog_df.to_csv(catalog_file, index=False)
    print(f"Transition catalog saved to: {catalog_file}")
    
    print("\nTransition catalog summary:")
    print(catalog_df.to_string(index=False))
else:
    print("No direct BULLISH/BEARISH transitions found in the data.")

print("\n" + "=" * 80)
print("PHASE 1 COMPLETE")
print("=" * 80)