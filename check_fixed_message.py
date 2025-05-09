#!/usr/bin/env python3
"""
Simple script to verify that the "Fixed Event class" message is gone.
"""
import sys
import os
import subprocess

def main():
    """Run the debug integration test and check for the message."""
    print("Running debug integration test...")
    
    # Capture output
    result = subprocess.run(
        [sys.executable, "run_tests.py", "--debug-integration"],
        capture_output=True,
        text=True
    )
    
    # Print output
    print("\nOutput:")
    print(result.stdout)
    
    # Check for the message
    if "Fixed Event class" in result.stdout:
        print("\n*** The 'Fixed Event class' message is still present! ***")
        print("Occurrences:", result.stdout.count("Fixed Event class"))
        
        # Try to locate where it's coming from
        lines = result.stdout.split("\n")
        for i, line in enumerate(lines):
            if "Fixed Event class" in line:
                context_start = max(0, i - 2)
                context_end = min(len(lines), i + 3)
                print("\nContext:")
                for j in range(context_start, context_end):
                    print(f"{j}: {lines[j]}")
    else:
        print("\nSuccess! The 'Fixed Event class' message is gone.")
    
    # Check exit code
    if result.returncode == 0:
        print("\nTest passed!")
    else:
        print("\nTest failed with exit code:", result.returncode)
        print("Error output:", result.stderr)

if __name__ == "__main__":
    main()
