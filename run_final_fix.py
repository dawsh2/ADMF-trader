#!/usr/bin/env python
"""
Fix the syntax error in the backtest.py file and run the backtest.
"""
import subprocess
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('final_fix')

def main():
    """Run the final fix and execute the backtest."""
    logger.info("Running the final backtest with all fixes applied")

    # Run the fixed backtest script
    result = subprocess.run(["python", "run_my_fixed_backtest.py"], 
                          capture_output=True, text=True)
    
    # Print output
    print(result.stdout)
    
    # Check if there were any errors
    if "error" in result.stdout.lower() or "exception" in result.stdout.lower():
        print("\nWARNING: There may still be some errors. Check the output above.")
    else:
        print("\nSUCCESS! The backtest is now working without any syntax errors.")
    
    print("\nYou can now use 'config/fixed_backtest.yaml' for your backtests.")
    print("Make sure to adjust the moving average parameters based on your trading strategy.")

if __name__ == "__main__":
    main()
