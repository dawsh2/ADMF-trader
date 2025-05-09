#!/usr/bin/env python3
"""
Test script to verify the trade tracking fix.

This script runs a simple backtest to test the trade tracking functionality
and reports on the results.
"""
import logging
import sys
import argparse
import datetime
from pathlib import Path

# Add project root to path to allow imports
sys.path.insert(0, str(Path(__file__).parent))

from src.core.system_bootstrap import Bootstrap
from src.risk.trades.trade_registry import TradeRegistry

def setup_logging(log_level="INFO"):
    """Set up logging."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("test_trade_tracking.log", mode="w")
        ]
    )
    return logging.getLogger(__name__)

def run_backtest(config_file, logger):
    """
    Run a backtest with the specified configuration.
    
    Args:
        config_file: Path to the configuration file
        logger: Logger instance
        
    Returns:
        Tuple of (success, backtest_results)
    """
    try:
        # Initialize bootstrap with config
        logger.info(f"Initializing bootstrap with config: {config_file}")
        bootstrap = Bootstrap(
            config_files=[config_file],
            log_level="INFO",
            log_file="backtest.log"
        )
        
        # Setup system
        container, config = bootstrap.setup()
        
        # Get components
        backtest = container.get("backtest")
        
        # Check for trade registry
        trade_registry = None
        if container.has("trade_registry"):
            trade_registry = container.get("trade_registry")
            logger.info(f"Using centralized trade registry: {trade_registry._name}")
        else:
            logger.warning("No trade registry found in container")
        
        # Run backtest
        logger.info("Starting backtest")
        start_time = datetime.datetime.now()
        results = backtest.run()
        duration = datetime.datetime.now() - start_time
        logger.info(f"Backtest completed in {duration.total_seconds():.2f} seconds")
        
        # Analyze results
        if 'trades' in results:
            trade_count = len(results['trades'])
            logger.info(f"Backtest reported {trade_count} trades")
            
            # Log the first few trades for inspection
            if trade_count > 0:
                for i, trade in enumerate(results['trades'][:3]):  # Just show first 3
                    logger.info(f"Trade {i+1}: {trade['symbol']} {trade['direction']} @ {trade['price']}, PnL: {trade.get('pnl', 0):.2f}")
        else:
            logger.error("No trades found in results")
            trade_count = 0
        
        # Check for performance metrics
        if 'metrics' in results:
            metrics = results['metrics']
            logger.info(f"Performance metrics: {metrics}")
        else:
            logger.error("No metrics found in results")
            
        # Print summary report if available
        if 'summary_report' in results:
            logger.info(f"Summary report:\n{results['summary_report']}")
        
        # Check trade registry stats if available
        if trade_registry:
            registry_stats = trade_registry.get_stats()
            logger.info(f"Trade registry stats: {registry_stats}")
            logger.info(f"Trade registry trade count: {trade_registry.get_trade_count()}")
        
        # Determine success
        success = trade_count > 0
        if success:
            logger.info("TEST PASSED: Found trades in backtest results")
        else:
            logger.error("TEST FAILED: No trades in backtest results")
            
        return success, results
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        return False, {}

def main():
    """Main function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Test trade tracking fix")
    parser.add_argument("--config", default="config/mini_test.yaml", help="Configuration file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Log level")
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    logger.info(f"Test started with config: {args.config}")
    
    # Run the test
    success, results = run_backtest(args.config, logger)
    
    # Return appropriate exit code
    if success:
        logger.info("Trade tracking test passed")
        return 0
    else:
        logger.error("Trade tracking test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
