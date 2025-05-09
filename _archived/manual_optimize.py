#!/usr/bin/env python
"""
Manual optimization script for ADMF-Trader.

This script bypasses the normal optimization flow to directly test the parameter optimization
with a manually created strategy.
"""

import os
import sys
import logging
import time
import numpy as np
import pandas as pd

from src.core.system_bootstrap import Bootstrap
from src.strategy.optimization.parameter_space import ParameterSpace
from src.strategy.optimization.grid_search import GridSearch
from src.execution.backtest.optimizing_backtest import OptimizingBacktestCoordinator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up module-level globals for the script
container = None
config = None
backtest = None
data_handler = None

def configure_system():
    """Configure the system with basic components."""
    global container, config, backtest, data_handler
    
    # Bootstrap the system
    bootstrap = Bootstrap(config_files=["config/head_test.yaml"])
    
    # Set up the system
    container, config = bootstrap.setup()
    
    # Get data handler
    data_handler = container.get("data_handler")
    if not data_handler:
        logger.error("No data handler found")
        sys.exit(1)
    
    # Create optimizing backtest coordinator
    backtest = OptimizingBacktestCoordinator(container, config)
    
    return backtest

def manually_create_strategy(params=None):
    """
    Manually create a moving average crossover strategy.
    
    Args:
        params: Optional parameters to configure the strategy
        
    Returns:
        Strategy instance
    """
    try:
        # Try to import the strategy class directly
        try:
            from src.strategy.implementations.ma_crossover import MovingAverageCrossover
            logger.info("Imported MovingAverageCrossover strategy directly")
        except ImportError:
            logger.warning("Could not import MovingAverageCrossover, trying fallback import")
            # Try another possible import path
            try:
                from src.strategy.ma_crossover import MovingAverageCrossover
                logger.info("Imported MovingAverageCrossover strategy from alternative path")
            except ImportError:
                logger.error("Could not import MovingAverageCrossover strategy")
                # Search for the file
                import subprocess
                result = subprocess.run(["find", "/Users/daws/ADMF-trader", "-name", "*.py", "-exec", "grep", "-l", "MovingAverageCrossover", "{}", "\\;"], capture_output=True, text=True)
                logger.info(f"Found files: {result.stdout}")
                sys.exit(1)
        
        # Get the event bus and data handler
        event_bus = container.get("event_bus")
        
        # Construct default parameters if not provided
        if not params:
            params = {
                "fast_window": 5,
                "slow_window": 15,
                "price_key": "close",
                "signal_threshold": 0.0
            }
        
        # Create the strategy
        strategy = MovingAverageCrossover(
            event_bus=event_bus,
            data_handler=data_handler,
            parameters=params
        )
        
        logger.info(f"Manually created strategy: {strategy}")
        return strategy
        
    except Exception as e:
        logger.error(f"Error creating strategy: {e}", exc_info=True)
        return None

def create_objective_function(strategy, params=None):
    """
    Create an objective function that evaluates a strategy with given parameters.
    
    Args:
        strategy: Strategy instance to evaluate
        params: Initial parameters
        
    Returns:
        Objective function that takes parameters and returns a score
    """
    def objective(eval_params):
        """
        Objective function for optimization.
        
        Args:
            eval_params: Parameters to evaluate
            
        Returns:
            Objective score (higher is better)
        """
        # Update strategy parameters
        strategy.set_parameters(eval_params)
        
        # Run backtest
        backtest.strategy = strategy  # Ensure strategy is set
        results = backtest.run()
        
        # Get metrics
        metrics = results.get('metrics', {})
        
        # Calculate objective score (for example, Sharpe ratio)
        score = metrics.get('sharpe_ratio', 0.0)
        
        logger.info(f"Evaluated parameters: {eval_params}, score: {score}")
        return score
    
    return objective

def run_optimization():
    """Run the optimization process."""
    global backtest
    
    # Configure system
    backtest = configure_system()
    
    # Create strategy
    strategy = manually_create_strategy()
    if not strategy:
        logger.error("Failed to create strategy")
        return
    
    # Create parameter space
    param_space = ParameterSpace(name="simple_ma_crossover")
    param_space.add_integer("fast_window", 2, 20, 2)
    param_space.add_integer("slow_window", 10, 50, 5)
    param_space.add_categorical("price_key", ["close"])
    
    # Create objective function
    objective_function = create_objective_function(strategy)
    
    # Create optimizer
    optimizer = GridSearch(param_space)
    
    # Run optimization
    logger.info("Starting optimization")
    start_time = time.time()
    
    results = optimizer.search(
        objective_function=objective_function,
        max_evaluations=10  # Limit for testing
    )
    
    elapsed_time = time.time() - start_time
    logger.info(f"Optimization completed in {elapsed_time:.2f} seconds")
    
    # Print results
    best_params = results.get('best_params')
    best_score = results.get('best_score')
    
    if best_params and best_score:
        logger.info(f"Best parameters: {best_params}")
        logger.info(f"Best score: {best_score}")
    else:
        logger.warning("No optimal parameters found")
    
    # Run final backtest with best parameters
    if best_params:
        logger.info("Running final backtest with best parameters")
        strategy.set_parameters(best_params)
        backtest.strategy = strategy
        final_results = backtest.run()
        
        # Print final metrics
        metrics = final_results.get('metrics', {})
        logger.info(f"Final metrics: {metrics}")
    
    return results

if __name__ == "__main__":
    try:
        run_optimization()
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        sys.exit(1)
