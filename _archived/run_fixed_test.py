#!/usr/bin/env python3
"""
Run the fixed MA Crossover implementation after applying the debug patch.

This script first applies the direct debug fix, then runs the implementation
to verify that it generates the correct number of trades.
"""

import sys
import os
import subprocess
import re

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def apply_debug_fix():
    """Apply the debug fix to the MA Crossover strategy."""
    print_header("APPLYING DIRECT FIX TO MA CROSSOVER STRATEGY")
    
    try:
        # Import and run the debug fix
        import debug_ma_strategy
        debug_ma_strategy.debug_rule_id_format()
        return True
    except Exception as e:
        print(f"Error applying debug fix: {e}")
        return False

def run_implementation():
    """Run the fixed MA Crossover implementation."""
    print_header("RUNNING FIXED MA CROSSOVER IMPLEMENTATION")
    
    # Run the implementation
    result = subprocess.run(
        ["python", "run_fixed_ma_crossover_v2.py"],
        capture_output=True,
        text=True
    )
    
    # Print stdout
    print(result.stdout)
    
    # Print stderr if any
    if result.stderr.strip():
        print("ERRORS:")
        print(result.stderr)
    
    # Check the output for trade counts
    expected_match = re.search(r'Validation signal direction changes: (\d+)', result.stdout)
    actual_match = re.search(r'Actual trades executed: (\d+)', result.stdout)
    
    if expected_match and actual_match:
        expected_count = int(expected_match.group(1))
        actual_count = int(actual_match.group(1))
        
        print_header("TRADE COUNT COMPARISON")
        print(f"Expected trades: {expected_count}")
        print(f"Actual trades: {actual_count}")
        
        if expected_count == actual_count:
            print("✅ SUCCESS! Trade counts match - The fix worked!")
            return True
        else:
            ratio = actual_count / expected_count if expected_count > 0 else 0
            print(f"❌ FAILURE: Trade counts don't match! Ratio: {ratio:.1f}")
            
            if abs(ratio - 3.0) < 0.5:
                print("⚠️ The 3:1 ratio suggests the rule_id format issue is still present.")
                print("Check if the fix was properly applied to the running instance.")
            
            return False
    else:
        print("⚠️ Could not extract trade counts from the output")
        return False

def main():
    """Run the full test sequence."""
    print_header("MA CROSSOVER SIGNAL GROUPING FIXED TEST")
    
    # Apply the debug fix
    if not apply_debug_fix():
        print("❌ Failed to apply debug fix. Aborting test.")
        return False
    
    # Run the implementation
    success = run_implementation()
    
    # Print final result
    print_header("TEST RESULT")
    if success:
        print("✅ TEST PASSED: The fix successfully reduced the trade count to match validation.")
        print("The rule_id format issue has been fixed and deduplication is working correctly.")
    else:
        print("❌ TEST FAILED: The fix did not resolve the issue completely.")
        print("Review the logs to identify remaining issues.")
    
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
