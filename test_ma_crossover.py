#!/usr/bin/env python
"""
Direct test of MA Crossover strategy with the HEAD_1min.csv data
to verify if crossover events occur.
"""
import os
import sys
import logging
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ma_crossover_test')

def load_csv_data(file_path):
    """Load data from CSV file."""
    logger.info(f"Loading data from {file_path}")
    try:
        df = pd.read_csv(file_path)
        
        # Check for timestamp column
        timestamp_column = None
        for col in ['timestamp', 'date', 'datetime']:
            if col in df.columns:
                timestamp_column = col
                break
                
        if timestamp_column:
            df[timestamp_column] = pd.to_datetime(df[timestamp_column])
            df.set_index(timestamp_column, inplace=True)
            
        logger.info(f"Loaded {len(df)} rows from {file_path}")
        logger.info(f"Columns: {df.columns.tolist()}")
        logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
        
        return df
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return None

def test_ma_crossover(df, fast_window=5, slow_window=15, price_col='close'):
    """Test MA crossover strategy directly."""
    logger.info(f"Testing MA crossover with fast={fast_window}, slow={slow_window}")
    
    # Calculate moving averages
    df['fast_ma'] = df[price_col].rolling(window=fast_window).mean()
    df['slow_ma'] = df[price_col].rolling(window=slow_window).mean()
    
    # Calculate difference
    df['ma_diff'] = df['fast_ma'] - df['slow_ma']
    df['prev_ma_diff'] = df['ma_diff'].shift(1)
    
    # Generate signals
    df['signal'] = 0
    
    # Buy signal: fast MA crosses above slow MA
    buy_condition = (df['prev_ma_diff'] <= 0) & (df['ma_diff'] > 0)
    df.loc[buy_condition, 'signal'] = 1
    
    # Sell signal: fast MA crosses below slow MA
    sell_condition = (df['prev_ma_diff'] >= 0) & (df['ma_diff'] < 0)
    df.loc[sell_condition, 'signal'] = -1
    
    # Count signals
    buy_signals = df[df['signal'] == 1]
    sell_signals = df[df['signal'] == -1]
    
    logger.info(f"Generated {len(buy_signals)} buy signals and {len(sell_signals)} sell signals")
    
    # Show signal details
    if not buy_signals.empty or not sell_signals.empty:
        logger.info("Signal details:")
        
        for idx, row in df[df['signal'] != 0].iterrows():
            signal_type = "BUY" if row['signal'] == 1 else "SELL"
            logger.info(f"{idx}: {signal_type} - Price: {row[price_col]:.2f}, Fast MA: {row['fast_ma']:.2f}, Slow MA: {row['slow_ma']:.2f}")
    else:
        logger.warning("No signals generated!")
        
    # Check for NaN values in critical columns
    for col in ['fast_ma', 'slow_ma', 'ma_diff', 'prev_ma_diff']:
        nan_count = df[col].isna().sum()
        if nan_count > 0:
            logger.warning(f"Column {col} has {nan_count} NaN values")
    
    # Check if we have enough data after NaN values
    valid_data = df.dropna()
    logger.info(f"Valid data points after dropping NaN: {len(valid_data)} of {len(df)} ({len(valid_data)/len(df)*100:.2f}%)")
    
    # Test different MA window combinations if no signals are generated
    if len(buy_signals) == 0 and len(sell_signals) == 0:
        logger.info("Testing different MA window combinations to find signals")
        
        window_combinations = [
            (2, 5), (3, 8), (4, 10), (1, 3), (10, 20)
        ]
        
        for fast, slow in window_combinations:
            if fast >= slow:
                continue
                
            logger.info(f"Testing windows: fast={fast}, slow={slow}")
            
            test_df = df.copy()
            test_df['fast_ma'] = test_df[price_col].rolling(window=fast).mean()
            test_df['slow_ma'] = test_df[price_col].rolling(window=slow).mean()
            test_df['ma_diff'] = test_df['fast_ma'] - test_df['slow_ma']
            test_df['prev_ma_diff'] = test_df['ma_diff'].shift(1)
            
            # Buy signal: fast MA crosses above slow MA
            buy_condition = (test_df['prev_ma_diff'] <= 0) & (test_df['ma_diff'] > 0)
            test_df.loc[buy_condition, 'signal'] = 1
            
            # Sell signal: fast MA crosses below slow MA
            sell_condition = (test_df['prev_ma_diff'] >= 0) & (test_df['ma_diff'] < 0)
            test_df.loc[sell_condition, 'signal'] = -1
            
            buy_count = len(test_df[test_df['signal'] == 1])
            sell_count = len(test_df[test_df['signal'] == -1])
            
            logger.info(f"Windows {fast}/{slow}: {buy_count} buy signals, {sell_count} sell signals")
    
    return df

def main():
    """Main entry point."""
    data_file = "./data/HEAD_1min.csv"
    
    if not os.path.exists(data_file):
        logger.error(f"Data file not found: {data_file}")
        return
    
    # Load data
    df = load_csv_data(data_file)
    if df is None:
        return
    
    # Test MA crossover with different window combinations
    window_combinations = [
        (5, 15),  # Default from config
        (2, 5),   # Very short windows
        (3, 10),  # More signals
        (1, 3)    # Extreme case
    ]
    
    for fast, slow in window_combinations:
        logger.info(f"\n===== Testing MA windows {fast}/{slow} =====")
        result_df = test_ma_crossover(df.copy(), fast_window=fast, slow_window=slow)
        
        # Save signals to CSV for inspection
        signals_df = result_df[result_df['signal'] != 0].copy()
        if not signals_df.empty:
            output_file = f"./ma_signals_{fast}_{slow}.csv"
            signals_df.to_csv(output_file)
            logger.info(f"Saved {len(signals_df)} signals to {output_file}")

if __name__ == "__main__":
    main()
