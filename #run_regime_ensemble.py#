#!/usr/bin/env python
"""
Regime Ensemble Strategy Backtest

This script runs a backtest for the Regime-Aware Ensemble Strategy, which:
1. Detects market regimes (trending, mean-reverting, volatile)
2. Combines multiple trading rules (trend, mean-reversion, volatility breakout)
3. Adapts rule weights based on detected regime

First, it generates synthetic multi-regime data, then runs the backtest.
"""
import os
import sys
import logging
import argparse
import datetime
import subprocess

from src.core.bootstrap import Bootstrap

def main():
    """Generate data and run regime ensemble backtest."""
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
    
    # Set up logging
    log_file = os.path.join(args.output_dir, "regime_ensemble_backtest.log")
    
    # Generate synthetic data if requested
    if args.generate_data:
        print("Generating synthetic multi-regime data...")
        try:
            # Import and run directly instead of subprocess to better handle errors
            from generate_multi_regime_data import main as generate_data
            import sys
            
            # Save original args
            original_args = sys.argv
            
            # Set args for data generation
            data_gen_args = ["generate_multi_regime_data.py", "--output-dir", args.data_dir, "--start-date", "2023-01-01"]
            if args.plot_data:
                data_gen_args.append("--plot")
            
            # Set args and run
            sys.argv = data_gen_args
            generate_data()
            
            # Restore original args
            sys.argv = original_args
            print("Data generation complete.")
        except Exception as e:
            print(f"Error generating data: {str(e)}")
            print("Continuing with existing data...")
            # Continue execution even if data generation fails
    
    # Create bootstrap with logging config
    bootstrap = Bootstrap(
        config_files=[args.config],
        log_level=getattr(logging, args.log_level),
        log_file=log_file,
        debug=(args.log_level == "DEBUG")
    )
    
    # Set up container with components
    container, config = bootstrap.setup()
    
    # Get logger
    logger = logging.getLogger("ADMF-Trader")
    logger.info("Starting Regime Ensemble Strategy backtest")
    
    # Get backtest coordinator
    backtest = container.get("backtest")
    
    # Set up the backtest
    logger.info("Setting up backtest...")
    setup_success = backtest.setup()
    if not setup_success:
        logger.error("Failed to set up backtest")
        return False
    
    # Get symbols from config
    symbols = config.get_section("backtest").get("symbols", ["AAPL", "MSFT", "GOOGL"])
    logger.info(f"Running backtest for symbols: {symbols}")
    
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
    logger.info("Saving results...")
    saved_files = report_generator.save_reports(
        results, 
        output_dir=args.output_dir,
        timestamp=timestamp
    )
    
    # Print summary results to console
    report_generator.print_summary(results)
    
    # Get order registry stats
    try:
        order_registry = container.get("order_registry")
        registry_stats = order_registry.get_stats()
        logger.info("Order Registry Statistics:")
        for key, value in registry_stats.items():
            logger.info(f"  {key}: {value}")
    except:
        pass
    
    # Get regime information
    try:
        strategy = container.get("strategy")
        if hasattr(strategy, "current_regimes"):
            logger.info("Final market regimes:")
            for symbol, regime in strategy.current_regimes.items():
                logger.info(f"  {symbol}: {regime}")
    except:
        pass
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logging.exception("Backtest failed with error")
        print(f"Error: {e}")
        sys.exit(1)
