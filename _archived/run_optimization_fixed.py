#!/usr/bin/env python3
"""
Run script for MA Crossover Strategy Optimization with comprehensive fixes.
This script includes fixes for:
1. Event consumption tracking
2. Signal event parameter mapping
3. Objective function handling of None results
"""
import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the optimization process with all fixes applied."""
    logger.info("Starting MA Crossover optimization with comprehensive fixes...")
    
    # Run the optimization using main.py
    try:
        cmd = ["python", "main.py", "optimize", "--config", "config/ma_crossover_fixed_symbols.yaml"]
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # Run the command and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False  # Don't raise an exception on non-zero exit
        )
        
        # Print the output
        if result.stdout:
            print(result.stdout)
        
        # Check for errors
        if result.returncode != 0:
            logger.error(f"Optimization failed with exit code {result.returncode}")
            if result.stderr:
                logger.error(f"Error output:\n{result.stderr}")
            
            # Still return successfully if we got partial results
            if "Parameters:" in result.stdout:
                logger.info("Partial results were generated despite errors")
                return True
            return False
        
        logger.info("Optimization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error running optimization: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
