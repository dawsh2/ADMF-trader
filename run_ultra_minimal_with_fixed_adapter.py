#!/usr/bin/env python
"""
Script to run the ultra minimal test with fixed adapter.
"""

import subprocess
import sys

def main():
    print("Running ultra minimal test with fixed adapter...")
    
    # Run with a timeout to avoid hanging indefinitely
    try:
        result = subprocess.run(
            [sys.executable, "tests/ultra_minimal_with_fixed_adapter.py"],
            timeout=5,
            capture_output=True,
            text=True
        )
        
        print(f"Test completed with exit code {result.returncode}")
        
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
        print(f"\nTest timed out after 5 seconds!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
