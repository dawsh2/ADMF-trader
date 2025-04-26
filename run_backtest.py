#!/usr/bin/env python
"""
ADMF-Trader Backtest Runner

This script runs a trading strategy backtest using the ADMF-Trader framework.
It leverages the Bootstrap pattern for clean setup and proper component initialization.

Usage:
    python run_backtest.py --config config/my_strategy.yaml --output-dir ./results
"""
import os
import sys
import argparse
import datetime
import logging

from src.core.bootstrap import Bootstrap

def main():
    """Run backtest using Bootstrap."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run ADMF-Trader backtest")
    parser.add_argument("--config", default="config/backtest.yaml", help="Configuration file")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--output-dir", default="./results", help="Results output directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--log-file", default="backtest.log", help="Log file path")
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create bootstrap with all configuration options
    bootstrap = Bootstrap(
        config_files=[args.config],
        log_level=getattr(logging, args.log_level),
        log_file=args.log_file,
        debug=args.debug
    )
    
    # Set up container with components
    container, config = bootstrap.setup()
    
    # Get backtest coordinator
    backtest = container.get("backtest")
    
    # Set up the backtest
    logger = logging.getLogger("ADMF-Trader")
    logger.info("Setting up backtest...")
    
    setup_success = backtest.setup()
    if not setup_success:
        logger.error("Failed to set up backtest")
        return False
    
    # Run the backtest
    logger.info("Running backtest...")
    results = backtest.run()
    
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
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logging.exception("Backtest failed with error")
        print(f"Error: {e}")
        sys.exit(1)
