#!/usr/bin/env python
"""
Direct Train/Test Split Fix

This script directly implements a train/test split without going through
the optimization framework, to isolate the issue.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('direct_fix.log')
    ]
)
logger = logging.getLogger('direct_fix')

def create_direct_train_test_split():
    """
    Create a direct train/test split without using the framework.
    This is to verify if the data can be properly split.
    """
    # Load data directly
    logger.info("Loading SPY 1min data directly")
    data_path = "data/SPY_1min.csv"
    
    if not os.path.exists(data_path):
        logger.error(f"Data file not found: {data_path}")
        return False
    
    # Load CSV data
    df = pd.read_csv(data_path)
    logger.info(f"Loaded {len(df)} rows from {data_path}")
    
    # Convert timestamp to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Create a simple train/test split - 70/30
    split_idx = int(len(df) * 0.7)
    
    # Create deep copies of the data to ensure isolation
    train_df = df.iloc[:split_idx].copy(deep=True)
    test_df = df.iloc[split_idx:].copy(deep=True)
    
    # Reset indices to avoid any shared state
    train_df = train_df.reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)
    
    # Add split markers for debugging
    train_df['_split'] = 'train'
    test_df['_split'] = 'test'
    
    logger.info(f"Created train dataset with {len(train_df)} rows")
    logger.info(f"Created test dataset with {len(test_df)} rows")
    
    # Verify train and test have no overlapping timestamps
    train_timestamps = set(train_df['timestamp'].astype(str))
    test_timestamps = set(test_df['timestamp'].astype(str))
    overlap = train_timestamps.intersection(test_timestamps)
    
    if overlap:
        logger.error(f"FOUND {len(overlap)} OVERLAPPING TIMESTAMPS!")
        logger.error(f"Example overlaps: {list(overlap)[:5]}")
    else:
        logger.info("SUCCESS: No overlapping timestamps between train and test.")
    
    # Run a simple strategy on both datasets
    # We'll use the same parameters, but if datasets are different,
    # results should be different
    
    # Simple Moving Average Crossover
    def run_simple_ma_strategy(data, fast_window=10, slow_window=30):
        """Run a simple MA strategy on the data"""
        result_df = data.copy()

        # Check for column names
        price_col = 'Close' if 'Close' in result_df.columns else 'close'
        logger.info(f"Using price column: {price_col}")

        # Calculate MAs
        result_df['fast_ma'] = result_df[price_col].rolling(window=fast_window).mean()
        result_df['slow_ma'] = result_df[price_col].rolling(window=slow_window).mean()

        # Create a signal
        result_df['signal'] = 0
        result_df.loc[result_df['fast_ma'] > result_df['slow_ma'], 'signal'] = 1
        result_df.loc[result_df['fast_ma'] < result_df['slow_ma'], 'signal'] = -1

        # Calculate strategy returns
        result_df['returns'] = result_df[price_col].pct_change()
        result_df['strategy_returns'] = result_df['signal'].shift() * result_df['returns']
        
        # Calculate cumulative returns
        result_df['cum_returns'] = (1 + result_df['strategy_returns']).cumprod()
        
        # Simple performance metrics
        metrics = {
            'total_return': result_df['cum_returns'].iloc[-1] - 1 if len(result_df) > 0 else 0,
            'sharpe_ratio': result_df['strategy_returns'].mean() / result_df['strategy_returns'].std() * np.sqrt(252) if len(result_df) > 0 else 0,
            'num_trades': len(result_df[result_df['signal'].diff() != 0]) if len(result_df) > 0 else 0
        }
        
        return result_df, metrics
    
    # Run strategy on both datasets
    logger.info("Running strategy on train dataset...")
    train_results, train_metrics = run_simple_ma_strategy(train_df)
    
    logger.info("Running strategy on test dataset...")
    test_results, test_metrics = run_simple_ma_strategy(test_df)
    
    # Compare results
    logger.info(f"Train results: {train_metrics}")
    logger.info(f"Test results: {test_metrics}")
    
    # Verify the results are different
    if (train_metrics['total_return'] == test_metrics['total_return'] and
        train_metrics['sharpe_ratio'] == test_metrics['sharpe_ratio']):
        logger.error("ISSUE: Train and test results are identical!")
        return False
    else:
        logger.info("SUCCESS: Train and test results are different as expected!")
        
        # Calculate difference percentage for clarity
        tr_diff_pct = (abs(train_metrics['total_return'] - test_metrics['total_return']) / 
                       (abs(train_metrics['total_return']) + 0.0001)) * 100
        sr_diff_pct = (abs(train_metrics['sharpe_ratio'] - test_metrics['sharpe_ratio']) / 
                       (abs(train_metrics['sharpe_ratio']) + 0.0001)) * 100
        
        logger.info(f"Total return difference: {tr_diff_pct:.2f}%")
        logger.info(f"Sharpe ratio difference: {sr_diff_pct:.2f}%")
        
        # If differences are very small, still consider it an issue
        if tr_diff_pct < 1.0 and sr_diff_pct < 1.0:
            logger.warning("WARNING: Differences are very small (< 1%), which might indicate a subtle issue")
        
        return True
    
if __name__ == "__main__":
    logger.info("Starting direct train/test split verification")
    
    if create_direct_train_test_split():
        logger.info("✅ VERIFICATION PASSED: Train/test split is working correctly in isolation")
        sys.exit(0)
    else:
        logger.error("❌ VERIFICATION FAILED: Train/test split is not working correctly")
        sys.exit(1)