#!/usr/bin/env python
"""
Script to run the mock event test that completely bypasses the real Event class.
"""

import subprocess
import sys
import os

def main():
    """Run the mock event test."""
    # Run the test directly, not through pytest
    print("Running mock event test directly...")
    
    # Execute the test file directly
    process = subprocess.run(
        [sys.executable, "tests/mock_event_test_complete.py"],
        capture_output=True,
        text=True
    )
    
    # Print output
    print("\nOutput:")
    print("-" * 60)
    print(process.stdout)
    
    if process.stderr:
        print("\nErrors:")
        print("-" * 60)
        print(process.stderr)
    
    return process.returncode

if __name__ == "__main__":
    sys.exit(main())
