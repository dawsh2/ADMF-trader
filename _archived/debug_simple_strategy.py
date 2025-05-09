#!/usr/bin/env python
"""
Simplified trading strategy test to debug inconsistencies between portfolio equity and trade PnL.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleTrade:
    """Simple trade class for debugging."""
    def __init__(self, trade_id, symbol, direction, entry_price, entry_time):
        self.id = trade_id
        self.symbol = symbol
        self.direction = direction
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.exit_price = None
        self.exit_time = None
        self.quantity = 1.0  # Fixed for simplicity
        self.pnl = None
        self.closed = False
    
    def close(self, exit_price, exit_time):
        """Close the trade and calculate PnL."""
        self.exit_price = exit_price
        self.exit_time = exit_time
        
        if self.direction == 'LONG':
            self.pnl = (exit_price - self.entry_price) * self.quantity
        else:  # SHORT
            self.pnl = (self.entry_price - exit_price) * self.quantity
        
        self.closed = True
        return self.pnl
    
    def to_dict(self):
        """Convert to dictionary for metrics calculation."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time,
            'quantity': self.quantity,
            'pnl': self.pnl,
            'closed': self.closed
        }

class SimplePortfolio:
    """Simple portfolio class for debugging."""
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades = []
        self.open_trades = {}
        self.closed_trades = []
        self.equity_curve = [{'timestamp': datetime.now(), 'equity': initial_capital}]
    
    def open_trade(self, symbol, direction, price, timestamp):
        """Open a new trade."""
        trade_id = f"trade_{len(self.trades) + 1}"
        trade = SimpleTrade(trade_id, symbol, direction, price, timestamp)
        self.trades.append(trade)
        self.open_trades[trade_id] = trade
        return trade_id
    
    def close_trade(self, trade_id, price, timestamp):
        """Close an existing trade."""
        if trade_id not in self.open_trades:
            logger.warning(f"Cannot close trade {trade_id} - not found in open trades")
            return 0
        
        trade = self.open_trades[trade_id]
        pnl = trade.close(price, timestamp)
        
        # Update capital
        self.current_capital += pnl
        
        # Update equity curve
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': self.current_capital
        })
        
        # Move to closed trades
        self.closed_trades.append(trade)
        del self.open_trades[trade_id]
        
        logger.info(f"Closed trade {trade_id} with PnL {pnl:.2f}, new capital: {self.current_capital:.2f}")
        return pnl
    
    def get_trades(self):
        """Get all trades."""
        return [t.to_dict() for t in self.trades]
    
    def get_closed_trades(self):
        """Get closed trades."""
        return [t.to_dict() for t in self.closed_trades]
    
    def get_equity_curve(self):
        """Get equity curve as DataFrame."""
        df = pd.DataFrame(self.equity_curve)
        df.set_index('timestamp', inplace=True)
        return df

