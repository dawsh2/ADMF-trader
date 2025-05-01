#!/usr/bin/env python
"""
Script to analyze trading signals and corresponding trades.
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import csv

def analyze_trades(trades_file, log_file=None):
    """Analyze trading signals and corresponding trades."""
    # Load trades
    df = pd.read_csv(trades_file)
    print(f"Loaded {len(df)} trades from {trades_file}")
    
    # Print column information
    print("\nColumns in trades file:")
    for col in df.columns:
        print(f"  {col}")
    
    # Basic statistics
    print("\nTrade Statistics:")
    print(f"Total trades: {len(df)}")
    
    # Count entry and exit trades
    if 'direction' in df.columns:
        entries = df[df['direction'] == 'BUY'].shape[0]
        exits = df[df['direction'] == 'SELL'].shape[0]
        print(f"Entries (BUY): {entries}")
        print(f"Exits (SELL): {exits}")
    
    # Calculate round trips
    if 'position_id' in df.columns:
        positions = df['position_id'].nunique()
        print(f"Unique positions (round trips): {positions}")
    
    # Analyze timestamps
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        min_time = df['timestamp'].min()
        max_time = df['timestamp'].max()
        time_span = max_time - min_time
        print(f"Trading time span: {time_span}")
        print(f"Average trades per minute: {len(df) / (time_span.total_seconds() / 60):.2f}")
    
    # Analyze PnL
    if 'pnl' in df.columns:
        total_pnl = df['pnl'].sum()
        avg_pnl = df['pnl'].mean()
        win_count = (df['pnl'] > 0).sum()
        loss_count = (df['pnl'] < 0).sum()
        win_rate = win_count / len(df) if len(df) > 0 else 0
        
        print(f"Total PnL: ${total_pnl:.2f}")
        print(f"Average PnL per trade: ${avg_pnl:.2f}")
        print(f"Win rate: {win_rate:.2%}")
        print(f"Win/Loss count: {win_count}/{loss_count}")
    
    # Analyze signals from log (if provided)
    if log_file:
        signals = extract_signals_from_log(log_file)
        print(f"\nFound {len(signals)} signals in log file")
        
        # Compare with trades
        print("\nSignal vs Trade analysis:")
        print(f"Signals emitted: {len(signals)}")
        print(f"Trades executed: {len(df)}")
        
        # Check for time alignment
        if 'timestamp' in df.columns and signals:
            trade_times = set(df['timestamp'].dt.floor('min'))
            signal_times = set([s['timestamp'] for s in signals if 'timestamp' in s])
            common_times = trade_times.intersection(signal_times)
            
            print(f"Times with both signals and trades: {len(common_times)}")
            print(f"Times with signals but no trades: {len(signal_times - trade_times)}")
            print(f"Times with trades but no signals: {len(trade_times - signal_times)}")
            
            # Plot signal and trade counts over time
            if len(signals) > 0:
                plot_signals_vs_trades(signals, df)
    
    return df

def extract_signals_from_log(log_file):
    """Extract signal events from log file."""
    signals = []
    signal_pattern = "Signal #(\\d+) emitted for ([A-Za-z0-9]+): (-?\\d+)"
    buy_pattern = "BUY signal for ([A-Za-z0-9]+): fast MA \\(([0-9.]+)\\) crossed above slow MA \\(([0-9.]+)\\)"
    sell_pattern = "SELL signal for ([A-Za-z0-9]+): fast MA \\(([0-9.]+)\\) crossed below slow MA \\(([0-9.]+)\\)"
    
    import re
    
    with open(log_file, 'r') as f:
        for line in f:
            # Look for signal emission
            signal_match = re.search(signal_pattern, line)
            if signal_match:
                signal_id = int(signal_match.group(1))
                symbol = signal_match.group(2)
                direction = int(signal_match.group(3))
                
                # Extract timestamp from log line
                timestamp_match = re.search("(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})", line)
                timestamp = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S") if timestamp_match else None
                
                signals.append({
                    'id': signal_id,
                    'symbol': symbol,
                    'direction': direction,
                    'timestamp': timestamp
                })
            
            # Look for buy signal details
            buy_match = re.search(buy_pattern, line)
            if buy_match:
                symbol = buy_match.group(1)
                fast_ma = float(buy_match.group(2))
                slow_ma = float(buy_match.group(3))
                
                # Extract timestamp from log line
                timestamp_match = re.search("(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})", line)
                timestamp = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S") if timestamp_match else None
                
                # Update the last buy signal if we can find it
                for signal in reversed(signals):
                    if signal['symbol'] == symbol and signal['direction'] > 0 and 'fast_ma' not in signal:
                        signal['fast_ma'] = fast_ma
                        signal['slow_ma'] = slow_ma
                        if 'timestamp' not in signal or signal['timestamp'] is None:
                            signal['timestamp'] = timestamp
                        break
            
            # Look for sell signal details
            sell_match = re.search(sell_pattern, line)
            if sell_match:
                symbol = sell_match.group(1)
                fast_ma = float(sell_match.group(2))
                slow_ma = float(sell_match.group(3))
                
                # Extract timestamp from log line
                timestamp_match = re.search("(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})", line)
                timestamp = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S") if timestamp_match else None
                
                # Update the last sell signal if we can find it
                for signal in reversed(signals):
                    if signal['symbol'] == symbol and signal['direction'] < 0 and 'fast_ma' not in signal:
                        signal['fast_ma'] = fast_ma
                        signal['slow_ma'] = slow_ma
                        if 'timestamp' not in signal or signal['timestamp'] is None:
                            signal['timestamp'] = timestamp
                        break
    
    return signals

def plot_signals_vs_trades(signals, trades_df):
    """Plot signals vs trades over time."""
    if 'timestamp' not in trades_df.columns:
        return
    
    # Convert signals to DataFrame for easier processing
    signals_data = []
    for s in signals:
        if 'timestamp' in s and s['timestamp'] is not None:
            signals_data.append({
                'timestamp': s['timestamp'],
                'direction': 'BUY' if s['direction'] > 0 else 'SELL',
                'id': s['id']
            })
    
    if not signals_data:
        return
        
    signals_df = pd.DataFrame(signals_data)
    signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp'])
    
    # Group by minute
    signals_by_min = signals_df.groupby(signals_df['timestamp'].dt.floor('min')).size()
    trades_by_min = trades_df.groupby(trades_df['timestamp'].dt.floor('min')).size()
    
    # Combine data
    all_minutes = signals_by_min.index.union(trades_by_min.index).sort_values()
    combined = pd.DataFrame(index=all_minutes)
    combined['signals'] = signals_by_min
    combined['trades'] = trades_by_min
    combined = combined.fillna(0)
    
    # Plot
    plt.figure(figsize=(15, 8))
    plt.plot(combined.index, combined['signals'], 'r-', label='Signals')
    plt.plot(combined.index, combined['trades'], 'b-', label='Trades')
    plt.title('Signals vs Trades Over Time')
    plt.xlabel('Time')
    plt.ylabel('Count')
    plt.legend()
    plt.grid(True)
    
    # Add annotations for large discrepancies
    for idx, row in combined.iterrows():
        diff = abs(row['signals'] - row['trades'])
        if diff > 5:  # Only annotate significant differences
            plt.annotate(f'Diff: {diff}', 
                        (idx, max(row['signals'], row['trades'])),
                        textcoords="offset points",
                        xytext=(0,10),
                        ha='center')
    
    # Save plot
    plt.savefig('signals_vs_trades.png')
    print("\nPlot saved to signals_vs_trades.png")
    
    # Get signal statistics by direction
    buy_signals = signals_df[signals_df['direction'] == 'BUY'].shape[0]
    sell_signals = signals_df[signals_df['direction'] == 'SELL'].shape[0]
    print(f"BUY signals: {buy_signals}")
    print(f"SELL signals: {sell_signals}")
    
    # Calculate ratio
    buy_trades = trades_df[trades_df['direction'] == 'BUY'].shape[0]
    sell_trades = trades_df[trades_df['direction'] == 'SELL'].shape[0]
    print(f"BUY trades: {buy_trades}")
    print(f"SELL trades: {sell_trades}")
    
    # Calculate trades per signal
    trades_per_buy_signal = buy_trades / buy_signals if buy_signals > 0 else float('inf')
    trades_per_sell_signal = sell_trades / sell_signals if sell_signals > 0 else float('inf')
    print(f"Trades per BUY signal: {trades_per_buy_signal:.2f}")
    print(f"Trades per SELL signal: {trades_per_sell_signal:.2f}")

def main():
    parser = argparse.ArgumentParser(description="Analyze trading signals and trades")
    parser.add_argument("--trades", default="./results/head_test/trades_20250429_151614.csv", help="Path to trades CSV file")
    parser.add_argument("--log", default="./results/head_test/head_test.log", help="Path to log file")
    parser.add_argument("--plot", action="store_true", help="Generate plots")
    args = parser.parse_args()
    
    if not os.path.exists(args.trades):
        print(f"Trades file not found: {args.trades}")
        return False
    
    analyze_trades(args.trades, args.log if os.path.exists(args.log) else None)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
