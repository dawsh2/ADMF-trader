#!/usr/bin/env python
"""
Script to run the super minimal debug test directly without pytest.
"""

import subprocess
import sys
import time

def main():
    print("Running minimal test directly (no pytest)...")
    
    # Record start time
    start_time = time.time()
    
    # Run the test script directly
    try:
        result = subprocess.run(
            [sys.executable, "tests/debug/test_event_only.py"],
            timeout=10,  # Short timeout
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
        print(f"\nTest timed out after 10 seconds!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
