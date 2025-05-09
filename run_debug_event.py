#!/usr/bin/env python
"""
Script to run the Event class debug with timeout protection.
"""

import subprocess
import sys
import time

def main():
    print("Running Event class debug with timeout protection...")
    
    # Record start time
    start_time = time.time()
    
    # Run with a short timeout to avoid hanging indefinitely
    try:
        result = subprocess.run(
            [sys.executable, "tests/debug_event_timeout.py"],
            timeout=10,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        print(f"Debug completed in {elapsed:.2f} seconds with exit code {result.returncode}")
        
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
        print(f"\nDebug timed out after 10 seconds!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
