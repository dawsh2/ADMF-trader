#!/usr/bin/env python
"""
Fix and run script for ADMF-Trader.
This script makes the necessary updates to fix the order flow issues
and then runs the validation backtest.
"""
import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Fix-and-Run")

def main():
    """Run the validation script and print the result."""
    logger.info("=== Running validation backtest ===")
    
    # Make script executable
    script_path = os.path.join(os.getcwd(), "validate_backtest.py")
    if os.path.exists(script_path):
        os.chmod(script_path, 0o755)
        
        # Run the validation script
        try:
            cmd = [sys.executable, script_path]
            logger.info(f"Executing: {' '.join(cmd)}")
            
            # Run the process
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            # Print the results
            print("\n=== VALIDATION OUTPUT ===")
            if result.stdout:
                print(result.stdout)
                
            if result.stderr:
                print("\nERRORS:")
                print(result.stderr)
                
            print(f"\nExit code: {result.returncode}")
            
            if result.returncode == 0:
                logger.info("Validation successful!")
            else:
                logger.error("Validation failed!")
                
            return result.returncode
        except Exception as e:
            logger.error(f"Error executing validation script: {e}")
            return 1
    else:
        logger.error(f"Validation script not found at {script_path}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
