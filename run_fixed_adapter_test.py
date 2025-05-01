#!/usr/bin/env python
"""
Script to run the fixed adapter test.
"""

import subprocess
import sys

def main():
    print("Running fixed adapter test...")
    
    # Run the test script
    result = subprocess.run(
        [sys.executable, "tests/fixed_adapter_test.py"],
        capture_output=True,
        text=True
    )
    
    # Print output
    print("\nOutput:")
    print("-" * 60)
    print(result.stdout)
    
    if result.stderr:
        print("\nErrors:")
        print("-" * 60)
        print(result.stderr)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
