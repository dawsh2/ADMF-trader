#!/usr/bin/env python
"""
Run the ADMF-Trader backtest with trade tracking diagnostics enabled
"""
import os
import sys
import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"diagnostic_run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("diagnostic_runner")

def main():
    """Run the backtest with diagnostic tools"""
    logger.info("=" * 80)
    logger.info("STARTING DIAGNOSTIC RUN")
    logger.info("=" * 80)
    
    # Install diagnostics
    try:
        logger.info("Installing portfolio diagnostics")
        # Add the current directory to the path to ensure imports work
        sys.path.insert(0, os.path.abspath('.'))
        
        # First, import and install the diagnostics
        from src.risk.portfolio.portfolio_diagnostics import install_diagnostics
        success = install_diagnostics()
        if not success:
            logger.error("Failed to install diagnostics")
            return False
            
        logger.info("Diagnostics installed successfully")
        
        # Import the standard modules
        import src.core.system_bootstrap as bootstrap
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Set up config path - use zero commission config by default
        config_path = "config/mini_test_zero_commission.yaml"
        if len(sys.argv) > 1:
            config_path = sys.argv[1]
        
        logger.info(f"Using configuration: {config_path}")
        
        # Create bootstrap object with the diagnostic hooks already installed
        bs = bootstrap.Bootstrap(
            config_files=[config_path],
            log_level="INFO",
            log_file=f"diagnostic_run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        # Setup container
        logger.info("Setting up system container")
        container, config = bs.setup()
        
        # Get portfolio and add diagnostic tracker if needed
        portfolio = container.get('portfolio')
        from src.risk.portfolio.portfolio_diagnostics import TradeTracker
        
        if not hasattr(portfolio, 'trade_tracker'):
            portfolio.trade_tracker = TradeTracker()
            logger.info(f"Added trade tracker to portfolio with ID: {portfolio.trade_tracker.id}")
        
        # Get and run backtest
        backtest = container.get('backtest')
        logger.info("Running backtest...")
        results = backtest.run()
        
        # Process results
        if results:
            logger.info("Backtest completed, checking results")
            
            # Check for trades
            trades = results.get('trades', [])
            logger.info(f"Found {len(trades)} trades in results")
            
            if trades:
                logger.info(f"First trade: {trades[0]}")
            else:
                logger.warning("No trades in backtest results!")
                
                # Check if portfolio has trades
                portfolio_trades = portfolio.get_recent_trades()
                logger.info(f"Portfolio has {len(portfolio_trades)} trades")
                
                # Check if portfolio tracker has trades
                if hasattr(portfolio, 'trade_tracker'):
                    tracker_trades = portfolio.trade_tracker.get_trades()
                    logger.info(f"Trade tracker has {len(tracker_trades)} trades")
                    
                    if tracker_trades and not portfolio_trades:
                        logger.info("Restoring trades from tracker to portfolio")
                        portfolio.trades = tracker_trades
                        
                        # Re-run results processing
                        logger.info("Re-running results processing with restored trades")
                        backtest._process_results()
            
            # Generate and save reports
            report_generator = container.get("report_generator")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save reports
            output_dir = f"./results/diagnostics_{timestamp}"
            os.makedirs(output_dir, exist_ok=True)
            
            saved_files = report_generator.save_reports(
                results, 
                output_dir=output_dir,
                timestamp=timestamp
            )
            
            # Print summary
            print("\nBacktest Results Summary:")
            report_generator.print_summary(results)
            
            print(f"\nResults saved to {output_dir}")
            for file_path in saved_files:
                print(f"- {os.path.basename(file_path)}")
                
            return True
        else:
            logger.error("Backtest did not produce any results")
            return False
    
    except Exception as e:
        logger.exception(f"Error in diagnostic run: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
