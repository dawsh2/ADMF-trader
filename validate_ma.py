import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def calculate_signals(data, fast_window=5, slow_window=15):
    """Calculate MA crossover signals on the data using same method as the strategy."""
    # Initialize columns
    data['fast_ma'] = None
    data['slow_ma'] = None
    data['fast_ma_prev'] = None
    data['slow_ma_prev'] = None
    data['signal'] = 0
    
    # Use manual calculation to match the strategy implementation
    for i in range(slow_window, len(data)):
        # Get price slice for calculations
        prices = data['Close'].values[:i+1]
        
        # Calculate fast MA - current and previous (matching strategy implementation)
        data.loc[data.index[i], 'fast_ma'] = sum(prices[-fast_window:]) / fast_window
        data.loc[data.index[i], 'fast_ma_prev'] = sum(prices[-(fast_window+1):-1]) / fast_window
        
        # Calculate slow MA - current and previous (matching strategy implementation)
        data.loc[data.index[i], 'slow_ma'] = sum(prices[-slow_window:]) / slow_window
        data.loc[data.index[i], 'slow_ma_prev'] = sum(prices[-(slow_window+1):-1]) / slow_window
        
        # Check for crossover exactly as in the strategy
        # Buy signal: fast MA crosses above slow MA
        if (data.loc[data.index[i], 'fast_ma_prev'] <= data.loc[data.index[i], 'slow_ma_prev'] and 
            data.loc[data.index[i], 'fast_ma'] > data.loc[data.index[i], 'slow_ma']):
            data.loc[data.index[i], 'signal'] = 1
        
        # Sell signal: fast MA crosses below slow MA
        elif (data.loc[data.index[i], 'fast_ma_prev'] >= data.loc[data.index[i], 'slow_ma_prev'] and 
              data.loc[data.index[i], 'fast_ma'] < data.loc[data.index[i], 'slow_ma']):
            data.loc[data.index[i], 'signal'] = -1
    
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
    
    # Only plot non-NA values for MAs
    valid_data = data.dropna(subset=['fast_ma', 'slow_ma'])
    plt.plot(valid_data.index, valid_data['fast_ma'], label=f'Fast MA ({fast_window})', alpha=0.8)
    plt.plot(valid_data.index, valid_data['slow_ma'], label=f'Slow MA ({slow_window})', alpha=0.8)
    
    # Plot a dotted line for previous MA values at signal points
    signal_points = data[data['signal'] != 0]
    if not signal_points.empty:
        plt.plot(signal_points.index, signal_points['fast_ma_prev'], 'o', color='blue', markersize=3, alpha=0.5, label='Prev Fast MA')
        plt.plot(signal_points.index, signal_points['slow_ma_prev'], 'o', color='purple', markersize=3, alpha=0.5, label='Prev Slow MA')
    
    # Highlight buy and sell signals
    buy_signals = data[data['signal'] == 1]
    sell_signals = data[data['signal'] == -1]
    
    plt.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='green', s=100, label='Buy Signal')
    plt.scatter(sell_signals.index, sell_signals['Close'], marker='v', color='red', s=100, label='Sell Signal')
    
    plt.title('MINI Price with Moving Averages and Signals')
    plt.ylabel('Price')
    plt.legend()
    
    # Plot signal values and crossover differences
    plt.subplot(2, 1, 2)
    
    # Add MA difference plot to see crossovers clearly
    valid_data['ma_diff'] = valid_data['fast_ma'] - valid_data['slow_ma']
    plt.plot(valid_data.index, valid_data['ma_diff'], label='MA Difference (Fast-Slow)', color='purple', alpha=0.7)
    
    # Plot a horizontal line at zero to show crossover points
    plt.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
    
    # Plot cumulative signal
    plt.plot(data.index, data['signal'].cumsum(), label='Cumulative Signal', color='black')
    
    plt.title('Crossovers and Cumulative Position')
    plt.ylabel('Value')
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
    
    # List all signals for detailed analysis
    print("\nDetailed signal list:")
    signals_df = data[data['signal'] != 0].copy()
    for i, row in signals_df.iterrows():
        signal_val = row['signal']
        fast_ma = row['fast_ma']
        slow_ma = row['slow_ma']
        fast_ma_prev = row['fast_ma_prev']
        slow_ma_prev = row['slow_ma_prev']
        close = row['Close']
        
        direction = "BUY" if signal_val == 1 else "SELL"
        diff_pct = abs((fast_ma - slow_ma) / slow_ma * 100)
        
        # Print crossover details
        print(f"{i}: {direction} - Fast MA: {fast_ma:.2f} (prev {fast_ma_prev:.2f}), " 
              f"Slow MA: {slow_ma:.2f} (prev {slow_ma_prev:.2f}), " 
              f"Close: {close:.2f}, Diff: {diff_pct:.4f}%")
    
    # Signal Verification
    if total_signals != log_signals:
        print("\nSignal Count Mismatch Analysis:")
        print(f"Expected {log_signals} signals from log, found {total_signals} signals in calculation")
        print("Possible causes:")
        print("1. The strategy might be using a different data window than our verification script")
        print("2. The crossover detection logic might have edge cases we're not capturing")
        print("3. The backtest system might be running multiple instances of the strategy")
        
        # Find the first few days in the dataset
        start_date = data.index.min().date()
        end_date = start_date + pd.Timedelta(days=1)
        first_day_data = data[(data.index.date >= start_date) & (data.index.date <= end_date)]
        signals_on_first_day = first_day_data[first_day_data['signal'] != 0]
        
        print(f"\nSignals on first day ({start_date}): {len(signals_on_first_day)}")
    
    # Summary of fixes applied
    print("\nSummary of Fixes Applied:")
    print("1. SimpleRiskManager - Now calculates final position size before creating orders")
    print("   - Prevents duplicate orders with different sizes")
    print("   - Ensures proper position sizing based on account equity")
    
    print("\n2. OrderRegistry - Added terminal state checking")
    print("   - Prevents invalid state transitions (e.g., FILLED -> PENDING)")
    print("   - Skips processing fills for orders already in terminal states")
    
    print("\n3. SimulatedBroker - Improved order state handling")
    print("   - Checks for terminal states before attempting to process orders")
    print("   - Prevents duplicate order processing")
    
    print("\n4. Validation Script - Updated to match strategy's MA calculation")
    print("   - Now uses the same window calculation method as the strategy")
    print("   - Provides detailed visualization of crossovers and signals")
    
    print("\nNext Steps:")
    print("1. Improve slippage model for more realistic fill prices")
    print("2. Further investigate the signal count discrepancy if it persists")
    print("3. Add unit tests to ensure the fixes work as expected")
    print("4. Consider using pandas rolling instead of manual calculation for better performance")
