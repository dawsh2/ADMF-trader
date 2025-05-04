#!/usr/bin/env python
"""
Run tests with fixed code.
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
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("test_runner")

def main():
    """Run tests and log results."""
    try:
        # Check if pytest is installed
        subprocess.run(["pytest", "--version"], check=True, capture_output=True)
        logger.info("Found pytest")
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("pytest not found. Please install pytest.")
        return 1
    
    # Run tests
    logger.info("Running tests...")
    cmd = ["python", "-m", "pytest", "tests", "-v"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print stdout
        if result.stdout:
            print(result.stdout)
        
        # Print stderr
        if result.stderr:
            print(result.stderr)
        
        # Return exit code
        return result.returncode
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
