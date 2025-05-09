#!/usr/bin/env python
"""
ADMF-Trader Balanced Optimization

This script runs optimization using an objective function that balances 
performance between training and testing periods to reduce overfitting.
"""

import os
import sys
import logging
import traceback
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from optimize_strategy import create_data_directories, load_config
from src.strategy.optimization.objective_functions import get_objective_function, sharpe_ratio
from src.core.event_bus import SimpleEventBus
from src.core.trade_repository import TradeRepository
from src.strategy.strategy_factory import StrategyFactory
from src.data.historical_data_handler import HistoricalDataHandler
from src.execution.portfolio import Portfolio
from src.execution.broker.simulated_broker import SimulatedBroker
from src.execution.order_manager import OrderManager
from src.execution.backtest.backtest_coordinator import BacktestCoordinator
from src.strategy.optimization.parameter_space import ParameterSpace, IntegerParameter

def balanced_objective(train_result, test_result, train_weight=0.5):
    """
    A balanced objective function that considers both training and test performance.
    
    Args:
        train_result (dict): Training backtest result
        test_result (dict): Test backtest result
        train_weight (float): Weight for training score (0-1)
        
    Returns:
        float: Combined score
    """
    # Calculate sharpe ratio for both periods
    train_sharpe = sharpe_ratio(train_result)
    test_sharpe = sharpe_ratio(test_result)
    
    # If either is extremely negative, penalize heavily
    if train_sharpe < -10 or test_sharpe < -10:
        return -100
    
    # Get the returns
    train_return = train_result.get('statistics', {}).get('return_pct', 0)
    test_return = test_result.get('statistics', {}).get('return_pct', 0)
    
    # Penalize if both periods have negative returns
    if train_return < 0 and test_return < 0:
        return -50
    
    # Calculate balanced score with more weight to test performance
    test_weight = 1.0 - train_weight
    combined_score = (train_weight * train_sharpe) + (test_weight * test_sharpe)
    
    # Bonus for consistency between periods
    consistency = 1.0 - abs(train_sharpe - test_sharpe) / max(abs(train_sharpe), abs(test_sharpe), 1.0)
    consistency_bonus = consistency * 2.0  # Scale the bonus
    
    return combined_score + consistency_bonus

def print_trade_stats(result):
    """
    Print detailed trade statistics.
    
    Args:
        result (dict): Backtest result
    """
    logger.info("=" * 80)
    logger.info("DETAILED TRADING STATISTICS")
    logger.info("=" * 80)
    
    # Get trades and statistics
    trades = result.get('trades', [])
    stats = result.get('statistics', {})
    
    # Print overall statistics
    logger.info(f"Initial Capital: ${stats.get('initial_capital', 0):,.2f}")
    logger.info(f"Final Capital: ${stats.get('final_capital', 0):,.2f}")
    logger.info(f"Total Return: {stats.get('return_pct', 0):.2f}%")
    logger.info(f"Total Trades: {stats.get('trades_executed', 0)}")
    
    if stats.get('trades_executed', 0) > 0:
        logger.info(f"Win Rate: {stats.get('win_rate', 0) * 100:.2f}%")
        logger.info(f"Profitable Trades: {stats.get('profitable_trades', 0)}")
        logger.info(f"Loss Trades: {stats.get('loss_trades', 0)}")
        logger.info(f"Average Profit: ${stats.get('avg_profit', 0):,.2f}")
        logger.info(f"Average Loss: ${stats.get('avg_loss', 0):,.2f}")
        logger.info(f"Profit Factor: {stats.get('profit_factor', 0):.2f}")
    
    # Print trade details
    if trades:
        logger.info("\nTRADES:")
        logger.info("-" * 80)
        logger.info(f"{'Symbol':<10} {'Direction':<10} {'Entry Time':<25} {'Exit Time':<25} {'PnL':>15}")
        logger.info("-" * 80)
        
        # Sort trades by entry time
        sorted_trades = sorted(trades, key=lambda t: t.get('entry_time', datetime.min))
        
        # Print all trades (up to 20)
        for trade in sorted_trades[:20]:
            symbol = trade.get('symbol', '')
            direction = trade.get('direction', '')
            entry_time = trade.get('entry_time', '')
            exit_time = trade.get('exit_time', '')
            pnl = trade.get('pnl', 0)
            
            logger.info(f"{symbol:<10} {direction:<10} {str(entry_time):<25} {str(exit_time):<25} ${pnl:>13,.2f}")