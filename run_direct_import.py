#!/usr/bin/env python
"""
Script to run the direct import test with timeout protection.
"""

import subprocess
import sys
import time

def main():
    print("Running direct import test with timeout protection...")
    
    # Record start time
    start_time = time.time()
    
    # Run with a timeout to avoid hanging indefinitely
    try:
        result = subprocess.run(
            [sys.executable, "tests/direct_import_test.py"],
            timeout=10,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        print(f"Test completed in {elapsed:.2f} seconds with exit code {result.returncode}")
        
        # Print output
        print("\nOutput:")
        print("-" * 60)
        print(result.stdout)
        
        if result.stderr:
            print("\nErrors:")
            print("-" * 60)
            print(result.stderr)
        
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"\nTest timed out after 10 seconds!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
