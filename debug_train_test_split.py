#!/usr/bin/env python
"""
Debug Train/Test Split

This script diagnoses if training and testing datasets are correctly isolated.
It adds comprehensive logging and verification steps to identify data leakage issues.
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import yaml
import time
import hashlib

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_train_test_split.log')
    ]
)
logger = logging.getLogger('debug_train_test')

# Add src to path
src_path = str(Path(__file__).parent / 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import relevant modules
from data.historical_data_handler import HistoricalDataHandler
from data.time_series_splitter import TimeSeriesSplitter
from execution.backtest.optimizing_backtest import OptimizingBacktest
from strategy.optimization.parameter_space import ParameterSpace
from core.config.config import Config
from strategy.strategy_factory import StrategyFactory

def data_fingerprint(df):
    """Create a unique fingerprint of a DataFrame for comparison"""
    if df is None or df.empty:
        return "empty_dataframe"
    
    # Use first 5 and last 5 rows for fingerprinting
    sample_rows = pd.concat([df.head(5), df.tail(5)])
    # Convert to string and hash
    hash_obj = hashlib.md5(pd.util.hash_pandas_object(sample_rows).values)
    return hash_obj.hexdigest()

def inspect_dataframe(df, name, detailed=False):
    """Inspect a DataFrame and return key statistics"""
    if df is None or df.empty:
        logger.warning(f"{name} DataFrame is empty or None")
        return
    
    logger.info(f"===== {name} DataFrame Inspection =====")
    logger.info(f"Shape: {df.shape}")
    logger.info(f"Date range: {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
    logger.info(f"Fingerprint: {data_fingerprint(df)}")
    
    if detailed:
        logger.info(f"First 5 rows:\n{df.head()}")
        logger.info(f"Last 5 rows:\n{df.tail()}")
        logger.info(f"Column info: {df.dtypes}")
        logger.info(f"Memory usage: {df.memory_usage().sum() / 1024**2:.2f} MB")
        if '_split' in df.columns:
            logger.info(f"Split marker: {df['_split'].unique()}")
        
    logger.info("=" * 50)

def debug_time_series_splitter():
    """Debug the TimeSeriesSplitter directly"""
    logger.info("\n\nTesting TimeSeriesSplitter in isolation")
    logger.info("=" * 50)
    
    # Create a simple test DataFrame
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    data = {
        'timestamp': dates,
        'value': np.arange(100),
        'close': np.random.randn(100).cumsum() + 100
    }
    test_df = pd.DataFrame(data)
    
    logger.info(f"Created test DataFrame with shape {test_df.shape}")
    inspect_dataframe(test_df, "Original Test Data")
    
    # Create a splitter with ratio method
    splitter = TimeSeriesSplitter(
        method="ratio",
        train_ratio=0.7,
        test_ratio=0.3
    )
    
    # Split the data
    split_data = splitter.split(test_df)
    train_df = split_data['train']
    test_df = split_data['test']
    
    # Inspect results
    inspect_dataframe(train_df, "Train Split (Direct)", detailed=True)
    inspect_dataframe(test_df, "Test Split (Direct)", detailed=True)
    
    # Check if the original DataFrame was modified
    logger.info("Checking for data isolation:")
    logger.info(f"Train shape: {train_df.shape}, Test shape: {test_df.shape}")
    logger.info(f"Are train and test DataFrames the same object? {train_df is test_df}")
    
    # Check if modifying one affects the other
    logger.info("Testing data isolation by modifying train DataFrame")
    if not train_df.empty:
        original_train_value = train_df.iloc[0]['value']
        train_df.iloc[0, train_df.columns.get_loc('value')] = 9999
        logger.info(f"Modified train_df[0, 'value'] to 9999")
        logger.info(f"Now train_df[0, 'value'] = {train_df.iloc[0]['value']}")
        logger.info(f"test_df first few rows:\n{test_df.head()}")
        
        # Check if test_df has been affected
        if not test_df.empty and 'value' in test_df.columns:
            if test_df.iloc[0]['value'] == 9999:
                logger.error("🛑 DATA LEAKAGE DETECTED: Modifying train affects test!")
            else:
                logger.info("✅ No data leakage detected. Modifications to train don't affect test.")

def debug_data_handler_with_config(config_path):
    """Debug HistoricalDataHandler with a specific configuration file"""
    logger.info("\n\nTesting HistoricalDataHandler with config file")
    logger.info("=" * 50)
    
    # Load config
    with open(config_path, 'r') as file:
        config_data = yaml.safe_load(file)
    
    logger.info(f"Loaded config from {config_path}")
    
    # Create data handler
    data_config = config_data.get('data', {})
    max_bars = config_data.get('max_bars', None)

    if max_bars:
        data_config['max_bars'] = max_bars
        logger.info(f"Using max_bars={max_bars} from config")

    # We need to create a minimal implementation of an event bus for the context
    class MockEventBus:
        def __init__(self):
            self.handlers = {}

        def subscribe(self, event_type, handler):
            if event_type not in self.handlers:
                self.handlers[event_type] = []
            self.handlers[event_type].append(handler)

        def publish(self, event):
            # Just log the event without actually publishing
            logger.info(f"MockEventBus received event: {event}")
            return True

        def reset(self):
            self.handlers = {}

    # Create a context with mock event bus and other required elements
    mock_event_bus = MockEventBus()
    context = {
        'event_bus': mock_event_bus,
        'shared_context': {
            'max_bars': max_bars
        } if max_bars else {}
    }

    # Create and initialize the data handler
    data_handler = HistoricalDataHandler("debug_data_handler", data_config)
    try:
        data_handler.initialize(context)
        logger.info("Successfully initialized data handler")
    except Exception as e:
        logger.error(f"Failed to initialize data handler: {str(e)}")
        # Continue with a simplified test that doesn't require a full data handler
    
    # Get symbols
    symbols = data_handler.get_symbols()
    logger.info(f"Data handler initialized with symbols: {symbols}")
    
    # Examine all data splits for each symbol
    for symbol in symbols:
        logger.info(f"\nExamining data for symbol: {symbol}")
        
        # Get raw data (if available)
        if hasattr(data_handler, '_data') and symbol in data_handler._data:
            raw_data = data_handler._data[symbol]
            inspect_dataframe(raw_data, f"{symbol} Raw Data")
        
        # Switch to train split and get the data
        if hasattr(data_handler, 'set_active_split'):
            data_handler.set_active_split('train')
        else:
            # If there's no method to set the split, we might need to access data directly
            logger.warning("No set_active_split method found, trying to access data directly")

        # Access internal data structures
        if hasattr(data_handler, 'data_splits') and symbol in data_handler.data_splits:
            train_data = data_handler.data_splits[symbol].get('train')
            inspect_dataframe(train_data, f"{symbol} Train Data", detailed=True)

            # Get test data
            test_data = data_handler.data_splits[symbol].get('test')
            inspect_dataframe(test_data, f"{symbol} Test Data", detailed=True)
        else:
            # If data_splits is not available, try to access raw data
            if hasattr(data_handler, 'data') and symbol in data_handler.data:
                raw_data = data_handler.data[symbol]
                logger.info(f"No train/test splits found. Examining raw data for {symbol}.")
                inspect_dataframe(raw_data, f"{symbol} Raw Data", detailed=True)
            else:
                logger.error(f"No data found for symbol {symbol}")
        
        # Check for overlapping timestamps
        if train_data is not None and test_data is not None:
            train_timestamps = set(train_data['timestamp'].astype(str))
            test_timestamps = set(test_data['timestamp'].astype(str))
            overlap = train_timestamps.intersection(test_timestamps)
            
            if overlap:
                logger.error(f"🛑 DATA LEAKAGE: Found {len(overlap)} overlapping timestamps between train and test!")
                logger.error(f"Example overlapping timestamps: {list(overlap)[:5]}")
            else:
                logger.info("✅ No overlapping timestamps between train and test datasets")
        
        # Check memory addresses to confirm they're different objects
        if train_data is not None and test_data is not None:
            logger.info(f"Train data memory id: {id(train_data)}")
            logger.info(f"Test data memory id: {id(test_data)}")
            if id(train_data) == id(test_data):
                logger.error("🛑 CRITICAL ISSUE: Train and test are the same DataFrame object!")
            else:
                logger.info("✅ Train and test are different DataFrame objects")
        
        # Test modification isolation
        if train_data is not None and not train_data.empty and test_data is not None and not test_data.empty:
            original_train_val = train_data.iloc[0]['close']
            logger.info(f"Modifying first row of train_data 'close' column from {original_train_val} to 999999")
            train_data.loc[0, 'close'] = 999999
            
            # Check if test data was modified
            if 'close' in test_data.columns and len(test_data) > 0:
                if test_data.iloc[0]['close'] == 999999:
                    logger.error("🛑 DATA LEAKAGE: Modifying train_data affected test_data!")
                else:
                    logger.info("✅ Modifying train_data did not affect test_data")

def trace_optimization_process(config_path):
    """Trace the optimization process to identify where data leakage might occur"""
    logger.info("\n\nTracing Optimization Process")
    logger.info("=" * 50)
    
    # Load config
    with open(config_path, 'r') as file:
        config_data = yaml.safe_load(file)
        
    # Set up optimization parameters for minimal test
    max_bars = 1000  # Use a small number for faster testing
    config_data['max_bars'] = max_bars
    
    # Simplify parameter space for debugging
    config_data['parameter_space'] = [
        {
            'name': 'fast_window',
            'type': 'integer',
            'values': [10, 20]  # Just two values for debugging
        },
        {
            'name': 'slow_window',
            'type': 'integer',
            'values': [30, 40]  # Just two values for debugging
        }
    ]
    
    # Create parameter space
    param_space = ParameterSpace()
    param_space.from_dict({'parameters': config_data['parameter_space']})
    logger.info(f"Created parameter space with {len(param_space)} combinations")
    
    # Create backtest configuration
    backtest_config = {}
    if 'backtest' in config_data:
        backtest_config.update(config_data['backtest'])
    if 'data' in config_data:
        backtest_config['data'] = config_data['data']
    if 'max_bars' in config_data:
        backtest_config['max_bars'] = config_data['max_bars']
    
    logger.info(f"Created backtest config with max_bars={backtest_config.get('max_bars')}")
    
    # Create optimizing backtest
    optimizer = OptimizingBacktest('debug_optimizer', backtest_config, param_space)
    
    # Set up strategy factory for the context
    strategy_dirs = [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'strategy', 'implementations')]
    factory = StrategyFactory(strategy_dirs)
    
    context = {'strategy_factory': factory}
    
    # Initialize optimizer
    optimizer.initialize(context)
    
    # Trace a single parameter evaluation process
    strategy_name = config_data['strategy']['name']
    logger.info(f"Tracing evaluation for strategy: {strategy_name}")
    
    # Get the first parameter combination
    first_params = next(param_space.get_combinations())
    logger.info(f"Testing with parameters: {first_params}")
    
    # Pre-optimization data check
    if hasattr(optimizer, '_data_handler'):
        data_handler = optimizer._data_handler
        symbols = data_handler.get_symbols()
        
        for symbol in symbols:
            logger.info(f"\nPre-optimization data check for {symbol}")
            
            train_data = data_handler.get_data_for_symbol(symbol, 'train')
            test_data = data_handler.get_data_for_symbol(symbol, 'test')
            
            train_fingerprint = data_fingerprint(train_data)
            test_fingerprint = data_fingerprint(test_data)
            
            logger.info(f"Train data fingerprint: {train_fingerprint}")
            logger.info(f"Test data fingerprint: {test_fingerprint}")
            
            if train_fingerprint == test_fingerprint:
                logger.error("🛑 CRITICAL ISSUE: Train and test data have identical fingerprints!")
            else:
                logger.info("✅ Train and test data have different fingerprints")
    
    # Run train and test backtests separately to monitor the process
    logger.info("\nRunning training backtest")
    train_results = optimizer._run_backtest_with_params(
        strategy_name, 
        first_params, 
        'train',
        config_data.get('data', {}).get('train_test_split', {})
    )
    
    logger.info("\nRunning testing backtest")
    test_results = optimizer._run_backtest_with_params(
        strategy_name, 
        first_params, 
        'test',
        config_data.get('data', {}).get('train_test_split', {})
    )
    
    # Compare results
    logger.info("\nComparing train and test results")
    if train_results and test_results:
        # Check equity curves
        train_equity = train_results.get('equity_curve')
        test_equity = test_results.get('equity_curve')
        
        if train_equity is not None and test_equity is not None:
            train_eq_fingerprint = data_fingerprint(train_equity)
            test_eq_fingerprint = data_fingerprint(test_equity)
            
            logger.info(f"Train equity curve fingerprint: {train_eq_fingerprint}")
            logger.info(f"Test equity curve fingerprint: {test_eq_fingerprint}")
            
            if train_eq_fingerprint == test_eq_fingerprint:
                logger.error("🛑 ISSUE: Train and test equity curves have identical fingerprints!")
            else:
                logger.info("✅ Train and test equity curves have different fingerprints")
        
        # Compare statistics
        train_stats = train_results.get('statistics', {})
        test_stats = test_results.get('statistics', {})
        
        logger.info("\nTrain Statistics:")
        for key, value in train_stats.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("\nTest Statistics:")
        for key, value in test_stats.items():
            logger.info(f"  {key}: {value}")
        
        # Check if metrics are identical
        identical_metrics = []
        different_metrics = []
        
        for key in set(train_stats.keys()).intersection(test_stats.keys()):
            train_val = train_stats.get(key)
            test_val = test_stats.get(key)
            
            if isinstance(train_val, (int, float)) and isinstance(test_val, (int, float)):
                if abs(train_val - test_val) < 0.0001:
                    identical_metrics.append(key)
                else:
                    different_metrics.append((key, train_val, test_val))
        
        if identical_metrics:
            logger.warning(f"Found {len(identical_metrics)} identical metrics between train and test:")
            logger.warning(f"  {', '.join(identical_metrics)}")
        
        if different_metrics:
            logger.info(f"Found {len(different_metrics)} different metrics between train and test:")
            for key, train_val, test_val in different_metrics:
                logger.info(f"  {key}: train={train_val}, test={test_val}")

if __name__ == "__main__":
    config_path = "config/simple_ma_optimization.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    logger.info(f"Starting train/test debug with config: {config_path}")
    
    # Run tests in sequence
    debug_time_series_splitter()
    debug_data_handler_with_config(config_path)
    trace_optimization_process(config_path)
    
    logger.info("Debug complete. Check the log for results.")