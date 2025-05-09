#!/usr/bin/env python
"""
ADMF-Trader Trade Diagnostics

This script diagnoses issues with trade calculations and performance metrics
to help identify inconsistencies in reporting.
"""

import os
import sys
import logging
import json
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trade_diagnostics.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analyze_trades(trades):
    """
    Analyze trades to identify inconsistencies.
    
    Args:
        trades (list): List of trades to analyze
    """
    logger.info(f"Analyzing {len(trades)} trades")
    
    # Basic trade statistics
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    win_trades = [t for t in trades if t.get('pnl', 0) > 0]
    loss_trades = [t for t in trades if t.get('pnl', 0) <= 0]
    
    logger.info(f"Total P&L: {total_pnl:.2f}")
    logger.info(f"Winning trades: {len(win_trades)}")
    logger.info(f"Losing trades: {len(loss_trades)}")
    
    if win_trades:
        avg_win = sum(t.get('pnl', 0) for t in win_trades) / len(win_trades)
        logger.info(f"Average win: {avg_win:.2f}")
    
    if loss_trades:
        avg_loss = sum(t.get('pnl', 0) for t in loss_trades) / len(loss_trades)
        logger.info(f"Average loss: {avg_loss:.2f}")
    
    # Check for trade entry and exit issues
    for i, trade in enumerate(trades):
        entry_price = trade.get('entry_price')
        close_price = trade.get('close_price')
        quantity = trade.get('quantity', 0)
        direction = trade.get('direction', '').lower()
        pnl = trade.get('pnl', 0)
        
        logger.info(f"Trade {i+1}: {direction}, Entry: {entry_price}, Exit: {close_price}, Qty: {quantity}, P&L: {pnl}")
        
        # Calculate expected P&L
        if entry_price is not None and close_price is not None and quantity is not None and direction:
            expected_pnl = 0
            if direction == 'long':
                expected_pnl = (close_price - entry_price) * quantity
            elif direction == 'short':
                expected_pnl = (entry_price - close_price) * quantity
                
            # Compare with actual P&L
            if abs(expected_pnl - pnl) > 0.01:  # Allow for small floating point differences
                logger.warning(f"P&L mismatch in trade {i+1}: Expected {expected_pnl:.2f}, Actual: {pnl:.2f}")
                
    # Check for potential issues with capital or position sizes
    logger.info("Checking for extreme values in trades...")
    for i, trade in enumerate(trades):
        # Check for extremely large position sizes
        quantity = trade.get('quantity', 0)
        if abs(quantity) > 1000000:
            logger.warning(f"Unusually large position size in trade {i+1}: {quantity}")
            
        # Check for extremely large P&L
        pnl = trade.get('pnl', 0)
        if abs(pnl) > 1000000:
            logger.warning(f"Unusually large P&L in trade {i+1}: {pnl}")
            
        # Check for extreme entry/exit prices
        entry_price = trade.get('entry_price')
        close_price = trade.get('close_price')
        if entry_price and entry_price > 1000000:
            logger.warning(f"Unusually high entry price in trade {i+1}: {entry_price}")
        if close_price and close_price > 1000000:
            logger.warning(f"Unusually high exit price in trade {i+1}: {close_price}")

def analyze_backtest_results(results):
    """
    Analyze backtest results to identify inconsistencies.
    
    Args:
        results (dict): Backtest results to analyze
    """
    logger.info("Analyzing backtest results")
    
    # Extract trades and statistics
    trades = results.get('trades', [])
    stats = results.get('statistics', {})
    
    logger.info(f"Statistics from results: {stats}")
    
    # Extract and analyze capital
    initial_capital = stats.get('initial_capital', 0)
    final_capital = stats.get('final_capital', 0)
    return_pct = stats.get('return_pct', 0)
    
    logger.info(f"Initial capital: {initial_capital:.2f}")
    logger.info(f"Final capital: {final_capital:.2f}")
    
    # Recalculate return percentage
    if initial_capital > 0:
        expected_return_pct = ((final_capital - initial_capital) / initial_capital) * 100
        logger.info(f"Expected return: {expected_return_pct:.2f}%")
        logger.info(f"Reported return: {return_pct:.2f}%")
        
        if abs(expected_return_pct - return_pct) > 0.01:
            logger.warning(f"Return percentage mismatch: Expected {expected_return_pct:.2f}%, Reported: {return_pct:.2f}%")
    
    # Analyze trades
    analyze_trades(trades)
    
    # Check for inconsistent statistics
    if len(trades) != stats.get('trades_executed', 0):
        logger.warning(f"Trade count mismatch: {len(trades)} trades found, but reported as {stats.get('trades_executed', 0)}")
        
    # Calculate expected profit factor
    win_trades = [t for t in trades if t.get('pnl', 0) > 0]
    loss_trades = [t for t in trades if t.get('pnl', 0) < 0]
    
    total_profit = sum(t.get('pnl', 0) for t in win_trades)
    total_loss = sum(abs(t.get('pnl', 0)) for t in loss_trades)
    
    if total_loss > 0:
        expected_profit_factor = total_profit / total_loss
        reported_profit_factor = stats.get('profit_factor', 0)
        
        logger.info(f"Expected profit factor: {expected_profit_factor:.2f}")
        logger.info(f"Reported profit factor: {reported_profit_factor:.2f}")
        
        if abs(expected_profit_factor - reported_profit_factor) > 0.01:
            logger.warning(f"Profit factor mismatch: Expected {expected_profit_factor:.2f}, Reported: {reported_profit_factor:.2f}")
    
    # Check max drawdown - should not be 0 with negative returns
    max_drawdown = stats.get('max_drawdown', 0)
    if return_pct < -10 and max_drawdown < 0.1:
        logger.warning(f"Suspicious max drawdown: {max_drawdown:.2f}% with return of {return_pct:.2f}%")

def check_optimization_results():
    """
    Check the latest optimization results for inconsistencies.
    """
    # Find latest optimization results file
    opt_dir = './optimization_results'
    json_files = [f for f in os.listdir(opt_dir) if f.endswith('.json')]
    
    if not json_files:
        logger.error("No optimization results found")
        return
    
    # Sort by modification time (newest first)
    json_files.sort(key=lambda f: os.path.getmtime(os.path.join(opt_dir, f)), reverse=True)
    latest_file = os.path.join(opt_dir, json_files[0])
    
    logger.info(f"Analyzing latest optimization results: {latest_file}")
    
    # Load results
    try:
        with open(latest_file, 'r') as f:
            results = json.load(f)
    except Exception as e:
        logger.error(f"Error loading results file: {e}")
        return
    
    # Analyze train results
    if 'train_results' in results:
        logger.info("Analyzing training results")
        analyze_backtest_results(results['train_results'])
    
    # Analyze test results
    if 'test_results' in results:
        logger.info("Analyzing testing results")
        analyze_backtest_results(results['test_results'])

def main():
    """Main function."""
    logger.info("Starting ADMF-Trader Trade Diagnostics")
    
    # Check optimization results
    check_optimization_results()
    
    logger.info("Trade diagnostics completed")
    
if __name__ == '__main__':
    main()
