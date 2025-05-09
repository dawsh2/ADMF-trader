#!/usr/bin/env python
"""
Debug script for ADMF-Trader optimization issues.

This script helps diagnose problems with the optimization process,
particularly focused on the case where all strategy parameters are
showing negative returns and zero Sharpe ratios.
"""

import os
import sys
import logging
import yaml
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def examine_data_file(file_path):
    """
    Examine the data file to ensure it's properly formatted.
    
    Args:
        file_path (str): Path to the data file
    """
    logger.info(f"Examining data file: {file_path}")
    
    try:
        # Load data
        df = pd.read_csv(file_path)
        
        # Print basic info
        print(f"\nData file: {file_path}")
        print(f"Shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Check for required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"WARNING: Missing required columns: {missing_columns}")
        
        # Check for data issues
        print("\nChecking for data issues...")
        
        # Check for missing values
        na_count = df.isna().sum()
        if na_count.sum() > 0:
            print(f"WARNING: Found {na_count.sum()} missing values:")
            for col, count in na_count.items():
                if count > 0:
                    print(f"  {col}: {count} missing values")
        else:
            print("No missing values found.")
        
        # Check for zero or negative prices
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                zero_count = (df[col] <= 0).sum()
                if zero_count > 0:
                    print(f"WARNING: Found {zero_count} zero or negative values in {col}")
        
        # Print sample data
        print("\nSample data:")
        print(df.head())
        
        # Plot price series
        if 'close' in df.columns:
            plt.figure(figsize=(12, 6))
            plt.plot(df['close'].values)
            plt.title('Close Price Series')
            plt.savefig('debug_price_series.png')
            print(f"Price series plot saved to debug_price_series.png")
        
        return df
    except Exception as e:
        logger.error(f"Error examining data file: {e}")
        return None

def test_strategy_single_run(data_file, params):
    """
    Test the strategy with a single set of parameters to see basic functionality.
    
    Args:
        data_file (str): Path to data file
        params (dict): Strategy parameters to test
    """
    from src.data.historical_data_handler import HistoricalDataHandler
    from src.core.event_bus import SimpleEventBus, EventType
    from src.core.trade_repository import TradeRepository
    from src.execution.backtest.backtest_coordinator import BacktestCoordinator
    from src.strategy.strategy_factory import StrategyFactory
    
    logger.info(f"Testing strategy with parameters: {params}")
    
    try:
        # Create event bus
        event_bus = SimpleEventBus()
        
        # Create trade repository
        trade_repository = TradeRepository()
        
        # Create strategy factory
        strategy_factory = StrategyFactory()
        
        # Configure data
        data_config = {
            'sources': [
                {
                    'symbol': 'TEST',
                    'file': data_file,
                    'date_column': 'timestamp',
                    'date_format': '%Y-%m-%d %H:%M:%S'
                }
            ]
        }
        
        # Create data handler
        data_handler = HistoricalDataHandler("data_handler", data_config)
        
        # Create context
        context = {
            'event_bus': event_bus,
            'trade_repository': trade_repository,
            'strategy_factory': strategy_factory
        }
        
        # Initialize data handler
        data_handler.initialize(context)
        
        # Create backtest configuration
        backtest_config = {
            'initial_capital': 100000.0,
            'commission': 0.001,
            'slippage': 0.0005
        }
        
        # Create backtest coordinator
        backtest = BacktestCoordinator("backtest", backtest_config)
        
        # Create strategy with parameters
        strategy_params = dict(params)  # Copy parameters
        strategy_params['name'] = 'strategy'  # Add required name parameter
        strategy = strategy_factory.create_strategy("simple_ma_crossover", **strategy_params)
        
        # Create portfolio and other required components
        from src.execution.portfolio import Portfolio
        from src.execution.broker.simulated_broker import SimulatedBroker
        from src.execution.order_manager import OrderManager
        
        portfolio = Portfolio("portfolio", backtest_config.get('initial_capital', 100000))
        broker = SimulatedBroker("broker")
        order_manager = OrderManager("order_manager")
        
        # Add components to backtest
        backtest.add_component('data_handler', data_handler)
        backtest.add_component('strategy', strategy)
        backtest.add_component('portfolio', portfolio)
        backtest.add_component('broker', broker)
        backtest.add_component('order_manager', order_manager)
        
        # Initialize backtest
        backtest.initialize(context)
        
        # Set up debugging listeners
        backtest.event_bus.subscribe(EventType.SIGNAL, lambda e: logger.debug(f"SIGNAL: {e.data}"))
        backtest.event_bus.subscribe(EventType.ORDER, lambda e: logger.debug(f"ORDER: {e.data}"))
        backtest.event_bus.subscribe(EventType.FILL, lambda e: logger.debug(f"FILL: {e.data}"))
        
        # Setup and run backtest
        backtest.setup()
        results = backtest.run()
        
        # Print results
        print("\nBacktest Results:")
        print(f"Initial Capital: {backtest_config['initial_capital']}")
        print(f"Final Equity: {results.get('final_equity', 0)}")
        print(f"Return: {results.get('return_pct', 0):.2f}%")
        print(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.4f}")
        
        trades = results.get('trades', [])
        print(f"Total Trades: {len(trades)}")
        
        if trades:
            print("\nSample Trades:")
            for i, trade in enumerate(trades[:5]):
                print(f"Trade {i+1}: {trade}")
        
        return results
    except Exception as e:
        logger.error(f"Error testing strategy: {e}")
        import traceback
        traceback.print_exc()
        return None

def inspect_strategy_implementation():
    """
    Inspect the strategy implementation to identify potential issues.
    """
    # Try to find the strategy implementation file
    import importlib.util
    import inspect
    
    strategy_paths = [
        'src/strategy/implementations/simple_ma_crossover.py',
        'src/strategy/implementations/ma_crossover_strategy.py',
        'src/strategy/ma_crossover_strategy.py',
        'src/strategy/simple_ma_crossover.py'
    ]
    
    for path in strategy_paths:
        if os.path.exists(path):
            print(f"\nExamining strategy file: {path}")
            with open(path, 'r') as f:
                print(f.read())
            return path
    
    print("\nStrategy implementation file not found. Searching for it...")
    
    # Search for the strategy implementation
    for root, dirs, files in os.walk('src'):
        for file in files:
            if 'ma_crossover' in file.lower() or 'simple_ma' in file.lower():
                path = os.path.join(root, file)
                print(f"\nFound potential strategy file: {path}")
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                        if 'class SimpleMACrossoverStrategy' in content or 'class MACrossoverStrategy' in content:
                            print(f"Strategy implementation found at {path}")
                            print(content)
                            return path
                except Exception as e:
                    print(f"Error reading file: {e}")
    
    print("\nStrategy implementation not found.")
    return None

def analyze_optimization_log(log_file):
    """
    Analyze an optimization log file to identify patterns or issues.
    
    Args:
        log_file (str): Path to the log file
    """
    try:
        with open(log_file, 'r') as f:
            content = f.read()
            
        print(f"\nAnalyzing optimization log: {log_file}")
        
        # Check for common error patterns
        error_patterns = [
            "Error", "Exception", "ValueError", "TypeError", 
            "AttributeError", "KeyError", "IndexError"
        ]
        
        for pattern in error_patterns:
            if pattern in content:
                print(f"Found potential issue: '{pattern}' in log")
                
                # Find context around the error
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if pattern in line:
                        start = max(0, i - 5)
                        end = min(len(lines), i + 5)
                        print("\nError context:")
                        for j in range(start, end):
                            if j == i:
                                print(f">>> {lines[j]}")
                            else:
                                print(f"    {lines[j]}")
                                
        return content
    except Exception as e:
        logger.error(f"Error analyzing log file: {e}")
        return None

def debug_parameter_space():
    """
    Debug parameter space and optimization settings.
    """
    from src.strategy.optimization.parameter_space import ParameterSpace, IntegerParameter

    # Create sample parameter space
    param_space = ParameterSpace()
    
    # Add parameter properly using the existing API
    fast_param = IntegerParameter('fast_period', 5, 30, 5)
    slow_param = IntegerParameter('slow_period', 20, 100, 20)
    
    param_space.add_parameter(fast_param)
    param_space.add_parameter(slow_param)
    
    # Print parameter combinations
    combinations = param_space.get_combinations()
    print(f"\nParameter space has {len(combinations)} combinations:")
    for i, params in enumerate(combinations):
        print(f"  {i+1}: {params}")
    
    return param_space

def debug_data_splitting():
    """
    Debug the train/test data splitting functionality.
    """
    from src.data.time_series_splitter import TimeSeriesSplitter
    
    # Create sample data
    dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
    df = pd.DataFrame({'timestamp': dates, 'close': np.random.randn(100).cumsum() + 100})
    
    # Create splitter with different methods
    methods = ['ratio', 'date', 'fixed']
    
    for method in methods:
        print(f"\nTesting {method} split method:")
        if method == 'ratio':
            splitter = TimeSeriesSplitter(method=method, train_ratio=0.7, test_ratio=0.3)
        elif method == 'date':
            split_date = dates[70]
            splitter = TimeSeriesSplitter(method=method, split_date=split_date)
        else:  # fixed
            splitter = TimeSeriesSplitter(method=method, train_periods=70, test_periods=30)
            
        # Split the data
        splits = splitter.split(df)
        
        # Print split info
        print(f"  Train data: {len(splits['train'])} rows ({splits['train']['timestamp'].min()} to {splits['train']['timestamp'].max()})")
        print(f"  Test data:  {len(splits['test'])} rows ({splits['test']['timestamp'].min()} to {splits['test']['timestamp'].max()})")
    
    return True

def debug_event_flow():
    """
    Debug the event flow during a backtest to identify where signals or orders might be lost.
    """
    from src.core.event_bus import SimpleEventBus, EventType
    
    class EventTracker:
        def __init__(self):
            self.events = {
                EventType.BAR: [],
                EventType.SIGNAL: [],
                EventType.ORDER: [],
                EventType.FILL: [],
                EventType.TRADE: []
            }
            
        def track_event(self, event_type, event):
            self.events[event_type].append(event)
            
        def print_summary(self):
            print("\nEvent Flow Summary:")
            for event_type, events in self.events.items():
                print(f"  {event_type.name}: {len(events)} events")
                
            # Print sample events
            for event_type, events in self.events.items():
                if events:
                    print(f"\nSample {event_type.name} events:")
                    for i, event in enumerate(events[:3]):
                        print(f"  {i+1}: {event.data}")
    
    # This function would be used during a backtest to track events
    print("Event tracker created for use in backtest.")
    return EventTracker()

def debug_optimization_process():
    """
    Debug the optimization process itself.
    """
    # Check optimization config
    config_files = [
        'config/ma_crossover_optimization.yaml',
        'config/optimization/ma_crossover_optimization.yaml'
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"\nExamining optimization config: {config_file}")
            try:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    
                print(f"Strategy: {config.get('strategy', {}).get('name')}")
                print(f"Parameter space: {config.get('parameter_space')}")
                print(f"Objective function: {config.get('optimization', {}).get('objective')}")
                print(f"Data sources: {config.get('data', {}).get('sources')}")
                
                return config
            except Exception as e:
                print(f"Error reading config file: {e}")
    
    print("\nOptimization config not found.")
    return None

def look_for_empty_trade_records():
    """
    Look for empty trade records in results files.
    """
    result_files = []
    
    # Look in optimization_results directory
    if os.path.exists('./optimization_results'):
        for file in os.listdir('./optimization_results'):
            if file.endswith('.json'):
                result_files.append(os.path.join('./optimization_results', file))
    
    # Look in results directory
    if os.path.exists('./results'):
        for file in os.listdir('./results'):
            if file.endswith('.json'):
                result_files.append(os.path.join('./results', file))
    
    # Process found files
    if not result_files:
        print("\nNo result files found to analyze trade records.")
        return
    
    print(f"\nFound {len(result_files)} result files to analyze.")
    
    for result_file in result_files:
        try:
            with open(result_file, 'r') as f:
                results = json.load(f)
                
            print(f"\nAnalyzing {result_file}:")
            
            # Check if results contains trades
            train_results = results.get('train_results', {})
            test_results = results.get('test_results', {})
            
            train_trades = train_results.get('trades', [])
            test_trades = test_results.get('trades', [])
            
            print(f"  Train trades: {len(train_trades)}")
            print(f"  Test trades: {len(test_trades)}")
            
            # Check for empty trade details
            if train_trades:
                empty_train_pnl = sum(1 for t in train_trades if t.get('pnl', 0) == 0)
                print(f"  Train trades with zero PnL: {empty_train_pnl} ({empty_train_pnl/len(train_trades)*100:.1f}%)")
                
                # Check a sample trade
                print(f"  Sample train trade: {train_trades[0] if train_trades else 'None'}")
            
            if test_trades:
                empty_test_pnl = sum(1 for t in test_trades if t.get('pnl', 0) == 0)
                print(f"  Test trades with zero PnL: {empty_test_pnl} ({empty_test_pnl/len(test_trades)*100:.1f}%)")
                
                # Check a sample trade
                print(f"  Sample test trade: {test_trades[0] if test_trades else 'None'}")
                
        except Exception as e:
            print(f"  Error analyzing {result_file}: {e}")

def main():
    """Main debug function."""
    
    debug_dir = "debug_output"
    os.makedirs(debug_dir, exist_ok=True)
    
    print("=" * 80)
    print("ADMF-Trader Optimization Debug Script")
    print("=" * 80)
    
    # 1. Check data file
    data_file = "data/HEAD_1min.csv"
    if os.path.exists(data_file):
        data = examine_data_file(data_file)
    else:
        print(f"Data file not found: {data_file}")
        
    # 2. Inspect strategy implementation
    strategy_file = inspect_strategy_implementation()
    
    # 3. Debug parameter space
    param_space = debug_parameter_space()
    
    # 4. Debug data splitting
    debug_data_splitting()
    
    # 5. Test strategy with a single set of parameters
    if os.path.exists(data_file):
        params = {'fast_period': 5, 'slow_period': 20}
        test_strategy_single_run(data_file, params)
        
    # 6. Analyze optimization logs
    log_files = [f for f in os.listdir('.') if f.endswith('.log') and ('optimize' in f or 'optimization' in f)]
    for log_file in log_files:
        analyze_optimization_log(log_file)
    
    # 7. Look for empty trade records
    look_for_empty_trade_records()
        
    # 8. Debug optimization process
    config = debug_optimization_process()
    
    print("\n" + "=" * 80)
    print("Debug complete. Check debug_output directory for results.")
    print("=" * 80)
    
if __name__ == "__main__":
    main()
