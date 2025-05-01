#!/usr/bin/env python3
"""
Independent validation script for MA Crossover strategy.
This script loads the same dataset and implements the same strategy 
as the main trading system to validate results independently.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Strategy parameters
FAST_WINDOW = 5
SLOW_WINDOW = 15
SLIPPAGE = 0.0  # Set this to match your current test settings

def load_data(file_path):
    """Load OHLCV data from CSV file."""
    print(f"Loading data from {file_path}")
    df = pd.read_csv(file_path)
    
    # Convert timestamp to datetime if it's not already
    if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Set timestamp as index
    if 'timestamp' in df.columns:
        df.set_index('timestamp', inplace=True)
    
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

def calculate_indicators(df):
    """Calculate moving averages and generate signals."""
    # Calculate moving averages
    df['fast_ma'] = df['close'].rolling(window=FAST_WINDOW).mean()
    df['slow_ma'] = df['close'].rolling(window=SLOW_WINDOW).mean()
    
    # Calculate crossover signals
    df['signal'] = 0
    
    # Previous values
    df['prev_fast_ma'] = df['fast_ma'].shift(1)
    df['prev_slow_ma'] = df['slow_ma'].shift(1)
    
    # Crossing above (buy signal)
    buy_condition = (df['prev_fast_ma'] < df['prev_slow_ma']) & (df['fast_ma'] > df['slow_ma'])
    df.loc[buy_condition, 'signal'] = 1
    
    # Crossing below (sell signal)
    sell_condition = (df['prev_fast_ma'] > df['prev_slow_ma']) & (df['fast_ma'] < df['slow_ma'])
    df.loc[sell_condition, 'signal'] = -1
    
    # Calculate crossover percentage to match main system metrics
    df['crossover_pct'] = np.abs(df['fast_ma'] - df['slow_ma']) / df['slow_ma'] * 100
    
    # Drop NaN values (from moving average calculation)
    df.dropna(inplace=True)
    
    return df

def extract_signal_changes(df, apply_slippage=True):
    """Extract signal changes and direction transitions without calculating PnL."""
    # Initialize positions and metrics columns
    df['position'] = 0
    df['trade_price'] = 0.0
    df['trade_id'] = 0
    
    # Keep track of open positions
    position = 0
    entry_price = 0.0
    trade_id = 0
    trades = []
    
    # Keep track of entry time for trades
    entry_time = None
    
    # Iterate through data
    for i, row in df.iterrows():
        # Process signals
        if row['signal'] != 0:
            signal = row['signal']
            
            # Calculate execution price with slippage
            if apply_slippage:
                # Similar to the main system's slippage model
                slippage_factor = 1.0 + (SLIPPAGE if signal == 1 else -SLIPPAGE)
                price = row['close'] * slippage_factor
            else:
                price = row['close']
            
            # Entering a new position or reversing
            if position == 0:
                # New position
                position = signal
                entry_price = price
                entry_time = i  # Set entry time
                trade_id += 1
                df.at[i, 'trade_price'] = price
            elif position == signal:
                # Adding to position (not implemented here for simplicity)
                pass
            else:
                # Exiting/reversing position
                # Record trade
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': i,
                    'direction': "SELL" if position == -1 else "BUY",
                    'entry_price': entry_price,
                    'exit_price': price,
                    'trade_id': trade_id
                })
                
                # Reverse position
                position = signal
                entry_price = price
                entry_time = i
                trade_id += 1
                df.at[i, 'trade_price'] = price
            
            # Update position
            df.at[i, 'position'] = position
            df.at[i, 'trade_id'] = trade_id
    
    # Close final position at the last price
    if position != 0 and entry_time is not None:
        last_price = df['close'].iloc[-1]
        if apply_slippage:
            # Apply slippage for closing
            slippage_factor = 1.0 + (SLIPPAGE if position == -1 else -SLIPPAGE)
            last_price = last_price * slippage_factor
            
        # Record trade
        trades.append({
            'entry_time': entry_time,
            'exit_time': df.index[-1],
            'direction': "SELL" if position == -1 else "BUY",
            'entry_price': entry_price,
            'exit_price': last_price,
            'trade_id': trade_id
        })
    
    # Convert trades to DataFrame
    trades_df = pd.DataFrame(trades)
    
    return df, trades_df

def calculate_signal_metrics(df, trades_df):
    """Calculate signal metrics without focusing on PnL."""
    # Basic metrics
    total_signals = len(df[df['signal'] != 0])
    total_trades = len(trades_df)
    
    # Direction statistics
    buy_signals = len(df[df['signal'] == 1])
    sell_signals = len(df[df['signal'] == -1])
    
    # Time between signals
    if total_signals > 1:
        signal_timestamps = df[df['signal'] != 0].index
        time_diffs = [signal_timestamps[i+1] - signal_timestamps[i] for i in range(len(signal_timestamps)-1)]
        avg_time_between_signals = sum(time_diffs, datetime.timedelta(0)) / len(time_diffs)
    else:
        avg_time_between_signals = datetime.timedelta(0)
    
    metrics = {
        'total_signals': total_signals,
        'total_trades': total_trades,
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'avg_time_between_signals': avg_time_between_signals
    }
    
    return metrics

def analyze_signal_distribution(trades_df):
    """Analyze pattern of signals and their distribution."""
    if trades_df.empty:
        print("No trades to analyze")
        return
    
    # Analyze time between signals
    if len(trades_df) > 1:
        trades_df = trades_df.sort_values('entry_time')
        trades_df['time_to_next'] = trades_df['entry_time'].shift(-1) - trades_df['entry_time']
        time_stats = trades_df['time_to_next'].describe()
        print("\nTime Between Signals:")
        print(time_stats)
    
    # Group by direction
    direction_counts = trades_df['direction'].value_counts()
    print("\nSignal Direction Distribution:")
    print(direction_counts)
    print(f"Percentage: {(direction_counts / len(trades_df) * 100).round(2)}%")
    
    # Analyze signal transitions
    if len(trades_df) > 1:
        trades_df['next_direction'] = trades_df['direction'].shift(-1)
        transition_counts = trades_df.groupby(['direction', 'next_direction']).size().unstack(fill_value=0)
        print("\nSignal Transition Analysis:")
        print(transition_counts)

def plot_signals(df, trades_df, slippage_applied=True):
    """Create plots of signals and direction changes."""
    # Create subplots
    fig, axs = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
    
    # Plot prices and moving averages
    axs[0].plot(df.index, df['close'], label='Close Price', alpha=0.7)
    axs[0].plot(df.index, df['fast_ma'], label=f'Fast MA ({FAST_WINDOW})', alpha=0.8)
    axs[0].plot(df.index, df['slow_ma'], label=f'Slow MA ({SLOW_WINDOW})', alpha=0.8)
    
    # Plot buy and sell signals
    buy_signals = df[df['signal'] == 1]
    sell_signals = df[df['signal'] == -1]
    
    axs[0].scatter(buy_signals.index, buy_signals['close'], 
                  marker='^', color='green', s=100, label='Buy Signal')
    axs[0].scatter(sell_signals.index, sell_signals['close'], 
                  marker='v', color='red', s=100, label='Sell Signal')
    
    # Plot actual trades
    if not trades_df.empty:
        for _, trade in trades_df.iterrows():
            # Plot entry point
            if trade['direction'] == 'SELL':
                axs[0].scatter(trade['entry_time'], trade['entry_price'], 
                              marker='v', color='red', s=150, edgecolors='black')
            else:
                axs[0].scatter(trade['entry_time'], trade['entry_price'], 
                              marker='^', color='green', s=150, edgecolors='black')
            
            # Plot exit point
            axs[0].scatter(trade['exit_time'], trade['exit_price'], 
                          marker='o', color='blue', s=150, edgecolors='black')
    
    # Plot position direction
    axs[1].plot(df.index, df['position'], label='Position Direction', color='blue', alpha=0.8)
    axs[1].set_yticks([-1, 0, 1])
    axs[1].set_yticklabels(['Short', 'Flat', 'Long'])
    
    # Set titles and labels
    slippage_text = f" with {SLIPPAGE*100}% slippage" if slippage_applied else " without slippage"
    fig.suptitle(f'MA Crossover Strategy Validation ({FAST_WINDOW}/{SLOW_WINDOW}){slippage_text}', fontsize=16)
    
    axs[0].set_title('Price and Signals')
    axs[0].set_ylabel('Price')
    axs[0].legend()
    axs[0].grid(True)
    
    axs[1].set_title('Position Direction')
    axs[1].set_ylabel('Direction')
    axs[1].legend()
    axs[1].grid(True)
    
    plt.tight_layout()
    
    # Save plot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ma_crossover_validation_{FAST_WINDOW}_{SLOW_WINDOW}_{timestamp}.png"
    plt.savefig(filename)
    print(f"Plot saved as {filename}")
    
    return filename

def analyze_crossovers(df):
    """Analyze the crossover patterns."""
    signal_df = df[df['signal'] != 0].copy()
    
    if signal_df.empty:
        print("No signals detected")
        return
    
    # Analyze crossover percentages
    crossover_stats = signal_df['crossover_pct'].describe()
    print("\nCrossover Percentage Statistics:")
    print(crossover_stats)
    
    # Count tiny crossovers (less than 0.01%)
    tiny_crossovers = len(signal_df[signal_df['crossover_pct'] < 0.01])
    print(f"Number of crossovers < 0.01%: {tiny_crossovers} ({tiny_crossovers/len(signal_df)*100:.2f}% of all signals)")
    
    # Show distribution of crossover sizes
    bins = [0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0, float('inf')]
    labels = ['<0.005%', '0.005-0.01%', '0.01-0.02%', '0.02-0.05%', '0.05-0.1%', '0.1-0.5%', '0.5-1.0%', '>1.0%']
    signal_df['crossover_bin'] = pd.cut(signal_df['crossover_pct'], bins=bins, labels=labels)
    crossover_distribution = signal_df['crossover_bin'].value_counts().sort_index()
    print("\nCrossover Size Distribution:")
    print(crossover_distribution)
    print(f"Percentage of total signals: {(crossover_distribution / len(signal_df) * 100).round(2)}")

def validate_signals(data_file):
    """Run signal validation analysis."""
    # Load and prepare data
    df = load_data(data_file)
    df = calculate_indicators(df)
    
    # Run with slippage
    with_slippage_df = df.copy()
    with_slippage_df, with_slippage_trades = extract_signal_changes(with_slippage_df, apply_slippage=True)
    with_slippage_metrics = calculate_signal_metrics(with_slippage_df, with_slippage_trades)
    plot_signals(with_slippage_df, with_slippage_trades, slippage_applied=True)
    
    print("\n=== SIGNAL VALIDATION RESULTS WITH SLIPPAGE ===")
    print(f"Total signals: {with_slippage_metrics['total_signals']}")
    print(f"Total trades: {with_slippage_metrics['total_trades']}")
    print(f"Buy signals: {with_slippage_metrics['buy_signals']}")
    print(f"Sell signals: {with_slippage_metrics['sell_signals']}")
    print(f"Average time between signals: {with_slippage_metrics['avg_time_between_signals']}")
    
    # Run without slippage
    without_slippage_df = df.copy()
    without_slippage_df, without_slippage_trades = extract_signal_changes(without_slippage_df, apply_slippage=False)
    without_slippage_metrics = calculate_signal_metrics(without_slippage_df, without_slippage_trades)
    plot_signals(without_slippage_df, without_slippage_trades, slippage_applied=False)
    
    print("\n=== SIGNAL VALIDATION RESULTS WITHOUT SLIPPAGE ===")
    print(f"Total signals: {without_slippage_metrics['total_signals']}")
    print(f"Total trades: {without_slippage_metrics['total_trades']}")
    print(f"Buy signals: {without_slippage_metrics['buy_signals']}")
    print(f"Sell signals: {without_slippage_metrics['sell_signals']}")
    print(f"Average time between signals: {without_slippage_metrics['avg_time_between_signals']}")
    
    # Analyze crossovers
    print("\n--- Crossover Analysis ---")
    analyze_crossovers(df)
    
    return with_slippage_metrics, without_slippage_metrics

def main():
    """Main function to run the validation."""
    print(f"\n{'='*60}")
    print(f"MA Crossover Strategy Validation (Fast MA: {FAST_WINDOW}, Slow MA: {SLOW_WINDOW})")
    print(f"{'='*60}")
    
    # Set data file path
    data_file = 'data/MINI_1min.csv'
    
    # Run validation
    with_metrics, without_metrics = validate_signals(data_file)
    
    # Print summary
    print("\n--- SUMMARY ---")
    print(f"Total signals: {with_metrics['total_signals']}")
    print(f"Buy signals: {with_metrics['buy_signals']} ({with_metrics['buy_signals']/with_metrics['total_signals']*100:.2f}%)")
    print(f"Sell signals: {with_metrics['sell_signals']} ({with_metrics['sell_signals']/with_metrics['total_signals']*100:.2f}%)")
    print(f"Average time between signals: {with_metrics['avg_time_between_signals']}")
    
    # Show impact of slippage
    signal_impact = with_metrics['total_signals'] - without_metrics['total_signals']
    print(f"\nImpact of slippage: {signal_impact} signal difference")

if __name__ == "__main__":
    main()
