#!/usr/bin/env python
"""
ADMF-Trader Main Entry Point

A unified entry point for running backtests with different strategies.
Simply provide the appropriate configuration file to run any strategy.
"""
import os
import sys
import argparse
import datetime

# Import bootstrap for clean initialization
from src.core.bootstrap import Bootstrap
from src.data.generators import data_generator


def main():
    """Run a backtest with the specified configuration."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="ADMF-Trader Backtest Runner")
    
    # Core configuration
    parser.add_argument("--config", required=True, help="Configuration file path")
    parser.add_argument("--output-dir", default="./results", help="Results output directory")
    parser.add_argument("--data-dir", default="./data", help="Data directory")
    parser.add_argument("--log-level", default="INFO", 
                      choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Logging level")
    
    # Data generation options
    parser.add_argument("--generate-data", action="store_true", 
                      help="Generate synthetic data before running backtest")
    parser.add_argument("--data-type", default="multi_regime", 
                      choices=["multi_regime", "trend", "mean_reversion", "volatility", "random"],
                      help="Type of synthetic data to generate")
    parser.add_argument("--plot-data", action="store_true", 
                      help="Plot generated data")
    
    args = parser.parse_args()
    
    # Create output and data directories
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.data_dir, exist_ok=True)
    
    # Extract strategy name from config path for output directory
    config_name = os.path.splitext(os.path.basename(args.config))[0]
    strategy_output_dir = os.path.join(args.output_dir, config_name)
    os.makedirs(strategy_output_dir, exist_ok=True)
    
    # Generate synthetic data if requested
    if args.generate_data:
        print(f"Generating synthetic {args.data_type} data...")
        try:
            if args.data_type == "multi_regime":
                data_generator.generate_multi_regime_data(
                    output_dir=args.data_dir,
                    start_date="2023-01-01",
                    plot=args.plot_data
                )
            # Additional data types could be added here
            print("Data generation complete.")
        except Exception as e:
            print(f"Error generating data: {str(e)}")
            print("Continuing with existing data...")
    
    # Set up log file
    log_file = os.path.join(strategy_output_dir, f"{config_name}.log")
    
    # Initialize the bootstrap
    bootstrap = Bootstrap(
        config_files=[args.config],
        log_level=args.log_level,
        log_file=log_file
    )
    
    # Setup container with components
    print(f"Initializing system with configuration: {args.config}")
    container, config = bootstrap.setup()
    
    # Get backtest coordinator
    backtest = container.get("backtest")
    
    # Run the backtest
    print("Running backtest...")
    results = backtest.run()
    
    # Generate and save reports
    if results:
        report_generator = container.get("report_generator")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save reports
        saved_files = report_generator.save_reports(
            results, 
            output_dir=strategy_output_dir,
            timestamp=timestamp
        )
        
        # Print summary
        print("\nBacktest Results Summary:")
        report_generator.print_summary(results)
        
        print(f"\nResults saved to {strategy_output_dir}")
        for file_path in saved_files:
            print(f"- {os.path.basename(file_path)}")
    else:
        print("Backtest did not produce any results")
        return False
    
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