def calculate_metrics(portfolio):
    """Calculate key metrics for portfolio."""
    from src.analytics.metrics.functional import (
        total_return,
        profit_factor,
        sharpe_ratio
    )
    
    equity_curve = portfolio.get_equity_curve()
    trades = portfolio.get_trades()
    closed_trades = portfolio.get_closed_trades()
    
    # Calculate metrics
    ret = total_return(equity_curve)
    total_return_pct = ret * 100
    pf = profit_factor(closed_trades)
    
    # Calculate total PnL from trades
    total_pnl = sum(t['pnl'] for t in closed_trades if t['closed'] and t['pnl'] is not None)
    
    # Equity change
    equity_change = portfolio.current_capital - portfolio.initial_capital
    
    # Check for consistency
    logger.info("-" * 80)
    logger.info("PORTFOLIO METRICS ANALYSIS")
    logger.info("-" * 80)
    logger.info(f"Initial Capital: {portfolio.initial_capital:.2f}")
    logger.info(f"Final Capital: {portfolio.current_capital:.2f}")
    logger.info(f"Total Return: {total_return_pct:.2f}%")
    logger.info(f"Profit Factor: {pf:.2f}")
    logger.info(f"Total PnL from trades: {total_pnl:.2f}")
    logger.info(f"Equity Change: {equity_change:.2f}")
    
    # Check for discrepancy between return and profit factor
    is_consistent = (total_return_pct > 0 and pf > 1.0) or (total_return_pct < 0 and pf < 1.0) or (abs(total_return_pct) < 0.01)
    if not is_consistent:
        logger.warning(f"INCONSISTENCY DETECTED: Return {total_return_pct:.2f}% vs Profit Factor {pf:.2f}")
        
        # Detailed analysis of the trades
        winning_trades = [t for t in closed_trades if t['pnl'] > 0]
        losing_trades = [t for t in closed_trades if t['pnl'] < 0]
        
        logger.info(f"Total trades: {len(trades)}")
        logger.info(f"Closed trades: {len(closed_trades)}")
        logger.info(f"Winning trades: {len(winning_trades)}")
        logger.info(f"Losing trades: {len(losing_trades)}")
        
        # Examine gross profit and loss
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        
        logger.info(f"Gross profit: {gross_profit:.2f}")
        logger.info(f"Gross loss: {gross_loss:.2f}")
        
        # Manual profit factor calculation to double-check
        if gross_loss > 0:
            manual_pf = gross_profit / gross_loss
            logger.info(f"Manually calculated profit factor: {manual_pf:.2f}")
    else:
        logger.info("Metrics are consistent.")
    
    return {
        'total_return_pct': total_return_pct,
        'profit_factor': pf,
        'total_pnl': total_pnl,
        'equity_change': equity_change,
        'is_consistent': is_consistent
    }

def run_test_scenario_1():
    """
    Run test scenario 1: Positive return with profit factor < 1
    This replicates the pattern seen in training data.
    """
    logger.info("=" * 80)
    logger.info("TEST SCENARIO 1: Positive return with profit factor < 1")
    logger.info("=" * 80)
    
    # Create portfolio
    portfolio = SimplePortfolio(initial_capital=100000)
    
    # Scenario 1: A few large winners followed by many small losers
    # Create a few large winning trades
    for i in range(3):
        trade_id = portfolio.open_trade('TEST', 'LONG', 100, datetime(2024, 1, 1) + timedelta(days=i*5))
        portfolio.close_trade(trade_id, 120, datetime(2024, 1, 1) + timedelta(days=i*5+3))
    
    # Create many small losing trades
    for i in range(15):
        trade_id = portfolio.open_trade('TEST', 'LONG', 100, datetime(2024, 2, 1) + timedelta(days=i*2))
        portfolio.close_trade(trade_id, 99, datetime(2024, 2, 1) + timedelta(days=i*2+1))
    
    # Calculate metrics
    metrics = calculate_metrics(portfolio)
    
    # Plot equity curve
    equity_curve = portfolio.get_equity_curve()
    plt.figure(figsize=(10, 6))
    plt.plot(equity_curve.index, equity_curve['equity'])
    plt.title(f'Scenario 1: Equity Curve\nReturn: {metrics["total_return_pct"]:.2f}%, PF: {metrics["profit_factor"]:.2f}')
    plt.xlabel('Date')
    plt.ylabel('Equity')
    plt.savefig('scenario1_equity.png')
    logger.info("Equity curve saved to 'scenario1_equity.png'")
    
    # Return metrics
    return metrics

