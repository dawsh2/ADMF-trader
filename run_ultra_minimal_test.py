#!/usr/bin/env python
"""
Script to run the ultra minimal integration test.
"""

import subprocess
import sys
import time

def main():
    # Run the ultra minimal integration test
    cmd = ["python", "-m", "pytest", "tests/integration/ultra_minimal_test.py", "-v"]
    print(f"Running: {' '.join(cmd)}")
    
    # Run with a timeout to avoid hanging indefinitely
    start_time = time.time()
    try:
        # Add -s to show print statements for debugging
        result = subprocess.run(cmd + ["-s"], timeout=30)
        elapsed = time.time() - start_time
        print(f"Test completed in {elapsed:.2f} seconds with exit code {result.returncode}")
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"\nTest timed out after 30 seconds!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
