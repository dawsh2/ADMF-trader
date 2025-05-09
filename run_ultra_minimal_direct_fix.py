#!/usr/bin/env python
"""
Script to run the directly fixed ultra minimal integration test.
This uses a modified version of the test file that accesses event.event_type directly.
"""

import subprocess
import sys
import time
import os

def main():
    # Add project root to PYTHONPATH for the subprocess
    env = os.environ.copy()
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Set PYTHONPATH environment variable
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{project_root}:{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = project_root
    
    # Run the directly fixed ultra minimal integration test
    cmd = ["python", "-m", "pytest", "tests/integration/ultra_minimal_test_fixed.py", "-v"]
    print(f"Running: {' '.join(cmd)}")
    print(f"PYTHONPATH set to: {env['PYTHONPATH']}")
    
    # Run with a timeout to avoid hanging indefinitely
    start_time = time.time()
    try:
        # Add -s to show print statements for debugging
        result = subprocess.run(cmd + ["-s"], timeout=30, env=env)
        elapsed = time.time() - start_time
        print(f"Test completed in {elapsed:.2f} seconds with exit code {result.returncode}")
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"\nTest timed out after 30 seconds!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
