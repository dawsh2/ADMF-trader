#!/usr/bin/env python
"""
Run optimization with fixed error handling.

This script runs the trading strategy optimization with improved error handling,
specifically addressing the 'NoneType' object has no attribute 'items' error.
"""

import os
import sys
import logging
import argparse
import yaml
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fixed_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fixed_optimization')

def load_config(config_path):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def main():
    """Main entry point for the fixed optimization application"""
    parser = argparse.ArgumentParser(description='Run trading strategy optimization with improved error handling')
    parser.add_argument('--config', required=True, help='Path to the configuration file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        logger.error("Failed to load configuration")
        return 1
        
    # Log basic configuration info
    strategy_name = config.get('strategy', {}).get('name', 'Unknown')
    logger.info(f"Running optimization for strategy: {strategy_name}")
    
    strategy_symbols = config.get('strategy', {}).get('parameters', {}).get('symbols', [])
    logger.info(f"Strategy symbols defined in config: {strategy_symbols}")
    
    backtest_symbols = config.get('backtest', {}).get('symbols', [])
    logger.info(f"Backtest symbols defined in config: {backtest_symbols}")
    
    data_sources = config.get('data', {}).get('sources', [])
    source_symbols = [source.get('symbol') for source in data_sources]
    logger.info(f"Data source symbols: {source_symbols}")
    
    # Run the optimization with error handling
    logger.info("Starting optimization with improved error handling...")
    
    try:
        # Import the fixed optimizer
        from src.strategy.optimization.fixed_optimizer import StrategyOptimizer
        
        # Create and run optimizer
        optimizer = StrategyOptimizer(config)
        results = optimizer.optimize()
        
        if results:
            logger.info("Optimization completed successfully")
            return 0
        else:
            logger.warning("Optimization completed but returned no results")
            return 1
            
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
