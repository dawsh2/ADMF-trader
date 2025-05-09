#!/usr/bin/env python
"""
Script to run the direct Event test with timeout protection.
"""

import subprocess
import sys
import time

def main():
    print("Running direct Event test with timeout protection...")
    
    # Record start time
    start_time = time.time()
    
    # Run the test script with a short timeout
    try:
        result = subprocess.run(
            [sys.executable, "tests/debug/direct_event_test.py"],
            timeout=5,  # Very short timeout
            capture_output=True,
            text=True
        )
        
        # Calculate elapsed time
        elapsed = time.time() - start_time
        
        # Print output
        print(f"\nTest output (completed in {elapsed:.2f} seconds):")
        print("-" * 60)
        print(result.stdout)
        
        if result.stderr:
            print("\nErrors:")
            print("-" * 60)
            print(result.stderr)
        
        return result.returncode
        
    except subprocess.TimeoutExpired:
        print(f"\nTest timed out after 5 seconds!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
