#!/usr/bin/env python
"""
Simple wrapper script for running analytics from the command line.

This script uses the analytics runner to analyze backtest results
and generate reports.

Usage:
  python run_analytics.py --config=config/analytics_standalone.yaml
  python run_analytics.py --equity-file=results/backtest/equity_curve.csv --trades-file=results/backtest/trades.csv
"""

import os
import sys
import argparse
import yaml
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the analytics runner
from src.analytics.runner import run_analytics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run analytics on backtest results')
    parser.add_argument('--config', help='Path to analytics configuration file')
    parser.add_argument('--equity-file', help='Path to equity curve CSV file')
    parser.add_argument('--trades-file', help='Path to trades CSV file')
    parser.add_argument('--output-dir', help='Output directory for reports')
    parser.add_argument('--generate-sample', action='store_true', help='Generate sample data for demo')
    
    args = parser.parse_args()
    
    # Load configuration if specified
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return 1
    
    # Generate sample data if requested
    if args.generate_sample:
        logger.info("Generating sample data...")
        from examples.analyze_backtest_results import generate_sample_data
        
        sample_dir = args.output_dir or './results/sample'
        equity_file, trades_file = generate_sample_data(sample_dir)
        
        # Override command-line arguments
        args.equity_file = equity_file
        args.trades_file = trades_file
        
        logger.info(f"Generated sample data: {equity_file}, {trades_file}")
    
    # Run analytics
    success, message = run_analytics(
        config,
        equity_file=args.equity_file,
        trades_file=args.trades_file,
        output_dir=args.output_dir
    )
    
    if success:
        logger.info(message)
        return 0
    else:
        logger.error(message)
        return 1


if __name__ == "__main__":
    sys.exit(main())