#!/usr/bin/env python
"""
Analyze the optimization results to check if the fixes worked properly.
"""

import os
import json
import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_latest_results():
    """Analyze the latest optimization results."""
    # Find the latest optimization results
    opt_dir = './optimization_results'
    if not os.path.exists(opt_dir):
        logger.error(f"Optimization directory not found: {opt_dir}")
        return False
        
    # Find all JSON files
    json_files = [f for f in os.listdir(opt_dir) if f.endswith('.json') and 'optimization' in f]
    if not json_files:
        logger.error("No optimization result files found")
        return False
        
    # Sort by modification time (newest first)
    json_files.sort(key=lambda f: os.path.getmtime(os.path.join(opt_dir, f)), reverse=True)
    latest_file = os.path.join(opt_dir, json_files[0])
    
    logger.info(f"Analyzing latest optimization results: {latest_file}")
    
    # Load the results
    try:
        with open(latest_file, 'r') as f:
            results = json.load(f)
    except Exception as e:
        logger.error(f"Error loading results file: {e}")
        return False
    
    # Check best score
    best_score = results.get('best_score', None)
    best_train_score = results.get('best_train_score', None)
    
    if best_score is None and best_train_score is None:
        logger.error("No best score found in results")
        return False
    
    score = best_score if best_score is not None else best_train_score
    logger.info(f"Best score: {score}")
    
    # Analyze train results
    train_results = results.get('train_results', {})
    if train_results:
        train_stats = train_results.get('statistics', {})
        return_pct = train_stats.get('return_pct', 0)
        sharpe = train_stats.get('sharpe_ratio', 0)
        profit_factor = train_stats.get('profit_factor', 0)
        max_dd = train_stats.get('max_drawdown', 0)
        trades = train_stats.get('trades_executed', 0)
        
        logger.info("Training Performance:")
        logger.info(f"  Return: {return_pct:.2f}%")
        logger.info(f"  Sharpe Ratio: {sharpe:.2f}")
        logger.info(f"  Profit Factor: {profit_factor:.2f}")
        logger.info(f"  Max Drawdown: {max_dd:.2f}%")
        logger.info(f"  Trades: {trades}")
        
        # Check for inconsistencies
        if return_pct > 0 and profit_factor < 1:
            logger.warning(f"Inconsistency: Positive return ({return_pct:.2f}%) but profit factor < 1 ({profit_factor:.2f})")
        if return_pct < 0 and profit_factor > 1:
            logger.warning(f"Inconsistency: Negative return ({return_pct:.2f}%) but profit factor > 1 ({profit_factor:.2f})")
        if return_pct > 20 and sharpe < 1:
            logger.warning(f"Inconsistency: High return ({return_pct:.2f}%) but low Sharpe ratio ({sharpe:.2f})")
        if abs(return_pct) > 50 and max_dd < 10:
            logger.warning(f"Inconsistency: Extreme return ({return_pct:.2f}%) but low max drawdown ({max_dd:.2f}%)")
        
        # Check trades
        trades_data = train_results.get('trades', [])
        if len(trades_data) != trades:
            logger.warning(f"Trade count mismatch: {len(trades_data)} trades found, but reported as {trades}")
    
    # Analyze test results
    test_results = results.get('test_results', {})
    if test_results:
        test_stats = test_results.get('statistics', {})
        return_pct = test_stats.get('return_pct', 0)
        sharpe = test_stats.get('sharpe_ratio', 0)
        profit_factor = test_stats.get('profit_factor', 0)
        max_dd = test_stats.get('max_drawdown', 0)
        trades = test_stats.get('trades_executed', 0)
        
        logger.info("Testing Performance:")
        logger.info(f"  Return: {return_pct:.2f}%")
        logger.info(f"  Sharpe Ratio: {sharpe:.2f}")
        logger.info(f"  Profit Factor: {profit_factor:.2f}")
        logger.info(f"  Max Drawdown: {max_dd:.2f}%")
        logger.info(f"  Trades: {trades}")
        
        # Check for inconsistencies
        if return_pct > 0 and profit_factor < 1:
            logger.warning(f"Inconsistency: Positive return ({return_pct:.2f}%) but profit factor < 1 ({profit_factor:.2f})")
        if return_pct < 0 and profit_factor > 1:
            logger.warning(f"Inconsistency: Negative return ({return_pct:.2f}%) but profit factor > 1 ({profit_factor:.2f})")
        if return_pct > 20 and sharpe < 1:
            logger.warning(f"Inconsistency: High return ({return_pct:.2f}%) but low Sharpe ratio ({sharpe:.2f})")
        if abs(return_pct) > 50 and max_dd < 10:
            logger.warning(f"Inconsistency: Extreme return ({return_pct:.2f}%) but low max drawdown ({max_dd:.2f}%)")
        
        # Check trades
        trades_data = test_results.get('trades', [])
        if len(trades_data) != trades:
            logger.warning(f"Trade count mismatch: {len(trades_data)} trades found, but reported as {trades}")
            
    return True

def main():
    """Main function."""
    # Analyze the latest optimization results
    success = analyze_latest_results()
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
