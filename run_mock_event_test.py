#!/usr/bin/env python
"""
Script to run the mock Event test.
"""

import subprocess
import sys

def main():
    print("Running mock Event test...")
    
    # Run the test script
    result = subprocess.run(
        [sys.executable, "tests/mock_event_test.py"],
        capture_output=True,
        text=True
    )
    
    # Print output
    print(result.stdout)
    
    if result.stderr:
        print("\nErrors:")
        print("-" * 60)
        print(result.stderr)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
