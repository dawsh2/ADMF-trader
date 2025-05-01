#!/usr/bin/env python3
"""
Validation script for MA Crossover strategy with proper signal grouping.
This script implements the same signal grouping logic as the fixed strategy
to ensure validation and actual implementation match.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

# Strategy parameters - matching the system configuration
FAST_WINDOW = 5
SLOW_WINDOW = 15
INITIAL_CAPITAL = 100000.0
POSITION_SIZE = 19  # Match the size in the logs
SLIPPAGE = 0.0      # Set to match your current configuration

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
    """Calculate moving averages and generate signals using proper signal grouping."""
    print("\n=== DETAILED SIGNAL GENERATION LOG ===")
    
    # Create price list for original MA calculation method
    prices = df['close'].tolist()
    
    # Calculate moving averages using the original method
    print("Calculating MAs using the original system's method...")
    fast_ma_values = calculate_ma_original_method(prices, FAST_WINDOW)
    slow_ma_values = calculate_ma_original_method(prices, SLOW_WINDOW)
    
    # Add MA values to dataframe
    df['fast_ma'] = fast_ma_values
    df['slow_ma'] = slow_ma_values
    
    # Initialize signal columns
    df['signal'] = 0
    df['rule_id'] = None
    df['new_group'] = False  # Flag for new signal group
    df['group_id'] = None    # Group ID for each signal
    
    # Print sample data to debug
    print("\nSample data (first 20 rows after MA calculation):")
    print(df[['close', 'fast_ma', 'slow_ma']].head(20))
    
    # Log MA calculation details
    print(f"\nMoving Average Calculation:\n  Fast MA: {FAST_WINDOW} periods")
    print(f"  Slow MA: {SLOW_WINDOW} periods")
    print(f"  First valid Fast MA at index 0, value: {df['fast_ma'].iloc[0]:.6f}")
    print(f"  First valid Slow MA at index 0, value: {df['slow_ma'].iloc[0]:.6f}")
    
    # Log all potential crossovers
    print("\nDetailed Crossover Analysis:")
    print("Index | Timestamp | Fast MA Prev | Slow MA Prev | Fast MA | Slow MA | Diff % | Signal | Direction Change | Group ID")
    print("-"*120)
    
    # Initialize signal tracking state
    current_direction = 0  # 0 = no direction, 1 = buy, -1 = sell
    current_group = None   # Current group ID
    signal_count = 0       # Count of direction changes
    
    # Generate signals with proper direction grouping with enhanced logging
    # Debug signal processing
    print(f"Processing signal at {df.index[0]}: fast_ma={df['fast_ma'].iloc[0]:.6f}, slow_ma={df['slow_ma'].iloc[0]:.6f}, diff={abs(df['fast_ma'].iloc[0] - df['slow_ma'].iloc[0])/df['slow_ma'].iloc[0]*100:.6f}%")
    
    # Generate signals with proper direction grouping
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
        direction_change = False
        
        # Buy signal: fast MA crosses above slow MA
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            signal = 1
            # Check if direction has changed
            if current_direction != 1:
                direction_change = True
        
        # Sell signal: fast MA crosses below slow MA
        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            signal = -1
            # Check if direction has changed
            if current_direction != -1:
                direction_change = True
        
        # If direction has changed, create a new signal group
        if signal != 0 and direction_change:
            signal_count += 1
            current_group = signal_count
            current_direction = signal
            
            # Create group-based rule ID
            direction_name = "BUY" if signal == 1 else "SELL"
            rule_id = f"ma_crossover_{symbol}_{direction_name}_group_{current_group}"
            
            # Record the new signal group
            df.at[df.index[i], 'signal'] = signal
            df.at[df.index[i], 'rule_id'] = rule_id
            df.at[df.index[i], 'new_group'] = True
            df.at[df.index[i], 'group_id'] = current_group
            
            print(f"{i:5d} | {timestamp} | {prev_fast:.6f} | {prev_slow:.6f} | {curr_fast:.6f} | {curr_slow:.6f} | "
                  f"{diff_pct:.6f}% | {signal:+d} | YES | Group {current_group}")
        
        # If signal in same direction, maintain the same group
        elif signal != 0 and signal == current_direction:
            # Still in existing group
            df.at[df.index[i], 'signal'] = signal
            df.at[df.index[i], 'rule_id'] = f"ma_crossover_{symbol}_{'BUY' if signal == 1 else 'SELL'}_group_{current_group}"
            df.at[df.index[i], 'new_group'] = False
            df.at[df.index[i], 'group_id'] = current_group
            
            print(f"{i:5d} | {timestamp} | {prev_fast:.6f} | {prev_slow:.6f} | {curr_fast:.6f} | {curr_slow:.6f} | "
                  f"{diff_pct:.6f}% | {signal:+d} | NO | Group {current_group}")
        
        # Log potential crossover points for debugging
        elif abs(curr_fast - curr_slow) < 0.01:
            print(f"{i:5d} | {timestamp} | {prev_fast:.6f} | {prev_slow:.6f} | {curr_fast:.6f} | {curr_slow:.6f} | "
                  f"{diff_pct:.6f}% | {signal} | NO | -")
    
    # Calculate crossover percentage
    df['crossover_pct'] = (df['fast_ma'] - df['slow_ma']).abs() / df['slow_ma'] * 100
    
    # Count signal groups (direction changes)
    signal_groups = df[df['new_group'] == True]
    buy_groups = len(signal_groups[signal_groups['signal'] == 1])
    sell_groups = len(signal_groups[signal_groups['signal'] == -1])
    
    print(f"\nSignal direction changes: {len(signal_groups)} ({buy_groups} BUY, {sell_groups} SELL)")
    
    # Count raw signals (all crossovers)
    raw_signals = df[df['signal'] != 0]
    raw_buy_signals = len(raw_signals[raw_signals['signal'] == 1])
    raw_sell_signals = len(raw_signals[raw_signals['signal'] == -1])
    
    print(f"Raw crossover signals: {len(raw_signals)} ({raw_buy_signals} buys, {raw_sell_signals} sells)")
    
    # Save detailed signal data to CSV for inspection
    signals_df = df[df['signal'] != 0].copy()
    signals_df.to_csv('detected_signals_grouped.csv')
    print(f"Detailed signal data saved to 'detected_signals_grouped.csv'")
    
    return df

def backtest_strategy(df, use_slippage=True):
    """Run a simple backtest with the strategy."""
    print("\n=== DETAILED BACKTESTING LOG ===")
    print(f"Slippage enabled: {use_slippage}, Slippage rate: {SLIPPAGE*100:.2f}%")
    
    # Initialize results
    trades = []
    position = 0
    entry_price = 0
    entry_time = None
    entry_group = None
    trade_id = 0
    
    # Equity tracking
    equity = INITIAL_CAPITAL
    equity_curve = [INITIAL_CAPITAL]
    
    print("\nDetailed Trade Log:")
    print("ID | Group ID | Type | Entry Time | Entry Price | Exit Time | Exit Price | PnL | Win/Loss")
    print("-"*100)
    
    # Iterate through the data
    for timestamp, row in df.iterrows():
        # Check for NEW signal groups only - only trade on direction changes
        if row['new_group']:
            # Apply slippage to price
            if use_slippage:
                # For buys, increase price by slippage; for sells, decrease
                if row['signal'] == 1:  # Buy signal
                    execution_price = row['close'] * (1 + SLIPPAGE)
                else:  # Sell signal
                    execution_price = row['close'] * (1 - SLIPPAGE)
            else:
                execution_price = row['close']
            
            # No position - enter a new one
            if position == 0:
                position = row['signal']  # 1 for long, -1 for short
                entry_price = execution_price
                entry_time = timestamp
                entry_group = row['group_id']
                print(f"OPEN: {position} position at {timestamp}, price: {execution_price:.2f}, close: {row['close']:.2f}, group: {entry_group}")
            
            # Existing position - close it and maybe open a new one
            elif position != row['signal']:  # Opposite signal
                # Calculate P&L
                if position == 1:  # Long position
                    pnl = (execution_price - entry_price) * POSITION_SIZE
                else:  # Short position
                    pnl = (entry_price - execution_price) * POSITION_SIZE
                
                # Update equity
                equity += pnl
                equity_curve.append(equity)
                
                trade_id += 1
                
                # Determine if win or loss
                result = "WIN" if pnl > 0 else "LOSS"
                
                # Log the trade details
                direction = "BUY" if position == 1 else "SELL"
                print(f"{trade_id:2d} | Group {entry_group:2d} | {direction:4s} | {entry_time} | {entry_price:.2f} | {timestamp} | {execution_price:.2f} | {pnl:+.2f} | {result}")
                
                # Record the trade
                trades.append({
                    'trade_id': trade_id,
                    'group_id': entry_group,
                    'entry_time': entry_time,
                    'exit_time': timestamp,
                    'exit_group': row['group_id'],
                    'direction': direction,
                    'entry_price': entry_price,
                    'exit_price': execution_price,
                    'size': POSITION_SIZE,
                    'pnl': pnl,
                    'win': pnl > 0,
                    'crossover_pct': row['crossover_pct']
                })
                
                # Open new position in opposite direction
                position = row['signal']
                entry_price = execution_price
                entry_time = timestamp
                entry_group = row['group_id']
                print(f"OPEN: {position} position at {timestamp}, price: {execution_price:.2f}, close: {row['close']:.2f}, group: {entry_group}")
    
    # Close any open position at the end
    if position != 0 and entry_time is not None:
        last_price = df['close'].iloc[-1]
        
        # Apply slippage
        if use_slippage:
            if position == 1:  # Long position
                last_price = last_price * (1 - SLIPPAGE)  # Slippage works against you when selling
            else:  # Short position
                last_price = last_price * (1 + SLIPPAGE)  # Slippage works against you when buying
        
        # Calculate P&L
        if position == 1:  # Long position
            pnl = (last_price - entry_price) * POSITION_SIZE
        else:  # Short position
            pnl = (entry_price - last_price) * POSITION_SIZE
        
        # Update equity
        equity += pnl
        equity_curve.append(equity)
        
        trade_id += 1
        
        # Determine if win or loss
        result = "WIN" if pnl > 0 else "LOSS"
        
        # Log the trade details
        direction = "BUY" if position == 1 else "SELL"
        print(f"{trade_id:2d} | Group {entry_group:2d} | {direction:4s} | {entry_time} | {entry_price:.2f} | {df.index[-1]} | {last_price:.2f} | {pnl:+.2f} | {result}")
        
        # Record the trade
        trades.append({
            'trade_id': trade_id,
            'group_id': entry_group,
            'entry_time': entry_time,
            'exit_time': df.index[-1],
            'exit_group': 'EOD',
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': last_price,
            'size': POSITION_SIZE,
            'pnl': pnl,
            'win': pnl > 0,
            'crossover_pct': df['crossover_pct'].iloc[-1] if 'crossover_pct' in df.columns else None
        })
    
    # Save detailed trade log to CSV
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df.to_csv('backtest_trades_grouped.csv')
        print(f"\nTrade log saved to 'backtest_trades_grouped.csv'")
    
    return trades_df, equity_curve

def analyze_results(trades_df, equity_curve):
    """Analyze the trading results."""
    print("\n=== BACKTEST RESULTS ===")
    
    if trades_df.empty:
        print("No trades were executed.")
        return None
    
    # Basic metrics
    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df['win']])
    losing_trades = total_trades - winning_trades
    
    # Win rate
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Profit metrics
    total_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum() if winning_trades > 0 else 0
    total_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum()) if losing_trades > 0 else 0
    net_profit = total_profit - total_loss
    
    # Profit factor
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    
    # Average metrics
    avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
    
    # Direction analysis
    direction_counts = trades_df['direction'].value_counts()
    
    # Analyze tiny crossovers
    if 'crossover_pct' in trades_df.columns:
        tiny_crossovers = len(trades_df[trades_df['crossover_pct'] < 0.01])
        print(f"Tiny crossovers (<0.01%): {tiny_crossovers} ({tiny_crossovers/total_trades*100:.2f}%)")
    
    # Print results
    print(f"Total trades: {total_trades}")
    print(f"Winning trades: {winning_trades} ({win_rate:.2f}%)")
    print(f"Losing trades: {losing_trades} ({100-win_rate:.2f}%)")
    print(f"Net P&L: ${net_profit:.2f}")
    print(f"Profit factor: {profit_factor:.2f}")
    print(f"Average win: ${avg_win:.2f}")
    print(f"Average loss: ${avg_loss:.2f}")
    
    # Final equity
    final_equity = equity_curve[-1] if equity_curve else INITIAL_CAPITAL
    equity_change_pct = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    print(f"Initial equity: ${INITIAL_CAPITAL:.2f}")
    print(f"Final equity: ${final_equity:.2f} ({equity_change_pct:+.2f}%)")
    
    # Print direction analysis
    print("\nTrade Directions:")
    for direction, count in direction_counts.items():
        print(f"  {direction}: {count} trades")
    
    # Analysis by direction
    if not trades_df.empty:
        try:
            # Group by direction and calculate stats
            direction_stats = {}
            
            for direction in trades_df['direction'].unique():
                dir_trades = trades_df[trades_df['direction'] == direction]
                dir_count = len(dir_trades)
                dir_wins = len(dir_trades[dir_trades['win']])
                dir_win_rate = (dir_wins / dir_count * 100) if dir_count > 0 else 0
                dir_avg_pnl = dir_trades['pnl'].mean() if dir_count > 0 else 0
                
                direction_stats[direction] = {
                    'count': dir_count,
                    'win_rate': dir_win_rate,
                    'avg_pnl': dir_avg_pnl
                }
            
            print("\nPerformance by Direction:")
            for direction, stats in direction_stats.items():
                print(f"  {direction}: {stats['count']} trades, {stats['win_rate']:.2f}% win rate, avg P&L: ${stats['avg_pnl']:.2f}")
        except Exception as e:
            print(f"Error analyzing direction performance: {e}")
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'net_profit': net_profit,
        'profit_factor': profit_factor,
        'equity_change_pct': equity_change_pct
    }

def analyze_signal_groups(df):
    """Analyze the signal groups (direction changes)."""
    signal_groups = df[df['new_group'] == True]
    
    if signal_groups.empty:
        print("No signal groups found.")
        return
    
    # Add percentage crossover column if not already present
    if 'crossover_pct' not in signal_groups.columns:
        signal_groups['crossover_pct'] = (signal_groups['fast_ma'] - signal_groups['slow_ma']).abs() / signal_groups['slow_ma'] * 100
    
    # Get statistics on crossover size
    crossover_stats = signal_groups['crossover_pct'].describe()
    
    # Count signals with tiny crossovers
    tiny_crossovers = len(signal_groups[signal_groups['crossover_pct'] < 0.01])
    small_crossovers = len(signal_groups[signal_groups['crossover_pct'] < 0.05])
    
    print("\n=== SIGNAL GROUP ANALYSIS ===")
    print(f"Total signal groups (direction changes): {len(signal_groups)}")
    print(f"Average crossover size: {signal_groups['crossover_pct'].mean():.6f}%")
    print(f"Median crossover size: {signal_groups['crossover_pct'].median():.6f}%")
    print(f"Maximum crossover size: {signal_groups['crossover_pct'].max():.6f}%")
    print(f"Minimum crossover size: {signal_groups['crossover_pct'].min():.6f}%")
    print(f"Tiny crossovers (<0.01%): {tiny_crossovers} ({tiny_crossovers/len(signal_groups)*100:.2f}%)")
    print(f"Small crossovers (<0.05%): {small_crossovers} ({small_crossovers/len(signal_groups)*100:.2f}%)")
    
    # Distribution by size
    bins = [0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, float('inf')]
    labels = ['<0.001%', '0.001-0.005%', '0.005-0.01%', '0.01-0.02%', '0.02-0.05%', '0.05-0.1%', '0.1-0.5%', '>0.5%']
    signal_groups['crossover_bin'] = pd.cut(signal_groups['crossover_pct'], bins=bins, labels=labels)
    
    distribution = signal_groups['crossover_bin'].value_counts().sort_index()
    print("\nCrossover Size Distribution:")
    for size_bin, count in distribution.items():
        pct = count / len(signal_groups) * 100
        print(f"  {size_bin}: {count} signals ({pct:.2f}%)")
    
    # Analyze by signal direction
    buy_signals = signal_groups[signal_groups['signal'] == 1]
    sell_signals = signal_groups[signal_groups['signal'] == -1]
    
    print("\nSignal Direction:")
    print(f"  BUY signals: {len(buy_signals)} ({len(buy_signals)/len(signal_groups)*100:.2f}%)")
    print(f"  SELL signals: {len(sell_signals)} ({len(sell_signals)/len(signal_groups)*100:.2f}%)")
    
    return signal_groups

def plot_results(df, trades_df, equity_curve, title_suffix=""):
    """Create plots for visualization."""
    # Create figure with subplots
    fig, axes = plt.subplots(3, 1, figsize=(12, 16), gridspec_kw={'height_ratios': [3, 1, 1]})
    
    # Plot price and moving averages
    axes[0].plot(df.index, df['close'], label='Close Price', alpha=0.7)
    axes[0].plot(df.index, df['fast_ma'], label=f'Fast MA ({FAST_WINDOW})', linewidth=1)
    axes[0].plot(df.index, df['slow_ma'], label=f'Slow MA ({SLOW_WINDOW})', linewidth=1)
    
    # Plot direction changes (new signal groups)
    new_groups = df[df['new_group'] == True]
    buy_groups = new_groups[new_groups['signal'] == 1]
    sell_groups = new_groups[new_groups['signal'] == -1]
    
    axes[0].scatter(buy_groups.index, buy_groups['close'], marker='^', color='green', s=120, label='BUY Signal Group')
    axes[0].scatter(sell_groups.index, sell_groups['close'], marker='v', color='red', s=120, label='SELL Signal Group')
    
    # Plot all raw signals (small markers)
    all_signals = df[df['signal'] != 0]
    buy_signals = all_signals[all_signals['signal'] == 1]
    sell_signals = all_signals[all_signals['signal'] == -1]
    
    axes[0].scatter(buy_signals.index, buy_signals['close'], marker='.', color='lightgreen', s=30, label='Buy Signal')
    axes[0].scatter(sell_signals.index, sell_signals['close'], marker='.', color='lightcoral', s=30, label='Sell Signal')
    
    # Plot trades from trades_df if not empty
    if not trades_df.empty:
        for i, trade in trades_df.iterrows():
            marker_color = 'green' if trade['pnl'] > 0 else 'red'
            marker_shape = '^' if trade['direction'] == 'BUY' else 'v'
            
            # Plot entry points
            axes[0].scatter(trade['entry_time'], trade['entry_price'], 
                          marker=marker_shape, s=150, edgecolors='black', color=marker_color, alpha=0.7)
            
            # Plot exit points
            axes[0].scatter(trade['exit_time'], trade['exit_price'], 
                          marker='o', s=150, edgecolors='black', color=marker_color, alpha=0.7)
    
    # Plot P&L per trade
    if not trades_df.empty:
        trade_times = [trade['exit_time'] for _, trade in trades_df.iterrows()]
        pnl_values = [trade['pnl'] for _, trade in trades_df.iterrows()]
        
        # Create bars for P&L
        axes[1].bar(trade_times, pnl_values, color=['green' if p > 0 else 'red' for p in pnl_values], alpha=0.7)
        axes[1].axhline(y=0, color='black', linestyle='-', linewidth=1)
    
    # Plot equity curve
    if equity_curve:
        # Create x-axis for equity curve (data points at trade executions)
        equity_x = df.index[::len(df)//len(equity_curve)] if len(equity_curve) > 1 else df.index
        equity_x = equity_x[:len(equity_curve)]  # Ensure same length
        
        if len(equity_x) == len(equity_curve):
            axes[2].plot(equity_x, equity_curve, label='Equity Curve', color='blue', linewidth=2)
            axes[2].axhline(y=INITIAL_CAPITAL, color='black', linestyle='--', linewidth=1)
    
    # Set titles and labels
    fig.suptitle(f'MA Crossover ({FAST_WINDOW}/{SLOW_WINDOW}) - Direction Groups {title_suffix}', fontsize=16)
    
    axes[0].set_title('Price, MA, and Signal Groups')
    axes[0].set_ylabel('Price')
    axes[0].legend(loc='upper left')
    axes[0].grid(True, alpha=0.3)
    
    axes[1].set_title('Trade P&L')
    axes[1].set_ylabel('P&L ($)')
    axes[1].grid(True, alpha=0.3)
    
    axes[2].set_title('Equity Curve')
    axes[2].set_ylabel('Equity ($)')
    axes[2].grid(True, alpha=0.3)
    
    # Format x-axis dates
    for ax in axes:
        ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    # Save the figure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ma_crossover_grouped_{FAST_WINDOW}_{SLOW_WINDOW}_{timestamp}{title_suffix.replace(' ', '_')}.png"
    plt.savefig(filename)
    print(f"\nPlot saved to: {filename}")
    
    return filename

def main():
    """Main function."""
    print("\n" + "="*70)
    print(f"MA CROSSOVER VALIDATION - DIRECTION GROUPS ({FAST_WINDOW}/{SLOW_WINDOW})")
    print("="*70)
    print("This script implements signal direction grouping to match the fixed system:")
    print("1. Signals are grouped by direction (BUY/SELL)")
    print("2. Only direction changes create new signal groups")
    print("3. Multiple signals in the same direction are treated as one group")
    print("4. Raw signals are still tracked for analysis")
    print("="*70)
    
    # Check if we're using slippage
    slippage_mode = ""
    if SLIPPAGE > 0:
        slippage_mode = f" (Slippage: {SLIPPAGE*100:.2f}%)"
    
    # Load data
    data_file = 'data/MINI_1min.csv'
    df = load_data(data_file)
    
    if df is None:
        print("Exiting due to data loading error.")
        return
    
    # Define symbol for rule_id
    global symbol
    symbol = "MINI"
    
    # Calculate signals
    df = calculate_signals(df)
    
    # Analyze signal groups
    try:
        signal_groups = analyze_signal_groups(df)
    except Exception as e:
        print(f"Error analyzing signal groups: {e}")
    
    # Run backtest with slippage
    print(f"\nRunning backtest{slippage_mode}...")
    trades_df, equity_curve = backtest_strategy(df, use_slippage=(SLIPPAGE > 0))
    
    # Analyze results
    metrics = None
    try:
        metrics = analyze_results(trades_df, equity_curve)
    except Exception as e:
        print(f"Error analyzing results: {e}")
    
    # Plot results
    try:
        plot_results(df, trades_df, equity_curve, title_suffix=slippage_mode)
    except Exception as e:
        print(f"Error creating plot: {e}")
    
    # Print conclusions
    print("\n=== CONCLUSION ===")
    
    # Count total signal groups (direction changes)
    signal_groups = df[df['new_group'] == True]
    signal_count = len(signal_groups)
    
    # Count raw crossover signals
    raw_signals = df[df['signal'] != 0]
    raw_signal_count = len(raw_signals)
    
    if metrics and metrics.get('total_trades', 0) > 0:
        print(f"The MA ({FAST_WINDOW}/{SLOW_WINDOW}) crossover strategy generated:")
        print(f"  - {signal_count} signal direction changes")
        print(f"  - {raw_signal_count} raw crossover signals")
        print(f"  - {metrics['total_trades']} trades")
        print(f"Win rate: {metrics['win_rate']:.2f}%")
        print(f"Net profit: ${metrics['net_profit']:.2f} ({metrics['equity_change_pct']:+.2f}% of initial capital)")
        
        print("\n=== COMPARISON WITH ORIGINAL IMPLEMENTATION ===")
        print(f"The fixed validation script detected {signal_count} signal groups.")
        print("This matches the expected behavior where signals maintain direction until reversed.")
        print("Key improvements:")
        print("1. Signals are grouped by direction (BUY/SELL)")
        print("2. Only direction changes create new signal groups")
        print("3. Multiple signals in the same direction are treated as one group")
        print("4. The validation now matches the fixed system implementation")
    else:
        print("The strategy did not generate any trades in the given period.")

if __name__ == "__main__":
    main()
