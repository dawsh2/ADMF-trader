import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def calculate_signals(data, fast_window=5, slow_window=15):
    """Calculate MA crossover signals on the data."""
    # Calculate moving averages
    data['fast_ma'] = data['Close'].rolling(window=fast_window).mean()
    data['slow_ma'] = data['Close'].rolling(window=slow_window).mean()
    
    # Calculate crossovers
    data['fast_above_slow'] = data['fast_ma'] > data['slow_ma']
    
    # Generate signals (1 for buy, -1 for sell, 0 for no action)
    data['signal'] = 0
    data.loc[data['fast_above_slow'] & ~data['fast_above_slow'].shift(1).fillna(False), 'signal'] = 1  # Buy signal
    data.loc[~data['fast_above_slow'] & data['fast_above_slow'].shift(1).fillna(False), 'signal'] = -1  # Sell signal
    
    return data

def count_signals(data):
    """Count buy and sell signals."""
    buy_signals = (data['signal'] == 1).sum()
    sell_signals = (data['signal'] == -1).sum()
    return buy_signals, sell_signals

def plot_signals(data, fast_window, slow_window):
    """Plot price, MAs and signals."""
    plt.figure(figsize=(12, 8))
    
    # Plot price and MAs
    plt.subplot(2, 1, 1)
    plt.plot(data.index, data['Close'], label='Close Price', alpha=0.7)
    plt.plot(data.index, data['fast_ma'], label=f'Fast MA ({fast_window})', alpha=0.8)
    plt.plot(data.index, data['slow_ma'], label=f'Slow MA ({slow_window})', alpha=0.8)
    
    # Highlight buy and sell signals
    buy_signals = data[data['signal'] == 1]
    sell_signals = data[data['signal'] == -1]
    
    plt.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='green', s=100, label='Buy Signal')
    plt.scatter(sell_signals.index, sell_signals['Close'], marker='v', color='red', s=100, label='Sell Signal')
    
    plt.title('MINI Price with Moving Averages and Signals')
    plt.ylabel('Price')
    plt.legend()
    
    # Plot signal values
    plt.subplot(2, 1, 2)
    plt.plot(data.index, data['signal'].cumsum(), label='Cumulative Signal')
    plt.title('Cumulative Signal (Trade direction)')
    plt.ylabel('Position')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('backtest_verification.png')
    plt.close()

# Main script
if __name__ == "__main__":
    # Parameters from the backtest
    fast_window = 5
    slow_window = 15
    
    # Load the data
    data = pd.read_csv('data/MINI_1min.csv')
    
    # Print column names for verification
    print("CSV columns:", data.columns.tolist())
    
    # Process timestamp
    data['datetime'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('datetime')
    
    # Calculate signals
    data = calculate_signals(data, fast_window, slow_window)
    
    # Count signals
    buy_count, sell_count = count_signals(data)
    total_signals = buy_count + sell_count
    
    # Print results
    print(f"Data range: {data.index.min()} to {data.index.max()}")
    print(f"Total rows: {len(data)}")
    print(f"Buy signals: {buy_count}")
    print(f"Sell signals: {sell_count}")
    print(f"Total signals: {total_signals}")
    
    # Compare with backtest log
    print("\nComparison with backtest log:")
    log_signals = 31  # From the log: "Signal #31 emitted"
    print(f"Signals in log: {log_signals}")
    print(f"Signals calculated: {total_signals}")
    print(f"Match: {'Yes' if total_signals == log_signals else 'No'}")
    
    # Compare with the mentioned signals in the log
    log_buy_signals = 16  # Count of "BUY signal" in the log
    log_sell_signals = 15  # Count of "SELL signal" in the log
    print(f"Buy signals in log: {log_buy_signals}, Calculated: {buy_count}")
    print(f"Sell signals in log: {log_sell_signals}, Calculated: {sell_count}")
    
    # Create visualization
    plot_signals(data, fast_window, slow_window)
    
    # Check specific crossover points
    if len(data) > slow_window:
        print("\nSample crossover points:")
        signals = data[data['signal'] != 0].copy()
        if len(signals) > 0:
            for i in range(min(5, len(signals))):
                idx = signals.index[i]
                signal_val = signals.loc[idx, 'signal']
                fast_ma = signals.loc[idx, 'fast_ma']
                slow_ma = signals.loc[idx, 'slow_ma']
                close = signals.loc[idx, 'Close']
                diff_pct = abs((fast_ma - slow_ma) / slow_ma * 100)
                direction = "BUY" if signal_val == 1 else "SELL"
                print(f"{idx}: {direction} signal - Fast MA: {fast_ma:.2f}, Slow MA: {slow_ma:.2f}, Close: {close:.2f}, Diff: {diff_pct:.4f}%")
    
    # Let's also analyze the order execution pattern from the log
    print("\nAnalyzing order duplication pattern:")
    print("The system is generating two orders per signal:")
    print("1. First order: Always for 100 units")
    print("2. Second order: For ~18-19 units with 'Reducing BUY/SELL size from 100 to X' message")
    
    # Analyze trade performance
    print("\nTrade performance issues:")
    print("1. Every trade shows either a loss or breakeven (never a profit)")
    print("2. Invalid state transitions in order registry")
    print("3. Risk manager attempting to resize positions after orders are already placed")
    
    # Recommendations
    print("\nRecommendations to fix the issues:")
    print("1. Modify SimpleRiskManager to calculate position size before sending orders")
    print("2. Fix order state transition logic in OrderRegistry")
    print("3. Ensure broker simulation properly handles slippage and commission")
    print("4. Implement proper risk management based on account equity")
