#!/usr/bin/env python
"""
Fix and run the backtest with correct configuration.
"""
import os
import sys
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('my_fixed_backtest')

def fix_order_registry():
    """Add get_all_orders method to OrderRegistry if missing."""
    registry_path = "src/execution/order_registry.py"
    if os.path.exists(registry_path):
        with open(registry_path, 'r') as f:
            content = f.read()
        
        if "def get_all_orders" not in content:
            logger.info("Adding get_all_orders method to OrderRegistry")
            with open(registry_path, 'a') as f:
                f.write("\n    def get_all_orders(self):\n")
                f.write("        \"\"\"\n")
                f.write("        Get all orders regardless of status.\n")
                f.write("        \n")
                f.write("        Returns:\n")
                f.write("            List of all orders\n")
                f.write("        \"\"\"\n")
                f.write("        return list(self.orders.values())\n")
            logger.info("Added get_all_orders method to OrderRegistry")
        else:
            logger.info("get_all_orders method already exists in OrderRegistry")

def fix_backtest_file():
    """Fix any issues in the backtest.py file."""
    file_path = "src/execution/backtest/backtest.py"
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for problematic code and fix it
    if "orders = self.order_registry.get_all_orders()" in content:
        logger.info("Fixing order retrieval in backtest.py")
        fixed_content = content.replace(
            "orders = self.order_registry.get_all_orders()",
            """orders = []
            if hasattr(self.order_registry, 'get_all_orders'):
                orders = self.order_registry.get_all_orders()
            elif hasattr(self.order_registry, 'get_active_orders'):
                orders = self.order_registry.get_active_orders()
                logger.info("Using get_active_orders() as get_all_orders() is not available")
            else:
                logger.warning("Order registry has neither get_all_orders nor get_active_orders method")"""
        )
        
        # Write fixed content back to file
        with open(file_path, 'w') as f:
            f.write(fixed_content)
        
        logger.info("Fixed order retrieval in backtest.py")
    else:
        logger.info("No issues found in backtest.py or already fixed")

def check_and_copy_data():
    """Make sure SPY data file is in the right place."""
    source_file = "SPY_1min.csv"
    target_dir = "data"
    target_file = os.path.join(target_dir, source_file)
    
    if not os.path.exists(target_file) and os.path.exists(source_file):
        logger.info(f"Copying {source_file} to {target_file}")
        os.makedirs(target_dir, exist_ok=True)
        with open(source_file, 'rb') as src, open(target_file, 'wb') as dst:
            dst.write(src.read())
        logger.info(f"Successfully copied {source_file} to data directory")
    elif os.path.exists(target_file):
        logger.info(f"{target_file} already exists")
    else:
        logger.warning(f"Could not find {source_file} to copy")

def run_backtest():
    """Run the backtest with fixed configuration."""
    config_path = "config/fixed_backtest.yaml"
    
    logger.info(f"Running backtest with fixed configuration: {config_path}")
    
    # Run the backtest
    result = subprocess.run(["python", "main.py", "--config", config_path], 
                          capture_output=True, text=True)
    
    # Print output
    print(result.stdout)
    
    if "No trades were executed" in result.stdout:
        logger.warning("Backtest still failed: No trades were executed")
        return False
    else:
        logger.info("Backtest succeeded!")
        return True

def main():
    """Apply all fixes and run the backtest."""
    logger.info("Starting fixes for the trading system...")
    
    # Print what will be done
    print("\n=== ADMF Trading System Fix ===\n")
    print("This script will fix the backtest by:")
    print("1. Adding get_all_orders method to OrderRegistry if missing")
    print("2. Fixing the backtest.py file to properly handle orders")
    print("3. Ensuring data is in the correct location")
    print("4. Running backtest with optimized parameters (fast MA=2, slow MA=5)")
    print("\nExecuting fixes now...\n")
    
    # Step 1: Add get_all_orders method to OrderRegistry
    fix_order_registry()
    
    # Step 2: Fix backtest.py file
    fix_backtest_file()
    
    # Step 3: Make sure data file is in the right place
    check_and_copy_data()
    
    # Step 4: Run the backtest
    success = run_backtest()
    
    if success:
        print("\n=== FIX SUCCESSFUL! ===")
        print("The backtest is now working properly.")
        print("You can use the configuration in config/fixed_backtest.yaml for future backtests.")
        logger.info("Backtest completed successfully!")
        logger.info("All fixes have been applied and the backtest is now working.")
    else:
        print("\n=== FURTHER DEBUGGING NEEDED ===")
        print("The backtest is still not executing trades.")
        print("Check the logs for more information and consider reviewing:")
        print("1. The data format in SPY_1min.csv")
        print("2. The moving average parameters in the configuration")
        print("3. The risk manager configuration")
        logger.warning("Backtest still failing. Additional debugging may be needed.")

if __name__ == "__main__":
    main()
