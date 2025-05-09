#!/usr/bin/env python
"""
Script to run the Event class extraction.
"""

import subprocess
import sys

def main():
    print("Extracting Event class definition without execution...")
    
    # Run extraction script
    result = subprocess.run(
        [sys.executable, "tests/extract_event_class.py"],
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
