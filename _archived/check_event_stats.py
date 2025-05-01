#!/usr/bin/env python
"""
Simple script to check event statistics after a backtest run.
"""
import sys
import logging
import argparse
import glob
import os
import re

def extract_event_counts(log_file):
    """Extract event counts from the log file."""
    event_counts = {
        'BAR': 0,
        'SIGNAL': 0,
        'ORDER': 0,
        'FILL': 0
    }
    
    bar_received_pattern = re.compile(r"Received bar event")
    signal_generated_pattern = re.compile(r"(BUY|SELL) signal for")
    signal_emitted_pattern = re.compile(r"Signal #\d+ emitted for")
    order_created_pattern = re.compile(r"Creating (BUY|SELL) order")
    fill_created_pattern = re.compile(r"Fill event for")
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if bar_received_pattern.search(line):
                    event_counts['BAR'] += 1
                elif signal_generated_pattern.search(line):
                    event_counts['SIGNAL'] += 1
                elif signal_emitted_pattern.search(line):
                    event_counts['SIGNAL EMITTED'] = event_counts.get('SIGNAL EMITTED', 0) + 1
                elif order_created_pattern.search(line):
                    event_counts['ORDER'] += 1
                elif fill_created_pattern.search(line):
                    event_counts['FILL'] += 1
    except Exception as e:
        print(f"Error reading log file: {e}")
        return {}
    
    return event_counts

def find_signal_events(log_file):
    """Find all signal events in the log file."""
    signal_events = []
    signal_pattern = re.compile(r"(BUY|SELL) signal for ([A-Za-z0-9]+): fast MA \(([0-9.]+)\) crossed (above|below) slow MA \(([0-9.]+)\), crossover: ([0-9.]+%)")
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                match = signal_pattern.search(line)
                if match:
                    direction, symbol, fast_ma, cross_direction, slow_ma, crossover_pct = match.groups()
                    signal_events.append({
                        'direction': direction,
                        'symbol': symbol,
                        'fast_ma': float(fast_ma),
                        'slow_ma': float(slow_ma),
                        'cross_direction': cross_direction,
                        'crossover_pct': crossover_pct,
                        'line': line.strip()
                    })
    except Exception as e:
        print(f"Error searching for signal events: {e}")
        return []
    
    return signal_events

def find_ma_calculations(log_file):
    """Find all MA calculations in the log file."""
    ma_logs = []
    ma_pattern = re.compile(r"Symbol: ([A-Za-z0-9]+), Fast MA: ([0-9.]+), Slow MA: ([0-9.]+), Prev Fast: ([0-9.]+), Prev Slow: ([0-9.]+), Diff: ([0-9.-]+), Prev Diff: ([0-9.-]+)")
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                match = ma_pattern.search(line)
                if match:
                    symbol, fast_ma, slow_ma, prev_fast, prev_slow, diff, prev_diff = match.groups()
                    ma_logs.append({
                        'symbol': symbol,
                        'fast_ma': float(fast_ma),
                        'slow_ma': float(slow_ma),
                        'prev_fast': float(prev_fast),
                        'prev_slow': float(prev_slow),
                        'diff': float(diff),
                        'prev_diff': float(prev_diff),
                        'line': line.strip()
                    })
    except Exception as e:
        print(f"Error searching for MA calculations: {e}")
        return []
    
    return ma_logs

def find_bar_events(log_file):
    """Find bar events in the log file."""
    bar_events = []
    bar_pattern = re.compile(r"Bar data: symbol=([A-Za-z0-9]+), price=([0-9.]+), timestamp=(.+)")
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                match = bar_pattern.search(line)
                if match:
                    symbol, price, timestamp = match.groups()
                    bar_events.append({
                        'symbol': symbol,
                        'price': float(price),
                        'timestamp': timestamp,
                        'line': line.strip()
                    })
    except Exception as e:
        print(f"Error searching for bar events: {e}")
        return []
    
    return bar_events

def find_latest_log_file(output_dir):
    """Find the latest log file in the output directory."""
    log_files = glob.glob(os.path.join(output_dir, "*.log"))
    if not log_files:
        return None
    return max(log_files, key=os.path.getmtime)

