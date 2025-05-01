#!/usr/bin/env python
"""
Independent Validation Script for ADMF-Trader

This script creates a synthetic price series with known crossover points
and expected trading behavior, then validates the system's output against
the expected results.

The validation:
1. Creates a synthetic price series with clear MA crossovers
2. Runs a simple MA crossover strategy with 5/15 period windows
3. Counts signals, trades, and position changes
4. Compares actual system behavior against expected behavior
"""
import os
import pandas as pd
import numpy as np
import logging
import datetime
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('indie_validator')

# Create synthetic data for validation
def create_synthetic_data(output_dir='./data', filename='SYNTH_1min.csv'):
    """
    Create a synthetic price series with known MA crossover points.
    The series has five clear crossovers (3 SELL signals, 2 BUY signals).
    """
    # Ensure data directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Start with base price of 100
    base_price = 100.0
    
    # Create timestamp range for a single day with 1-minute intervals
    start_time = datetime.datetime(2024, 3, 26, 9, 30, 0)
    periods = 120  # 2 hours of 1-minute data
    timestamps = [start_time + datetime.timedelta(minutes=i) for i in range(periods)]
    
    # Create price series with two clear uptrends and two clear downtrends
    # to generate predictable MA crossovers
    prices = []
    
    # Initial price series - flat period (first 10 minutes)
    prices.extend([base_price] * 10)
    
    # First uptrend (10 minutes)
    for i in range(10):
        prices.append(base_price + (i+1) * 0.2)
    
    # Flat high period (15 minutes)
    high_price = prices[-1]
    prices.extend([high_price] * 15)
    
    # First downtrend (15 minutes)
    for i in range(15):
        prices.append(high_price - (i+1) * 0.15)
    
    # Flat low period (10 minutes)
    low_price = prices[-1]
    prices.extend([low_price] * 10)
    
    # Second uptrend (15 minutes)
    for i in range(15):
        prices.append(low_price + (i+1) * 0.2)
    
    # Flat high period (10 minutes)
    high_price_2 = prices[-1]
    prices.extend([high_price_2] * 10)
    
    # Second downtrend (10 minutes)
    for i in range(10):
        prices.append(high_price_2 - (i+1) * 0.25)
    
    # Extend to fill periods if needed
    if len(prices) < periods:
        prices.extend([prices[-1]] * (periods - len(prices)))
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'Open': prices,
        'High': [p + 0.1 for p in prices],
        'Low': [p - 0.1 for p in prices],
        'Close': prices,
        'Volume': [1000] * periods
    })
    
    # Save to CSV
    output_path = os.path.join(output_dir, filename)
    df.to_csv(output_path, index=False)
    logger.info(f"Synthetic data created: {output_path}")
    
    # Calculate and log the expected MA crossovers for 5/15 window
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA15'] = df['Close'].rolling(window=15).mean()
    df['Signal'] = np.where(df['MA5'] > df['MA15'], 1, -1)
    
    # Find crossover points
    df['SignalChange'] = df['Signal'].diff()
    crossovers = df[df['SignalChange'] != 0]
    
    logger.info(f"Expected crossovers with 5/15 MA windows:")
    for idx, row in crossovers.iterrows():
        signal = "BUY" if row['Signal'] == 1 else "SELL"
        logger.info(f"Crossover at {row['timestamp']} - Signal: {signal}")
    
    logger.info(f"Total expected crossovers: {len(crossovers)}")
    
    # Calculate expected trades in enhanced risk manager
    # In enhanced risk manager, each signal change causes:
    # 1. A CLOSE trade for the existing position (if any)
    # 2. An OPEN trade for the new position
    # So for N signals, we expect approximately 2*N trades (slightly less for the first signal)
    
    # Starting from no position, first signal = 1 OPEN
    # Each subsequent signal = 1 CLOSE + 1 OPEN = 2 trades
    if len(crossovers) > 0:
        expected_trades = 1 + (len(crossovers) - 1) * 2
        # The first signal needs special handling since there might be no position to close
        first_signal_time = crossovers.iloc[0]['timestamp']
        if first_signal_time != start_time:
            # If the first signal is not at the start, it's likely to
            # close a position before opening a new one
            expected_trades = len(crossovers) * 2
            
        logger.info(f"Total expected trades (OPEN+CLOSE): {expected_trades}")
    else:
        expected_trades = 0
        logger.warning("No crossovers found in synthetic data")
    
    return output_path, crossovers, expected_trades

