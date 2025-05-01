#!/usr/bin/env python
"""
Script to run the fixed ultra simple test.
"""

import os
import sys
import subprocess
import time

def main():
    """Run the fixed ultra simple test."""
    print("Running fixed ultra simple test...")
    
    # Start time
    start_time = time.time()
    
    # Add project root to PYTHONPATH
    env = os.environ.copy()
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Set PYTHONPATH
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{project_root}:{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = project_root
    
    # Command to run
    cmd = ["python", "-m", "pytest", "tests/integration/ultra_simple_test_fixed.py", "-v"]
    print(f"Running: {' '.join(cmd)}")
    print(f"PYTHONPATH: {env['PYTHONPATH']}")
    
    # Run with timeout
    try:
        result = subprocess.run(cmd, timeout=30, env=env)
        elapsed = time.time() - start_time
        print(f"Test completed in {elapsed:.2f}s with exit code {result.returncode}")
        return result.returncode
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"Test timed out after {elapsed:.2f}s")
        return 1

if __name__ == "__main__":
    sys.exit(main())
