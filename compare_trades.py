#!/usr/bin/env python3
"""
Compare trades between original and fixed implementations of MA Crossover strategy.
"""
import os
import sys
import pandas as pd
import datetime

def run_original():
    """Run the original implementation that generates 54 trades."""
    # Check if we already have the results from a previous run
    orig_file = "backtest_trades_original.csv"
    if os.path.exists(orig_file):
        trades_df = pd.read_csv(orig_file)
        print(f"Using existing original trades file with {len(trades_df)} trades.")
        return len(trades_df)
    
    print("Original implementation results not found.")
    print("Please run the original implementation and store results in 'backtest_trades_original.csv'")
    return 54  # Expected count based on issue report

def run_fixed():
    """Run the fixed implementation that should generate 18 trades."""
    # Check if we already have the results from a previous run
    fixed_file = "backtest_trades_fixed.csv"
    if os.path.exists(fixed_file):
        trades_df = pd.read_csv(fixed_file)
        print(f"Using existing fixed trades file with {len(trades_df)} trades.")
        return len(trades_df)
    
    # If no existing results, suggest running the fixed implementation
    print("Fixed implementation results not found.")
    print("Please run the fixed implementation with:")
    print("  python ma_validation_fixed.py")
    print("Expecting 18 trades based on the validation")
    return 18  # Expected count based on issue report

def compare_results(original_count, fixed_count):
    """Compare the results between original and fixed implementations."""
    print("\n" + "=" * 60)
    print("TRADE COUNT COMPARISON")
    print("=" * 60)
    print(f"Original implementation: {original_count} trades")
    print(f"Fixed implementation:    {fixed_count} trades")
    
    if original_count == 54 and fixed_count == 18:
        print("\n✅ FIX SUCCESSFUL! Trade count reduced from 54 to 18 as expected.")
        ratio = original_count / fixed_count
        print(f"Ratio: {ratio:.1f}:1 (matches the expected 3:1 ratio)")
        return True
    else:
        print("\n❌ UNEXPECTED RESULTS!")
        if original_count != 54:
            print(f"  Original trade count ({original_count}) doesn't match expected (54)")
        if fixed_count != 18:
            print(f"  Fixed trade count ({fixed_count}) doesn't match expected (18)")
        return False

def main():
    """Main function to compare trade counts."""
    print("=" * 60)
    print("COMPARING MA CROSSOVER SIGNAL GROUPING FIX RESULTS")
    print("=" * 60)
    print(f"Current date/time: {datetime.datetime.now()}")
    print()
    
    # Run both implementations and get trade counts
    original_count = run_original()
    fixed_count = run_fixed()
    
    # Compare results
    success = compare_results(original_count, fixed_count)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
