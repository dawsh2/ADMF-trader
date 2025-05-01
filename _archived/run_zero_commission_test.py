#!/usr/bin/env python3
"""
Run backtest with zero commission configuration.
This script runs the trading system with commissions set to zero
to isolate the effect of slippage on performance.
"""

import logging
import os
import sys
from typing import Dict, Any

from src.core.system_bootstrap import Bootstrap

def run_test():
    """Run the backtest with zero commission configuration."""
    # Set up logging
    os.makedirs("results/zero_commission_test", exist_ok=True)
    log_file = "./results/zero_commission_test/zero_commission_test.log"
    
    # Initialize system with zero commission configuration
    bootstrap = Bootstrap(
        config_files=["config/mini_test_zero_commission.yaml"],
        log_level=logging.INFO,
        log_file=log_file
    )
    
    # Set up system components
    container, config = bootstrap.setup()
    
    try:
        # Get backtest coordinator
        backtest = container.get("backtest")
        
        # Run backtest
        print("Initializing system with configuration: config/mini_test_zero_commission.yaml")
        print("Running backtest with zero commission...")
        backtest.run()
        
        # Generate report
        report_generator = container.get("report_generator")
        report = report_generator.generate_report()
        
        # Print summary results
        print("\nBacktest Results Summary:\n")
        print("=== Backtest Results ===")
        print(f"Trades executed: {report.get('num_trades', 0)}")
        print(f"Total Return: {report.get('total_return', 0.0):.2f}%")
        print(f"Sharpe Ratio: {report.get('sharpe_ratio', 0.0):.4f}")
        print(f"Sortino Ratio: {report.get('sortino_ratio', 0.0):.4f}")
        print(f"Maximum Drawdown: {report.get('max_drawdown', 0.0):.2f}%")
        print(f"Win Rate: {report.get('win_rate', 0.0):.2f}%")
        print(f"Profit Factor: {report.get('profit_factor', 0.0):.4f}")
        print(f"Average Trade: {report.get('avg_trade', 0.0):.4f}")
        
        # Save results
        report_file = report_generator.save_report()
        equity_curve_file = report_generator.save_equity_curve()
        trades_file = report_generator.save_trades()
        
        print(f"\nDetailed report saved to: {report_file}")
        print(f"Equity curve saved to: {equity_curve_file}")
        
        print(f"\nResults saved to ./results/zero_commission_test")
        print("- equity_curve_file")
        print("- detailed_report_file")
        print("- trades_file")
        
    except Exception as e: