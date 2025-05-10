#!/usr/bin/env python
"""
Run a direct test of the train/test isolation fix.

This script uses the fix_strategy_state.py to directly verify that our fix works.
"""

import os
import sys
import logging
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('direct_test.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    # Install fixes
    logger.info("Installing fixes")
    from fix_strategy_state import run_direct_test

    # Run the direct test
    logger.info("Running direct test of train/test isolation fix")
    success = run_direct_test()

    # Log results
    if success:
        logger.info("TEST PASSED: Train/test isolation fix works properly")
        return 0
    else:
        logger.error("TEST FAILED: Train/test isolation fix did not work properly")
        return 1

if __name__ == "__main__":
    sys.exit(main())