#!/usr/bin/env python
"""
Debugging script for analyzing inconsistencies between return calculations and profit factor.
This script uses synthetic data to isolate the issue.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import relevant metrics functions
try:
    from src.analytics.metrics.functional import (
        total_return,
        profit_factor,
        sharpe_ratio,
        calculate_all_metrics
    )
except ImportError:
    logger.error("Could not import metrics functions from src.analytics.metrics.functional")
    # Define simplified versions for standalone testing
    def total_return(equity_curve):
        """Calculate total return from equity curve."""
        if len(equity_curve) < 2:
            return 0.0
        initial = equity_curve['equity'].iloc[0]
        final = equity_curve['equity'].iloc[-1]
        return (final - initial) / initial

    def profit_factor(trades):
        """Calculate profit factor from trades."""
        if not trades:
            return 0.0
        # Only include closed trades with valid PnL
        valid_trades = [t for t in trades if t.get('closed', True) and 'pnl' in t and t['pnl'] is not None]
        if not valid_trades:
            return 0.0
            
        gross_profit = sum(t['pnl'] for t in valid_trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in valid_trades if t['pnl'] < 0))
        
        if gross_loss < 0.001:
            return 100.0 if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

def generate_synthetic_data(initial_capital=100000, num_trades=20, seed=42):
    """
    Generate synthetic trading data for testing.
    
    Args:
        initial_capital (float): Initial capital
        num_trades (int): Number of trades to generate
        seed (int): Random seed for reproducibility
        
    Returns:
        tuple: (equity_curve, trades)
    """
    np.random.seed(seed)
    
    # Generate trade data
    trades = []
    current_capital = initial_capital
    
    # Create timestamp base
    start_date = datetime(2024, 1, 1)
    
    # Create equity curve points
    equity_curve = [{'timestamp': start_date, 'equity': initial_capital}]
    
    # First, let's generate trades with normal profit/loss distribution
    for i in range(num_trades):
        # Generate entry and exit
        entry_time = start_date + timedelta(days=i*5)
        exit_time = entry_time + timedelta(days=3)
        
        # Generate PnL - mixture of gains and losses with slight positive bias
        if i < num_trades / 2:
            # First half: normal mix of gains and losses
            pnl = np.random.normal(500, 2000)
        else:
            # Second half: more skewed to show the issue
            pnl = np.random.normal(-300, 1000)
            
        # Create trade record
        trade = {
            'id': f'trade_{i}',
            'symbol': 'TEST',
            'direction': 'LONG' if np.random.rand() > 0.5 else 'SHORT',
            'entry_time': entry_time,
            'exit_time': exit_time,
            'closed': True,
            'pnl': float(pnl)
        }
        trades.append(trade)
        
        # Update capital and equity curve
        current_capital += pnl
        equity_curve.append({'timestamp': exit_time, 'equity': current_capital})
    
    # Convert equity curve to DataFrame
    equity_df = pd.DataFrame(equity_curve)
    equity_df.set_index('timestamp', inplace=True)
    
    return equity_df, trades

def analyze_metrics_consistency(equity_curve, trades):
    """
    Analyze consistency between return and profit factor.
    
    Args:
        equity_curve (pd.DataFrame): Equity curve
        trades (list): List of trades
    """
    # Calculate return
    ret = total_return(equity_curve)
    total_return_pct = ret * 100
    
    # Calculate profit factor
    pf = profit_factor(trades)
    
    # Calculate total PnL from trades
    total_pnl = sum(t.get('pnl', 0) for t in trades if t.get('closed', True))
    
    # Equity change
    equity_change = equity_curve['equity'].iloc[-1] - equity_curve['equity'].iloc[0]
    
    # Check for consistency
    logger.info("-" * 80)
    logger.info("METRICS CONSISTENCY ANALYSIS")
    logger.info("-" * 80)
    logger.info(f"Total Return: {total_return_pct:.2f}%")
    logger.info(f"Profit Factor: {pf:.2f}")
    logger.info(f"Total PnL from trades: {total_pnl:.2f}")
    logger.info(f"Equity Change: {equity_change:.2f}")
    
    # Check for discrepancy between return and profit factor
    is_consistent = (total_return_pct > 0 and pf > 1.0) or (total_return_pct < 0 and pf < 1.0) or (abs(total_return_pct) < 0.01)
    if not is_consistent:
        logger.warning(f"INCONSISTENCY DETECTED: Return {total_return_pct:.2f}% {'positive' if total_return_pct > 0 else 'negative'} but Profit Factor {pf:.2f}")
        
        # Detailed analysis of the trades
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        
        logger.info(f"Total trades: {len(trades)}")
        logger.info(f"Winning trades: {len(winning_trades)}")
        logger.info(f"Losing trades: {len(losing_trades)}")
        
        # Examine gross profit and loss
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        calculated_pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        logger.info(f"Gross profit: {gross_profit:.2f}")
        logger.info(f"Gross loss: {gross_loss:.2f}")
        logger.info(f"Manually calculated profit factor: {calculated_pf:.2f}")
        
        # Check if pnl matches equity change
        pnl_equity_diff = abs(total_pnl - equity_change)
        logger.info(f"PnL vs Equity Change Difference: {pnl_equity_diff:.2f}")
        
        # Check individual trades for issues
        for i, trade in enumerate(trades):
            if not trade.get('closed', True) or 'pnl' not in trade or trade['pnl'] is None:
                logger.warning(f"Trade {i} issue: closed={trade.get('closed')}, pnl={trade.get('pnl')}")
    else:
        logger.info("Metrics are consistent.")
    
    logger.info("-" * 80)
    
    return {
        'total_return_pct': total_return_pct,
        'profit_factor': pf,
        'total_pnl': total_pnl,
        'equity_change': equity_change,
        'is_consistent': is_consistent
    }

def simulate_scenarios():
    """
    Simulate different scenarios to identify when inconsistencies occur.
    """
    logger.info("=" * 80)
    logger.info("SCENARIO ANALYSIS")
    logger.info("=" * 80)
    
    # Scenario 1: Normal trading with positive return
    logger.info("\nScenario 1: Normal trading with positive return")
    equity_curve, trades = generate_synthetic_data(initial_capital=100000, num_trades=20, seed=42)
    analyze_metrics_consistency(equity_curve, trades)
    
    # Scenario 2: Trading with overall loss
    logger.info("\nScenario 2: Trading with overall loss")
    equity_curve, trades = generate_synthetic_data(initial_capital=100000, num_trades=20, seed=123)
    # Modify to ensure overall loss
    for trade in trades:
        trade['pnl'] = trade['pnl'] * -0.5
    # Recalculate equity curve
    current_capital = 100000
    equity_data = [{'timestamp': datetime(2024, 1, 1), 'equity': current_capital}]
    for trade in trades:
        current_capital += trade['pnl']
        equity_data.append({'timestamp': trade['exit_time'], 'equity': current_capital})
    equity_curve = pd.DataFrame(equity_data)
    equity_curve.set_index('timestamp', inplace=True)
    analyze_metrics_consistency(equity_curve, trades)
    
    # Scenario 3: Mixed trades with inconsistent accounting
    logger.info("\nScenario 3: Mixed trades with inconsistent accounting")
    equity_curve, trades = generate_synthetic_data(initial_capital=100000, num_trades=20, seed=99)
    # Modify to create inconsistency between PnL sum and equity curve
    equity_adjustment = 5000  # Add extra gains to equity not reflected in trades
    last_equity = equity_curve['equity'].iloc[-1]
    equity_curve['equity'].iloc[-1] = last_equity + equity_adjustment
    analyze_metrics_consistency(equity_curve, trades)
    
    # Scenario 4: Edge case with few trades
    logger.info("\nScenario 4: Edge case with few trades")
    equity_curve, trades = generate_synthetic_data(initial_capital=100000, num_trades=3, seed=456)
    analyze_metrics_consistency(equity_curve, trades)
    
    # Scenario 5: The specific pattern we're seeing in the real data
    logger.info("\nScenario 5: Replicating the pattern in the real data (positive return, profit factor < 1)")
    equity_curve, trades = generate_synthetic_data(initial_capital=100000, num_trades=25, seed=789)
    
    # Modify to create the specific scenario: positive return but profit factor < 1
    # This happens when a few large winning trades dominate many small losing trades
    winning_trades = []
    losing_trades = []
    
    for i, trade in enumerate(trades):
        if i < 5:  # First 5 trades are big winners
            trade['pnl'] = np.random.uniform(5000, 10000)
            winning_trades.append(trade)
        else:  # Rest are small losers
            trade['pnl'] = np.random.uniform(-500, -100)
            losing_trades.append(trade)
    
    # Recalculate equity curve
    current_capital = 100000
    equity_data = [{'timestamp': datetime(2024, 1, 1), 'equity': current_capital}]
    for trade in trades:
        current_capital += trade['pnl']
        equity_data.append({'timestamp': trade['exit_time'], 'equity': current_capital})
    equity_curve = pd.DataFrame(equity_data)
    equity_curve.set_index('timestamp', inplace=True)
    
    results = analyze_metrics_consistency(equity_curve, trades)
    
    # Analyze the opposite scenario too
    logger.info("\nScenario 6: Replicating opposite pattern (negative return, profit factor > 1)")
    for trade in trades:
        trade['pnl'] = -trade['pnl']  # Invert all PnLs
    
    # Recalculate equity curve
    current_capital = 100000
    equity_data = [{'timestamp': datetime(2024, 1, 1), 'equity': current_capital}]
    for trade in trades:
        current_capital += trade['pnl']
        equity_data.append({'timestamp': trade['exit_time'], 'equity': current_capital})
    equity_curve = pd.DataFrame(equity_data)
    equity_curve.set_index('timestamp', inplace=True)
    
    analyze_metrics_consistency(equity_curve, trades)
    
    logger.info("=" * 80)

def reproduce_actual_scenario(initial_capital=100000):
    """
    Reproduce the scenario we're seeing in the actual backtesting system.
    """
    logger.info("=" * 80)
    logger.info("REPRODUCING ACTUAL SCENARIO FROM BACKTEST")
    logger.info("=" * 80)
    
    # Created based on the output from your log
    # Parameters: fast_period=10, slow_period=20
    # Training: Return: 104.92%, Profit Factor: 0.62
    # Testing: Return: -1.91%, Profit Factor: 2.96
    
    # Create synthetic trades that would match this pattern
    
    # Training scenario: Positive return but low profit factor
    train_trades = []
    train_equity = [{'timestamp': datetime(2024, 1, 1), 'equity': initial_capital}]
    
    # Create a few large winning trades
    for i in range(3):
        trade = {
            'id': f'train_win_{i}',
            'symbol': 'TEST',
            'direction': 'LONG',
            'entry_time': datetime(2024, 1, 1) + timedelta(days=i*5),
            'exit_time': datetime(2024, 1, 1) + timedelta(days=i*5+3),
            'closed': True,
            'pnl': 50000  # Large winning trades
        }
        train_trades.append(trade)
    
    # Create many small losing trades
    for i in range(15):
        trade = {
            'id': f'train_loss_{i}',
            'symbol': 'TEST',
            'direction': 'LONG',
            'entry_time': datetime(2024, 2, 1) + timedelta(days=i*2),
            'exit_time': datetime(2024, 2, 1) + timedelta(days=i*2+1),
            'closed': True,
            'pnl': -1500  # Small losing trades
        }
        train_trades.append(trade)
    
    # Calculate equity curve
    current_capital = initial_capital
    for trade in train_trades:
        current_capital += trade['pnl']
        train_equity.append({'timestamp': trade['exit_time'], 'equity': current_capital})
    
    train_equity_df = pd.DataFrame(train_equity)
    train_equity_df.set_index('timestamp', inplace=True)
    
    logger.info("\nTraining Scenario Analysis:")
    train_results = analyze_metrics_consistency(train_equity_df, train_trades)
    
    # Testing scenario: Negative return but high profit factor
    test_trades = []
    test_equity = [{'timestamp': datetime(2024, 5, 1), 'equity': initial_capital}]
    
    # Create several small winning trades
    for i in range(6):
        trade = {
            'id': f'test_win_{i}',
            'symbol': 'TEST',
            'direction': 'LONG',
            'entry_time': datetime(2024, 5, 1) + timedelta(days=i*3),
            'exit_time': datetime(2024, 5, 1) + timedelta(days=i*3+2),
            'closed': True,
            'pnl': 800  # Small winning trades
        }
        test_trades.append(trade)
    
    # Create one large losing trade
    trade = {
        'id': 'test_loss_big',
        'symbol': 'TEST',
        'direction': 'LONG',
        'entry_time': datetime(2024, 6, 15),
        'exit_time': datetime(2024, 6, 18),
        'closed': True,
        'pnl': -10000  # One large losing trade
    }
    test_trades.append(trade)
    
    # Calculate equity curve
    current_capital = initial_capital
    for trade in test_trades:
        current_capital += trade['pnl']
        test_equity.append({'timestamp': trade['exit_time'], 'equity': current_capital})
    
    test_equity_df = pd.DataFrame(test_equity)
    test_equity_df.set_index('timestamp', inplace=True)
    
    logger.info("\nTesting Scenario Analysis:")
    test_results = analyze_metrics_consistency(test_equity_df, test_trades)
    
    # Create visualizations to understand the pattern
    plt.figure(figsize=(12, 10))
    
    # Plot training equity curve
    plt.subplot(2, 2, 1)
    plt.plot(train_equity_df.index, train_equity_df['equity'])
    plt.title(f'Training Equity Curve\nReturn: {train_results["total_return_pct"]:.2f}%, PF: {train_results["profit_factor"]:.2f}')
    plt.xlabel('Date')
    plt.ylabel('Equity')
    plt.xticks(rotation=45)
    
    # Plot testing equity curve
    plt.subplot(2, 2, 2)
    plt.plot(test_equity_df.index, test_equity_df['equity'])
    plt.title(f'Testing Equity Curve\nReturn: {test_results["total_return_pct"]:.2f}%, PF: {test_results["profit_factor"]:.2f}')
    plt.xlabel('Date')
    plt.ylabel('Equity')
    plt.xticks(rotation=45)
    
    # Plot training trade distribution
    plt.subplot(2, 2, 3)
    train_pnls = [t['pnl'] for t in train_trades]
    plt.hist(train_pnls, bins=20)
    plt.title('Training Trade PnL Distribution')
    plt.xlabel('PnL')
    plt.ylabel('Frequency')
    
    # Plot testing trade distribution
    plt.subplot(2, 2, 4)
    test_pnls = [t['pnl'] for t in test_trades]
    plt.hist(test_pnls, bins=20)
    plt.title('Testing Trade PnL Distribution')
    plt.xlabel('PnL')
    plt.ylabel('Frequency')
    
    plt.tight_layout()
    plt.savefig('scenario_analysis.png')
    logger.info("Visualization saved to 'scenario_analysis.png'")
    
    logger.info("=" * 80)
    
    return {
        'train': train_results,
        'test': test_results
    }

def main():
    """Main function."""
    # First, run a simple synthetic test
    logger.info("Running synthetic data metrics test")
    equity_curve, trades = generate_synthetic_data()
    analyze_metrics_consistency(equity_curve, trades)
    
    # Then simulate different scenarios
    simulate_scenarios()
    
    # Finally, reproduce the actual scenario we're seeing
    reproduce_actual_scenario()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
