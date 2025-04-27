#!/usr/bin/env python
"""
Integration Test Backtest Script

This script runs an integration test with a Moving Average Crossover strategy
using the ADMF-Trader framework with proper Bootstrap and centralized order registry.
"""
import os
import logging
import argparse
import datetime
import pandas as pd
import numpy as np
import yaml
import sys

from src.core.bootstrap import Bootstrap
from src.core.config.config import Config

def create_test_data(symbols, start_date, end_date, data_dir):
    """Create test data with sine wave patterns to ensure MA crossovers."""
    logger = logging.getLogger(__name__)
    logger.info(f"Creating test data for {symbols}")
    
    # Create data directory if needed
    os.makedirs(data_dir, exist_ok=True)
    
    # Convert dates to datetime objects if needed
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    # Generate date range
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
    
    np.random.seed(42)  # For reproducibility
    
    for symbol in symbols:
        # Create price data with forced crossovers
        base_price = 100.0 if symbol == 'AAPL' else 200.0
        prices = []
        
        # Create a sine wave pattern for predictable crossovers
        for i in range(len(dates)):
            t = i / len(dates)
            # Multiple frequency components to create crossovers
            sine_component = 15 * np.sin(t * 20 * np.pi) + 7 * np.sin(t * 5 * np.pi)
            # Add slight trend and noise
            price = base_price + sine_component + i * 0.01 + np.random.normal(0, 0.5)
            prices.append(max(price, 1.0))  # Ensure positive prices
        
        # Generate OHLCV data
        data = []
        for i, date in enumerate(dates):
            close = prices[i]
            high = close * (1 + abs(np.random.normal(0, 0.01)))
            low = close * (1 - abs(np.random.normal(0, 0.01)))
            open_price = low + (high - low) * np.random.random()
            volume = int(np.random.exponential(100000))
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(data)
        filename = os.path.join(data_dir, f"{symbol}_1d.csv")
        df.to_csv(filename, index=False)
        logger.info(f"Created test data for {symbol} with {len(data)} bars")
    
    return True

def create_config(data_dir, config_output_path="backtest_config.yaml"):
    """Create configuration for the backtest."""
    config_dict = {
        'backtest': {
            'initial_capital': 100000.0,
            'symbols': ['AAPL', 'MSFT'],
            'data_dir': data_dir,
            'timeframe': '1d',
            'strategy': 'ma_crossover'
        },
        'strategies': {
            'ma_crossover': {
                'fast_window': 5,  # Use fast window for more signals in test
                'slow_window': 20,
                'symbols': ['AAPL', 'MSFT'],
            }
        },
        'data': {
            'source_type': 'csv',
            'data_dir': data_dir,
        },
        'risk_manager': {
            'position_size': 100,
            'max_position_pct': 0.1,  # Max 10% of equity per position
        },
        'portfolio': {
            'initial_cash': 100000.0,
        },
        'broker': {
            'slippage': 0.001,  # 0.1% slippage
            'commission': 0.001,  # 0.1% commission
        }
    }
    
    # Save config to YAML file for reference
    with open(config_output_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False)
    
    # Create Config object
    config = Config()
    for section, values in config_dict.items():
        for key, value in values.items():
            config.get_section(section).set(key, value)
    
    return config

def main():
    """Run integration backtest with test data."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run ADMF-Trader integration backtest")
    parser.add_argument("--output-dir", default="./results", help="Results output directory")
    parser.add_argument("--data-dir", default="./data", help="Data directory")
    parser.add_argument("--log-file", default="integration_backtest.log", help="Log file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Create data and output directories
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.data_dir, exist_ok=True)
    
    # Define test parameters
    symbols = ['AAPL', 'MSFT']
    start_date = '2023-01-01'
    end_date = '2023-02-28'  # Shorter period for faster testing
    
    # Initialize Bootstrap with debug options
    bootstrap = Bootstrap(
        log_level=logging.DEBUG if args.debug else logging.INFO,
        log_file=args.log_file,
        debug=args.debug
    )
    
    # Initialize logging early for data generation
    bootstrap._setup_logging()
    logger = logging.getLogger(__name__)
    
    # Create test data
    logger.info("Generating test data...")
    create_test_data(symbols, start_date, end_date, args.data_dir)
    
    # Create configuration
    config_path = "integration_test_config.yaml"
    logger.info(f"Creating configuration at {config_path}...")
    config = create_config(args.data_dir, config_path)
    
    # Add config to bootstrap
    bootstrap.config_files = [config_path]
    
    # Set up container with components
    logger.info("Setting up container...")
    container, _ = bootstrap.setup()
    
    # Get backtest coordinator
    backtest = container.get('backtest')
    
    # Set up the backtest
    logger.info("Setting up backtest...")
    setup_success = backtest.setup()
    if not setup_success:
        logger.error("Failed to set up backtest")
        return False
    
    # Run the backtest
    logger.info("Running backtest...")
    results = backtest.run(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000.0,
        timeframe='1d'
    )
    
    # Check if we got any results
    if not results:
        logger.error("Backtest produced no results")
        return False
    
    # Get report generator for reporting and file saving
    report_generator = container.get("report_generator")
    
    # Generate timestamp for file naming
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save results and get file paths
    saved_files = report_generator.save_reports(
        results, 
        output_dir=args.output_dir,
        timestamp=timestamp
    )
    
    # Print summary results to console
    report_generator.print_summary(results)
    
    # Try to get order registry stats
    try:
        order_registry = container.get('order_registry')
        if order_registry:
            registry_stats = order_registry.get_stats()
            logger.info("\nOrder Registry Statistics:")
            for key, value in registry_stats.items():
                logger.info(f"  {key}: {value}")
    except Exception as e:
        logger.error(f"Error getting order registry stats: {e}")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        print("\n=== Integration Backtest Completed Successfully! ===" if success else "\n=== Integration Backtest Failed! ===")
        sys.exit(0 if success else 1)
    except Exception as e:
        logging.exception("Integration backtest failed with error")
        print(f"Error: {e}")
        sys.exit(1)
