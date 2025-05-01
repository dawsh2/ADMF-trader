#!/usr/bin/env python3
"""
Independent validation script for MA Crossover strategy.
This script loads the same dataset and implements the same strategy 
as the main trading system to validate results independently.

FIXED VERSION: Removes PnL calculations and focuses on signal validation only.
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from datetime import datetime

def load_data(file_path):
    """Load OHLCV data from CSV file."""
    print(f"Loading data from {file_path}")
    df = pd.read_csv(file_path)
    
    # Convert timestamp/datetime to datetime if it's not already
    if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    elif 'datetime' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['datetime']):
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    # Set timestamp as index
    if 'timestamp' in df.columns:
        df.set_index('timestamp', inplace=True)
    elif 'datetime' in df.columns:
        df.set_index('datetime', inplace=True)
    
    # Standardize column names
    column_mapping = {
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }
    df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, inplace=True)
    
    print(f"Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    return df

def calculate_moving_averages(df, fast_window, slow_window):
    """Calculate moving averages on price data."""
    df = df.copy()
    df['fast_ma'] = df['close'].rolling(window=fast_window).mean()
    df['slow_ma'] = df['close'].rolling(window=slow_window).mean()
    return df

def generate_signals(df):
    """Generate signals based on MA crossover."""
    df = df.copy()
    # Generate crossover signals: 1 for buy (fast > slow), -1 for sell (fast < slow), 0 for no action
    df['signal'] = 0
    df.loc[df['fast_ma'] > df['slow_ma'], 'signal'] = 1
    df.loc[df['fast_ma'] < df['slow_ma'], 'signal'] = -1
    
    # Only register a signal when there's a change in direction
    df['signal_change'] = df['signal'].diff().fillna(0)
    df.loc[df['signal_change'] == 0, 'signal_change'] = 0
    
    return df

def extract_signals_from_log(log_file):
    """Extract trading signals from a backtest log file."""
    with open(log_file, 'r') as f:
        log_content = f.read()
    
    # Extract trading decisions from the log
    pattern = r"Trading decision: (BUY|SELL) .+ @ (\d+\.\d+), rule_id=(\w+)"
    matches = re.findall(pattern, log_content)
    
    signals = []
    for direction, price, rule_id in matches:
        # Extract timestamp from the log entry if available
        timestamp_match = re.search(r"timestamp=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", log_content)
        timestamp = datetime.now()
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        
        signal_value = 1 if direction == 'BUY' else -1
        signals.append({
            'log_timestamp': timestamp,  # Renamed to avoid ambiguity
            'signal': signal_value,
            'price': float(price),
            'rule_id': rule_id
        })
    
    return pd.DataFrame(signals)

def visualize_signals(df, title="Moving Average Crossover Signals"):
    """Visualize price, moving averages, and signals."""
    plt.figure(figsize=(14, 8))
    
    # Plot price and MAs
    plt.subplot(2, 1, 1)
    plt.plot(df.index, df['close'], label='Price', alpha=0.5)
    plt.plot(df.index, df['fast_ma'], label=f'Fast MA', color='green')
    plt.plot(df.index, df['slow_ma'], label=f'Slow MA', color='red')
    
    # Highlight buy/sell signals
    buy_signals = df[df['signal_change'] > 0]
    sell_signals = df[df['signal_change'] < 0]
    
    plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='Buy Signal')
    plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='Sell Signal')
    
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    
    # Plot signal changes
    plt.subplot(2, 1, 2)
    plt.plot(df.index, df['signal'], label='Position Direction')
    plt.title('Signal Direction')
    plt.xlabel('Date')
    plt.ylabel('Signal Value')
    plt.yticks([-1, 0, 1], ['Sell', 'Neutral', 'Buy'])
    plt.grid(True)
    
    plt.tight_layout()
    
    # Save plot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ma_crossover_validation_{fast_window}_{slow_window}_{timestamp}.png"
    plt.savefig(filename)
    print(f"Plot saved as {filename}")
    
    return filename

def compare_with_log(df, log_file):
    """Compare generated signals with trading decisions from a log file."""
    # Extract signals from the log file
    log_signals = extract_signals_from_log(log_file)
    
    # Extract signals from our dataframe
    signal_changes = df[df['signal_change'] != 0].copy()
    signal_changes['signal_timestamp'] = signal_changes.index  # Renamed to avoid ambiguity
    
    print(f"\nFound {len(log_signals)} trading decisions in the log file")
    print(f"Generated {len(signal_changes)} signals in our analysis")
    
    # Compare signal counts
    if len(log_signals) == len(signal_changes):
        print("✓ Signal count matches!")
    else:
        print(f"✗ Signal count mismatch: {len(log_signals)} in log vs {len(signal_changes)} generated")
    
    # Compare signal directions (if log signals are available)
    if not log_signals.empty and not signal_changes.empty:
        # Sort both by timestamp for comparison
        if 'log_timestamp' in log_signals.columns:
            log_signals = log_signals.sort_values('log_timestamp')
        
        # Reset index to avoid the ambiguity with timestamp being both index and column
        signal_changes = signal_changes.reset_index()
        
        # Compare directions
        log_directions = log_signals['signal'].values
        gen_directions = [int(0 if s == 0 else (1 if s > 0 else -1)) 
                         for s in signal_changes['signal_change'].values]
        
        # Use the minimum length for comparison
        min_len = min(len(log_directions), len(gen_directions))
        
        if min_len > 0:
            matching_directions = sum(
                log_directions[:min_len] == np.array(gen_directions[:min_len])
            )
            match_percentage = (matching_directions / min_len) * 100
            print(f"Direction match: {matching_directions}/{min_len} ({match_percentage:.2f}%)")
        
    return log_signals

def main():
    parser = argparse.ArgumentParser(description='Validate Moving Average Crossover Strategy')
    parser.add_argument('--data-file', required=True, help='CSV file with price data')
    parser.add_argument('--symbol', default='SYMBOL', help='Trading symbol')
    parser.add_argument('--fast-window', type=int, default=5, help='Fast MA window')
    parser.add_argument('--slow-window', type=int, default=15, help='Slow MA window')
    parser.add_argument('--compare-log', help='Compare with trade log file')
    parser.add_argument('--visualize', action='store_true', help='Visualize signals')
    
    args = parser.parse_args()
    
    # Store parameters for convenience
    global fast_window, slow_window
    fast_window = args.fast_window
    slow_window = args.slow_window
    
    print(f"Validating MA strategy with fast window={fast_window}, slow window={slow_window}")
    
    # Load and process data
    df = load_data(args.data_file)
    df = calculate_moving_averages(df, fast_window, slow_window)
    df = generate_signals(df)
    
    # Count signals
    signal_changes = df[df['signal_change'] != 0]
    buy_signals = df[df['signal_change'] > 0]
    sell_signals = df[df['signal_change'] < 0]
    
    print(f"\nGenerated {len(signal_changes)} signal changes:")
    print(f"- Buy signals: {len(buy_signals)}")
    print(f"- Sell signals: {len(sell_signals)}")
    
    # Compare with log if requested
    if args.compare_log:
        log_signals = compare_with_log(df, args.compare_log)
    
    # Visualize if requested
    if args.visualize:
        visualize_signals(df, f"{args.symbol} - Fast MA({fast_window}) / Slow MA({slow_window})")
    
    print("\nValidation complete!")

if __name__ == "__main__":
    main()
