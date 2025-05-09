#!/usr/bin/env python3
"""
Trade Backtest Diagnostic Tool for ADMF-trader

This script performs comprehensive diagnostics on the ADMF-trader system, focusing on:
1. Event flow tracing from signals to trades
2. Trade statistics calculation validation
3. PnL computation verification
4. Win rate and total return discrepancy analysis

Use this to debug issues like 100% win rate with negative returns or other inconsistencies.
"""
import os
import sys
import logging
import datetime
import pandas as pd
import numpy as np
import argparse
import json
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"trade_diagnostic_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)


class TradeBacktestDiagnostic:
    """Diagnostic tool for analyzing backtest trade data and results."""
    
    def __init__(self):
        """Initialize the diagnostic tool."""
        self.equity_curve = None
        self.trades = None
        self.metrics = None
        self.trade_events = []
        self.signal_events = []
        self.fill_events = []
        self.pnl_discrepancies = []
        self.win_rate_issues = False
            
    def load_backtest_results(self, results_dir: str, run_id: Optional[str] = None):
        """
        Load backtest results from a specified directory.
        
        Args:
            results_dir: Directory containing results
            run_id: Specific run ID (timestamp) to load, or None for latest
        """
        logger.info(f"Loading backtest results from {results_dir}")
        
        # Find the latest run if no specific run_id provided
        if not run_id:
            # Find all equity curve files and sort by timestamp
            equity_files = [f for f in os.listdir(results_dir) if f.startswith("equity_curve_")]
            if not equity_files:
                logger.error(f"No equity curve files found in {results_dir}")
                return False
                
            # Sort by timestamp
            equity_files.sort(reverse=True)
            # Extract run_id (timestamp) from filename
            run_id = equity_files[0].replace("equity_curve_", "").replace(".csv", "")
            
        logger.info(f"Using run ID: {run_id}")
        
        # Load equity curve
        equity_file = os.path.join(results_dir, f"equity_curve_{run_id}.csv")
        if not os.path.exists(equity_file):
            logger.error(f"Equity curve file not found: {equity_file}")
            return False
            
        self.equity_curve = pd.read_csv(equity_file)
        logger.info(f"Loaded equity curve with {len(self.equity_curve)} data points")
        
        # Load trades if available
        trades_file = os.path.join(results_dir, f"trades_{run_id}.csv")
        if os.path.exists(trades_file):
            self.trades = pd.read_csv(trades_file)
            logger.info(f"Loaded {len(self.trades)} trades from {trades_file}")
        else:
            logger.warning(f"Trades file not found: {trades_file}")
            
        # Load backtest report for metrics
        report_file = os.path.join(results_dir, f"backtest_report_{run_id}.txt")
        if os.path.exists(report_file):
            self.metrics = self._parse_backtest_report(report_file)
            logger.info(f"Loaded metrics from backtest report")
        else:
            logger.warning(f"Backtest report not found: {report_file}")
            
        return True
        
    def _parse_backtest_report(self, report_file: str) -> Dict:
        """
        Parse backtest report file to extract metrics.
        
        Args:
            report_file: Path to backtest report file
            
        Returns:
            Dictionary of metrics
        """
        metrics = {}
        with open(report_file, 'r') as f:
            lines = f.readlines()
            
        in_summary = False
        for line in lines:
            line = line.strip()
            # Check for summary section
            if "=== Backtest Results ===" in line:
                in_summary = True
                continue
                
            if in_summary and line and ":" in line:
                parts = line.split(":")
                key = parts[0].strip()
                value = parts[1].strip()
                
                # Convert percentages to floats
                if "%" in value:
                    value = value.replace("%", "")
                    try:
                        metrics[key] = float(value) / 100.0
                    except ValueError:
                        metrics[key] = value
                # Convert numbers to floats
                else:
                    try:
                        metrics[key] = float(value)
                    except ValueError:
                        metrics[key] = value
                        
        return metrics
    
    def analyze_trades(self):
        """Analyze trades for inconsistencies and discrepancies."""
        if self.trades is None or len(self.trades) == 0:
            logger.error("No trades available for analysis")
            return False
            
        logger.info(f"Analyzing {len(self.trades)} trades...")
        
        # Check for basic trade attributes
        required_columns = ['symbol', 'direction', 'quantity', 'price', 'pnl']
        missing_columns = [col for col in required_columns if col not in self.trades.columns]
        if missing_columns:
            logger.error(f"Trades data is missing required columns: {missing_columns}")
            return False
        
        # Check trade directions
        buy_trades = self.trades[self.trades['direction'] == 'BUY']
        sell_trades = self.trades[self.trades['direction'] == 'SELL']
        logger.info(f"Trade direction stats: {len(buy_trades)} BUY, {len(sell_trades)} SELL")
        
        # Check trade PnL distribution
        winning_trades = self.trades[self.trades['pnl'] > 0]
        losing_trades = self.trades[self.trades['pnl'] < 0]
        zero_pnl_trades = self.trades[self.trades['pnl'] == 0]
        
        win_rate = len(winning_trades) / len(self.trades) if len(self.trades) > 0 else 0
        
        logger.info(f"PnL distribution:")
        logger.info(f"  - Winning trades: {len(winning_trades)} ({win_rate:.2%})")
        logger.info(f"  - Losing trades: {len(losing_trades)} ({len(losing_trades)/len(self.trades):.2%})")
        logger.info(f"  - Zero PnL trades: {len(zero_pnl_trades)} ({len(zero_pnl_trades)/len(self.trades):.2%})")
        
        # Check for win rate vs. reported metrics discrepancy
        if self.metrics and 'Win Rate' in self.metrics:
            reported_win_rate = self.metrics['Win Rate']
            win_rate_diff = abs(win_rate - reported_win_rate)
            
            if win_rate_diff > 0.01:  # More than 1% difference
                logger.warning(f"Win rate discrepancy: Calculated {win_rate:.2%} vs Reported {reported_win_rate:.2%}")
                self.win_rate_issues = True
            
        # Check total return consistency
        total_pnl = self.trades['pnl'].sum()
        
        if self.metrics and 'Total Return' in self.metrics:
            reported_return = self.metrics['Total Return']
            
            # Calculate implied PnL from equity curve
            if self.equity_curve is not None and len(self.equity_curve) > 1:
                initial_equity = self.equity_curve['equity'].iloc[0]
                final_equity = self.equity_curve['equity'].iloc[-1]
                implied_pnl = final_equity - initial_equity
                
                logger.info(f"Return measures:")
                logger.info(f"  - Sum of trade PnLs: {total_pnl:.2f}")
                logger.info(f"  - Implied PnL from equity curve: {implied_pnl:.2f}")
                logger.info(f"  - Reported total return: {reported_return:.2%} (on initial equity: {initial_equity:.2f})")
                
                # Check for inconsistency
                expected_return = implied_pnl / initial_equity
                if abs(expected_return - reported_return) > 0.01:  # More than 1% difference
                    logger.warning(f"Total return inconsistency: {expected_return:.2%} vs {reported_return:.2%}")
                    
        # Detect strange patterns
        all_wins = len(winning_trades) == len(self.trades) and len(self.trades) > 0
        all_losses = len(losing_trades) == len(self.trades) and len(self.trades) > 0
        
        if all_wins:
            logger.warning("ISSUE DETECTED: All trades are winners (100% win rate)")
            if total_pnl <= 0:
                logger.error("CRITICAL ISSUE: 100% win rate but negative or zero total PnL!")
                
        if all_losses:
            logger.warning("ISSUE DETECTED: All trades are losers (0% win rate)")
            
        # Check for duplicate trades
        if 'timestamp' in self.trades.columns:
            dupes = self.trades.duplicated(subset=['timestamp', 'symbol', 'direction', 'quantity', 'price'], keep=False)
            if dupes.any():
                logger.warning(f"Found {dupes.sum()} duplicate trades")
                
        return True
    
    def check_for_artificial_trades(self):
        """Check if trades show signs of artificial PnL generation."""
        if self.trades is None or len(self.trades) == 0:
            return False
            
        # Check if trades have entry_price and exit_price columns
        has_entry_exit = 'entry_price' in self.trades.columns and 'exit_price' in self.trades.columns
        
        if has_entry_exit:
            # Check for patterns in entry/exit price relationships
            if 'direction' in self.trades.columns:
                buy_trades = self.trades[self.trades['direction'] == 'BUY']
                sell_trades = self.trades[self.trades['direction'] == 'SELL']
                
                # For buy trades, check if exit is consistently higher than entry
                if len(buy_trades) > 10:
                    exit_higher = (buy_trades['exit_price'] > buy_trades['entry_price']).mean()
                    logger.info(f"Buy trades with exit price > entry price: {exit_higher:.2%}")
                    
                    # If extremely consistent percentage, likely artificial
                    if exit_higher > 0.95 or exit_higher < 0.05:
                        logger.warning(f"ARTIFICIAL PATTERN DETECTED: {exit_higher:.2%} of buy trades have exit price {'>' if exit_higher > 0.5 else '<'} entry price")
                        
                # For sell trades, check if exit is consistently lower than entry
                if len(sell_trades) > 10:
                    exit_lower = (sell_trades['exit_price'] < sell_trades['entry_price']).mean()
                    logger.info(f"Sell trades with exit price < entry price: {exit_lower:.2%}")
                    
                    # If extremely consistent percentage, likely artificial
                    if exit_lower > 0.95 or exit_lower < 0.05:
                        logger.warning(f"ARTIFICIAL PATTERN DETECTED: {exit_lower:.2%} of sell trades have exit price {'<' if exit_lower > 0.5 else '>'} entry price")
            
            # Check for specific price adjustment patterns (e.g., fixed multiplier)
            if len(self.trades) > 10:
                # Calculate ratio between exit and entry prices
                self.trades['price_ratio'] = self.trades['exit_price'] / self.trades['entry_price'].replace(0, float('nan'))
                
                # Remove outliers and check for clustered ratios
                valid_ratios = self.trades['price_ratio'].dropna()
                if len(valid_ratios) > 5:
                    ratio_std = valid_ratios.std()
                    ratio_mean = valid_ratios.mean()
                    
                    # Very low standard deviation might indicate fixed multiplier
                    if ratio_std < 0.0001 and ratio_mean != 1.0:
                        logger.warning(f"ARTIFICIAL PATTERN DETECTED: Fixed price ratio detected ({ratio_mean:.6f})")
                        logger.warning("This suggests artificial price adjustments rather than market-driven pricing")
                        
                    # Look for common ratios like 1.001 (0.1% up) or 0.999 (0.1% down)
                    common_ratios = [1.001, 0.999, 1.01, 0.99, 1.005, 0.995]
                    
                    for ratio in common_ratios:
                        close_to_ratio = (valid_ratios > ratio - 0.0001) & (valid_ratios < ratio + 0.0001)
                        pct_close = close_to_ratio.mean()
                        
                        if pct_close > 0.2:  # More than 20% of trades
                            logger.warning(f"ARTIFICIAL PATTERN DETECTED: {pct_close:.2%} of trades have price ratio very close to {ratio}")
                            
        return True
    
    def verify_performance_metrics(self):
        """Verify performance metrics for consistency."""
        if self.metrics is None:
            logger.error("No metrics available for verification")
            return False
            
        logger.info("Verifying performance metrics...")
        
        # Check win rate vs. total return consistency
        if 'Win Rate' in self.metrics and 'Total Return' in self.metrics:
            win_rate = self.metrics['Win Rate']
            total_return = self.metrics['Total Return']
            
            # A very high win rate should generally correspond to a positive return
            if win_rate > 0.8 and total_return < 0:
                logger.error(f"INCONSISTENCY: High win rate ({win_rate:.2%}) with negative return ({total_return:.2%})")
                logger.error("This strongly suggests issues with PnL calculation or artificial trade generation")
                
            # A very low win rate should generally correspond to a negative return
            if win_rate < 0.2 and total_return > 0:
                logger.error(f"INCONSISTENCY: Low win rate ({win_rate:.2%}) with positive return ({total_return:.2%})")
                
        # Check Sharpe ratio consistency with returns
        if 'Sharpe Ratio' in self.metrics and 'Total Return' in self.metrics:
            sharpe = self.metrics['Sharpe Ratio']
            total_return = self.metrics['Total Return']
            
            # Sign mismatch
            if (sharpe > 0 and total_return < 0) or (sharpe < 0 and total_return > 0):
                logger.error(f"INCONSISTENCY: Sharpe ratio ({sharpe:.4f}) and Total Return ({total_return:.2%}) have opposite signs")
                
        # Check profit factor versus win rate
        if 'Profit Factor' in self.metrics and 'Win Rate' in self.metrics:
            profit_factor = self.metrics['Profit Factor']
            win_rate = self.metrics['Win Rate']
            
            # Profit factor should be reasonable given the win rate
            if win_rate == 1.0 and profit_factor != float('inf'):
                logger.error(f"INCONSISTENCY: 100% win rate should have infinite profit factor, got {profit_factor}")
                
            if win_rate == 0.0 and profit_factor != 0.0:
                logger.error(f"INCONSISTENCY: 0% win rate should have zero profit factor, got {profit_factor}")
                
        return True
        
    def recommend_fixes(self):
        """Provide recommendations to fix detected issues."""
        logger.info("\n=== DIAGNOSTIC RECOMMENDATIONS ===\n")
        
        if self.win_rate_issues:
            logger.info("1. Win Rate Calculation Issues:")
            logger.info("   - Check src/analytics/metrics/functional.py, win_rate() function")
            logger.info("   - Verify trades are being properly filtered (only closed trades should be counted)")
            logger.info("   - Check that zero-PnL trades are handled correctly in calculations")
            logger.info("   - Ensure losing trades aren't being filtered out accidentally")
            
        if self.trades is not None and len(self.trades) > 0:
            winning_trades = self.trades[self.trades['pnl'] > 0]
            losing_trades = self.trades[self.trades['pnl'] < 0]
            
            if len(winning_trades) == len(self.trades) and len(self.trades) > 0:
                logger.info("2. Artificial Trade Generation Detected:")
                logger.info("   - Check src/execution/order_manager.py, handle_fill() method")
                logger.info("   - Look for code that artificially sets exit_price based on entry price")
                logger.info("   - Check for patterns like 'exit_price = price * 1.001' or similar")
                logger.info("   - Consider removing artificial price adjustments to let strategy determine outcomes")
                logger.info("   - Strategy should generate trade signals based on actual market data")
        
        # Check for typical event flow issues
        logger.info("3. Event Flow and Order Execution:")
        logger.info("   - Check event bus for proper event propagation (src/core/events/event_bus.py)")
        logger.info("   - Verify portfolio correctly processes TRADE_OPEN/TRADE_CLOSE events (src/risk/portfolio/portfolio.py)")
        logger.info("   - Consider implementing a debug tool to trace event flow through the system")
        
        # Recommendations for proper backtest setup
        logger.info("4. Proper Backtest Configuration:")
        logger.info("   - Check src/execution/backtest/backtest.py for proper component initialization")
        logger.info("   - Ensure event bus is properly reset between test runs")
        logger.info("   - Verify that strategy signal generation works with your test data")
        
        # Artificial test data and validation
        logger.info("5. Test Data and Validation:")
        logger.info("   - Create synthetic test data with known patterns to validate strategy")
        logger.info("   - Implement a separate validation script to verify trades against raw price data")
        logger.info("   - Check if HEAD_1min.csv or other synthetic datasets are properly formatted")
        
        return True
    
    def create_validation_script(self):
        """Generate a validation script to cross-check trades against price data."""
        validation_code = '''#!/usr/bin/env python3
"""
Trade Validation Script for ADMF-trader

This script validates trades against raw price data to ensure they're correctly generated.
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

def load_price_data(data_file):
    """Load price data from CSV file."""
    try:
        data = pd.read_csv(data_file)
        # Ensure we have datetime index
        if 'timestamp' in data.columns:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            data.set_index('timestamp', inplace=True)
        elif 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            data.set_index('date', inplace=True)
        
        logger.info(f"Loaded {len(data)} price data points from {data_file}")
        return data
    except Exception as e:
        logger.error(f"Error loading price data: {e}")
        return None

def load_trades(trades_file):
    """Load trades from CSV file."""
    try:
        trades = pd.read_csv(trades_file)
        
        # Convert timestamps to datetime
        if 'timestamp' in trades.columns:
            trades['timestamp'] = pd.to_datetime(trades['timestamp'])
            
        # Convert entry/exit times to datetime if they exist
        for col in ['entry_time', 'exit_time']:
            if col in trades.columns:
                trades[col] = pd.to_datetime(trades[col])
        
        logger.info(f"Loaded {len(trades)} trades from {trades_file}")
        return trades
    except Exception as e:
        logger.error(f"Error loading trades: {e}")
        return None

def validate_trades_against_price_data(trades, price_data, symbol=None):
    """Validate trades against price data to ensure they're plausible."""
    if symbol:
        # Filter trades for specific symbol
        trades = trades[trades['symbol'] == symbol]
        
    if 'entry_time' not in trades.columns or 'exit_time' not in trades.columns:
        logger.warning("Trades data missing entry_time/exit_time fields, can't validate timing")
        return False
    
    valid_trades = 0
    invalid_trades = 0
    
    for idx, trade in trades.iterrows():
        # Find price data within the entry and exit time range
        entry_time = trade['entry_time']
        exit_time = trade['exit_time']
        
        # Skip trades without timing info
        if pd.isna(entry_time) or pd.isna(exit_time):
            continue
            
        try:
            # Get price data between entry and exit time
            mask = (price_data.index >= entry_time) & (price_data.index <= exit_time)
            trade_period_data = price_data[mask]
            
            if len(trade_period_data) == 0:
                logger.warning(f"No price data found for trade {idx} time period")
                invalid_trades += 1
                continue
                
            # Check if entry and exit prices are within the range of prices during the period
            min_price = trade_period_data['low'].min() if 'low' in trade_period_data.columns else trade_period_data['close'].min()
            max_price = trade_period_data['high'].max() if 'high' in trade_period_data.columns else trade_period_data['close'].max()
            
            entry_price = trade['entry_price'] if 'entry_price' in trade.columns else trade['price']
            exit_price = trade['exit_price'] if 'exit_price' in trade.columns else None
            
            # Check if entry price is plausible
            if entry_price < min_price * 0.99 or entry_price > max_price * 1.01:
                logger.warning(f"Trade {idx} entry price {entry_price} outside price range [{min_price}, {max_price}]")
                invalid_trades += 1
                continue
                
            # Check if exit price is plausible
            if exit_price is not None:
                if exit_price < min_price * 0.99 or exit_price > max_price * 1.01:
                    logger.warning(f"Trade {idx} exit price {exit_price} outside price range [{min_price}, {max_price}]")
                    invalid_trades += 1
                    continue
            
            valid_trades += 1
            
        except Exception as e:
            logger.error(f"Error validating trade {idx}: {e}")
            invalid_trades += 1
    
    logger.info(f"Trade validation results: {valid_trades} valid, {invalid_trades} invalid")
    
    # Create a validation plot if we have enough data
    if valid_trades > 0 and len(price_data) > 0:
        try:
            plt.figure(figsize=(12, 8))
            
            # Plot price data
            plt.subplot(2, 1, 1)
            plt.plot(price_data.index, price_data['close'], label='Close Price')
            plt.title('Price Data with Trade Entry/Exit Points')
            plt.xlabel('Time')
            plt.ylabel('Price')
            
            # Add trade entry/exit points
            for idx, trade in trades.iterrows():
                if 'entry_time' in trade and not pd.isna(trade['entry_time']):
                    entry_time = trade['entry_time']
                    entry_price = trade['entry_price'] if 'entry_price' in trade else trade['price']
                    plt.scatter(entry_time, entry_price, color='green', marker='^', s=100)
                    
                if 'exit_time' in trade and not pd.isna(trade['exit_time']):
                    exit_time = trade['exit_time']
                    exit_price = trade['exit_price'] if 'exit_price' in trade else trade['price']
                    plt.scatter(exit_time, exit_price, color='red', marker='v', s=100)
            
            # Plot trade PnL
            plt.subplot(2, 1, 2)
            if 'pnl' in trades.columns:
                if 'timestamp' in trades.columns:
                    plt.bar(trades['timestamp'], trades['pnl'], color=['green' if p > 0 else 'red' for p in trades['pnl']])
                else:
                    plt.bar(range(len(trades)), trades['pnl'], color=['green' if p > 0 else 'red' for p in trades['pnl']])
                    
                plt.title('Trade PnL')
                plt.xlabel('Trade')
                plt.ylabel('PnL')
            
            plt.tight_layout()
            plt.savefig('trade_validation_plot.png')
            logger.info("Saved validation plot to trade_validation_plot.png")
            
        except Exception as e:
            logger.error(f"Error creating validation plot: {e}")
    
    return valid_trades > 0

def main():
    """Main function to validate trades against price data."""
    # Adjust these paths to your actual data
    price_data_file = "data/HEAD_1min.csv"  # Change to your price data file
    trades_file = "results/head_test/trades_20250504_160528.csv"  # Change to your trades file
    
    # Load data
    price_data = load_price_data(price_data_file)
    trades = load_trades(trades_file)
    
    if price_data is None or trades is None:
        logger.error("Failed to load required data")
        return
        
    # Validate trades
    validate_trades_against_price_data(trades, price_data)

if __name__ == "__main__":
    main()
'''
        
        # Write the validation script
        validation_file = "validate_trades.py"
        with open(validation_file, "w") as f:
            f.write(validation_code)
            
        # Make it executable
        os.chmod(validation_file, 0o755)
        
        logger.info(f"Created validation script at {validation_file}")
        logger.info("You can run this script to validate trades against price data")
        
        return validation_file
        
    def run_full_diagnostic(self, results_dir, run_id=None):
        """Run a full diagnostic on backtest results."""
        # Load results
        if not self.load_backtest_results(results_dir, run_id):
            logger.error("Failed to load backtest results")
            return False
            
        # Analyze trades
        self.analyze_trades()
        
        # Check for artificial trade patterns
        self.check_for_artificial_trades()
        
        # Verify performance metrics
        self.verify_performance_metrics()
        
        # Provide recommendations
        self.recommend_fixes()
        
        # Create validation script
        self.create_validation_script()
        
        logger.info("Diagnostic completed. Check the log for details and recommendations.")
        return True
        

def main():
    """Main function to run the diagnostic tool."""
    parser = argparse.ArgumentParser(description='ADMF-trader Backtest Diagnostic Tool')
    parser.add_argument('--results-dir', '-r', type=str, default='results/head_test',
                        help='Directory containing backtest results (default: results/head_test)')
    parser.add_argument('--run-id', '-i', type=str, 
                        help='Specific run ID (timestamp) to analyze (default: most recent)')
    
    args = parser.parse_args()
    
    # Run diagnostic
    diagnostic = TradeBacktestDiagnostic()
    diagnostic.run_full_diagnostic(args.results_dir, args.run_id)
    

if __name__ == "__main__":
    main()