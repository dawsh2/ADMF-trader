#!/usr/bin/env python3
"""
Run a backtest with the trade reporting fix applied.

This script first applies the fix to the trade reporting system,
then runs a backtest with the mini_test configuration.
"""
import sys
import logging
import importlib
import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_fixed_backtest")

def apply_trade_report_fix():
    """Apply the trade reporting fix."""
    try:
        # First import the fix module
        import trade_report_fix
        
        # Apply all patches
        result = trade_report_fix.run_all_patches()
        
        if result:
            logger.info("Successfully applied trade reporting fix")
            return True
        else:
            logger.error("Failed to apply trade reporting fix")
            return False
    except Exception as e:
        logger.error(f"Error applying trade reporting fix: {e}", exc_info=True)
        return False

def run_backtest():
    """Run a backtest with the mini_test configuration."""
    try:
        # Import main modules
        from src.execution.backtest.backtest import Backtest
        from src.core.config.config_manager import ConfigManager
        
        # Create timestamp for output files
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Running backtest with timestamp: {timestamp}")
        
        # Load mini_test configuration
        config_path = "config/mini_test.yaml"
        if not os.path.exists(config_path):
            # Try zero_commission configuration as backup
            config_path = "config/mini_test_zero_commission.yaml"
            if not os.path.exists(config_path):
                logger.error("Could not find mini_test or mini_test_zero_commission configuration")
                return False
        
        logger.info(f"Using configuration: {config_path}")
        config = ConfigManager(config_path)
        
        # Create and run backtest
        backtest = Backtest(config)
        results = backtest.run()
        
        # Generate reports with timestamp
        output_dir = f"results/fixed_backtest_{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Get backtest report
        report_path = f"{output_dir}/backtest_report_{timestamp}.txt"
        trades_path = f"{output_dir}/trades_{timestamp}.csv"
        equity_path = f"{output_dir}/equity_curve_{timestamp}.csv"
        
        logger.info(f"Generating backtest report: {report_path}")
        backtest.generate_report(report_path)
        
        # Save trades and equity curve
        if hasattr(backtest, 'portfolio'):
            if hasattr(backtest.portfolio, 'get_trades_as_df'):
                trades_df = backtest.portfolio.get_trades_as_df()
                trades_df.to_csv(trades_path)
                logger.info(f"Saved trades to: {trades_path}")
            
            if hasattr(backtest.portfolio, 'get_equity_curve_df'):
                equity_df = backtest.portfolio.get_equity_curve_df()
                equity_df.to_csv(equity_path)
                logger.info(f"Saved equity curve to: {equity_path}")
        
        # Print summary of results
        print("\n====== BACKTEST RESULTS SUMMARY ======")
        print(f"Configuration: {config_path}")
        print(f"Report saved to: {report_path}")
        
        # Print portfolio summary if available
        if hasattr(backtest, 'portfolio'):
            portfolio = backtest.portfolio
            stats = portfolio.get_stats()
            print(f"Trades executed: {stats.get('trades_executed', 0)}")
            print(f"Total PnL: ${stats.get('total_pnl', 0):.2f}")
            print(f"Win rate: {stats.get('win_rate', 0) * 100:.2f}%")
            
            # Count trades with different status values
            all_trades = portfolio.trades
            open_count = sum(1 for t in all_trades if t.get('status') == 'OPEN')
            closed_count = sum(1 for t in all_trades if t.get('status') == 'CLOSED')
            print(f"Trade status counts: OPEN={open_count}, CLOSED={closed_count}")
            
            # Show warning if all trades are open
            if open_count > 0 and closed_count == 0:
                print("\nWARNING: All trades are still marked as OPEN.")
                print("This means positions aren't being properly closed.")
                print("Check src/risk/managers/simple.py to ensure position_action='CLOSE' is set for closing trades.")
        
        print("========================================")
        return True
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        return False

def main():
    """Main entry point."""
    logger.info("Starting fixed backtest")
    
    # First apply the fix
    if not apply_trade_report_fix():
        logger.error("Failed to apply trade reporting fix, aborting backtest")
        return 1
    
    # Then run the backtest
    if run_backtest():
        logger.info("Backtest completed successfully")
        return 0
    else:
        logger.error("Backtest failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
