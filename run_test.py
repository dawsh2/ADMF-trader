#!/usr/bin/env python
"""
Run the test_order_flow.py script to see if our fix works.
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
        logging.FileHandler('test_output.log', mode='w')
    ]
)
logger = logging.getLogger("TestRunner")

def run_test():
    """Run the test_order_flow.py script."""
    try:
        # Run the test
        logger.info("Running test_order_flow.py...")
        
        result = subprocess.run(
            ["python", "test_order_flow.py"],
            cwd="/Users/daws/ADMF-trader",
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        # Log the output
        logger.info(f"Exit code: {result.returncode}")
        
        # Save output to file
        with open("test_log.txt", "w") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\nSTDERR:\n")
                f.write(result.stderr)
        
        # Print last 20 lines of output
        lines = result.stdout.strip().split('\n')
        last_lines = lines[-20:] if len(lines) > 20 else lines
        logger.info("Last 20 lines of output:")
        for line in last_lines:
            logger.info(line)
        
        # Check if all tests passed
        if "Failed: 0" in result.stdout:
            logger.info("SUCCESS! All tests passed!")
            return 0
        else:
            logger.error("Some tests still failing. Check test_log.txt for details.")
            return 1
        
    except Exception as e:
        logger.error(f"Error running test: {e}")
        return 2

if __name__ == "__main__":
    sys.exit(run_test())
