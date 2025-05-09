#!/usr/bin/env python
"""
Script to run the Event class inspection with timeout protection.
"""

import subprocess
import sys
import time

def main():
    print("Running Event class inspection with timeout protection...")
    
    # Record start time
    start_time = time.time()
    
    # Run the inspection script with a timeout
    try:
        result = subprocess.run(
            [sys.executable, "tests/debug/inspect_event_class.py"],
            timeout=10,  # Short timeout
            capture_output=True,
            text=True
        )
        
        # Calculate elapsed time
        elapsed = time.time() - start_time
        
        # Print output
        print(f"\nInspection output (completed in {elapsed:.2f} seconds):")
        print("-" * 60)
        print(result.stdout)
        
        if result.stderr:
            print("\nErrors:")
            print("-" * 60)
            print(result.stderr)
        
        return result.returncode
        
    except subprocess.TimeoutExpired:
        print(f"\nInspection timed out after 10 seconds!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
