#!/usr/bin/env python
"""
Run just the test_risk_manager_deduplication test.
"""
import subprocess
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('single_test_output.log', mode='w')
    ]
)
logger = logging.getLogger("SingleTestRunner")

def run_test():
    """Run just the test_risk_manager_deduplication test."""
    try:
        # Run the test
        logger.info("Running test_risk_manager_deduplication...")
        
        result = subprocess.run(
            ["python", "-c", "from test_order_flow import test_risk_manager_deduplication; result = test_risk_manager_deduplication(); print(f'Test result: {result}')"],
            cwd="/Users/daws/ADMF-trader",
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        # Log the output
        logger.info(f"Exit code: {result.returncode}")
        
        stdout = result.stdout.strip()
        logger.info(f"STDOUT: {stdout}")
        
        if result.stderr:
            logger.error(f"STDERR: {result.stderr}")
        
        # Check if the test passed
        if "Test result: True" in stdout:
            logger.info("SUCCESS! The test passed!")
            return 0
        else:
            logger.error("FAILURE: The test is still failing.")
            return 1
    except Exception as e:
        logger.error(f"Error running test: {e}")
        return 2

if __name__ == "__main__":
    sys.exit(run_test())
