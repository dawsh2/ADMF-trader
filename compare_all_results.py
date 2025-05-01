#!/usr/bin/env python3
"""
Compare All MA Crossover Strategy Results

This script compares the results from three implementations:
1. The main system backtest
2. The simple verification
3. The enhanced verification

to identify which one matches the main system most closely.
"""

import pandas as pd
import numpy as np
import logging
import glob
import os
import sys
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ma_strategy_all_comparison.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ma_strategy_all_comparison')

def find_latest_backtest_trades():
    """Find the most recent backtest trades CSV file."""
    # Look in the mini_test directory for the most recent trades file
    trades_files = glob.glob('results/mini_test/trades_*.csv')
    if not trades_files:
        return None
    
    # Sort by modification time (most recent first)
    latest_file = max(trades_files, key=os.path.getmtime)
    logger.info(f"Latest backtest trades file: {latest_file}")
    return latest_file

def load_trades_data():
    """
    Load trading data from all implementations.
    
    Returns:
        tuple: (main_df, simple_df, enhanced_df) trade DataFrames
    """
    # Find the main system trades file
    main_trades_file = find_latest_backtest_trades()
    if not main_trades_file:
        logger.error("No backtest trades file found")
        return None, None, None
    
    # Check simple verification trades file
    simple_trades_file = 'ma_strategy_verification_trades.csv'
    if not os.path.exists(simple_trades_file):
        logger.warning(f"Simple verification trades file not found: {simple_trades_file}")
        simple_df = None
    else:
        simple_df = pd.read_csv(simple_trades_file)
        logger.info(f"Simple verification trades: {len(simple_df)}")
    
    # Check enhanced verification trades file
    enhanced_trades_file = 'ma_strategy_verification_enhanced_trades.csv'
    if not os.path.exists(enhanced_trades_file):
        logger.warning(f"Enhanced verification trades file not found: {enhanced_trades_file}")
        enhanced_df = None
    else:
        enhanced_df = pd.read_csv(enhanced_trades_file)
        logger.info(f"Enhanced verification trades: {len(enhanced_df)}")
    
    # Load main system trades
    if not os.path.exists(main_trades_file):
        logger.error(f"Main trades file not found: {main_trades_file}")
        return None, simple_df, enhanced_df
    
    main_df = pd.read_csv(main_trades_file)
    logger.info(f"Main system trades: {len(main_df)}")
    
    return main_df, simple_df, enhanced_df

def compare_trade_counts(main_df, simple_df, enhanced_df):
    """Compare trade counts between implementations."""
    print("\n" + "=" * 60)
    print("TRADE COUNT COMPARISON")
    print("=" * 60)
    
    # Main system
    main_count = len(main_df) if main_df is not None else 0
    main_buys = len(main_df[main_df['direction'] == 'BUY']) if main_df is not None else 0
    main_sells = len(main_df[main_df['direction'] == 'SELL']) if main_df is not None else 0
    
    # Simple verification
    simple_count = len(simple_df) if simple_df is not None else 0
    simple_buys = len(simple_df[simple_df['direction'] == 'BUY']) if simple_df is not None else 0
    simple_sells = len(simple_df[simple_df['direction'] == 'SELL']) if simple_df is not None else 0
    
    # Enhanced verification
    enhanced_count = len(enhanced_df) if enhanced_df is not None else 0
    enhanced_buys = len(enhanced_df[enhanced_df['direction'] == 'BUY']) if enhanced_df is not None else 0
    enhanced_sells = len(enhanced_df[enhanced_df['direction'] == 'SELL']) if enhanced_df is not None else 0
    
    print(f"{'Implementation':<20} {'Total':<10} {'BUY':<10} {'SELL':<10}")
    print("-" * 60)
    print(f"{'Main System':<20} {main_count:<10} {main_buys:<10} {main_sells:<10}")
    print(f"{'Simple Verification':<20} {simple_count:<10} {simple_buys:<10} {simple_sells:<10}")
    print(f"{'Enhanced Verification':<20} {enhanced_count:<10} {enhanced_buys:<10} {enhanced_sells:<10}")
    
    # Compare with main system
    simple_match = (main_count == simple_count and main_buys == simple_buys and main_sells == simple_sells)
    enhanced_match = (main_count == enhanced_count and main_buys == enhanced_buys and main_sells == enhanced_sells)
    
    print("\nTrade Count Match with Main System:")
    print(f"Simple Verification: {'✅ Match' if simple_match else '❌ Mismatch'}")
    print(f"Enhanced Verification: {'✅ Match' if enhanced_match else '❌ Mismatch'}")
    
    return simple_match, enhanced_match

