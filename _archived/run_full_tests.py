#!/usr/bin/env python
"""
Run all tests to verify our fix.
"""
import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('full_test.log', mode='w')
    ]
)
logger = logging.getLogger("FullTestRunner")

def run_all_tests():
    """Run the full test suite."""
    logger.info("Running full test suite...")
    
    # Run the test
    result = subprocess.run(
        ["python", "test_order_flow.py"],
        cwd="/Users/daws/ADMF-trader",
        capture_output=True,
        text=True,
        timeout=60  # 60 second timeout
    )
    
    # Save output to file
    with open("full_test_output.txt", "w") as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n\nSTDERR:\n")
            f.write(result.stderr)
    
    logger.info(f"Test exit code: {result.returncode}")
    
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
        logger.error("Some tests still failing.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
