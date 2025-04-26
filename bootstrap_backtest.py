#!/usr/bin/env python
"""
Simple Backtest Runner Script

This script runs a backtest using the ADMF-Trader framework with the Bootstrap pattern,
allowing for clean separation of concerns and focusing on strategy development.
"""
import os
import logging
import argparse
from datetime import datetime

from src.core.bootstrap import Bootstrap

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run ADMF-Trader backtest")
    parser.add_argument("--config", default="config/backtest.yaml", help="Configuration file")
    parser.add_argument("--output-dir", default="./results", help="Results output directory")
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set up the system with bootstrap
    bootstrap = Bootstrap(config_files=[args.config])
    container, config = bootstrap.setup()
    
    # Get backtest coordinator and run
    backtest = container.get("backtest")
    if backtest.setup():
        # Run backtest
        results = backtest.run()
        
        # Save results
        if results:
            # Save equity curve
            equity_curve = results.get('equity_curve')
            if equity_curve is not None and not equity_curve.empty:
                equity_curve.to_csv(f"{args.output_dir}/equity_curve.csv")
                
            # Save detailed report
            detailed_report = results.get('detailed_report', '')
            if detailed_report:
                with open(f"{args.output_dir}/backtest_report.txt", 'w') as f:
                    f.write(detailed_report)
            
            # Print summary
            print("\n=== Backtest Results ===")
            metrics = results.get('metrics', {})
            trades = results.get('trades', [])
            
            print(f"Executed {len(trades)} trades")
            for metric in ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']:
                if metric in metrics:
                    print(f"{metric}: {metrics[metric]:.4f}")
            
            print(f"\nDetailed results saved to {args.output_dir}/")
            return 0
    
    # If we got here, something failed
    print("Backtest failed - check logs for details")
    return 1

if __name__ == "__main__":
    exit(main())
