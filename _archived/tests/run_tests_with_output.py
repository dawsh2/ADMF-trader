#!/usr/bin/env python
"""
Run the tests and capture output.
"""
import os
import sys
import subprocess
import datetime

def run_test(test_script):
    """Run a test script and return results."""
    print(f"Running test: {test_script}")
    
    # Set the timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_output_{timestamp}.txt"
    
    # Run the test
    try:
        result = subprocess.run(
            [sys.executable, test_script],
            check=False,
            capture_output=True,
            text=True
        )
        
        # Save output to file
        with open(output_file, "w") as f:
            f.write(f"Return code: {result.returncode}\n\n")
            f.write("=== STDOUT ===\n")
            f.write(result.stdout or "No output")
            f.write("\n\n=== STDERR ===\n")
            f.write(result.stderr or "No errors")
        
        print(f"Test output saved to {output_file}")
        
        # Print a summary
        print(f"Test result: {'PASSED' if result.returncode == 0 else 'FAILED'}")
        
        return result.returncode == 0
    
    except Exception as e:
        print(f"Error running test: {e}")
        return False

if __name__ == "__main__":
    # Run the test
    success = run_test("/Users/daws/ADMF-trader/test_the_fixes.py")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
