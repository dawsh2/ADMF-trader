#!/usr/bin/env python
"""
Debug tool for analyzing MA Crossover strategy.
This script will load data and run the MA strategy in isolation to verify it correctly
generates signals with the given data.
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
import datetime
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug_strategy.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("debug")

def load_data(file_path):
    """Load data from CSV file."""
    logger.info(f"Loading data from: {file_path}")
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} rows from {file_path}")
        logger.info(f"Columns: {df.columns.tolist()}")
        
        # Check if timestamp column exists
        timestamp_col = None
        for col in ['timestamp', 'date', 'datetime']:
            if col in df.columns:
                timestamp_col = col
                break
                
        if timestamp_col:
            # Convert to datetime
            if pd.api.types.is_string_dtype(df[timestamp_col]):
                df[timestamp_col] = pd.to_datetime(df[timestamp_col])
                logger.info(f"Converted {timestamp_col} to datetime")
                
            # Set as index
            df.set_index(timestamp_col, inplace=True)
            logger.info(f"Set {timestamp_col} as index")
        
        # Print data summary
        logger.info(f"Data range: {df.index.min()} to {df.index.max()}")
        logger.info(f"Data sample: \n{df.head()}")
        
        return df
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return None

def simulate_ma_crossover(df, fast_window=5, slow_window=15, price_col='close'):
    """Simulate MA crossover strategy on dataframe."""
    logger.info(f"Running MA Crossover simulation with fast={fast_window}, slow={slow_window}")
    
    # Ensure we have price data
    if price_col not in df.columns:
        available_cols = [c for c in df.columns if c.lower() in ['close', 'price', 'adjclose', 'adj_close', 'adj close']]
        if available_cols:
            price_col = available_cols[0]
            logger.info(f"Price column '{price_col}' not found, using '{price_col}' instead")
        else:
            logger.error(f"Price column not found in data. Available columns: {df.columns.tolist()}")
            return None
    
    try:
        # Calculate moving averages
        df['fast_ma'] = df[price_col].rolling(window=fast_window).mean()
        df['slow_ma'] = df[price_col].rolling(window=slow_window).mean()
        df['ma_diff'] = df['fast_ma'] - df['slow_ma']
        
        # Calculate crossover signals
        df['signal'] = 0
        df['prev_ma_diff'] = df['ma_diff'].shift(1)
        
        # Buy signal: fast MA crosses above slow MA (prev_diff <= 0 and current_diff > 0)
        buy_signals = (df['prev_ma_diff'] <= 0) & (df['ma_diff'] > 0)
        df.loc[buy_signals, 'signal'] = 1
        
        # Sell signal: fast MA crosses below slow MA (prev_diff >= 0 and current_diff < 0)
        sell_signals = (df['prev_ma_diff'] >= 0) & (df['ma_diff'] < 0)
        df.loc[sell_signals, 'signal'] = -1
        
        # Count signals
        buy_count = len(df[df['signal'] == 1])
        sell_count = len(df[df['signal'] == -1])
        logger.info(f"Generated {buy_count} buy signals and {sell_count} sell signals")
        
        # Show signal points
        signals = df[df['signal'] != 0].copy()
        if not signals.empty:
            logger.info("Signals generated:")
            for idx, row in signals.iterrows():
                signal_type = "BUY" if row['signal'] == 1 else "SELL"
                logger.info(f"{idx}: {signal_type} at price {row[price_col]:.2f}, fast_ma={row['fast_ma']:.2f}, slow_ma={row['slow_ma']:.2f}, diff={row['ma_diff']:.4f}")
        else:
            logger.warning("No signals were generated!")
            
        # Check data quality
        nan_count = df['fast_ma'].isna().sum()
        if nan_count > 0:
            logger.warning(f"Found {nan_count} NaN values in fast MA - this is normal for the first {fast_window-1} rows")
            
        nan_count = df['slow_ma'].isna().sum()
        if nan_count > 0:
            logger.warning(f"Found {nan_count} NaN values in slow MA - this is normal for the first {slow_window-1} rows")
            
        # Check for potential issues
        if buy_count == 0 and sell_count == 0:
            logger.warning("NO SIGNALS GENERATED! Possible issues:")
            
            # Check if we have enough data
            if len(df) <= slow_window:
                logger.warning(f"Not enough data: {len(df)} rows < {slow_window} (slow window)")
            
            # Check if MA difference is too small
            diff_range = df['ma_diff'].abs().max()
            if diff_range < 0.0001:
                logger.warning(f"MA difference range is very small: {diff_range:.6f}")
                
            # Check if we have any crossovers that might have been missed
            close_points = df[abs(df['ma_diff']) < 0.01]
            if not close_points.empty:
                logger.warning(f"Found {len(close_points)} points where MAs are very close (diff < 0.01):")
                logger.warning(f"{close_points.head()}")
                
            # Check for precision issues
            if (df['ma_diff'] == 0).any():
                exact_zero = df[df['ma_diff'] == 0]
                logger.warning(f"Found {len(exact_zero)} points with exactly zero difference (precision issue?):")
                logger.warning(f"{exact_zero.head()}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error simulating MA strategy: {e}")
        return None

def main():
    """Main entry point."""
    logger.info("Starting debug script")
    
    # Load data
    data_file = "./data/HEAD_1min.csv"
    if not os.path.exists(data_file):
        logger.error(f"Data file not found: {data_file}")
        return
    
    df = load_data(data_file)
    if df is None:
        return
    
    # Run strategy simulation with different windows to find good parameters
    windows = [
        (5, 15),  # Default in config
        (3, 10),  # Shorter for more signals
        (10, 30), # Longer for less noise
        (2, 5)    # Very short for more signals
    ]
    
    results = {}
    for fast, slow in windows:
        logger.info(f"\n\n===== Testing MA windows: fast={fast}, slow={slow} =====")
        result_df = simulate_ma_crossover(df.copy(), fast_window=fast, slow_window=slow)
        if result_df is not None:
            signal_count = len(result_df[result_df['signal'] != 0])
            results[(fast, slow)] = signal_count
    
    # Summary
    logger.info("\n===== SUMMARY =====")
    for windows, count in results.items():
        fast, slow = windows
        logger.info(f"Windows {fast}/{slow}: {count} signals")
    
    best_windows = max(results.items(), key=lambda x: x[1])[0]
    logger.info(f"Best windows for signal generation: fast={best_windows[0]}, slow={best_windows[1]} with {results[best_windows]} signals")
    
    logger.info("Debug script completed")

if __name__ == "__main__":
    main()
