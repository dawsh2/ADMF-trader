#!/usr/bin/env python
"""
Diagnostic tool for analyzing optimization results and identifying inconsistencies.
"""

import os
import sys
import logging
import json
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_optimization_result(result_file):
    """
    Analyze a single optimization result file for inconsistencies.
    
    Args:
        result_file (str): Path to result JSON file
    """
    logger.info(f"Analyzing optimization result: {result_file}")
    
    try:
        with open(result_file, 'r') as f:
            result = json.load(f)
    except Exception as e:
        logger.error(f"Error loading result file: {e}")
        return
    
    # Extract key information
    train_results = result.get('train_results', {})
    test_results = result.get('test_results', {})
    
    # Analyze train/test results
    for split_name, split_results in [('Train', train_results), ('Test', test_results)]:
        if not split_results:
            logger.warning(f"No {split_name.lower()} results found")
            continue
        
        logger.info(f"\n{split_name} Results Analysis:")
        
        # Get statistics
        statistics = split_results.get('statistics', {})
        return_pct = statistics.get('return_pct', 0)
        profit_factor = statistics.get('profit_factor', 0)
        
        logger.info(f"Return: {return_pct:.2f}%")
        logger.info(f"Profit Factor: {profit_factor:.2f}")
        
        # Check for consistency
        is_consistent = (return_pct > 0 and profit_factor > 1) or (return_pct < 0 and profit_factor < 1) or (abs(return_pct) < 0.01)
        logger.info(f"Metrics consistency: {is_consistent}")
        
        if not is_consistent:
            logger.warning(f"INCONSISTENCY DETECTED: {split_name} return {return_pct:.2f}% but profit factor {profit_factor:.2f}")
            
            # Analyze trades to understand the issue
            trades = split_results.get('trades', [])
            closed_trades = [t for t in trades if t.get('closed', True)]
            
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
            
            logger.info(f"Total trades: {len(trades)}")
            logger.info(f"Closed trades: {len(closed_trades)}")
            logger.info(f"Winning trades: {len(winning_trades)} ({len(winning_trades)/len(closed_trades)*100:.1f}%)")
            logger.info(f"Losing trades: {len(losing_trades)} ({len(losing_trades)/len(closed_trades)*100:.1f}%)")
            
            # Calculate trade statistics
            gross_profit = sum(t.get('pnl', 0) for t in winning_trades)
            gross_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
            total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
            
            logger.info(f"Gross profit: {gross_profit:.2f}")
            logger.info(f"Gross loss: {gross_loss:.2f}")
            logger.info(f"Total PnL from trades: {total_pnl:.2f}")
            
            # Calculate profit factor manually
            calculated_pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            logger.info(f"Manually calculated profit factor: {calculated_pf:.2f}")
            
            # Analyze equity curve
            equity_curve = split_results.get('equity_curve', [])
            if equity_curve:
                try:
                    # Convert to DataFrame if needed
                    if isinstance(equity_curve, list):
                        equity_df = pd.DataFrame(equity_curve)
                    else:
                        equity_df = equity_curve
                    
                    initial_equity = equity_df['equity'].iloc[0] if 'equity' in equity_df.columns else 0
                    final_equity = equity_df['equity'].iloc[-1] if 'equity' in equity_df.columns else 0
                    equity_change = final_equity - initial_equity
                    
                    logger.info(f"Initial equity: {initial_equity:.2f}")
                    logger.info(f"Final equity: {final_equity:.2f}")
                    logger.info(f"Equity change: {equity_change:.2f}")
                    
                    # Check if equity change matches total PnL
                    pnl_equity_diff = abs(total_pnl - equity_change)
                    logger.info(f"PnL vs Equity difference: {pnl_equity_diff:.2f}")
                    
                    if pnl_equity_diff > 0.01 * abs(equity_change):
                        logger.warning(f"Trade PnL doesn't match equity change - this explains the metrics inconsistency")
                        
                        # Plot equity curve to visualize
                        plt.figure(figsize=(10, 6))
                        plt.plot(range(len(equity_df)), equity_df['equity'])
                        plt.title(f"{split_name} Equity Curve\nReturn: {return_pct:.2f}%, PF: {profit_factor:.2f}")
                        plt.xlabel('Bar')
                        plt.ylabel('Equity')
                        
                        # Mark trades on the curve
                        for i, trade in enumerate(closed_trades):
                            if 'exit_time' in trade and 'pnl' in trade:
                                # Find closest equity point to trade exit
                                if 'timestamp' in equity_df.columns:
                                    # Find by timestamp
                                    exit_time = trade['exit_time']
                                    closest_idx = (equity_df['timestamp'] - exit_time).abs().idxmin()
                                else:
                                    # Use a simple approximation - assuming trades are evenly distributed
                                    closest_idx = int(i * len(equity_df) / len(closed_trades))
                                
                                if closest_idx < len(equity_df):
                                    if trade.get('pnl', 0) > 0:
                                        plt.plot(closest_idx, equity_df['equity'].iloc[closest_idx], 'go', alpha=0.5)
                                    else:
                                        plt.plot(closest_idx, equity_df['equity'].iloc[closest_idx], 'ro', alpha=0.5)
                        
                        plt.savefig(f"{split_name.lower()}_equity_analysis.png")
                        logger.info(f"Saved equity curve to {split_name.lower()}_equity_analysis.png")
                        
                except Exception as e:
                    logger.error(f"Error analyzing equity curve: {e}")
            else:
                logger.warning(f"No equity curve data available for {split_name}")
        
        logger.info("-" * 80)
    
    return result

def find_latest_result():
    """Find the latest optimization result file."""
    result_dir = './optimization_results'
    if not os.path.exists(result_dir):
        logger.error(f"Optimization directory not found: {result_dir}")
        return None
    
    json_files = [f for f in glob.glob(os.path.join(result_dir, '*.json')) if 'optimization' in f]
    if not json_files:
        logger.error("No optimization result files found")
        return None
    
    # Sort by modification time (newest first)
    json_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    return json_files[0]

def diagnose_trade_accounting():
    """
    Diagnose potential trade accounting issues.
    
    This function analyzes trade accounting in the current system
    to identify any discrepancies between trade PnL and equity changes.
    """
    logger.info("=" * 80)
    logger.info("TRADE ACCOUNTING DIAGNOSTIC")
    logger.info("=" * 80)
    
    # Find latest result file
    result_file = find_latest_result()
    if not result_file:
        return False
    
    # Analyze the result
    result = analyze_optimization_result(result_file)
    
    logger.info("\nDiagnostic Summary:")
    logger.info("1. Check if trades match equity curve changes")
    logger.info("2. Verify that profit factor calculation uses the same trades as return calculation")
    logger.info("3. Look for any trades with missing or invalid PnL values")
    logger.info("4. Check for any external factors affecting equity that aren't reflected in trades")
    
    logger.info("\nRecommended Actions:")
    logger.info("1. Add verification to BacktestCoordinator._process_results() to check consistency")
    logger.info("2. Ensure all trades are properly closed and accounted for")
    logger.info("3. Verify that the same trade repository is used throughout the system")
    logger.info("4. Check for any external equity adjustments not reflected in trade PnL")
    
    return True

def main():
    """Main function."""
    # Run diagnostic on trade accounting
    diagnose_trade_accounting()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
