#!/usr/bin/env python
"""
Simple script to run one test file and report results.
"""
import os
import sys
import subprocess

def run_test(test_script):
    """Run a test script and print results."""
    print(f"Running test: {test_script}")
    
    try:
        result = subprocess.run(
            [sys.executable, test_script],
            check=False,
            capture_output=True,
            text=True
        )
        
        # Print stdout
        if result.stdout:
            print("\nOutput:")
            print(result.stdout)
        
        # Print stderr
        if result.stderr:
            print("\nErrors:")
            print(result.stderr)
        
        # Print result
        if result.returncode == 0:
            print("\nTest PASSED!")
        else:
            print(f"\nTest FAILED with return code {result.returncode}")
            
    except Exception as e:
        print(f"Error running test: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specified test
        test_script = sys.argv[1]
        run_test(test_script)
    else:
        # Default to testing the event system
        run_test("/Users/daws/ADMF-trader/test_event_system.py")
