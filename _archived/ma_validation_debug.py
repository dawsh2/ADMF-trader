#!/usr/bin/env python3
"""
Debug-focused validation script for MA Crossover strategy.
This script aims to identify exactly where the original system generates signals
but our validation script doesn't.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os
import re

# Strategy parameters - matching the system configuration
FAST_WINDOW = 5
SLOW_WINDOW = 15
INITIAL_CAPITAL = 100000.0
POSITION_SIZE = 19  # Match the size in the logs
SLIPPAGE = 0.0

def load_data(file_path):
    """Load OHLCV data from CSV file."""
    print(f"Loading data from {file_path}")
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found!")
        return None
        
    df = pd.read_csv(file_path)
    
    # Convert timestamp to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    
    # Standardize column names to lowercase
    df.columns = [col.lower() for col in df.columns]
    
    print(f"Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    return df

def extract_system_signals(log_file):
    """
    Extract signal information from system logs.
    
    Args:
        log_file: Path to system log file
        
    Returns:
        list: List of signal details extracted from logs
    """
    signals = []
    ma_values = []
    
    if not os.path.exists(log_file):
        print(f"Error: Log file {log_file} not found!")
        return signals, ma_values
        
    with open(log_file, 'r') as f:
        content = f.read()
        
    # Extract signal emissions
    signal_pattern = r"Signal #(\d+) emitted for MINI: ([+-]?\d+)"
    for match in re.finditer(signal_pattern, content):
        signal_num = int(match.group(1))
        signal_val = int(match.group(2))
        signals.append((signal_num, signal_val))
    
    # Extract MA crossover data
    ma_pattern = r"(BUY|SELL) signal for MINI: fast MA \((\d+\.\d+)\) crossed (above|below) slow MA \((\d+\.\d+)\), crossover: (\d+\.\d+)%"
    for match in re.finditer(ma_pattern, content):
        direction = match.group(1)
        fast_ma = float(match.group(2))
        cross_type = match.group(3)
        slow_ma = float(match.group(4))
        crossover_pct = float(match.group(5))
        
        signal_value = 1 if direction == "BUY" else -1
        ma_values.append((direction, fast_ma, slow_ma, crossover_pct, signal_value))
    
    return signals, ma_values

def calculate_ma_original_method(prices, window):
    """
    Calculate moving averages using the original system's method.
    
    Args:
        prices: List of price values
        window: MA window size
        
    Returns:
        list: Moving averages calculated with the same method as the original system
    """
    ma_values = []
    
    for i in range(len(prices)):
        if i < window - 1:
            # Not enough data for full window, use available data
            if i > 0:
                ma_values.append(sum(prices[:i+1]) / (i+1))
            else:
                ma_values.append(prices[0])  # First value is just the price
        else:
            # Full window available
            ma_values.append(sum(prices[i-window+1:i+1]) / window)
    
    return ma_values

def calculate_signals(df):
    """Calculate moving averages and generate signals for comparison."""
    # Create price list for original MA calculation method
    prices = df['close'].tolist()
    
    # Calculate moving averages using the original method
    fast_ma_values = calculate_ma_original_method(prices, FAST_WINDOW)
    slow_ma_values = calculate_ma_original_method(prices, SLOW_WINDOW)
    
    # Add MA values to dataframe
    df['fast_ma'] = fast_ma_values
    df['slow_ma'] = slow_ma_values
    
    # Initialize signal columns
    df['signal'] = 0
    df['rule_id'] = None
    df['potential_signal'] = 0  # Flag for any near-crossover condition
    df['system_signal'] = 0     # Will be filled in with system signals
    df['delta_fast'] = 0.0      # Change in fast MA
    df['delta_slow'] = 0.0      # Change in slow MA
    df['ma_diff'] = 0.0         # Difference between fast and slow MA
    
    # Calculate additional metrics for every bar
    for i in range(1, len(df)):
        # Get previous and current values
        prev_fast = df['fast_ma'].iloc[i-1]
        prev_slow = df['slow_ma'].iloc[i-1]
        curr_fast = df['fast_ma'].iloc[i]
        curr_slow = df['slow_ma'].iloc[i]
        
        # Calculate deltas and differences
        df.at[df.index[i], 'delta_fast'] = curr_fast - prev_fast
        df.at[df.index[i], 'delta_slow'] = curr_slow - prev_slow
        df.at[df.index[i], 'ma_diff'] = curr_fast - curr_slow
    
    # Generate signals using our standard logic
    signal_count = 0
    
    for i in range(1, len(df)):
        # Get previous and current values
        prev_fast = df['fast_ma'].iloc[i-1]
        prev_slow = df['slow_ma'].iloc[i-1]
        curr_fast = df['fast_ma'].iloc[i]
        curr_slow = df['slow_ma'].iloc[i]
        
        timestamp = df.index[i]
        
        # Calculate difference percentage
        diff_pct = abs(curr_fast - curr_slow) / curr_slow * 100
        
        signal = 0
        rule_id = None
        
        # Buy signal: fast MA crosses above slow MA
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            signal = 1
            signal_count += 1
            rule_id = f"ma_crossover_{signal_count}"
            df.at[df.index[i], 'signal'] = signal
            df.at[df.index[i], 'rule_id'] = rule_id
        
        # Sell signal: fast MA crosses below slow MA
        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            signal = -1
            signal_count += 1
            rule_id = f"ma_crossover_{signal_count}"
            df.at[df.index[i], 'signal'] = signal
            df.at[df.index[i], 'rule_id'] = rule_id
            
        # CRITICAL: Check for "equality crossovers" (where the values are exactly equal)
        elif abs(prev_fast - prev_slow) < 0.0000001 and abs(curr_fast - curr_slow) < 0.0000001:
            # If we're at an equality point, check which direction we're moving
            if curr_fast > prev_fast:  # Moving up
                signal = 1
                signal_count += 1
                rule_id = f"ma_crossover_{signal_count}"
                df.at[df.index[i], 'signal'] = signal
                df.at[df.index[i], 'rule_id'] = rule_id
            elif curr_fast < prev_fast:  # Moving down
                signal = -1
                signal_count += 1
                rule_id = f"ma_crossover_{signal_count}"
                df.at[df.index[i], 'signal'] = signal
                df.at[df.index[i], 'rule_id'] = rule_id
                
        # Flag any potential near-crossover conditions
        if abs(curr_fast - curr_slow) < 0.01:
            df.at[df.index[i], 'potential_signal'] = 1
            
    # Count signals
    buy_signals = (df['signal'] == 1).sum()
    sell_signals = (df['signal'] == -1).sum()
    print(f"\nDetected signals in validation script: {buy_signals + sell_signals} ({buy_signals} buys, {sell_signals} sells)")
    
    return df, signal_count

def align_system_signals(df, system_signals, ma_values):
    """
    Align system signals with our calculated data points.
    
    Args:
        df: DataFrame with our calculated signals
        system_signals: List of system signal numbers and values
        ma_values: List of MA values from system log
        
    Returns:
        DataFrame with system signals aligned
    """
    print("\n=== ALIGNING SYSTEM SIGNALS WITH OUR DATA ===")
    
    # First, match the MA values from system to our dataframe
    matched_signals = 0
    ma_precision = 2  # Precision for MA value matching (try different values)
    
    for direction, fast_ma, slow_ma, crossover_pct, signal_value in ma_values:
        # Look for matching MA values in our dataframe
        for i in range(1, len(df)):
            our_fast = round(df['fast_ma'].iloc[i], ma_precision)
            our_slow = round(df['slow_ma'].iloc[i], ma_precision)
            
            # If we find a match in MA values
            if (abs(our_fast - fast_ma) < 0.01 and abs(our_slow - slow_ma) < 0.01):
                # Mark as system signal if not already marked
                if df['system_signal'].iloc[i] == 0:
                    df.at[df.index[i], 'system_signal'] = signal_value
                    matched_signals += 1
                    break
    
    # Count system signals we've matched
    system_buy_signals = (df['system_signal'] == 1).sum()
    system_sell_signals = (df['system_signal'] == -1).sum()
    
    print(f"Matched system signals: {matched_signals} out of {len(ma_values)}")
    print(f"System signals in our data: {system_buy_signals + system_sell_signals} "
          f"({system_buy_signals} buys, {system_sell_signals} sells)")
    
    return df

def analyze_signal_differences(df):
    """
    Analyze differences between our signals and system signals.
    
    Args:
        df: DataFrame with both our signals and system signals
        
    Returns:
        Analysis results
    """
    print("\n=== SIGNAL DIFFERENCE ANALYSIS ===")
    
    # Find where our script detected signals but system didn't
    our_signals_only = df[(df['signal'] != 0) & (df['system_signal'] == 0)]
    
    # Find where system detected signals but our script didn't
    system_signals_only = df[(df['signal'] == 0) & (df['system_signal'] != 0)]
    
    # Find agreement between system and our script
    matching_signals = df[(df['signal'] != 0) & (df['system_signal'] != 0)]
    
    print(f"Our signals only: {len(our_signals_only)}")
    print(f"System signals only: {len(system_signals_only)}")
    print(f"Matching signals: {len(matching_signals)}")
    
    # Analyze what's different about system-only signals
    if len(system_signals_only) > 0:
        print("\nAnalysis of system-only signals:")
        print("MA Diff | Fast Delta | Slow Delta | MA Diff % | Potential Signal Flag")
        print("-"*80)
        
        for idx, row in system_signals_only.iterrows():
            ma_diff = row['ma_diff']
            ma_diff_pct = abs(ma_diff) / row['slow_ma'] * 100 if row['slow_ma'] != 0 else 0
            
            print(f"{ma_diff:.6f} | {row['delta_fast']:.6f} | {row['delta_slow']:.6f} | "
                  f"{ma_diff_pct:.6f}% | {'YES' if row['potential_signal'] == 1 else 'NO'}")
    
    # Look for patterns in potential signals
    potential_signals = df[df['potential_signal'] == 1]
    potential_with_system = potential_signals[potential_signals['system_signal'] != 0]
    
    print(f"\nPotential signal conditions: {len(potential_signals)}")
    print(f"Potential conditions with system signals: {len(potential_with_system)}")
    
    # Check for cases where MAs are equal or very close
    near_equal_mas = df[abs(df['fast_ma'] - df['slow_ma']) < 0.0001]
    near_equal_with_system = near_equal_mas[near_equal_mas['system_signal'] != 0]
    
    print(f"Bars with nearly equal MAs: {len(near_equal_mas)}")
    print(f"Nearly equal MAs with system signals: {len(near_equal_with_system)}")
    
    # Look at sign changes in MA deltas
    sign_changes = df[(df['delta_fast'] * df['delta_slow'] < 0) | 
                      (df['delta_fast'] * df['delta_fast'].shift(1) < 0) |
                      (df['delta_slow'] * df['delta_slow'].shift(1) < 0)]
    sign_changes_with_system = sign_changes[sign_changes['system_signal'] != 0]
    
    print(f"Bars with MA delta sign changes: {len(sign_changes)}")
    print(f"MA delta sign changes with system signals: {len(sign_changes_with_system)}")
    
    return {
        'our_signals_only': our_signals_only,
        'system_signals_only': system_signals_only,
        'matching_signals': matching_signals,
        'potential_signals': potential_signals,
        'potential_with_system': potential_with_system,
        'near_equal_mas': near_equal_mas,
        'near_equal_with_system': near_equal_with_system,
        'sign_changes': sign_changes,
        'sign_changes_with_system': sign_changes_with_system
    }

def generate_detailed_log(df, analysis_results):
    """Generate detailed log file with bar-by-bar analysis."""
    log_file = 'detailed_signal_analysis.log'
    
    with open(log_file, 'w') as f:
        f.write("=== DETAILED BAR-BY-BAR ANALYSIS ===\n\n")
        f.write("Bar | Timestamp | Fast MA | Slow MA | MA Diff | Fast Delta | Slow Delta | Our Signal | System Signal\n")
        f.write("-"*100 + "\n")
        
        for i in range(1, len(df)):
            # Only log rows with signals or potential signals
            if (df['signal'].iloc[i] != 0 or df['system_signal'].iloc[i] != 0 or 
                df['potential_signal'].iloc[i] != 0):
                
                # Format the row
                f.write(f"{i:3d} | {df.index[i]} | {df['fast_ma'].iloc[i]:.6f} | {df['slow_ma'].iloc[i]:.6f} | "
                        f"{df['ma_diff'].iloc[i]:.6f} | {df['delta_fast'].iloc[i]:.6f} | {df['delta_slow'].iloc[i]:.6f} | "
                        f"{df['signal'].iloc[i]:+d} | {df['system_signal'].iloc[i]:+d}\n")
                        
        # Write detailed statistics
        f.write("\n\n=== SIGNAL STATISTICS ===\n")
        f.write(f"Our signals: {(df['signal'] != 0).sum()}\n")
        f.write(f"System signals: {(df['system_signal'] != 0).sum()}\n")
        f.write(f"Matching signals: {len(analysis_results['matching_signals'])}\n")
        f.write(f"Our signals only: {len(analysis_results['our_signals_only'])}\n")
        f.write(f"System signals only: {len(analysis_results['system_signals_only'])}\n")
        
        # Write hypotheses about missing signals
        f.write("\n\n=== HYPOTHESES FOR MISSING SIGNALS ===\n")
        
        # Analyze additional patterns in system-only signals
        system_only = analysis_results['system_signals_only']
        
        if len(system_only) > 0:
            # Check for patterns in MA relationships
            close_values = system_only[abs(system_only['ma_diff']) < 0.001]
            f.write(f"Very close MA values (<0.001 diff): {len(close_values)}\n")
            
            # Check for patterns in MA delta relationships
            opposite_deltas = system_only[system_only['delta_fast'] * system_only['delta_slow'] < 0]
            f.write(f"Opposite direction MA deltas: {len(opposite_deltas)}\n")
            
            # Check for zero-crossing in MA difference
            sign_changes = system_only[system_only['ma_diff'] * system_only['ma_diff'].shift(1) < 0]
            f.write(f"Sign change in MA difference: {len(sign_changes)}\n")
            
            # Check for patterns in absolute values (e.g., MAs are exactly equal)
            equal_values = system_only[abs(system_only['fast_ma'] - system_only['slow_ma']) < 0.00001]
            f.write(f"Exactly equal MA values: {len(equal_values)}\n")
    
    print(f"\nDetailed analysis saved to: {log_file}")
    return log_file

def main():
    """Main function."""
    print("\n" + "="*70)
    print("MA CROSSOVER SIGNAL DEBUG ANALYSIS")
    print("="*70)
    
    # Load data
    data_file = 'data/MINI_1min.csv'
    df = load_data(data_file)
    
    if df is None:
        print("Exiting due to data loading error.")
        return
    
    # Extract system signals from log
    system_log = 'out.txt'
    system_signals, ma_values = extract_system_signals(system_log)
    
    if not system_signals:
        print(f"No system signals found in log file: {system_log}")
        print("Please provide a log file with system signal information.")
        return
    
    print(f"Extracted {len(system_signals)} signal events from system log")
    print(f"Extracted {len(ma_values)} MA crossover events from system log")
    
    # Calculate our signals
    df, signal_count = calculate_signals(df)
    
    # Align system signals with our data
    df = align_system_signals(df, system_signals, ma_values)
    
    # Analyze signal differences
    analysis_results = analyze_signal_differences(df)
    
    # Generate detailed log with bar-by-bar analysis
    log_file = generate_detailed_log(df, analysis_results)
    
    # Final output
    print("\n=== ARCHITECTURAL SIGNAL ANALYSIS ===")
    print(f"System signal count (from log): {len(system_signals)}")
    print(f"Our signal count: {signal_count}")
    print(f"Matched signals: {len(analysis_results['matching_signals'])}")
    print(f"System signals we didn't detect: {len(analysis_results['system_signals_only'])}")
    print(f"Our signals not in system: {len(analysis_results['our_signals_only'])}")
    
    print("\nHypotheses for system signals we didn't detect:")
    print("1. System may be detecting sub-crossover conditions where MAs are close but not crossing")
    print("2. System might be generating signals on MA delta sign changes")
    print("3. System could be emitting multiple signals for the same condition")
    print("4. Event bus architecture might be counting signals differently")
    print("5. Precision differences in floating-point calculations")
    
    print(f"\nDetailed analysis with specific examples saved to: {log_file}")

if __name__ == "__main__":
    main()