def main():
    parser = argparse.ArgumentParser(description="Check event statistics after a backtest run")
    parser.add_argument("--log-file", help="Path to log file")
    parser.add_argument("--output-dir", default="./results/head_test", help="Output directory for logs")
    args = parser.parse_args()
    
    # Find log file
    log_file = args.log_file
    if not log_file:
        log_file = find_latest_log_file(args.output_dir)
        if not log_file:
            print(f"No log file found in {args.output_dir}")
            return False
    
    print(f"Analyzing log file: {log_file}")
    
    # Extract event counts
    event_counts = extract_event_counts(log_file)
    if not event_counts:
        print("No event data found in log file")
        return False
    
    # Print event counts
    print("\nEvent Counts:")
    for event_type, count in event_counts.items():
        print(f"  {event_type}: {count}")
    
    # Find signal events
    signal_events = find_signal_events(log_file)
    print(f"\nFound {len(signal_events)} signal events:")
    for i, event in enumerate(signal_events[:10]):  # Show first 10
        print(f"  {i+1}. {event['direction']} signal for {event['symbol']}, "
              f"fast MA: {event['fast_ma']:.2f}, slow MA: {event['slow_ma']:.2f}, "
              f"crossover: {event['crossover_pct']}")
    
    if len(signal_events) > 10:
        print(f"  ... and {len(signal_events) - 10} more")
    
    # Find MA calculations - just show start, middle, and end to avoid huge output
    ma_logs = find_ma_calculations(log_file)
    print(f"\nFound {len(ma_logs)} MA calculations")
    
    if ma_logs:
        # Show first few
        print("\nFirst few MA calculations:")
        for ma in ma_logs[:3]:
            print(f"  Symbol: {ma['symbol']}, "
                  f"Fast MA: {ma['fast_ma']:.2f}, Slow MA: {ma['slow_ma']:.2f}, "
                  f"Diff: {ma['diff']:.4f}, Prev Diff: {ma['prev_diff']:.4f}")
        
        # Show middle few
        if len(ma_logs) > 6:
            mid_idx = len(ma_logs) // 2
            print("\nMiddle MA calculations:")
            for ma in ma_logs[mid_idx:mid_idx+3]:
                print(f"  Symbol: {ma['symbol']}, "
                      f"Fast MA: {ma['fast_ma']:.2f}, Slow MA: {ma['slow_ma']:.2f}, "
                      f"Diff: {ma['diff']:.4f}, Prev Diff: {ma['prev_diff']:.4f}")
        
        # Show last few
        if len(ma_logs) > 3:
            print("\nLast few MA calculations:")
            for ma in ma_logs[-3:]:
                print(f"  Symbol: {ma['symbol']}, "
                      f"Fast MA: {ma['fast_ma']:.2f}, Slow MA: {ma['slow_ma']:.2f}, "
                      f"Diff: {ma['diff']:.4f}, Prev Diff: {ma['prev_diff']:.4f}")
    
    # Find potential crossover points
    if len(ma_logs) > 1:
        print("\nAnalyzing potential crossover points...")
        crossover_points = []
        
        for i in range(1, len(ma_logs)):
            prev = ma_logs[i-1]
            curr = ma_logs[i]
            
            # Check for zero crossing in diff - indicator of MA crossover
            if (prev['diff'] <= 0 and curr['diff'] > 0) or (prev['diff'] >= 0 and curr['diff'] < 0):
                crossover_points.append({
                    'index': i,
                    'prev': prev,
                    'curr': curr,
                    'direction': 'BUY' if curr['diff'] > 0 else 'SELL'
                })
        
        print(f"\nFound {len(crossover_points)} potential crossover points:")
        for i, point in enumerate(crossover_points[:10]):  # Show first 10
            print(f"  {i+1}. {point['direction']} crossover at index {point['index']}, "
                  f"prev diff: {point['prev']['diff']:.4f}, "
                  f"curr diff: {point['curr']['diff']:.4f}")
        
        if len(crossover_points) > 10:
            print(f"  ... and {len(crossover_points) - 10} more")
            
        if signal_events:
            print(f"\nDiscrepancy: Found {len(crossover_points)} potential crossovers but only {len(signal_events)} signals")
            
    # Check for bar events
    bar_events = find_bar_events(log_file)
    print(f"\nFound {len(bar_events)} bar events logged")
    
    if bar_events:
        # Show first few
        print("\nFirst few bar events:")
        for event in bar_events[:3]:
            print(f"  Symbol: {event['symbol']}, "
                  f"Price: {event['price']:.2f}, "
                  f"Timestamp: {event['timestamp']}")
        
        # Show last few
        if len(bar_events) > 3:
            print("\nLast few bar events:")
            for event in bar_events[-3:]:
                print(f"  Symbol: {event['symbol']}, "
                      f"Price: {event['price']:.2f}, "
                      f"Timestamp: {event['timestamp']}")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