def compare_direction_patterns(main_df, simple_df, enhanced_df):
    """Compare trading direction patterns between implementations."""
    print("\n" + "=" * 60)
    print("DIRECTION PATTERN COMPARISON")
    print("=" * 60)
    
    # Create direction patterns
    if main_df is not None:
        main_pattern = ''.join(['B' if d == 'BUY' else 'S' for d in main_df['direction']])
    else:
        main_pattern = ""
        
    if simple_df is not None:
        simple_pattern = ''.join(['B' if d == 'BUY' else 'S' for d in simple_df['direction']])
    else:
        simple_pattern = ""
        
    if enhanced_df is not None:
        enhanced_pattern = ''.join(['B' if d == 'BUY' else 'S' for d in enhanced_df['direction']])
    else:
        enhanced_pattern = ""
    
    # Compare patterns
    simple_alternating = len(simple_pattern) > 0
    enhanced_alternating = len(enhanced_pattern) > 0
    main_alternating = len(main_pattern) > 0
    
    prev_char = None
    for char in simple_pattern:
        if prev_char == char:
            simple_alternating = False
            break
        prev_char = char
        
    prev_char = None
    for char in enhanced_pattern:
        if prev_char == char:
            enhanced_alternating = False
            break
        prev_char = char
        
    prev_char = None
    for char in main_pattern:
        if prev_char == char:
            main_alternating = False
            break
        prev_char = char
    
    print(f"Main System Pattern: {main_pattern}")
    print(f"Simple Verification Pattern: {simple_pattern}")
    print(f"Enhanced Verification Pattern: {enhanced_pattern}")
    
    print("\nAlternating Pattern Check:")
    print(f"Main System: {'✅ Alternating' if main_alternating else '❌ Not alternating'}")
    print(f"Simple Verification: {'✅ Alternating' if simple_alternating else '❌ Not alternating'}")
    print(f"Enhanced Verification: {'✅ Alternating' if enhanced_alternating else '❌ Not alternating'}")
    
    # Pattern match
    simple_pattern_match = main_pattern == simple_pattern
    enhanced_pattern_match = main_pattern == enhanced_pattern
    
    print("\nPattern Match with Main System:")
    print(f"Simple Verification: {'✅ Match' if simple_pattern_match else '❌ Mismatch'}")
    print(f"Enhanced Verification: {'✅ Match' if enhanced_pattern_match else '❌ Mismatch'}")
    
    # If patterns have different lengths but one is a substring of the other, that's partial match
    if not simple_pattern_match and len(simple_pattern) > 0 and len(main_pattern) > 0:
        if simple_pattern in main_pattern:
            print(f"Simple pattern is a substring of main pattern")
        elif main_pattern in simple_pattern:
            print(f"Main pattern is a substring of simple pattern")
    
    if not enhanced_pattern_match and len(enhanced_pattern) > 0 and len(main_pattern) > 0:
        if enhanced_pattern in main_pattern:
            print(f"Enhanced pattern is a substring of main pattern")
        elif main_pattern in enhanced_pattern:
            print(f"Main pattern is a substring of enhanced pattern")
    
    return simple_pattern_match, enhanced_pattern_match

def compare_pnl(main_df, simple_df, enhanced_df):
    """Compare PnL between implementations."""
    print("\n" + "=" * 60)
    print("PNL COMPARISON")
    print("=" * 60)
    
    # Calculate total PnL
    main_pnl = main_df['pnl'].sum() if main_df is not None and 'pnl' in main_df.columns else 0
    
    simple_pnl = simple_df['pnl'].sum() if simple_df is not None and 'pnl' in simple_df.columns else 0
    
    enhanced_pnl = enhanced_df['pnl'].sum() if enhanced_df is not None and 'pnl' in enhanced_df.columns else 0
    
    print(f"{'Implementation':<20} {'Total PnL':<15}")
    print("-" * 60)
    print(f"{'Main System':<20} ${main_pnl:.2f}")
    print(f"{'Simple Verification':<20} ${simple_pnl:.2f}")
    print(f"{'Enhanced Verification':<20} ${enhanced_pnl:.2f}")
    
    # Calculate differences
    if main_pnl != 0:
        simple_pnl_diff_pct = abs((simple_pnl - main_pnl) / main_pnl * 100)
        enhanced_pnl_diff_pct = abs((enhanced_pnl - main_pnl) / main_pnl * 100)
        
        print(f"\nPnL Difference from Main System:")
        print(f"Simple Verification: ${abs(simple_pnl - main_pnl):.2f} ({simple_pnl_diff_pct:.2f}%)")
        print(f"Enhanced Verification: ${abs(enhanced_pnl - main_pnl):.2f} ({enhanced_pnl_diff_pct:.2f}%)")
        
        # Check for close match (within 5%)
        simple_pnl_match = simple_pnl_diff_pct < 5.0
        enhanced_pnl_match = enhanced_pnl_diff_pct < 5.0
        
        print("\nPnL Match with Main System (within 5%):")
        print(f"Simple Verification: {'✅ Match' if simple_pnl_match else '❌ Mismatch'}")
        print(f"Enhanced Verification: {'✅ Match' if enhanced_pnl_match else '❌ Mismatch'}")
    else:
        simple_pnl_match = False
        enhanced_pnl_match = False
        print("\nCannot calculate percentage difference - main PnL is zero")
    
    return simple_pnl_match, enhanced_pnl_match

