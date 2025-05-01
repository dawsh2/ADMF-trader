#!/usr/bin/env python
"""
Execute test using os.system to avoid integration issues.
"""
import os
import sys

def main():
    # Execute the test in the shell
    cmd = "cd /Users/daws/ADMF-trader && python final_test.py"
    print(f"Executing: {cmd}")
    
    # Run the command
    exit_code = os.system(cmd)
    
    # Report result
    if exit_code == 0:
        print("SUCCESS: Test passed!")
    else:
        print(f"FAILED: Test exited with code {exit_code}")
    
    # Regardless of result, try to output the logs
    print("\nAttempting to display test logs for analysis:")
    try:
        with open("/Users/daws/ADMF-trader/fixed_output.txt", "r") as f:
            output = f.read()
            
        # Print the last 30 lines which should contain the test summary
        lines = output.split('\n')
        if len(lines) > 30:
            print("\nLast 30 lines of test output:")
            for line in lines[-30:]:
                print(line)
        else:
            print("\nFull test output:")
            print(output)
    except Exception as e:
        print(f"Failed to read output: {e}")
        
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