def create_validation_config(config_path='config/validation_test.yaml'):
    """Create a configuration file for the validation test."""
    # Ensure config directory exists
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    config_content = """# Configuration for Validation Test
# ------------------------------------------------------

# Global backtest settings
backtest:
  initial_capital: 100000.0
  symbols: ['SYNTH']
  data_dir: "./data"
  timeframe: "1min"
  data_source: "csv"
  start_date: "2024-03-26 09:30:00"
  end_date: "2024-03-26 11:30:00"
  strategy: "simple_ma_crossover"

# Data handling configuration
data:
  source_type: "csv"
  data_dir: "./data"
  file_pattern: "{symbol}_{timeframe}.csv"
  timestamp_column: "timestamp"
  price_columns:
    open: "Open" 
    high: "High"
    low: "Low"
    close: "Close"
    volume: "Volume"

# Strategy configuration
strategies:
  simple_ma_crossover:
    enabled: true
    fast_window: 5
    slow_window: 15
    price_key: "close"

# Risk management settings - using enhanced risk manager
risk_manager:
  type: "enhanced"
  position_sizing_method: "fixed"
  position_size: 100
  max_position_size: 1000
  equity_percent: 5.0
  risk_percent: 2.0
  max_open_trades: 5
  
# Order handling settings
order_manager:
  default_order_type: "MARKET"

# Broker simulation settings
broker:
  slippage: 0.0
  commission: 0.0
  delay: 0

# Performance metrics settings
performance:
  metrics:
    - "total_return"
    - "sharpe_ratio"
    - "max_drawdown"
    - "win_rate"
    - "profit_factor"
  
# Logging settings
logging:
  level: "INFO"
  
# Output settings
output:
  save_trades: True
  save_equity_curve: True
  output_dir: "./results/validation_test"
  plot_results: True
  plot_format: "png"
  verbose: True
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    logger.info(f"Validation config created: {config_path}")
    return config_path

def parse_log_file(log_path):
    """
    Parse the log file to extract trading decisions and signals.
    
    Returns:
        tuple: (signals, trades) where signals is a list of signal events
               and trades is a list of trading decisions
    """
    signals = []
    trades = []
    
    try:
        with open(log_path, 'r') as f:
            for line in f:
                if 'Received signal:' in line:
                    signals.append(line.strip())
                elif 'Trading decision:' in line:
                    trades.append(line.strip())
    except FileNotFoundError:
        logger.error(f"Log file not found: {log_path}")
        return [], []
    
    return signals, trades

def validate_trading_behavior(log_path, expected_crossovers, expected_trades):
    """
    Validate that the trading behavior matches expectations.
    
    Args:
        log_path: Path to the log file
        expected_crossovers: DataFrame with expected MA crossover points
        expected_trades: Expected number of trades
    
    Returns:
        bool: True if validation passed, False otherwise
    """
    signals, trades = parse_log_file(log_path)
    
    # Count signals and trades
    logger.info(f"Found {len(signals)} signals in log")
    logger.info(f"Found {len(trades)} trades in log")
    
    # Count close and open actions
    open_trades = [t for t in trades if 'action=OPEN' in t]
    close_trades = [t for t in trades if 'action=CLOSE' in t]
    
    logger.info(f"Open trades: {len(open_trades)}")
    logger.info(f"Close trades: {len(close_trades)}")
    
    # Expected number of signals based on crossovers
    expected_signals = len(expected_crossovers)
    
    # Validate numbers
    validation_passed = True
    
    # Allow some flexibility in signal count (due to initial MA calculation periods)
    # We might miss the first signal due to MA calculation periods
    if abs(len(signals) - expected_signals) > 1:
        logger.error(f"Signal count mismatch: Expected {expected_signals}, got {len(signals)}")
        validation_passed = False
    else:
        logger.info(f"Signal count is acceptable: Expected ~{expected_signals}, got {len(signals)}")
    
    # For the enhanced risk manager, we expect:
    # - One OPEN trade for each signal
    # - One CLOSE trade for each signal change after the first one
    # This typically results in twice the number of trades as signals (minus one)
    # We'll allow some flexibility for edge cases
    
    # Check if trade count is within acceptable limits
    if abs(len(trades) - expected_trades) > 2:
        logger.error(f"Trade count mismatch: Expected ~{expected_trades}, got {len(trades)}")
        validation_passed = False
    else:
        logger.info(f"Trade count is acceptable: Expected ~{expected_trades}, got {len(trades)}")
    
    # Validate signal directions
    buy_signals = [s for s in signals if 'direction=1' in s]
    sell_signals = [s for s in signals if 'direction=-1' in s]
    
    logger.info(f"Buy signals: {len(buy_signals)}")
    logger.info(f"Sell signals: {len(sell_signals)}")
    
    # Validate trade directions
    buy_trades = [t for t in trades if 'BUY' in t]
    sell_trades = [t for t in trades if 'SELL' in t]
    
    logger.info(f"Buy trades: {len(buy_trades)}")
    logger.info(f"Sell trades: {len(sell_trades)}")
    
    # Check for duplicate rule IDs
    rule_ids = [t.split('rule_id=')[1].split(',')[0] for t in trades]
    duplicate_rule_ids = set([rid for rid in rule_ids if rule_ids.count(rid) > 1])
    
    if duplicate_rule_ids:
        logger.error(f"Found duplicate rule IDs: {duplicate_rule_ids}")
        validation_passed = False
    
    # Ensure we have a proper balance of OPEN and CLOSE trades
    # In normal operation, we should have one more OPEN than CLOSE
    # due to the final position being left open
    if abs(len(open_trades) - len(close_trades)) > 1:
        logger.warning(f"Unbalanced OPEN/CLOSE trades: {len(open_trades)} open vs {len(close_trades)} close")
    else:
        logger.info("OPEN/CLOSE trade balance is good")
    
    return validation_passed

def main():
    """Run the validation process."""
    logger.info("Starting independent validation of ADMF-Trader")
    
    # Create synthetic data with known crossover points
    data_path, expected_crossovers, expected_trades = create_synthetic_data()
    
    # Create validation config
    config_path = create_validation_config()
    
    # Run the backtest using the main script
    logger.info("Running backtest with validation config...")
    os.system(f"python main.py --config {config_path}")
    
    # Path to the log file generated by the backtest
    log_path = "./results/validation_test/validation_test.log"
    
    # Wait for log file to be written
    if not os.path.exists(log_path):
        logger.error(f"Log file not found: {log_path}")
        return False
    
    # Validate trading behavior
    validation_passed = validate_trading_behavior(log_path, expected_crossovers, expected_trades)
    
    if validation_passed:
        logger.info("✅ Validation PASSED: System behavior matches expectations")
    else:
        logger.error("❌ Validation FAILED: System behavior does not match expectations")
    
    return validation_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
