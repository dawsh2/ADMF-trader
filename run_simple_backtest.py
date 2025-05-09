#!/usr/bin/env python
"""
Run a simple backtest with all fixes applied.
"""

import os
import sys
import logging
import importlib

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simple_backtest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('simple_backtest')

def run_backtest():
    """Run a simple backtest with all fixes"""
    logger.info("Running simple backtest with all fixes...")
    
    # First, install hooks for debugging
    try:
        from src.util.backtest_hooks import install_hooks
        install_hooks()
        logger.info("Installed backtest hooks")
    except ImportError:
        logger.warning("Could not import backtest hooks - run fix_data_handler.py first")
    
    # Import required components
    from src.execution.backtest.backtest_coordinator import BacktestCoordinator
    import yaml
    
    # Load the configuration
    config_path = "config/simple_ma_crossover.yaml"
    logger.info(f"Loading configuration from {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return False
    
    # Create and run the backtest
    logger.info("Creating backtest coordinator")
    backtest = BacktestCoordinator('simple_backtest', config)
    
    # Initialize and run backtest
    logger.info("Initializing backtest")
    backtest.initialize()
    
    logger.info("Running backtest")
    backtest.run()
    
    # Get and print results
    results = backtest.get_results()
    
    # Check for trades
    trades = results.get('trades', [])
    logger.info(f"Backtest completed with {len(trades)} trades")
    
    # Print trade details if any
    if trades:
        logger.info("Trade details:")
        for i, trade in enumerate(trades[:5]):  # Print first 5 trades
            logger.info(f"  Trade {i+1}: {trade}")
        
        if len(trades) > 5:
            logger.info(f"  ... and {len(trades) - 5} more trades")
    else:
        logger.warning("No trades were generated!")
    
    # Print statistics
    stats = results.get('statistics', {})
    logger.info("Backtest statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    return len(trades) > 0

if __name__ == "__main__":
    success = run_backtest()
    
    if success:
        logger.info("SUCCESS: The backtest generated trades!")
    else:
        logger.warning("FAILURE: The backtest did not generate any trades.")
