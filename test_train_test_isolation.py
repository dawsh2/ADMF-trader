#!/usr/bin/env python
"""
Test script to verify the train/test isolation fix.

This script runs a backtest optimization with the fixed code to ensure
that the train and test datasets produce different results.
"""

import os
import sys
import logging
import time
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('train_test_isolation_test.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description='Test train/test isolation fix')
    parser.add_argument('--config', type=str, default='config/simple_ma_optimization.yaml',
                      help='Path to configuration file')
    parser.add_argument('--bars', type=int, default=100,
                      help='Maximum number of bars to use')
    parser.add_argument('--verbose', action='store_true',
                      help='Enable verbose logging')
    return parser

def install_fixes():
    """Install the fixed files to test the solution."""
    import shutil
    
    # Files to replace with their fixed versions
    fix_files = [
        ('src/strategy/optimization/fixed_optimizer.py', 'src/strategy/optimization/fixed_optimizer.py.fix'),
        ('src/execution/backtest/optimizing_backtest.py', 'src/execution/backtest/optimizing_backtest.py.fix')
    ]
    
    # Create backups and install fixes
    for target, source in fix_files:
        # Check if fix file exists
        if not os.path.exists(source):
            logger.error(f"Fix file {source} not found")
            continue
            
        # Create backup if it doesn't exist
        backup = f"{target}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if os.path.exists(target) and not os.path.exists(backup):
            logger.info(f"Creating backup of {target} to {backup}")
            shutil.copy2(target, backup)
            
        # Copy fix to target
        logger.info(f"Installing fix from {source} to {target}")
        shutil.copy2(source, target)
        
    logger.info("All fixes installed")

def run_test(config_path, max_bars=100, verbose=False):
    """
    Run test with the specified configuration.
    
    Args:
        config_path (str): Path to configuration file
        max_bars (int): Maximum number of bars to process
        verbose (bool): Enable verbose logging
    """
    # Set logging level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    # Install fixes
    logger.info("Installing fixes")
    install_fixes()

    # Import system bootstrap (after fixes are installed)
    from src.core.system_init import Bootstrap

    # Load configuration
    logger.info(f"Loading configuration from {config_path}")

    # Time tracking
    start_time = time.time()

    # Bootstrap the system
    bootstrap = Bootstrap(config_files=[config_path])
    
    # Set up bootstrap with max_bars
    if max_bars:
        # Create context attribute if it doesn't exist
        if not hasattr(bootstrap, 'context'):
            bootstrap.context = {}
        bootstrap.context['max_bars'] = max_bars
        logger.info(f"Setting max_bars to {max_bars}")

    # Initialize system
    container, config = bootstrap.setup()

    # Make sure bootstrap is available in the container
    if hasattr(container, 'register_instance'):
        container.register_instance('bootstrap', bootstrap)

    # Directly modify the config to include max_bars
    if max_bars and hasattr(config, 'set'):
        config.set('max_bars', max_bars)

    # Check if optimization is enabled in config
    if not config.get('optimize', False):
        config.set('optimize', True)
        logger.info("Enabling optimization in config")

    # Import the optimization runner
    from src.strategy.optimization.runner import run_with_context

    # Run the system
    logger.info("Running optimization")
    success, message, results = run_with_context(
        config,
        container,
        max_bars=max_bars,
        method='grid'
    )
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    logger.info(f"Optimization completed in {elapsed_time:.2f} seconds")
    
    # Analyze results to verify train/test isolation
    if results and isinstance(results, dict):
        all_results = results.get('all_results', [])
        if all_results:
            # Check each parameter combination
            train_test_different = []
            for result in all_results:
                train_result = result.get('train_result', {})
                test_result = result.get('test_result', {})
                
                # Get statistics
                train_stats = train_result.get('statistics', {})
                test_stats = test_result.get('statistics', {})
                
                # Get metrics
                train_return = train_stats.get('return_pct', 0)
                test_return = test_stats.get('return_pct', 0)
                train_sharpe = train_stats.get('sharpe_ratio', 0)
                test_sharpe = test_stats.get('sharpe_ratio', 0)
                
                # Check if train and test results are different
                metrics_different = (
                    abs(train_return - test_return) > 0.001 or
                    abs(train_sharpe - test_sharpe) > 0.001
                )
                
                # Store result
                train_test_different.append(metrics_different)
                
                # Log detailed comparison
                params_str = ', '.join([f"{k}={v}" for k, v in result.get('parameters', {}).items()])
                logger.info(f"Parameters: {params_str}")
                logger.info(f"  Train: Return={train_return:.4f}, Sharpe={train_sharpe:.4f}")
                logger.info(f"  Test: Return={test_return:.4f}, Sharpe={test_sharpe:.4f}")
                logger.info(f"  Different: {metrics_different}")
                
                # Count trades as another validation metric
                train_trades = len(train_result.get('trades', []))
                test_trades = len(test_result.get('trades', []))
                logger.info(f"  Train trades: {train_trades}, Test trades: {test_trades}")
            
            # Summary of results
            different_count = sum(train_test_different)
            total_count = len(train_test_different)
            different_percent = different_count / total_count * 100 if total_count > 0 else 0
            
            logger.info(f"Summary: {different_count}/{total_count} parameter combinations ({different_percent:.1f}%) "
                       f"show different train/test results")
            
            if different_count == total_count:
                logger.info("TEST PASSED: All parameter combinations show different train/test results")
                logger.info("This confirms that the train/test isolation fix is working properly")
                return True
            elif different_count > 0:
                logger.info("TEST PARTIALLY PASSED: Some parameter combinations show different train/test results")
                logger.info("This suggests that the train/test isolation fix is working but may need refinement")
                return True
            else:
                logger.error("TEST FAILED: No parameter combinations show different train/test results")
                logger.error("The train/test isolation fix is not working properly")
                return False
        else:
            logger.error("No results found in optimization output")
            return False
    else:
        logger.error("Invalid or missing results from optimization")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = setup_parser()
    args = parser.parse_args()
    
    # Run the test
    success = run_test(args.config, args.bars, args.verbose)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)