def detailed_trade_comparison(main_df, simple_df, enhanced_df):
    """Show detailed trade comparison if not too many trades."""
    max_trades_to_show = 20
    num_trades_to_show = min(
        max(
            len(main_df) if main_df is not None else 0,
            len(simple_df) if simple_df is not None else 0,
            len(enhanced_df) if enhanced_df is not None else 0
        ),
        max_trades_to_show
    )
    
    if num_trades_to_show > 0:
        print("\n" + "=" * 90)
        print("DETAILED TRADE COMPARISON")
        print("=" * 90)
        print(f"{'#':<3} {'Main Direction':<15} {'Simple Direction':<20} {'Enhanced Direction':<20}")
        print("-" * 90)
        
        for i in range(num_trades_to_show):
            main_dir = main_df.iloc[i]['direction'] if main_df is not None and i < len(main_df) else "N/A"
            simple_dir = simple_df.iloc[i]['direction'] if simple_df is not None and i < len(simple_df) else "N/A"
            enhanced_dir = enhanced_df.iloc[i]['direction'] if enhanced_df is not None and i < len(enhanced_df) else "N/A"
            
            main_match = "✅" if main_dir == simple_dir else "❌"
            enhanced_match = "✅" if main_dir == enhanced_dir else "❌"
            
            print(f"{i+1:<3} {main_dir:<15} {simple_dir} {main_match:<5} {enhanced_dir} {enhanced_match:<5}")

def overall_assessment(simple_count_match, enhanced_count_match, 
                       simple_pattern_match, enhanced_pattern_match,
                       simple_pnl_match, enhanced_pnl_match):
    """Provide overall assessment of which implementation matches better."""
    print("\n" + "=" * 60)
    print("OVERALL ASSESSMENT")
    print("=" * 60)
    
    # Score each implementation
    simple_score = sum([simple_count_match, simple_pattern_match, simple_pnl_match])
    enhanced_score = sum([enhanced_count_match, enhanced_pattern_match, enhanced_pnl_match])
    
    # Create feature comparison table
    print(f"{'Feature':<25} {'Simple':<15} {'Enhanced':<15}")
    print("-" * 60)
    print(f"{'Trade Count Match':<25} {'✅' if simple_count_match else '❌':<15} {'✅' if enhanced_count_match else '❌':<15}")
    print(f"{'Direction Pattern Match':<25} {'✅' if simple_pattern_match else '❌':<15} {'✅' if enhanced_pattern_match else '❌':<15}")
    print(f"{'PnL Match (within 5%)':<25} {'✅' if simple_pnl_match else '❌':<15} {'✅' if enhanced_pnl_match else '❌':<15}")
    print("-" * 60)
    print(f"{'TOTAL SCORE':<25} {simple_score}/3{' '*10} {enhanced_score}/3")
    
    # Determine best match
    if simple_score > enhanced_score:
        print("\nConclusion: Simple verification matches the main system better")
    elif enhanced_score > simple_score:
        print("\nConclusion: Enhanced verification matches the main system better")
    else:
        print("\nConclusion: Both implementations match the main system equally")
    
    # Identify discrepancies
    print("\nDiscrepancies to address:")
    
    if not simple_count_match:
        print("- Simple verification has different trade count than main system")
    if not enhanced_count_match:
        print("- Enhanced verification has different trade count than main system")
    
    if not simple_pattern_match:
        print("- Simple verification has different direction pattern than main system")
    if not enhanced_pattern_match:
        print("- Enhanced verification has different direction pattern than main system")
    
    if not simple_pnl_match:
        print("- Simple verification has significantly different PnL than main system")
    if not enhanced_pnl_match:
        print("- Enhanced verification has significantly different PnL than main system")
    
    # If both match perfectly, note that
    if simple_score == 3 and enhanced_score == 3:
        print("No discrepancies found - all implementations match perfectly!")

def main():
    """Main execution function."""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE MA CROSSOVER STRATEGY COMPARISON")
    print("=" * 60)
    
    # Load trade data from all implementations
    main_df, simple_df, enhanced_df = load_trades_data()
    
    if main_df is None:
        print("Main system trades not found. Run the main backtest first.")
        return
    
    if simple_df is None and enhanced_df is None:
        print("No verification trades found. Run at least one verification script first.")
        return
    
    # Compare trade counts
    simple_count_match, enhanced_count_match = compare_trade_counts(main_df, simple_df, enhanced_df)
    
    # Compare direction patterns
    simple_pattern_match, enhanced_pattern_match = compare_direction_patterns(main_df, simple_df, enhanced_df)
    
    # Compare PnL
    simple_pnl_match, enhanced_pnl_match = compare_pnl(main_df, simple_df, enhanced_df)
    
    # Show detailed comparison
    detailed_trade_comparison(main_df, simple_df, enhanced_df)
    
    # Overall assessment
    overall_assessment(simple_count_match, enhanced_count_match, 
                      simple_pattern_match, enhanced_pattern_match,
                      simple_pnl_match, enhanced_pnl_match)
    
    print("\nDetailed log saved to ma_strategy_all_comparison.log")
    
if __name__ == "__main__":
    main()