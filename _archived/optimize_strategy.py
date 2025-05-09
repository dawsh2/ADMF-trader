#!/usr/bin/env python
"""
ADMF-Trader Optimization Script

This script runs strategy optimization with train/test validation
using the improved architecture.
"""

import os
import sys
import argparse
import yaml
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.FileHandler("optimization.log"),
                       logging.StreamHandler()
                   ])
logger = logging.getLogger(__name__)

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from src.core.event_bus import SimpleEventBus
from src.core.trade_repository import TradeRepository
from src.strategy.strategy_factory import StrategyFactory
from src.strategy.optimization.parameter_space import ParameterSpace
from src.strategy.optimization.objective_functions import get_objective_function
from src.execution.backtest.optimizing_backtest import OptimizingBacktest

def load_config(config_file):
    """
    Load configuration from a YAML file.
    
    Args:
        config_file (str): Path to config file
        
    Returns:
        dict: Configuration dictionary
    """
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)

def load_parameter_space(param_file):
    """
    Load parameter space from a YAML file.
    
    Args:
        param_file (str): Path to parameter file
        
    Returns:
        ParameterSpace: Parameter space
    """
    try:
        # Load parameter configuration
        with open(param_file, 'r') as f:
            param_config = yaml.safe_load(f)
            
        # Create parameter space
        param_space = ParameterSpace()
        param_space.from_dict(param_config)
        
        return param_space
    except Exception as e:
        logger.error(f"Error loading parameter space: {e}")
        sys.exit(1)

def setup_strategy_factory():
    """
    Set up the strategy factory.
    
    Returns:
        StrategyFactory: Strategy factory instance
    """
    # Define strategy directories
    strategy_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'strategy', 'implementations')
    ]
    
    # Create strategy factory
    factory = StrategyFactory(strategy_dirs)
    
    # Print debug info
    factory.print_debug_info()
    
    return factory

def create_data_directories():
    """Create data directories if they don't exist."""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    # Create data directory if it doesn't exist
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.info(f"Created data directory: {data_dir}")
        
    # Check if the required data file exists
    required_file = os.path.join(data_dir, 'HEAD_1min.csv')
    if not os.path.exists(required_file):
        logger.error(f"Required data file not found: {required_file}")
        logger.info("Please ensure the HEAD_1min.csv file is in the data directory")
        sys.exit(1)

# Sample data creation removed as we're using existing data files

def run_optimization(args):
    """
    Run the optimization process.
    
    Args:
        args: Command line arguments
        
    Returns:
        dict: Optimization results
    """
    # Load configuration
    config = load_config(args.config)
    
    # Load parameter space
    param_space = load_parameter_space(args.param_file)
    
    # Set up strategy factory
    strategy_factory = setup_strategy_factory()
    
    # Get objective function
    objective_function = get_objective_function(args.objective)
    
    # Create optimization context
    context = {
        'strategy_factory': strategy_factory
    }
    
    # Create optimizing backtest
    optimizer = OptimizingBacktest('optimizer', config, param_space)
    
    # Initialize optimizer
    optimizer.initialize(context)
    
    # Set up train/test configuration
    if args.skip_train_test:
        # Use all data for both training and testing
        train_test_config = {
            'method': 'ratio',
            'train_ratio': 1.0,
            'test_ratio': 1.0
        }
    else:
        train_test_config = {
            'method': args.split_method,
            'train_ratio': args.train_ratio,
            'test_ratio': args.test_ratio
        }
    
    # Run optimization
    results = optimizer.optimize(args.strategy, objective_function, train_test_config)
    
    # Print results
    logger.info("Optimization completed!")
    
    # Print best parameters
    logger.info(f"Best parameters: {results['best_parameters']}")
    logger.info(f"Best train score: {results['best_train_score']}")
    logger.info(f"Best test score: {results['best_test_score']}")
    
    # Print detailed results
    if results.get('all_results'):
        logger.info("Results from all parameter combinations:")
        for i, result in enumerate(results['all_results']):
            params = result.get('parameters', {})
            train_score = result.get('train_score', 0)
            test_score = result.get('test_score', 0)
            
            # Format parameters nicely
            params_str = ', '.join([f"{k}={v}" for k, v in params.items()])
            
            logger.info(f"  {i+1}: {params_str} - Train: {train_score:.4f}, Test: {test_score:.4f}")
    
    # Save results to file
    import json
    import os
    from datetime import datetime
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'optimization_results')
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    # Save results to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"{args.strategy}_optimization_{timestamp}.json")
    
    # Convert non-serializable objects to strings
    serializable_results = {}
    for key, value in results.items():
        if key == 'all_results':
            serializable_results[key] = []
            for result in value:
                serializable_result = {}
                for k, v in result.items():
                    if k in ['parameters', 'train_score', 'test_score']:
                        serializable_result[k] = v
                    elif k in ['train_result', 'test_result']:
                        # Extract key metrics from results
                        metrics = {}
                        if isinstance(v, dict):
                            if 'statistics' in v:
                                metrics = v['statistics']
                            if 'trades' in v:
                                metrics['trades_count'] = len(v['trades'])
                        serializable_result[k + '_metrics'] = metrics
                serializable_results[key].append(serializable_result)
        else:
            serializable_results[key] = value
    
    try:
        with open(results_file, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        logger.info(f"Results saved to {results_file}")
    except Exception as e:
        logger.error(f"Error saving results: {e}")
    
    return results

def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='ADMF-Trader Optimization')
    parser.add_argument('--config', required=True, help='Path to config file')
    parser.add_argument('--strategy', required=True, help='Strategy name')
    parser.add_argument('--param-file', required=True, help='Path to parameter file')
    parser.add_argument('--objective', default='sharpe_ratio', help='Objective function')
    parser.add_argument('--train-ratio', type=float, default=0.7, help='Training data ratio')
    parser.add_argument('--test-ratio', type=float, default=0.3, help='Testing data ratio')
    parser.add_argument('--split-method', default='ratio', choices=['ratio', 'date', 'fixed'],
                       help='Train/test split method')
    parser.add_argument('--skip-train-test', action='store_true', 
                       help='Skip train/test validation')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Set log level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Create data directories and sample data if needed
    create_data_directories()
    
    # Run optimization
    return run_optimization(args)

if __name__ == '__main__':
    main()
