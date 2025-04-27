#!/usr/bin/env python
"""
Simple backtest runner for ADMF-Trader.

This script uses the Bootstrap pattern to set up and run a backtest
using the configuration specified in config/backtest.yaml.
"""
import os
import sys
import logging
import argparse
import datetime

from src.core.bootstrap import Bootstrap
from src.execution.backtest.backtest import BacktestCoordinator

def main():
    """Run backtest using Bootstrap."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run ADMF-Trader backtest")
    parser.add_argument("--config", default="config/backtest.yaml", help="Configuration file")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--output-dir", default="./results", help="Results output directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('backtest.log', mode='w')
        ]
    )
    logger = logging.getLogger("ADMF-Trader")
    
    # Log debug info
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
        
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create Bootstrap
    bootstrap = Bootstrap(
        config_files=[args.config],
        log_level=getattr(logging, args.log_level)
    )
    
    # Set up container with components
    logger.info("Setting up container...")
    container, config = bootstrap.setup()
    
    # Get backtest coordinator
    backtest = container.get("backtest")
    
    # Set up the backtest
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
    
    # Save results
    logger.info("Processing results...")
    equity_curve = results.get("equity_curve")
    trades = results.get("trades")
    detailed_report = results.get("detailed_report", "")
    
    # Log basic results
    if equity_curve is not None and not equity_curve.empty:
        start_equity = equity_curve['equity'].iloc[0]
        end_equity = equity_curve['equity'].iloc[-1]
        total_return = (end_equity - start_equity) / start_equity
        
        logger.info(f"Trades executed: {len(trades)}")
        logger.info(f"Initial equity: ${start_equity:.2f}")
        logger.info(f"Final equity: ${end_equity:.2f}")
        logger.info(f"Total return: {total_return:.2%}")
        
        # Save equity curve
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        equity_curve.to_csv(f"{args.output_dir}/equity_curve_{timestamp}.csv")
        logger.info(f"Saved equity curve to '{args.output_dir}/equity_curve_{timestamp}.csv'")
        
        # Save detailed report
        with open(f"{args.output_dir}/backtest_report_{timestamp}.txt", 'w') as f:
            f.write(detailed_report)
        logger.info(f"Saved detailed report to '{args.output_dir}/backtest_report_{timestamp}.txt'")
    
    # Print summary
    print("\n=== Backtest Results ===")
    print(f"Trades executed: {len(trades)}")
    
    # Print key metrics
    metrics = results.get('metrics', {})
    for metric_name in ['total_return', 'sharpe_ratio', 'sortino_ratio', 'max_drawdown', 'win_rate']:
        if metric_name in metrics:
            value = metrics[metric_name]
            if isinstance(value, float):
                if 'return' in metric_name or 'drawdown' in metric_name or 'rate' in metric_name:
                    print(f"{metric_name}: {value:.2%}")
                else:
                    print(f"{metric_name}: {value:.4f}")
            else:
                print(f"{metric_name}: {value}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
