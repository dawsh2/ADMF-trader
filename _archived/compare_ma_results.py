#!/usr/bin/env python3
"""
Compare MA Crossover Strategy Results

This script compares the results from the main system backtest with
the standalone implementation to verify they generate identical
signal patterns.
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
        logging.FileHandler('ma_strategy_comparison.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ma_strategy_comparison')

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

def load_and_prepare_data(main_trades_file, verification_trades_file):
    """
    Load and prepare trading data from both implementations for comparison.
    
    Args:
        main_trades_file: Path to the main system trades CSV
        verification_trades_file: Path to the verification trades CSV
        
    Returns:
        tuple: (main_df, verification_df) prepared DataFrames
    """
    # Check if files exist
    if not os.path.exists(main_trades_file):
        logger.error(f"Main trades file not found: {main_trades_file}")
        return None, None
    
    if not os.path.exists(verification_trades_file):
        logger.error(f"Verification trades file not found: {verification_trades_file}")
        return None, None
    
    # Load the data
    main_df = pd.read_csv(main_trades_file)
    verification_df = pd.read_csv(verification_trades_file)
    
    # Log basic info
    logger.info(f"Main system trades: {len(main_df)}")
    logger.info(f"Verification trades: {len(verification_df)}")
    
    return main_df, verification_df

def analyze_rule_ids(main_df, verification_df):
    """
    Analyze rule IDs in both implementations.
    
    Args:
        main_df: Main system trades DataFrame
        verification_df: Verification trades DataFrame
    """
    # Extract rule IDs if they exist
    main_rule_ids = []
    if 'rule_id' in verification_df.columns:
        verification_rule_ids = verification_df['rule_id'].tolist()
        
        # Count by direction
        verification_buys = verification_df[verification_df['direction'] == 'BUY'].shape[0]
        verification_sells = verification_df[verification_df['direction'] == 'SELL'].shape[0]
        
        # Check alternating pattern
        alternating = True
        prev_direction = None
        for idx, row in verification_df.iterrows():
            if prev_direction == row['direction']:
                alternating = False
                break
            prev_direction = row['direction']
        
        logger.info(f"Verification rule IDs: {verification_rule_ids}")
        logger.info(f"Verification trades: {verification_buys} BUY, {verification_sells} SELL")
        logger.info(f"Verification alternating pattern: {alternating}")
    else:
        logger.warning("No rule_id column in verification trades")
    
    # Compare main and verification
    main_buys = main_df[main_df['direction'] == 'BUY'].shape[0]
    main_sells = main_df[main_df['direction'] == 'SELL'].shape[0]
    
    main_alternating = True
    prev_direction = None
    for idx, row in main_df.iterrows():
        if prev_direction == row['direction']:
            main_alternating = False
            break
        prev_direction = row['direction']
    
    logger.info(f"Main trades: {main_buys} BUY, {main_sells} SELL")
    logger.info(f"Main alternating pattern: {main_alternating}")
    
    print("\n" + "=" * 50)
    print("RULE ID PATTERN ANALYSIS")
    print("=" * 50)
    print(f"Main system trades: {len(main_df)} total, {main_buys} BUY, {main_sells} SELL")
    print(f"Verification trades: {len(verification_df)} total, {verification_buys} BUY, {verification_sells} SELL")
    print(f"Main alternating pattern: {main_alternating}")
    print(f"Verification alternating pattern: {alternating}")
    
    # Check if counts match
    count_match = (len(main_df) == len(verification_df) and 
                  main_buys == verification_buys and 
                  main_sells == verification_sells)
    
    print(f"Trade counts match: {count_match}")
    print("=" * 50)

def compare_trade_patterns(main_df, verification_df):
    """
    Compare trading patterns between both implementations.
    
    Args:
        main_df: Main system trades DataFrame
        verification_df: Verification trades DataFrame
    """
    # Check if both DataFrames have appropriate columns
    required_columns = ['direction', 'quantity', 'price']
    main_has_columns = all(col in main_df.columns for col in required_columns)
    verif_has_columns = all(col in verification_df.columns for col in required_columns)
    
    if not (main_has_columns and verif_has_columns):
        logger.error("Missing required columns for comparison")
        print("Cannot compare trade patterns due to missing columns")
        return
    
    # Sort by timestamp if available, otherwise by index
    if 'timestamp' in main_df.columns:
        main_df = main_df.sort_values('timestamp')
    
    if 'timestamp' in verification_df.columns:
        verification_df = verification_df.sort_values('timestamp')
    
    # Prepare comparison data
    main_patterns = []
    for idx, row in main_df.iterrows():
        main_patterns.append({
            'direction': row['direction'],
            'quantity': row['quantity']
        })
    
    verif_patterns = []
    for idx, row in verification_df.iterrows():
        verif_patterns.append({
            'direction': row['direction'],
            'quantity': row['quantity']
        })
    
    # Check if patterns match
    patterns_match = True
    if len(main_patterns) != len(verif_patterns):
        patterns_match = False
    else:
        for i in range(len(main_patterns)):
            if (main_patterns[i]['direction'] != verif_patterns[i]['direction'] or
                main_patterns[i]['quantity'] != verif_patterns[i]['quantity']):
                patterns_match = False
                break
    
    # Calculate average prices
    main_avg_price = main_df['price'].mean() if 'price' in main_df.columns else 0
    verif_avg_price = verification_df['price'].mean() if 'price' in verification_df.columns else 0
    
    print("\n" + "=" * 50)
    print("TRADE PATTERN ANALYSIS")
    print("=" * 50)
    print(f"Trade patterns match: {patterns_match}")
    print(f"Main system average price: {main_avg_price:.2f}")
    print(f"Verification average price: {verif_avg_price:.2f}")
    
    # Show detailed comparison if small number of trades
    if len(main_df) <= 20 and len(verification_df) <= 20:
        print("\nDetailed comparison:")
        print("{:<5} {:<6} {:<6} {:<10} {:<10}".format(
            "Trade", "Main", "Verif", "Main Qty", "Verif Qty"))
        print("-" * 40)
        
        for i in range(max(len(main_patterns), len(verif_patterns))):
            main_dir = main_patterns[i]['direction'] if i < len(main_patterns) else "N/A"
            main_qty = main_patterns[i]['quantity'] if i < len(main_patterns) else "N/A"
            verif_dir = verif_patterns[i]['direction'] if i < len(verif_patterns) else "N/A"
            verif_qty = verif_patterns[i]['quantity'] if i < len(verif_patterns) else "N/A"
            
            print("{:<5} {:<6} {:<6} {:<10} {:<10}".format(
                i+1, main_dir, verif_dir, main_qty, verif_qty))
    
    print("=" * 50)

def compare_pnl(main_df, verification_df):
    """
    Compare PnL between both implementations.
    
    Args:
        main_df: Main system trades DataFrame
        verification_df: Verification trades DataFrame
    """
    # Check if both DataFrames have PnL column
    if 'pnl' not in main_df.columns or 'pnl' not in verification_df.columns:
        logger.warning("PnL column missing in one or both DataFrames")
        print("Cannot compare PnL due to missing columns")
        return
    
    # Calculate total PnL
    main_total_pnl = main_df['pnl'].sum()
    verif_total_pnl = verification_df['pnl'].sum()
    
    # Calculate PnL by direction
    main_buy_pnl = main_df[main_df['direction'] == 'BUY']['pnl'].sum()
    main_sell_pnl = main_df[main_df['direction'] == 'SELL']['pnl'].sum()
    
    verif_buy_pnl = verification_df[verification_df['direction'] == 'BUY']['pnl'].sum()
    verif_sell_pnl = verification_df[verification_df['direction'] == 'SELL']['pnl'].sum()
    
    print("\n" + "=" * 50)
    print("PNL COMPARISON")
    print("=" * 50)
    print(f"Main system total PnL: ${main_total_pnl:.2f}")
    print(f"Verification total PnL: ${verif_total_pnl:.2f}")
    print(f"PnL difference: ${verif_total_pnl - main_total_pnl:.2f}")
    print(f"PnL % difference: {abs((verif_total_pnl - main_total_pnl) / main_total_pnl * 100):.2f}% (if main PnL != 0)")
    
    print(f"\nMain system BUY PnL: ${main_buy_pnl:.2f}")
    print(f"Verification BUY PnL: ${verif_buy_pnl:.2f}")
    
    print(f"\nMain system SELL PnL: ${main_sell_pnl:.2f}")
    print(f"Verification SELL PnL: ${verif_sell_pnl:.2f}")
    print("=" * 50)

def main():
    """Main execution function."""
    print("\n" + "=" * 50)
    print("MA CROSSOVER STRATEGY COMPARISON")
    print("=" * 50)
    
    # Find the latest backtest trades file
    main_trades_file = find_latest_backtest_trades()
    if not main_trades_file:
        print("No backtest trades file found. Run the backtest first.")
        sys.exit(1)
    
    # Set the verification trades file path
    verification_trades_file = 'ma_strategy_verification_trades.csv'
    
    # Check if verification file exists
    if not os.path.exists(verification_trades_file):
        print(f"Verification trades file not found: {verification_trades_file}")
        print("Run the verify_ma_strategy.py script first.")
        sys.exit(1)
    
    # Load the data
    main_df, verification_df = load_and_prepare_data(main_trades_file, verification_trades_file)
    if main_df is None or verification_df is None:
        sys.exit(1)
    
    # Perform comparisons
    analyze_rule_ids(main_df, verification_df)
    compare_trade_patterns(main_df, verification_df)
    compare_pnl(main_df, verification_df)
    
    # Provide overall assessment
    print("\n" + "=" * 50)
    print("OVERALL ASSESSMENT")
    print("=" * 50)
    
    if len(main_df) == len(verification_df):
        print("✅ Trade count matches")
    else:
        print(f"❌ Trade count mismatch: Main={len(main_df)}, Verification={len(verification_df)}")
    
    # Check direction patterns
    main_directions = ''.join(['B' if d == 'BUY' else 'S' for d in main_df['direction']])
    verif_directions = ''.join(['B' if d == 'BUY' else 'S' for d in verification_df['direction']])
    
    if len(main_directions) == len(verif_directions) and main_directions == verif_directions:
        print("✅ Direction pattern matches")
    else:
        print("❌ Direction pattern mismatch")
    
    # Check quantity patterns
    main_quantities = main_df['quantity'].tolist()
    verif_quantities = verification_df['quantity'].tolist()
    
    if len(main_quantities) == len(verif_quantities) and all(m == v for m, v in zip(main_quantities, verif_quantities)):
        print("✅ Quantity pattern matches")
    else:
        print("❌ Quantity pattern mismatch")
    
    if 'pnl' in main_df.columns and 'pnl' in verification_df.columns:
        main_pnl = main_df['pnl'].sum()
        verif_pnl = verification_df['pnl'].sum()
        pnl_diff_pct = abs((verif_pnl - main_pnl) / main_pnl * 100) if main_pnl != 0 else float('inf')
        
        if pnl_diff_pct < 1.0:  # Less than 1% difference
            print(f"✅ PnL matches within 1% (diff: {pnl_diff_pct:.2f}%)")
        else:
            print(f"❌ PnL difference: {pnl_diff_pct:.2f}%")
    
    print("=" * 50)
    print("\nDetailed log saved to ma_strategy_comparison.log")
    
if __name__ == "__main__":
    main()