#!/usr/bin/env python
"""
Run the official test case to validate the fix
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
        logging.FileHandler('official_test.log', mode='w')
    ]
)
logger = logging.getLogger("OfficialTest")

def run_test():
    """Run just the test_risk_manager_deduplication test from test_order_flow.py."""
    try:
        cmd = [
            'python', 
            '-c', 
            'from test_order_flow import test_risk_manager_deduplication; result = test_risk_manager_deduplication(); print(f"Test result: {result}"); import sys; sys.exit(0 if result else 1)'
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd="/Users/daws/ADMF-trader",
            capture_output=True,
            text=True
        )
        
        # Log the output
        logger.info(f"Exit code: {result.returncode}")
        logger.info(f"STDOUT: {result.stdout}")
        
        if result.stderr:
            logger.error(f"STDERR: {result.stderr}")
        
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error running test: {e}")
        return False

if __name__ == "__main__":
    success = run_test()
    print(f"Test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
