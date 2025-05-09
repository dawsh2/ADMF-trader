#!/usr/bin/env python
"""
ADMF-Trader Optimization Runner

This script is a simplified runner for the optimization process
that avoids the complexity of the command line arguments.
"""

import os
import sys
import logging
import yaml
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from optimize_strategy import create_data_directories, load_config, load_parameter_space, setup_strategy_factory
from src.strategy.optimization.objective_functions import get_objective_function
from src.core.event_bus import SimpleEventBus
from src.core.trade_repository import TradeRepository
from src.execution.backtest.optimizing_backtest import OptimizingBacktest

def main():
    """Main function."""
    try:
        # Configuration
        config_path = 'config/backtest_config.yaml'
        strategy_name = 'simple_ma_crossover'
        param_file = 'config/parameter_spaces/ma_crossover_params.yaml'
        objective_name = 'sharpe_ratio'
        
        logger.info("Starting ADMF-Trader optimization...")
        logger.info(f"Config: {config_path}")
        logger.info(f"Strategy: {strategy_name}")
        logger.info(f"Parameter file: {param_file}")
        logger.info(f"Objective: {objective_name}")
        
        # Create data directories
        logger.info("Checking data directories...")
        create_data_directories()
        
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config(config_path)
        
        # Load parameter space
        logger.info("Loading parameter space...")
        param_space = load_parameter_space(param_file)
        
        # Set up strategy factory
        logger.info("Setting up strategy factory...")
        strategy_factory = setup_strategy_factory()
        
        # Get objective function
        logger.info("Getting objective function...")
        objective_function = get_objective_function(objective_name)
        
        # Create optimization context
        logger.info("Creating optimization context...")
        context = {
            'strategy_factory': strategy_factory
        }
        
        # Create optimizing backtest
        logger.info("Creating optimizing backtest...")
        optimizer = OptimizingBacktest('optimizer', config, param_space)
        
        # Initialize optimizer
        logger.info("Initializing optimizer...")
        optimizer.initialize(context)
        
        # Set up train/test configuration
        train_test_config = {
            'method': 'ratio',
            'train_ratio': 0.7,
            'test_ratio': 0.3
        }
        
        # Use a smaller parameter space for testing
        logger.info("Restricting parameter space for initial testing...")
        # Get only two combinations to test
        param_space.parameters['fast_period'].min_value = 5
        param_space.parameters['fast_period'].max_value = 10
        param_space.parameters['slow_period'].min_value = 20
        param_space.parameters['slow_period'].max_value = 30
        
        # Run optimization
        logger.info("Starting optimization process...")
        results = optimizer.optimize(strategy_name, objective_function, train_test_config)
        
        # Print results
        logger.info("Optimization completed!")
        
        # Print best parameters
        logger.info(f"Best parameters: {results['best_parameters']}")
        logger.info(f"Best train score: {results['best_train_score']}")
        logger.info(f"Best test score: {results['best_test_score']}")
        
        return results
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        logger.error(traceback.format_exc())
        return None

if __name__ == '__main__':
    main()
