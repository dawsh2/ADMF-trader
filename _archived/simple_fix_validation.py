#!/usr/bin/env python3
"""
Simple validation script for the MA Crossover Signal Grouping fix.

This script runs the check and then the fixed implementation to verify
that the fix was successfully applied.
"""

import subprocess
import sys

def run_command(command, label):
    """Run a command and return its output."""
    print(f"\n=== Running {label} ===")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        shell=isinstance(command, str)
    )
    
    # Print command output
    print(result.stdout)
    if result.stderr.strip():
        print("ERRORS:")
        print(result.stderr)
    
    return result.returncode == 0, result.stdout

def run_validation():
    """Run the validation to verify the fix."""
    # Step 1: Run the fixed check script
    check_ok, check_output = run_command(
        ["python", "check_rule_id_flow_fixed.py"], 
        "Rule ID Flow Check"
    )
    
    # Step 2: Run the fixed MA Crossover implementation
    impl_ok, impl_output = run_command(
        ["python", "run_fixed_ma_crossover_v2.py"],
        "Fixed MA Crossover Implementation"
    )
    
    # Check the output for trade counts
    import re
    
    expected_count = None
    actual_count = None
    
    # Try to extract the expected count
    expected_match = re.search(r'Validation signal direction changes: (\d+)', impl_output)
    if expected_match:
        expected_count = int(expected_match.group(1))
    
    # Try to extract the actual count
    actual_match = re.search(r'Actual trades executed: (\d+)', impl_output)
    if actual_match:
        actual_count = int(actual_match.group(1))
    
    # Print the results
    print("\n=== VALIDATION RESULTS ===")
    
    if check_ok:
        print("✅ Rule ID Flow Check: PASSED")
    else:
        print("❌ Rule ID Flow Check: FAILED")
    
    if expected_count is not None and actual_count is not None:
        print(f"Expected trades: {expected_count}")
        print(f"Actual trades: {actual_count}")
        
        if expected_count == actual_count:
            print("✅ Trade counts match!")
            counts_ok = True
        else:
            print(f"❌ Trade counts don't match: {expected_count} vs {actual_count}")
            counts_ok = False
    else:
        print("⚠️ Could not extract trade counts from output")
        counts_ok = False
    
    # Overall result
    print("\n=== FINAL RESULT ===")
    
    if check_ok and impl_ok and counts_ok:
        print("✅ FIX SUCCESSFULLY APPLIED! The system now generates the correct number of trades.")
        return True
    else:
        print("❌ FIX VERIFICATION FAILED")
        failed = []
        if not check_ok:
            failed.append("Rule ID flow check")
        if not impl_ok:
            failed.append("MA Crossover implementation")
        if not counts_ok:
            failed.append("Trade count verification")
            
        print(f"Failed steps: {', '.join(failed)}")
        
        # Additional debug information
        if not counts_ok and expected_count is not None and actual_count is not None:
            ratio = actual_count / expected_count if expected_count > 0 else 0
            print(f"Actual/Expected ratio: {ratio:.1f}")
            
            if abs(ratio - 3.0) < 0.5:
                print("⚠️ The 3:1 ratio suggests the rule_id format issue is still present")
                
                # Try to extract rule IDs from logs
                impl_rule_ids = re.findall(r'RULE ID CREATED: ([^ ]+)', impl_output)
                if impl_rule_ids:
                    print(f"Sample rule IDs from implementation:")
                    for i, rule_id in enumerate(impl_rule_ids[:3]):
                        print(f"  {i+1}. {rule_id}")
        
        return False

if __name__ == "__main__":
    sys.exit(0 if run_validation() else 1)
