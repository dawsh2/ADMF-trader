#!/usr/bin/env python
"""
Regime Ensemble Strategy Backtest Runner

This script runs a backtest for the Regime-Aware Ensemble Strategy, which:
1. Detects market regimes (trending, mean-reverting, volatile)
2. Combines multiple trading rules (trend, mean-reversion, volatility breakout)
3. Adapts rule weights based on detected regime
"""
import os
import sys
import argparse
import datetime

# Import bootstrap for clean initialization
from src.core.bootstrap import Bootstrap
from src.data.generators import data_generator


def main():
    """Run regime ensemble backtest."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run Regime Ensemble Strategy Backtest")
    parser.add_argument("--config", default="config/regime_ensemble.yaml", help="Configuration file")
    parser.add_argument("--output-dir", default="./results/regime_ensemble", help="Results output directory")
    parser.add_argument("--data-dir", default="./data", help="Data directory")
    parser.add_argument("--generate-data", action="store_true", help="Generate synthetic data")
    parser.add_argument("--plot-data", action="store_true", help="Plot generated data")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()
    
    # Create output and data directories
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.data_dir, exist_ok=True)
    
    # Generate synthetic data if requested
    if args.generate_data:
        print("Generating synthetic multi-regime data...")
        try:
            data_generator.generate_multi_regime_data(
                output_dir=args.data_dir,
                start_date="2023-01-01",
                plot=args.plot_data,
                seed=42
            )
            print("Data generation complete.")
        except Exception as e:
            print(f"Error generating data: {str(e)}")
            print("Continuing with existing data...")
    
    # Set up log file path
    log_file = os.path.join(args.output_dir, "regime_ensemble_backtest.log")
    
    # Initialize the bootstrap with configuration
    bootstrap = Bootstrap(
        config_files=[args.config],
        log_level=args.log_level,
        log_file=log_file
    )
    
    # Setup container and get components
    container, config = bootstrap.setup()
    
    # Get backtest coordinator and run the backtest
    backtest = container.get("backtest")
    results = backtest.run()
    
    # Generate and save reports
    if results:
        report_generator = container.get("report_generator")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_generator.save_reports(results, output_dir=args.output_dir, timestamp=timestamp)
        report_generator.print_summary(results)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        import logging
        logging.exception("Backtest failed with error")
        print(f"Error: {e}")
        sys.exit(1)
