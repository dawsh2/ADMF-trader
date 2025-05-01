#!/usr/bin/env python3
"""
Simple validation script for MA Crossover strategy.
This script loads the MINI_1min.csv data and implements the same strategy (5/15 SMA crossover) 
to validate the results independently.
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

def calculate_signals(df):
    """Calculate moving averages and generate signals."""
    print("\n=== DETAILED SIGNAL GENERATION LOG ===")
    # Calculate moving averages
    df['fast_ma'] = df['close'].rolling(window=FAST_WINDOW).mean()
    df['slow_ma'] = df['close'].rolling(window=SLOW_WINDOW).mean()
    
    # Calculate crossover signals
    df['signal'] = 0
    
    # Print sample data to debug
    print("\nSample data (first 20 rows after MA calculation):")
    print(df[['close', 'fast_ma', 'slow_ma']].head(20))
    
    # Log MA calculation details
    print(f"\nMoving Average Calculation:\n  Fast MA: {FAST_WINDOW} periods")
    print(f"  Slow MA: {SLOW_WINDOW} periods")
    print(f"  First valid Fast MA at index {FAST_WINDOW-1}, value: {df['fast_ma'].iloc[FAST_WINDOW-1]:.6f}")
    print(f"  First valid Slow MA at index {SLOW_WINDOW-1}, value: {df['slow_ma'].iloc[SLOW_WINDOW-1]:.6f}")
    
    # We need at least SLOW_WINDOW bars to calculate MAs
    if len(df) <= SLOW_WINDOW:
        print(f"Warning: Not enough data points ({len(df)}) for MA calculation with window {SLOW_WINDOW}")
        return df
    
    # Log all potential crossovers
    print("\nDetailed Crossover Analysis:")
    print("Index | Timestamp | Fast MA Previous | Slow MA Previous | Fast MA Current | Slow MA Current | Diff % | Signal")
    print("-"*100)
    
    # Generate signals manually by iterating through rows
    crossover_count = 0
    for i in range(SLOW_WINDOW, len(df)):
        # Get previous and current values
        prev_fast = df['fast_ma'].iloc[i-1]
        prev_slow = df['slow_ma'].iloc[i-1]
        curr_fast = df['fast_ma'].iloc[i]
        curr_slow = df['slow_ma'].iloc[i]
        
        timestamp = df.index[i]
        
        # Check if we have valid values
        if pd.notna(prev_fast) and pd.notna(prev_slow) and pd.notna(curr_fast) and pd.notna(curr_slow):
            # Calculate difference percentage
            diff_pct = abs(curr_fast - curr_slow) / curr_slow * 100
            
            signal = 0
            # Buy signal: fast MA crosses above slow MA
            if prev_fast < prev_slow and curr_fast > curr_slow:
                signal = 1
                df.at[df.index[i], 'signal'] = 1
                crossover_count += 1
            
            # Sell signal: fast MA crosses below slow MA
            elif prev_fast > prev_slow and curr_fast < curr_slow:
                signal = -1
                df.at[df.index[i], 'signal'] = -1
                crossover_count += 1
            
            # Log each potential crossover point for debugging
            if prev_fast != prev_slow:  # Only show rows where MAs are different
                print(f"{i:5d} | {timestamp} | {prev_fast:.6f} | {prev_slow:.6f} | {curr_fast:.6f} | {curr_slow:.6f} | {diff_pct:.6f}% | {signal}")
    
    # Calculate crossover percentage
    df['crossover_pct'] = (df['fast_ma'] - df['slow_ma']).abs() / df['slow_ma'] * 100
    
    # Count signals
    buy_signals = (df['signal'] == 1).sum()
    sell_signals = (df['signal'] == -1).sum()
    print(f"\nDetected signals: {buy_signals + sell_signals} ({buy_signals} buys, {sell_signals} sells)")
    
    # Save detailed signal data to CSV for inspection
    signals_df = df[df['signal'] != 0].copy()
    signals_df.to_csv('detected_signals.csv')
    print(f"Detailed signal data saved to 'detected_signals.csv'")
    
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
    trade_id = 0
    
    # Equity tracking
    equity = INITIAL_CAPITAL
    equity_curve = [INITIAL_CAPITAL]
    
    print("\nDetailed Trade Log:")
    print("ID | Type | Entry Time | Entry Price | Exit Time | Exit Price | PnL | Win/Loss")
    print("-"*80)
    
    # Iterate through the data
    for timestamp, row in df.iterrows():
        # Check for trade signals
        if row['signal'] != 0:
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
                print(f"OPEN: {position} position at {timestamp}, price: {execution_price:.2f}, close: {row['close']:.2f}")
            
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
                print(f"{trade_id:2d} | {direction:4s} | {entry_time} | {entry_price:.2f} | {timestamp} | {execution_price:.2f} | {pnl:+.2f} | {result}")
                
                # Record the trade
                trades.append({
                    'trade_id': trade_id,
                    'entry_time': entry_time,
                    'exit_time': timestamp,
                    'direction': direction,
                    'entry_price': entry_price,
                    'exit_price': execution_price,
                    'size': POSITION_SIZE,
                    'pnl': pnl,
                    'win': pnl > 0
                })
                
                # Open new position in opposite direction
                position = row['signal']
                entry_price = execution_price
                entry_time = timestamp
                print(f"OPEN: {position} position at {timestamp}, price: {execution_price:.2f}, close: {row['close']:.2f}")
    
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
        print(f"{trade_id:2d} | {direction:4s} | {entry_time} | {entry_price:.2f} | {df.index[-1]} | {last_price:.2f} | {pnl:+.2f} | {result}")
        
        # Record the trade
        trades.append({
            'trade_id': trade_id,
            'entry_time': entry_time,
            'exit_time': df.index[-1],
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': last_price,
            'size': POSITION_SIZE,
            'pnl': pnl,
            'win': pnl > 0
        })
    
    # Save detailed trade log to CSV
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df.to_csv('backtest_trades.csv')
        print(f"\nTrade log saved to 'backtest_trades.csv'")
    
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
    tiny_crossovers = len(trades_df[trades_df['crossover_pct'] < 0.01]) if 'crossover_pct' in trades_df.columns else "N/A"
    
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

def analyze_crossovers(df):
    """Analyze the crossover signals."""
    signal_df = df[df['signal'] != 0].copy()
    
    if signal_df.empty:
        print("No crossover signals found.")
        return
    
    # Add percentage crossover column if not already present
    if 'crossover_pct' not in signal_df.columns:
        signal_df['crossover_pct'] = (signal_df['fast_ma'] - signal_df['slow_ma']).abs() / signal_df['slow_ma'] * 100
    
    # Get statistics on crossover size
    crossover_stats = signal_df['crossover_pct'].describe()
    
    # Count signals with tiny crossovers
    tiny_crossovers = len(signal_df[signal_df['crossover_pct'] < 0.01])
    small_crossovers = len(signal_df[signal_df['crossover_pct'] < 0.05])
    
    print("\n=== CROSSOVER ANALYSIS ===")
    print(f"Total signals: {len(signal_df)}")
    print(f"Average crossover size: {signal_df['crossover_pct'].mean():.4f}%")
    print(f"Median crossover size: {signal_df['crossover_pct'].median():.4f}%")
    print(f"Maximum crossover size: {signal_df['crossover_pct'].max():.4f}%")
    print(f"Minimum crossover size: {signal_df['crossover_pct'].min():.4f}%")
    print(f"Tiny crossovers (<0.01%): {tiny_crossovers} ({tiny_crossovers/len(signal_df)*100:.2f}%)")
    print(f"Small crossovers (<0.05%): {small_crossovers} ({small_crossovers/len(signal_df)*100:.2f}%)")
    
    # Distribution by size
    bins = [0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0, float('inf')]
    labels = ['<0.005%', '0.005-0.01%', '0.01-0.02%', '0.02-0.05%', '0.05-0.1%', '0.1-0.5%', '0.5-1.0%', '>1.0%']
    signal_df['crossover_bin'] = pd.cut(signal_df['crossover_pct'], bins=bins, labels=labels)
    
    distribution = signal_df['crossover_bin'].value_counts().sort_index()
    print("\nCrossover Size Distribution:")
    for size_bin, count in distribution.items():
        pct = count / len(signal_df) * 100
        print(f"  {size_bin}: {count} signals ({pct:.2f}%)")
    
    # Analyze by signal direction
    buy_signals = signal_df[signal_df['signal'] == 1]
    sell_signals = signal_df[signal_df['signal'] == -1]
    
    print("\nSignal Direction:")
    print(f"  BUY signals: {len(buy_signals)} ({len(buy_signals)/len(signal_df)*100:.2f}%)")
    print(f"  SELL signals: {len(sell_signals)} ({len(sell_signals)/len(signal_df)*100:.2f}%)")
    
    return signal_df

def plot_results(df, trades_df, equity_curve, title_suffix=""):
    """Create plots for visualization."""
    # Create figure with subplots
    fig, axes = plt.subplots(3, 1, figsize=(12, 16), gridspec_kw={'height_ratios': [3, 1, 1]})
    
    # Plot price and moving averages
    axes[0].plot(df.index, df['close'], label='Close Price', alpha=0.7)
    axes[0].plot(df.index, df['fast_ma'], label=f'Fast MA ({FAST_WINDOW})', linewidth=1)
    axes[0].plot(df.index, df['slow_ma'], label=f'Slow MA ({SLOW_WINDOW})', linewidth=1)
    
    # Plot buy/sell signals
    buy_signals = df[df['signal'] == 1]
    sell_signals = df[df['signal'] == -1]
    
    axes[0].scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=120, label='Buy Signal')
    axes[0].scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=120, label='Sell Signal')
    
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
    fig.suptitle(f'MA Crossover ({FAST_WINDOW}/{SLOW_WINDOW}) Validation {title_suffix}', fontsize=16)
    
    axes[0].set_title('Price, MA, and Trade Signals')
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
    filename = f"ma_crossover_validation_{FAST_WINDOW}_{SLOW_WINDOW}_{timestamp}{title_suffix.replace(' ', '_')}.png"
    plt.savefig(filename)
    print(f"\nPlot saved to: {filename}")
    
    return filename

def main():
    """Main function."""
    print("\n" + "="*60)
    print(f"MA CROSSOVER STRATEGY VALIDATION ({FAST_WINDOW}/{SLOW_WINDOW})")
    print("="*60)
    
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
    
    # Calculate signals
    df = calculate_signals(df)
    
    # Analyze crossovers
    try:
        crossover_df = analyze_crossovers(df)
    except Exception as e:
        print(f"Error analyzing crossovers: {e}")
    
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
    if metrics and metrics.get('total_trades', 0) > 0:
        print(f"The MA ({FAST_WINDOW}/{SLOW_WINDOW}) crossover strategy generated {metrics['total_trades']} trades.")
        print(f"Win rate: {metrics['win_rate']:.2f}%")
        print(f"Net profit: ${metrics['net_profit']:.2f} ({metrics['equity_change_pct']:+.2f}% of initial capital)")
    else:
        print("The strategy did not generate any trades in the given period.")

if __name__ == "__main__":
    main()
