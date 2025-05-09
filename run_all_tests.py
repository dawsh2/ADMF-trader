#!/usr/bin/env python
"""
Run all test scripts to verify our fixes.
"""

import os
import sys
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test_script(script_path):
    """Run a test script and return success status."""
    logger.info(f"Running test script: {script_path}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=False,
            capture_output=True,
            text=True
        )
        
        # Log output
        if result.stdout:
            logger.info(result.stdout)
        
        # Log errors
        if result.stderr:
            logger.error(result.stderr)
        
        # Return success status
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error running {script_path}: {e}")
        return False

def main():
    """Run all test scripts."""
    logger.info("Running all test scripts...")
    
    # Define test scripts
    test_scripts = [
        "test_event_system.py",
        "test_portfolio.py",
        "test_ma_strategy.py",
        "test_integration.py"
    ]
    
    # Run each test script
    results = {}
    for script in test_scripts:
        script_path = os.path.join(os.path.dirname(__file__), script)
        success = run_test_script(script_path)
        results[script] = success
    
    # Print summary
    logger.info("======== Test Results ========")
    all_passed = True
    for script, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{script}: {status}")
        if not success:
            all_passed = False
    
    logger.info("============================")
    
    if all_passed:
        logger.info("All tests passed! The fixes are working. ✅")
        return 0
    else:
        logger.error("Some tests failed. The fixes need more work. ❌")
        return 1

if __name__ == "__main__":
    sys.exit(main())
