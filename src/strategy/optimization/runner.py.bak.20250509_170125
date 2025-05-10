"""
Optimization runner module.

This module provides a self-contained system for running strategy optimizations,
without requiring the main entry point to manage optimization details.
"""

import os
import sys
import logging
import traceback
import yaml
from pathlib import Path

from src.strategy.optimization.fixed_optimizer import FixedOptimizer as StrategyOptimizer
from src.core.system_init import Bootstrap
from src.core.configuration.config import Config

logger = logging.getLogger(__name__)

def run_with_context(config, container, **kwargs):
    """
    Run optimization with an existing container and configuration.
    This is intended to be called from main.py which handles the initialization.

    Args:
        config: Configuration object or dictionary
        container: Dependency injection container
        **kwargs: Optional overrides for configuration

    Returns:
        tuple: (success flag, result message, results dict)
    """
    # Get necessary components from container
    # Extract max_bars from the bootstrap context if available
    max_bars = None
    if hasattr(container, 'get') and callable(container.get):
        # Try to get the bootstrap context
        bootstrap = container.get('bootstrap') if container.has('bootstrap') else None
        if bootstrap and hasattr(bootstrap, 'context'):
            max_bars = bootstrap.context.get('max_bars')
            if max_bars:
                logger.info(f"Found max_bars={max_bars} in bootstrap context")

    # Convert config to dictionary if it's a Config object
    if hasattr(config, 'as_dict'):
        config_dict = config.as_dict()
    elif hasattr(config, 'to_dict'):
        config_dict = config.to_dict()
    else:
        # Try to convert to dictionary
        try:
            config_dict = dict(config)
        except (TypeError, ValueError):
            # If all else fails, just get the raw data if possible
            if hasattr(config, 'data'):
                config_dict = config.data
            else:
                logger.error(f"Failed to convert config to dictionary: unsupported type {type(config)}")
                return False, "Configuration conversion error", None

    # Add max_bars to kwargs if found
    if max_bars:
        kwargs['max_bars'] = max_bars

    # Run optimization with the provided configuration and overrides
    return run_optimization(config_dict, **kwargs)

