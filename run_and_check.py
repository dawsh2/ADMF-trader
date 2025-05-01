#!/usr/bin/env python3
"""
Run the check and the fixed MA Crossover implementation.

This script first verifies that the rule_id flow is correct, then
runs the fixed MA Crossover implementation to generate the correct
number of trades.
"""

import os
import sys
import subprocess

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def run_check():
    """Run the rule_id flow check."""
    print_header("RUNNING RULE ID FLOW CHECK")
    
    try:
        # Run the check script
        result = subprocess.run(
            ['python', 'check_rule_id_flow.py'],
            check=False,
            capture_output=True,
            text=True
        )
        
        # Print the output
        print(result.stdout)
        if result.stderr:
            print("ERRORS:")
            print(result.stderr)
        
        # Check if the test passed
        if "ALL CHECKS PASSED" in result.stdout:
            print("✅ Rule ID flow check passed!")
            return True
        else:
            print("❌ Rule ID flow check failed")
            return False
    except Exception as e:
        print(f"❌ Error running check: {e}")
        return False

def run_implementation():
    """Run the fixed MA Crossover implementation."""
    print_header("RUNNING FIXED MA CROSSOVER IMPLEMENTATION")
    
    try:
        # Run the implementation
        result = subprocess.run(
            ['python', 'run_fixed_ma_crossover_v2.py'],
            check=False,
            capture_output=True,
            text=True
        )
        
        # Extract the important parts of the output
        import re
        
        # Find expected and actual counts
        expected_match = re.search(r'Validation signal direction changes: (\d+)', result.stdout)
        actual_match = re.search(r'Actual trades executed: (\d+)', result.stdout)
        
        if expected_match and actual_match:
            expected = int(expected_match.group(1))
            actual = int(actual_match.group(1))
            
            print(f"Expected trades: {expected}")
            print(f"Actual trades: {actual}")
            
            if expected == actual:
                print("✅ Trade counts match! The fix was successful.")
                return True
            else:
                print(f"❌ Trade counts do not match! Expected {expected}, got {actual}")
                
                # Show more info from the output
                print("\nMore information:")
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if "DISCREPANCY" in line:
                        start = max(0, i-5)
                        end = min(len(lines), i+10)
                        print("\n".join(lines[start:end]))
                        break
                
                return False
        else:
            print("❌ Could not extract counts from output")
            print("Here's the end of the output:")
            lines = result.stdout.split('\n')
            print("\n".join(lines[-20:]))
            return False
    except Exception as e:
        print(f"❌ Error running implementation: {e}")
        return False

def main():
    """Run the full sequence."""
    print_header("MA CROSSOVER SIGNAL GROUPING FIX CHECK")
    print("This script checks the rule_id flow and runs the fixed implementation")
    
    # First run the check
    check_ok = run_check()
    
    # Then run the implementation if the check passed
    if check_ok:
        print("\nCheck passed, now running the fixed implementation...")
        impl_ok = run_implementation()
        
        if impl_ok:
            print_header("SUCCESS: THE FIX IS WORKING!")
            print("The rule_id format and processing are correct, and")
            print("the system now generates the expected number of trades.")
            return True
        else:
            print_header("PARTIAL SUCCESS")
            print("The rule_id flow check passed, but the implementation")
            print("still doesn't generate the correct number of trades.")
            print("Check the logs for more details.")
            return False
    else:
        print("\nCheck failed, fix is not complete.")
        print("See the logged errors above for more details.")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
