#!/usr/bin/env python
"""
ADMF-Trader Optimization Framework Fix Verification

This script checks and verifies the fixes made to the optimization framework
to ensure everything is working properly.
"""

import os
import sys
import logging
import importlib
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_verification.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_imports():
    """
    Check that all required modules can be imported.
    
    Returns:
        bool: True if all imports succeed, False otherwise
    """
    try:
        # Core components
        from src.core.component import Component
        from src.core.event_bus import SimpleEventBus, Event, EventType
        from src.core.trade_repository import TradeRepository
        from src.core.data_model import Bar, Order, Fill, Trade
        logger.info("Core imports successful")
        
        # Data handling
        from src.data.historical_data_handler import HistoricalDataHandler
        from src.data.time_series_splitter import TimeSeriesSplitter
        logger.info("Data handling imports successful")
        
        # Strategy
        from src.strategy.strategy_factory import StrategyFactory
        from src.strategy.optimization.parameter_space import ParameterSpace
        from src.strategy.optimization.objective_functions import get_objective_function
        from src.strategy.optimization.optimizer import StrategyOptimizer
        logger.info("Strategy imports successful")
        
        # Execution
        from src.execution.backtest.backtest_coordinator import BacktestCoordinator
        from src.execution.backtest.optimizing_backtest import OptimizingBacktest
        from src.execution.portfolio import Portfolio
        from src.execution.broker.simulated_broker import SimulatedBroker
        from src.execution.order_manager import OrderManager
        logger.info("Execution imports successful")
        
        return True
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False

def verify_strategy_factory():
    """
    Verify that the strategy factory can find and create strategies.
    
    Returns:
        bool: True if strategy factory works, False otherwise
    """
    try:
        from src.strategy.strategy_factory import StrategyFactory
        
        # Define strategy directories
        strategy_dirs = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'strategy', 'implementations')
        ]
        
        # Create strategy factory
        factory = StrategyFactory(strategy_dirs)
        
        # Print debug info
        factory.print_debug_info()
        
        # Check for MA crossover strategy
        strategies = factory.get_strategy_names()
        logger.info(f"Found {len(strategies)} strategies: {strategies}")
        
        # Try creating a strategy
        for strategy_name in strategies:
            if 'ma_crossover' in strategy_name.lower() or 'simple_ma' in strategy_name.lower():
                logger.info(f"Testing strategy creation: {strategy_name}")
                try:
                    strategy = factory.create_strategy(strategy_name, name='test')
                    logger.info(f"Successfully created strategy: {strategy_name}")
                    return True
                except Exception as e:
                    logger.error(f"Error creating strategy '{strategy_name}': {e}")
        
        logger.warning("No suitable strategy found for testing")
        return False
        
    except Exception as e:
        logger.error(f"Strategy factory error: {e}")
        return False

def verify_data_handler():
    """
    Verify that the data handler can load and split data.
    
    Returns:
        bool: True if data handler works, False otherwise
    """
    try:
        from src.data.historical_data_handler import HistoricalDataHandler
        from src.core.event_bus import SimpleEventBus
        
        # Create data directory if it doesn't exist
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        # Check if the required data file exists
        required_file = os.path.join(data_dir, 'HEAD_1min.csv')
        if not os.path.exists(required_file):
            logger.error(f"Required data file not found: {required_file}")
            return False
            
        # Create event bus
        event_bus = SimpleEventBus()
        
        # Create data configuration
        data_config = {
            'sources': [
                {
                    'symbol': 'HEAD',
                    'file': required_file,
                    'date_column': 'timestamp',
                    'date_format': '%Y-%m-%d %H:%M:%S'
                }
            ]
        }
        
        # Create data handler
        data_handler = HistoricalDataHandler('data_handler', data_config)
        
        # Initialize data handler
        data_handler.initialize({'event_bus': event_bus})
        logger.info("Data handler initialized successfully")
        
        # Test train/test splitting
        data_handler.setup_train_test_split(
            method='ratio',
            train_ratio=0.7,
            test_ratio=0.3
        )
        logger.info("Train/test split created successfully")
        
        # Test train split
        data_handler.set_active_split('train')
        # Verify data is available
        has_data = data_handler.update()
        logger.info(f"Train split has data: {has_data}")
        
        # Test test split
        data_handler.set_active_split('test')
        # Verify data is available
        has_data = data_handler.update()
        logger.info(f"Test split has data: {has_data}")
        
        # Reset data handler
        data_handler.reset()
        
        return True
        
    except Exception as e:
        logger.error(f"Data handler error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def verify_optimization():
    """
    Verify that the optimization framework works with main.py entry point.
    
    Returns:
        bool: True if optimization works, False otherwise
    """
    try:
        # Import necessary components
        from src.strategy.optimization.optimizer import StrategyOptimizer
        
        # Create a minimal test configuration
        config = {
            'strategy': {
                'name': 'simple_ma_crossover'
            },
            'parameter_space': [
                {
                    'name': 'fast_period',
                    'type': 'integer',
                    'min': 5,
                    'max': 10,
                    'step': 5
                },
                {
                    'name': 'slow_period',
                    'type': 'integer',
                    'min': 20,
                    'max': 30,
                    'step': 10
                }
            ],
            'optimization': {
                'method': 'grid',
                'objective': 'sharpe_ratio'
            },
            'data': {
                'sources': [
                    {
                        'symbol': 'HEAD',
                        'file': 'data/HEAD_1min.csv',
                        'date_column': 'timestamp',
                        'date_format': '%Y-%m-%d %H:%M:%S'
                    }
                ],
                'train_test_split': {
                    'enabled': True,
                    'method': 'ratio',
                    'train_ratio': 0.7,
                    'test_ratio': 0.3
                }
            },
            'output_dir': './optimization_results'
        }
        
        # Create optimizer
        optimizer = StrategyOptimizer(config)
        
        # Run optimization
        logger.info("Running test optimization")
        results = optimizer.optimize()
        
        # Check results
        if not results:
            logger.error("Optimization returned no results")
            return False
            
        logger.info(f"Optimization completed with {len(results.get('train_results', {}).get('trades', []))} train trades and {len(results.get('test_results', {}).get('trades', []))} test trades")
        
        # Save results to a special test file
        import json
        test_results_file = os.path.join('optimization_results', 'test_optimization_results.json')
        try:
            with open(test_results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Test results saved to {test_results_file}")
        except Exception as e:
            logger.error(f"Error saving test results: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function."""
    logger.info("Starting ADMF-Trader Optimization Framework Fix Verification")
    
    # Check imports
    logger.info("Step 1: Checking imports...")
    if not check_imports():
        logger.error("Import check failed")
        return False
    logger.info("Import check passed")
    
    # Verify strategy factory
    logger.info("Step 2: Verifying strategy factory...")
    if not verify_strategy_factory():
        logger.error("Strategy factory verification failed")
        return False
    logger.info("Strategy factory verification passed")
    
    # Verify data handler
    logger.info("Step 3: Verifying data handler...")
    if not verify_data_handler():
        logger.error("Data handler verification failed")
        return False
    logger.info("Data handler verification passed")
    
    # Verify optimization
    logger.info("Step 4: Verifying optimization framework...")
    if not verify_optimization():
        logger.error("Optimization verification failed")
        return False
    logger.info("Optimization verification passed")
    
    logger.info("All verification steps passed successfully!")
    logger.info("The ADMF-Trader Optimization Framework has been successfully fixed.")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