def run_test_scenario_2():
    """
    Run test scenario 2: Negative return with profit factor > 1
    This replicates the pattern seen in testing data.
    """
    logger.info("=" * 80)
    logger.info("TEST SCENARIO 2: Negative return with profit factor > 1")
    logger.info("=" * 80)
    
    # Create portfolio
    portfolio = SimplePortfolio(initial_capital=100000)
    
    # Scenario 2: Many small winners with one large loser
    # Create several small winning trades
    for i in range(10):
        trade_id = portfolio.open_trade('TEST', 'LONG', 100, datetime(2024, 5, 1) + timedelta(days=i*3))
        portfolio.close_trade(trade_id, 101, datetime(2024, 5, 1) + timedelta(days=i*3+2))
    
    # Create one large losing trade
    trade_id = portfolio.open_trade('TEST', 'LONG', 100, datetime(2024, 6, 15))
    portfolio.close_trade(trade_id, 80, datetime(2024, 6, 18))
    
    # Calculate metrics
    metrics = calculate_metrics(portfolio)
    
    # Plot equity curve
    equity_curve = portfolio.get_equity_curve()
    plt.figure(figsize=(10, 6))
    plt.plot(equity_curve.index, equity_curve['equity'])
    plt.title(f'Scenario 2: Equity Curve\nReturn: {metrics["total_return_pct"]:.2f}%, PF: {metrics["profit_factor"]:.2f}')
    plt.xlabel('Date')
    plt.ylabel('Equity')
    plt.savefig('scenario2_equity.png')
    logger.info("Equity curve saved to 'scenario2_equity.png'")
    
    # Return metrics
    return metrics

def trace_profit_factor_calculation():
    """
    Trace the profit factor calculation step by step to understand any issues.
    """
    logger.info("=" * 80)
    logger.info("TRACING PROFIT FACTOR CALCULATION")
    logger.info("=" * 80)
    
    # Create sample trades
    trades = [
        {'id': 'trade_1', 'pnl': 5000, 'closed': True},
        {'id': 'trade_2', 'pnl': 3000, 'closed': True},
        {'id': 'trade_3', 'pnl': -500, 'closed': True},
        {'id': 'trade_4', 'pnl': -600, 'closed': True},
        {'id': 'trade_5', 'pnl': -700, 'closed': True},
        {'id': 'trade_6', 'pnl': -400, 'closed': True},
        {'id': 'trade_7', 'pnl': -300, 'closed': True}
    ]
    
    # Trace calculation
    logger.info("Sample trades:")
    for t in trades:
        logger.info(f"  {t['id']}: PnL = {t['pnl']}")
    
    # Calculate gross profit
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    logger.info(f"Gross profit: {gross_profit}")
    
    # Calculate gross loss
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    logger.info(f"Gross loss: {gross_loss}")
    
    # Calculate profit factor
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    logger.info(f"Profit factor: {profit_factor}")
    
    # Calculate total PnL
    total_pnl = sum(t['pnl'] for t in trades)
    logger.info(f"Total PnL: {total_pnl}")
    
    # Verify consistency
    is_consistent = (total_pnl > 0 and profit_factor > 1.0) or (total_pnl < 0 and profit_factor < 1.0) or (abs(total_pnl) < 0.01)
    logger.info(f"Is metrics consistent? {is_consistent}")
    
    # Let's compare with the formula:
    # If total_pnl = gross_profit + (-gross_loss) > 0
    # Then gross_profit > gross_loss
    # And profit_factor = gross_profit / gross_loss > 1
    # So positive return should always give profit_factor > 1
    
    # If gross_profit > gross_loss:
    #   total_pnl = gross_profit - gross_loss > 0
    #   profit_factor = gross_profit / gross_loss > 1
    # If gross_profit < gross_loss:
    #   total_pnl = gross_profit - gross_loss < 0
    #   profit_factor = gross_profit / gross_loss < 1
    
    # Therefore, these are always consistent!
    # If there's an inconsistency, it suggests:
    # 1. A calculation error
    # 2. Different trades being used for the two calculations
    # 3. Additional factors affecting the equity curve beyond the trades
    
    if not is_consistent:
        logger.warning("INCONSISTENCY FOUND! This should not be possible if calculation is correct.")
        logger.warning("This suggests a problem in implementation, not the formula.")
    
    logger.info("=" * 80)

def main():
    """Main function."""
    # First, trace the profit factor calculation for clarity
    trace_profit_factor_calculation()
    
    # Run scenario 1: Positive return with profit factor < 1
    scenario1_results = run_test_scenario_1()
    
    # Run scenario 2: Negative return with profit factor > 1 
    scenario2_results = run_test_scenario_2()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
