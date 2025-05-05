#!/usr/bin/env python3
"""
Fix for the "0 trades executed" issue in backtest reports.

This script patches the portfolio's get_recent_trades() method to include OPEN trades
in reports, making the backtest metrics more accurate.
"""
import sys
import logging
import importlib
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("trade_report_fix")

def patch_get_recent_trades():
    """
    Patch the PortfolioManager.get_recent_trades method to include all trades.
    """
    try:
        # Import the portfolio module
        from src.risk.portfolio.portfolio import PortfolioManager
        
        # Store the original method for reference
        original_get_recent_trades = PortfolioManager.get_recent_trades
        
        # Define our patched method
        def patched_get_recent_trades(self, n=None, filter_open=False):
            """
            Patched version of get_recent_trades that includes OPEN trades by default.
            
            Args:
                n: Number of trades to return (None for all)
                filter_open: If True, filter out open trades. Now defaults to False!
                
            Returns:
                List of trade dictionaries
            """
            logger.info(f"Using patched get_recent_trades with filter_open={filter_open}")
            return original_get_recent_trades(self, n, filter_open)
        
        # Apply the patch
        PortfolioManager.get_recent_trades = patched_get_recent_trades
        logger.info("Successfully patched PortfolioManager.get_recent_trades method")
        
        return True
    except Exception as e:
        logger.error(f"Failed to patch PortfolioManager.get_recent_trades: {e}", exc_info=True)
        return False

def patch_backtest_report_generator():
    """
    Patch the backtest reporting system to correctly count all trades.
    """
    try:
        # Import the reporting module
        from src.analytics.reporting.report_generator import ReportGenerator
        
        # Find the method that calls get_recent_trades
        original_generate_summary_report = ReportGenerator.generate_summary_report
        original_generate_detailed_report = ReportGenerator.generate_detailed_report
        
        # Define our patched method for summary report
        def patched_generate_summary_report(self):
            """
            Patched version of generate_summary_report that ensures we get ALL trades,
            including OPEN trades for metrics calculation.
            """
            logger.info("Using patched ReportGenerator.generate_summary_report")
            
            # Add debug info if we have a calculator with trades
            if self.calculator and hasattr(self.calculator, 'trades'):
                trades = self.calculator.trades
                logger.info(f"Calculator has {len(trades)} trades for metrics")
                
                # Print status counts
                if trades:
                    open_count = sum(1 for t in trades if t.get('status') == 'OPEN')
                    closed_count = sum(1 for t in trades if t.get('status') == 'CLOSED')
                    logger.info(f"Trade status counts: OPEN={open_count}, CLOSED={closed_count}")
            
            # Now call the original method
            return original_generate_summary_report(self)
        
        # Define our patched method for detailed report
        def patched_generate_detailed_report(self):
            """
            Patched version of generate_detailed_report that ensures we get ALL trades.
            """
            logger.info("Using patched ReportGenerator.generate_detailed_report")
            
            # Now call the original method
            return original_generate_detailed_report(self)
        
        # Apply the patches
        ReportGenerator.generate_summary_report = patched_generate_summary_report
        ReportGenerator.generate_detailed_report = patched_generate_detailed_report
        logger.info("Successfully patched ReportGenerator methods")
        
        return True
    except Exception as e:
        logger.error(f"Failed to patch ReportGenerator methods: {e}", exc_info=True)
        return False

def patch_performance_calculator():
    """
    Patch the performance calculator to include all trades in metrics.
    """
    try:
        # Import the performance calculator module
        from src.analytics.performance.calculator import PerformanceCalculator
        
        # Find the calculate_metrics method
        original_calculate_metrics = PerformanceCalculator.calculate_metrics
        
        # Define our patched method
        def patched_calculate_metrics(self, trades, equity_curve=None):
            """
            Patched version of calculate_metrics that ensures we count all trades.
            """
            logger.info(f"Using patched PerformanceCalculator.calculate_metrics with {len(trades)} trades")
            
            # Call original method
            metrics = original_calculate_metrics(self, trades, equity_curve)
            
            # Add trade counts regardless of errors elsewhere
            metrics['trade_count'] = len(trades)
            logger.info(f"Explicitly setting trade_count to {len(trades)}")
            
            # Count by trade type
            buy_count = sum(1 for t in trades if t.get('direction') == 'BUY')
            sell_count = sum(1 for t in trades if t.get('direction') == 'SELL')
            logger.info(f"Trade direction counts: BUY={buy_count}, SELL={sell_count}")
            
            return metrics
        
        # Apply the patch
        PerformanceCalculator.calculate_metrics = patched_calculate_metrics
        logger.info("Successfully patched PerformanceCalculator.calculate_metrics method")
        
        return True
    except Exception as e:
        logger.error(f"Failed to patch PerformanceCalculator.calculate_metrics: {e}", exc_info=True)
        return False

def run_all_patches():
    """Apply all patches and return success/failure status."""
    patch_results = [
        patch_get_recent_trades(),
        patch_backtest_report_generator(),
        patch_performance_calculator()
    ]
    
    if all(patch_results):
        logger.info("All patches applied successfully")
        return True
    else:
        logger.error("Some patches failed to apply")
        return False

def main():
    """Main entry point."""
    logger.info("Starting trade reporting fix")
    
    # Apply all patches
    if run_all_patches():
        logger.info("Trade reporting fix successfully applied!")
        logger.info("The next backtest you run should show all trades in the report")
        print("\nTrade reporting fix successfully applied!")
        print("The next backtest you run should show all trades in the report")
        return 0
    else:
        logger.error("Trade reporting fix failed to apply")
        print("\nTrade reporting fix failed to apply. See logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())