def run_optimization(config, **kwargs):
    """
    Run parameter optimization for a trading strategy.

    Args:
        config (dict): Base configuration with strategy and data settings
        **kwargs: Optional configuration overrides:
            - method (str): Optimization method override
            - param_file (str): Parameter space file path override
            - output_dir (str): Output directory override
            - max_bars (int): Maximum number of bars to process in each backtest

    Returns:
        tuple: (success flag, result message, results dict)
    """
    # Create a mutable copy of the configuration
    optimization_config = dict(config)

    # Apply command-line overrides if provided
    method = kwargs.get('method')
    param_file = kwargs.get('param_file')
    output_dir = kwargs.get('output_dir')
    max_bars = kwargs.get('max_bars')

    # Apply overrides if provided
    if method:
        logger.info(f"Using optimization method: {method}")
        if 'optimization' not in optimization_config:
            optimization_config['optimization'] = {}
        optimization_config['optimization']['method'] = method

    if output_dir:
        logger.info(f"Using output directory: {output_dir}")
        optimization_config['output_dir'] = output_dir

        # Create output directory if it doesn't exist
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create output directory {output_dir}: {e}")

    if param_file:
        logger.info(f"Using parameter space from: {param_file}")
        optimization_config['parameter_file'] = param_file

        # Validate parameter file exists
        if not os.path.exists(param_file):
            message = f"Parameter file not found: {param_file}"
            logger.error(message)
            return False, message, None

    # Add max_bars to optimization config if specified
    if max_bars:
        logger.info(f"Using max_bars={max_bars} for optimization")
        optimization_config['max_bars'] = max_bars

    try:
        # Create parameter space from config
        from src.strategy.optimization.parameter_space import ParameterSpace

        # Extract parameter space config
        param_space_config = {}
        if 'optimization' in optimization_config and 'parameters' in optimization_config['optimization']:
            param_space_config = {'parameters': optimization_config['optimization']['parameters']}
        elif 'parameter_space' in optimization_config:
            param_space_config = {'parameters': optimization_config['parameter_space']}
        
        # Create parameter space and initialize it from the config
        parameter_space = ParameterSpace()
        parameter_space.from_dict(param_space_config)
        
        # Get strategy name
        strategy_name = optimization_config.get('strategy', {}).get('name', 'simple_ma_crossover')
        
        logger.info(f"Created parameter space with {len(parameter_space.get_combinations())} combinations")
        
        # Create and initialize optimizer
        optimizer = StrategyOptimizer(
            strategy_name=strategy_name,
            config=optimization_config,
            parameter_space=parameter_space
        )

        # Run optimization
        logger.info(f"Starting optimization for strategy: {strategy_name}")
        results = optimizer.optimize()
        
        # Check for successful optimization
        if results and results.get('best_parameters'):
            best_score = results.get('best_score', 0)
            best_params = results.get('best_parameters')
            
            # Log train/test performance if available
            train_results = results.get('train_results', {})
            test_results = results.get('test_results', {})
            
            performance_summary = []
            
            if train_results:
                train_stats = train_results.get('statistics', {})
                train_summary = (
                    f"Training: Return={train_stats.get('return_pct', 0):.2f}%, "
                    f"Sharpe={train_stats.get('sharpe_ratio', 0):.2f}, "
                    f"DrawDown={train_stats.get('max_drawdown', 0):.2f}%"
                )
                performance_summary.append(train_summary)
                logger.info(train_summary)
                
            if test_results:
                test_stats = test_results.get('statistics', {})
                test_summary = (
                    f"Testing: Return={test_stats.get('return_pct', 0):.2f}%, "
                    f"Sharpe={test_stats.get('sharpe_ratio', 0):.2f}, "
                    f"DrawDown={test_stats.get('max_drawdown', 0):.2f}%"
                )
                performance_summary.append(test_summary)
                logger.info(test_summary)
                
            if 'output_dir' in optimization_config:
                results_path = os.path.join(optimization_config['output_dir'], 
                                        results.get('filename', 'optimization_results.json'))
                logger.info(f"Detailed results saved to: {results_path}")
            
            # Create success message
            performance_text = "\n".join(performance_summary)
            message = (
                f"Optimization completed successfully.\n"
                f"Best score: {best_score:.4f}\n"
                f"Best parameters: {best_params}\n"
                f"{performance_text}"
            )
            
            return True, message, results
        else:
            message = "Optimization did not produce valid results"
            logger.error(message)
            return False, message, results
            
    except ImportError as e:
        message = f"Failed to import optimization components: {e}"
        logger.error(message)
        return False, message, None
    except Exception as e:
        message = f"Error running optimization: {e}"
        logger.error(message)
        logger.error(traceback.format_exc())
        return False, message, None

def parse_arguments():
    """
    Parse command line arguments when running this module directly.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Strategy Optimization Runner")
    parser.add_argument("--config", required=True, help="Path to configuration file")
    parser.add_argument("--method", choices=["grid", "random", "walk_forward"], 
                        help="Optimization method")
    parser.add_argument("--param-file", help="Parameter space file path")
    parser.add_argument("--output-dir", help="Output directory for results")
    parser.add_argument("--log-file", help="Log file path")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    return parser.parse_args()

def setup_logging(log_file=None, verbose=False):
    """
    Set up logging configuration.
    
    Args:
        log_file (str, optional): Path to log file
        verbose (bool, optional): Enable verbose logging
    """
    # Set up logging level
    log_level = logging.INFO if verbose else logging.WARNING
    
    # Create handlers
    handlers = [logging.StreamHandler()]
    
    # Add file handler if specified
    if log_file:
        handlers.append(logging.FileHandler(log_file, mode='w'))
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

if __name__ == "__main__":
    """Run optimization directly from command line."""
    args = parse_arguments()
    
    # Set up logging
    setup_logging(log_file=args.log_file, verbose=args.verbose)
    
    # Run optimization
    success, message, results = run_from_config(
        args.config,
        method=args.method,
        param_file=args.param_file,
        output_dir=args.output_dir
    )
    
    # Print result
    if success:
        print(message)
        sys.exit(0)
    else:
        print(f"ERROR: {message}")
        sys.exit(1)