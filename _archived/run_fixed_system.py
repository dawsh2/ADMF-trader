#!/usr/bin/env python
"""
Test script to verify the fixes to the backtesting system.

This script runs the optimization process with the fixes applied to:
1. Logger initialization in Portfolio class
2. Added get_current_timestamp() method to HistoricalDataHandler
3. Added get_current_price() method to HistoricalDataHandler
4. Added supporting methods for optimization (get_current_symbol, get_split_sizes, is_empty)
"""

import logging
import sys
from src.core.event_bus import SimpleEventBus, Event, EventType
from src.core.trade_repository import TradeRepository
from src.execution.backtest.optimizing_backtest import OptimizingBacktest
from src.strategy.optimization.parameter_space import ParameterSpace
from src.strategy.strategy_factory import StrategyFactory
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)
logger.info("Starting fixed optimization test")

def load_config(config_file):
    """Load configuration from file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def main():
    # Load configuration
    config_file = "config/ma_crossover_optimization.yaml"
    logger.info(f"Loading optimization configuration from {config_file}")
    
    try:
        config = load_config(config_file)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return
    
    # Create strategy factory
    strategy_factory = StrategyFactory()
    strategy_factory.load_strategies()
    
    # Create parameter space from config
    param_space = ParameterSpace.from_dict(config.get('optimization', {}).get('parameters', {}))
    
    # Create optimization context
    context = {
        'strategy_factory': strategy_factory
    }
    
    # Create optimizing backtest
    optimizer = OptimizingBacktest("optimizer", config, param_space)
    optimizer.initialize(context)
    
    # Define objective function
    def objective_function(result):
        """Simple objective function for testing."""
        stats = result.get('statistics', {})
        return stats.get('return_pct', 0) * 1.0 + stats.get('sharpe_ratio', 0) * 0.5
    
    # Run optimization
    try:
        train_test_config = {
            'method': 'ratio',
            'train_ratio': 0.7,
            'test_ratio': 0.3
        }
        
        strategy_name = config.get('strategy', {}).get('name', 'simple_ma_crossover')
        
        logger.info(f"Starting optimization for strategy: {strategy_name}")
        results = optimizer.optimize(
            strategy_name=strategy_name,
            objective_function=objective_function,
            train_test_config=train_test_config
        )
        
        # Print best parameters
        logger.info("Optimization completed successfully!")
        logger.info(f"Best parameters: {results.get('best_parameters')}")
        logger.info(f"Best train score: {results.get('best_train_score'):.4f}")
        logger.info(f"Best test score: {results.get('best_test_score'):.4f}")
        
        # Print train/test stats
        train_stats = results.get('train_results', {}).get('statistics', {})
        test_stats = results.get('test_results', {}).get('statistics', {})
        
        logger.info(f"Train statistics: Return={train_stats.get('return_pct', 0):.2f}%, "
                  f"Sharpe={train_stats.get('sharpe_ratio', 0):.2f}, "
                  f"Trades={train_stats.get('trades_executed', 0)}")
                  
        logger.info(f"Test statistics: Return={test_stats.get('return_pct', 0):.2f}%, "
                  f"Sharpe={test_stats.get('sharpe_ratio', 0):.2f}, "
                  f"Trades={test_stats.get('trades_executed', 0)}")
        
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
if __name__ == "__main__":
    main()
