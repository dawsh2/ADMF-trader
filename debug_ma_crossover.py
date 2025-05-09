#!/usr/bin/env python
"""
Debugging script for MA crossover strategy with synthetic data.
This helps diagnose inconsistencies between profit factor and returns.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleMAStrategy:
    """Simplified MA crossover strategy."""
    
    def __init__(self, fast_period=10, slow_period=30):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.positions = {}
        
    def calculate_signals(self, df):
        """Calculate trading signals for the dataset."""
        # Calculate moving averages
        df['fast_ma'] = df['close'].rolling(window=self.fast_period).mean()
        df['slow_ma'] = df['close'].rolling(window=self.slow_period).mean()
        
        # Initialize signals
        df['signal'] = np.nan
        
        # Calculate crossover signals
        for i in range(1, len(df)):
            if pd.notna(df['fast_ma'].iloc[i-1]) and pd.notna(df['slow_ma'].iloc[i-1]):
                prev_fast = df['fast_ma'].iloc[i-1]
                prev_slow = df['slow_ma'].iloc[i-1]
                curr_fast = df['fast_ma'].iloc[i]
                curr_slow = df['slow_ma'].iloc[i]
                
                # Bullish crossover
                if prev_fast <= prev_slow and curr_fast > curr_slow:
                    df.loc[df.index[i], 'signal'] = 1
                # Bearish crossover
                elif prev_fast >= prev_slow and curr_fast < curr_slow:
                    df.loc[df.index[i], 'signal'] = -1
                
        return df

def generate_synthetic_data(days=365, seed=42):
    """Generate synthetic price data."""
    np.random.seed(seed)
    
    # Create date range
    start_date = datetime(2023, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(days)]
    
    # Generate price series with trends and noise
    price = 100.0
    prices = []
    
    # Add some trends
    trends = [
        {'length': 60, 'direction': 0.5},  # Uptrend
        {'length': 40, 'direction': -0.3},  # Downtrend
        {'length': 50, 'direction': 0.2},  # Mild uptrend
        {'length': 30, 'direction': -0.4},  # Downtrend
        {'length': 80, 'direction': 0.6},  # Strong uptrend
        {'length': 70, 'direction': -0.2},  # Mild downtrend
        {'length': 35, 'direction': 0.0},  # Sideways
    ]
    
    current_day = 0
    for trend in trends:
        length = trend['length']
        direction = trend['direction']
        
        for i in range(length):
            if current_day < days:
                # Add daily change with trend and noise
                daily_change = direction + np.random.normal(0, 0.5)
                price = max(0.01, price * (1 + daily_change / 100))
                prices.append(price)
                current_day += 1
                
    # Fill any remaining days with sideways movement
    while current_day < days:
        daily_change = np.random.normal(0, 0.5)
        price = max(0.01, price * (1 + daily_change / 100))
        prices.append(price)
        current_day += 1
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + np.random.uniform(0, 0.01)) for p in prices],
        'low': [p * (1 - np.random.uniform(0, 0.01)) for p in prices],
        'close': prices,
        'volume': [np.random.randint(10000, 100000) for _ in range(days)]
    })
    
    df.set_index('date', inplace=True)
    return df

class SimpleBacktester:
    """Simplified backtester for debugging."""
    
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0
        self.trades = []
        self.open_trade = None
        self.equity_curve = []
        
    def execute_trades(self, df, split=None):
        """Execute trades based on signals in the DataFrame."""
        # Reset state for a fresh run
        self.capital = self.initial_capital
        self.position = 0
        self.trades = []
        self.open_trade = None
        self.equity_curve = [{'date': df.index[0], 'equity': self.initial_capital}]
        
        # Subset the data if split is specified
        if split is not None:
            if split == 'train':
                split_point = int(len(df) * 0.7)
                df = df.iloc[:split_point]
            elif split == 'test':
                split_point = int(len(df) * 0.7)
                df = df.iloc[split_point:]
        
        # Iterate through each bar and generate trades
        for i in range(len(df)):
            date = df.index[i]
            close = df['close'].iloc[i]
            signal = df['signal'].iloc[i]
            
            # Process signals
            if pd.notna(signal):
                if signal == 1 and self.position <= 0:  # Buy signal
                    # Close any existing short position
                    if self.position < 0:
                        self._close_trade(date, close)
                    
                    # Open new long position
                    self._open_trade(date, close, 'LONG')
                    self.position = 1
                    
                elif signal == -1 and self.position >= 0:  # Sell signal
                    # Close any existing long position
                    if self.position > 0:
                        self._close_trade(date, close)
                    
                    # Open new short position
                    self._open_trade(date, close, 'SHORT')
                    self.position = -1
            
            # Update equity curve
            self.equity_curve.append({
                'date': date,
                'equity': self.capital + (self.position * 1.0 * close)  # Include open position value
            })
        
        # Close any open trade at the end
        if self.open_trade:
            self._close_trade(df.index[-1], df['close'].iloc[-1])
        
        # Convert equity curve to DataFrame
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index('date', inplace=True)
        
        return {
            'trades': self.trades,
            'equity_curve': equity_df,
            'final_capital': self.capital,
            'return_pct': (self.capital - self.initial_capital) / self.initial_capital * 100
        }
    
    def _open_trade(self, date, price, direction):
        """Open a new trade."""
        self.open_trade = {
            'id': f"trade_{len(self.trades) + 1}",
            'entry_date': date,
            'entry_price': price,
            'direction': direction,
            'quantity': 1.0,
            'exit_date': None,
            'exit_price': None,
            'pnl': None,
            'closed': False
        }
    
    def _close_trade(self, date, price):
        """Close the current open trade."""
        if not self.open_trade:
            return
        
        # Set exit details
        self.open_trade['exit_date'] = date
        self.open_trade['exit_price'] = price
        
        # Calculate PnL
        if self.open_trade['direction'] == 'LONG':
            pnl = (price - self.open_trade['entry_price']) * self.open_trade['quantity']
        else:  # SHORT
            pnl = (self.open_trade['entry_price'] - price) * self.open_trade['quantity']
        
        self.open_trade['pnl'] = pnl
        self.open_trade['closed'] = True
        
        # Update capital
        self.capital += pnl
        
        # Add to completed trades
        self.trades.append(self.open_trade)
        self.open_trade = None

def calculate_profit_factor(trades):
    """Calculate profit factor from trades."""
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]
    
    gross_profit = sum(t['pnl'] for t in winning_trades)
    gross_loss = abs(sum(t['pnl'] for t in losing_trades))
    
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    
    return gross_profit / gross_loss

def analyze_results(results, name=""):
    """Analyze trading results and check for inconsistencies."""
    trades = results['trades']
    equity_curve = results['equity_curve']
    
    # Calculate metrics
    total_pnl = sum(t['pnl'] for t in trades)
    equity_change = results['final_capital'] - 100000  # Initial capital
    return_pct = results['return_pct']
    profit_factor = calculate_profit_factor(trades)
    
    # Log results
    logger.info(f"Analysis for {name}:")
    logger.info(f"  Total trades: {len(trades)}")
    logger.info(f"  Total PnL: {total_pnl:.2f}")
    logger.info(f"  Equity change: {equity_change:.2f}")
    logger.info(f"  Return: {return_pct:.2f}%")
    logger.info(f"  Profit factor: {profit_factor:.2f}")
    
    # Check for consistency
    is_consistent = (return_pct > 0 and profit_factor > 1.0) or (return_pct < 0 and profit_factor < 1.0) or (abs(return_pct) < 0.01)
    
    if not is_consistent:
        logger.warning(f"  INCONSISTENCY DETECTED: Return {return_pct:.2f}% but Profit Factor {profit_factor:.2f}")
        
        # Detailed analysis to understand the discrepancy
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        logger.info(f"  Winning trades: {len(winning_trades)}")
        logger.info(f"  Losing trades: {len(losing_trades)}")
        
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        
        logger.info(f"  Gross profit: {gross_profit:.2f}")
        logger.info(f"  Gross loss: {gross_loss:.2f}")
        
        # Calculate averages
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        
        logger.info(f"  Average win: {avg_win:.2f}")
        logger.info(f"  Average loss: {avg_loss:.2f}")
        
        # Plot largest trades to see if any outliers are causing issues
        if trades:
            trades_sorted = sorted(trades, key=lambda x: abs(x['pnl']), reverse=True)
            top_trades = trades_sorted[:min(5, len(trades))]
            
            logger.info("  Top trades by absolute PnL:")
            for i, t in enumerate(top_trades):
                logger.info(f"    {i+1}: {t['direction']} - PnL: {t['pnl']:.2f} ({t['entry_date']} to {t['exit_date']})")
    else:
        logger.info("  Metrics are consistent.")
    
    # Plot equity curve
    plt.figure(figsize=(10, 6))
    plt.plot(equity_curve.index, equity_curve['equity'])
    plt.title(f"{name} Equity Curve\nReturn: {return_pct:.2f}%, PF: {profit_factor:.2f}")
    plt.xlabel('Date')
    plt.ylabel('Equity')
    plt.savefig(f"{name.lower().replace(' ', '_')}_equity.png")
    
    return {
        'total_pnl': total_pnl,
        'equity_change': equity_change,
        'return_pct': return_pct,
        'profit_factor': profit_factor,
        'is_consistent': is_consistent
    }

def run_strategy_with_different_params():
    """Run the strategy with different parameters to test for inconsistencies."""
    # Generate synthetic data
    df = generate_synthetic_data(days=365, seed=42)
    
    # Define parameter combinations to test
    params = [
        {'fast_period': 5, 'slow_period': 20},
        {'fast_period': 5, 'slow_period': 30},
        {'fast_period': 10, 'slow_period': 20},
        {'fast_period': 10, 'slow_period': 30}
    ]
    
    # Test each parameter set
    results = []
    for p in params:
        # Create strategy
        strategy = SimpleMAStrategy(fast_period=p['fast_period'], slow_period=p['slow_period'])
        
        # Calculate signals
        df_with_signals = strategy.calculate_signals(df.copy())
        
        # Run backtest on full data
        backtester = SimpleBacktester(initial_capital=100000)
        backtest_results = backtester.execute_trades(df_with_signals)
        
        # Run backtest on train data
        train_backtester = SimpleBacktester(initial_capital=100000)
        train_results = train_backtester.execute_trades(df_with_signals, split='train')
        
        # Run backtest on test data
        test_backtester = SimpleBacktester(initial_capital=100000)
        test_results = test_backtester.execute_trades(df_with_signals, split='test')
        
        # Analyze results
        logger.info(f"\nTesting parameters: fast_period={p['fast_period']}, slow_period={p['slow_period']}")
        full_metrics = analyze_results(backtest_results, name=f"Full Data ({p['fast_period']}/{p['slow_period']})")
        train_metrics = analyze_results(train_results, name=f"Train Data ({p['fast_period']}/{p['slow_period']})")
        test_metrics = analyze_results(test_results, name=f"Test Data ({p['fast_period']}/{p['slow_period']})")
        
        # Store results
        results.append({
            'params': p,
            'full_metrics': full_metrics,
            'train_metrics': train_metrics,
            'test_metrics': test_metrics
        })
    
    # Print summary table
    logger.info("\n" + "=" * 100)
    logger.info("STRATEGY PARAMETERS COMPARISON")
    logger.info("=" * 100)
    
    headers = ["Params", "Train Return", "Train PF", "Consistent?", "Test Return", "Test PF", "Consistent?"]
    logger.info(f"{headers[0]:<15} {headers[1]:<12} {headers[2]:<10} {headers[3]:<12} {headers[4]:<12} {headers[5]:<10} {headers[6]:<12}")
    logger.info("-" * 100)
    
    for r in results:
        p = r['params']
        params_str = f"{p['fast_period']}/{p['slow_period']}"
        train = r['train_metrics']
        test = r['test_metrics']
        
        logger.info(f"{params_str:<15} {train['return_pct']:<12.2f} {train['profit_factor']:<10.2f} {train['is_consistent']!s:<12} {test['return_pct']:<12.2f} {test['profit_factor']:<10.2f} {test['is_consistent']!s:<12}")
    
    return results

def main():
    """Main function."""
    # Run strategy with different parameters
    results = run_strategy_with_different_params()
    
    # Check if any parameter set reproduced the observed inconsistency
    inconsistent_params = []
    for r in results:
        if not r['train_metrics']['is_consistent'] or not r['test_metrics']['is_consistent']:
            inconsistent_params.append(r['params'])
    
    if inconsistent_params:
        logger.info("\nFound parameter sets with metric inconsistencies:")
        for p in inconsistent_params:
            logger.info(f"  Fast period: {p['fast_period']}, Slow period: {p['slow_period']}")
    else:
        logger.info("\nNo inconsistencies found with the parameters tested.")
        logger.info("This suggests the issue may be in the actual implementation's calculations rather than the strategy itself.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
