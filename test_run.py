#!/usr/bin/env python
"""
Test script to verify our fixes to the ADMF-Trader Optimization Framework.
"""

import os
import sys
import subprocess
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the fix verification script and capture the output."""
    try:
        # Run the fix verification script
        cmd = [sys.executable, 'fix_verification.py']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Log success or failure
        if result.returncode == 0:
            logger.info("Fix verification completed successfully!")
            logger.info("\n".join(line for line in result.stdout.split('\n') if 'Performance:' in line or 'parameter' in line))
        else:
            logger.error(f"Fix verification failed with return code: {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error running fix verification: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
