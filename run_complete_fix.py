#!/usr/bin/env python
"""
Complete Fix for ADMF-Trader Trade Tracking Issue

This script:
1. Installs the fixed portfolio manager
2. Runs a backtest with diagnostics
3. Verifies that trades are properly tracked

Usage:
    python run_complete_fix.py [config_file]
"""
import os
import sys
import datetime
import logging
import importlib
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"complete_fix_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("complete_fix")

def install_modified_files():
    """Install modified files"""
    try:
        # 1. Fix order_manager.py - already done in previous fixes
        logger.info("Skipping order_manager.py fix - already done")
        
        # 2. Install fixed portfolio manager
        logger.info("Installing fixed portfolio manager...")
        # Check if the fixed_portfolio.py file exists
        if os.path.exists("src/risk/portfolio/fixed_portfolio.py"):
            # Import the installation script
            sys.path.insert(0, os.path.abspath('.'))
            from install_fixed_portfolio import install_fixed_portfolio
            success = install_fixed_portfolio()
            if not success:
                logger.error("Failed to install fixed portfolio manager")
                return False
            logger.info("Fixed portfolio manager installed successfully")
        else:
            logger.error("Could not find fixed_portfolio.py")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error installing modified files: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def run_backtest(config_path="config/mini_test.yaml"):
    """Run the backtest with the fixed code"""
    try:
        logger.info(f"Running backtest with config: {config_path}")
        
        # Import core modules
        import src.core.system_bootstrap as bootstrap
        
        # Create bootstrap object
        bs = bootstrap.Bootstrap(
            config_files=[config_path],
            log_level="INFO",
            log_file=f"complete_fix_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        # Setup container
        logger.info("Setting up system container")
        container, config = bs.setup()
        
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
                
                # Generate and save reports
                report_generator = container.get("report_generator")
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Save reports
                output_dir = f"./results/fixed_{timestamp}"
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
                    
                return len(trades) > 0
            else:
                logger.error("No trades in backtest results!")
                return False
        else:
            logger.error("Backtest did not produce any results")
            return False
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to run the complete fix"""
    logger.info("=" * 80)
    logger.info("STARTING COMPLETE FIX FOR ADMF-TRADER")
    logger.info("=" * 80)
    
    # Get config path
    config_path = "config/mini_test.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # Step 1: Install modified files
    logger.info("Step 1: Installing modified files")
    if not install_modified_files():
        logger.error("Failed to install modified files")
        return False
    
    # Step 2: Run backtest
    logger.info("Step 2: Running backtest with fixes")
    success = run_backtest(config_path)
    
    if success:
        logger.info("=" * 80)
        logger.info("FIX SUCCESSFUL: Trades are now properly tracked!")
        logger.info("=" * 80)
    else:
        logger.error("=" * 80)
        logger.error("FIX FAILED: Trades are still not properly tracked")
        logger.error("=" * 80)
    
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
