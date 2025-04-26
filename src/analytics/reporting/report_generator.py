# src/core/analytics/reporting/report_generator.py
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

class ReportGenerator:
    """Generator for performance reports with improved log return metrics."""
    
    def __init__(self, calculator=None):
        """
        Initialize the report generator.
        
        Args:
            calculator: PerformanceCalculator instance
        """
        self.calculator = calculator
    
    def set_calculator(self, calculator):
        """Set performance calculator."""
        self.calculator = calculator
    
    def generate_summary_report(self):
        """
        Generate a summary performance report.
        
        Returns:
            str: Report text
        """
        if not self.calculator or self.calculator.equity_curve is None:
            return "No performance data available."
            
        # Calculate metrics
        metrics = self.calculator.calculate_all_metrics()
        
        # Format report
        report = []
        report.append("Performance Summary")
        report.append("=" * 50)
        
        # Returns section
        report.append("\nReturns:")
        report.append(f"Total Return: {metrics['total_return']:.2%}")
        report.append(f"Annualized Return: {metrics['annualized_return']:.2%}")
        
        # Log returns section (new)
        if 'mean_log_return' in metrics:
            report.append("\nLog Return Analysis:")
            report.append(f"Daily Mean Log Return: {metrics['mean_log_return']*100:.4f}%")
            report.append(f"Annualized Volatility: {metrics['volatility']*np.sqrt(252)*100:.2f}%")
            # Include skewness and kurtosis if available
            if 'skewness' in metrics:
                report.append(f"Skewness: {metrics['skewness']:.2f}")
            if 'kurtosis' in metrics:
                report.append(f"Excess Kurtosis: {metrics['kurtosis']:.2f}")
        
        # Risk metrics section
        report.append("\nRisk Metrics:")
        report.append(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        report.append(f"Sortino Ratio: {metrics['sortino_ratio']:.2f}")
        report.append(f"Maximum Drawdown: {metrics['max_drawdown']:.2%}")
        report.append(f"Calmar Ratio: {metrics['calmar_ratio']:.2f}")
        
        # Trade statistics (if available)
        if 'win_rate' in metrics:
            report.append("\nTrade Statistics:")
            report.append(f"Total Trades: {metrics.get('trade_count', 0)}")
            report.append(f"Win Rate: {metrics['win_rate']:.2%}")
            report.append(f"Profit Factor: {metrics['profit_factor']:.2f}")
            report.append(f"Average Trade: {metrics['avg_trade']:.2f}")
            report.append(f"Average Win: {metrics['avg_win']:.2f}")
            report.append(f"Average Loss: {metrics['avg_loss']:.2f}")
            report.append(f"Win/Loss Ratio: {metrics['win_loss_ratio']:.2f}")
        
        return "\n".join(report)
    
    def generate_detailed_report(self):
        """
        Generate a detailed performance report with log return analysis.
        
        Returns:
            str: Report text
        """
        summary = self.generate_summary_report()
        
        if summary == "No performance data available.":
            return summary
            
        # Get equity curve
        equity_curve = self.calculator.equity_curve
        
        # Format detailed report
        report = [summary]
        
        # Equity curve statistics
        report.append("\nEquity Curve Statistics:")
        report.append(f"Start Date: {equity_curve.index[0]}")
        report.append(f"End Date: {equity_curve.index[-1]}")
        report.append(f"Duration: {(equity_curve.index[-1] - equity_curve.index[0]).days} days")
        report.append(f"Starting Equity: {equity_curve['equity'].iloc[0]:.2f}")
        report.append(f"Ending Equity: {equity_curve['equity'].iloc[-1]:.2f}")
        
        # Advanced return analysis (using log returns)
        log_returns = self.calculator.get_log_returns()
        if len(log_returns) > 0:
            report.append("\nDetailed Return Analysis:")
            # Calculate compound annual growth rate (CAGR) from log returns
            total_years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365.0
            if total_years > 0:
                total_log_return = np.log(equity_curve['equity'].iloc[-1] / equity_curve['equity'].iloc[0])
                cagr = np.exp(total_log_return / total_years) - 1
                report.append(f"CAGR: {cagr:.2%}")
            
            # Calculate rolling metrics if enough data
            if len(log_returns) > 60:  # Require at least 60 data points for meaningful rolling analysis
                # Calculate 20-day rolling volatility
                rolling_vol = log_returns.rolling(window=20).std() * np.sqrt(252)
                recent_vol = rolling_vol.iloc[-20:].mean() if len(rolling_vol) >= 20 else rolling_vol.mean()
                report.append(f"Recent 20-day Volatility (Annualized): {recent_vol*100:.2f}%")
                
                # Calculate 20-day rolling Sharpe ratio
                rolling_ret = log_returns.rolling(window=20).mean() * 252
                rolling_sharpe = rolling_ret / rolling_vol
                recent_sharpe = rolling_sharpe.iloc[-20:].mean() if len(rolling_sharpe) >= 20 else rolling_sharpe.mean()
                report.append(f"Recent 20-day Sharpe Ratio: {recent_sharpe:.2f}")
        
        # Monthly returns if enough data
        if len(equity_curve) > 20:  # Arbitrary threshold
            report.append("\nMonthly Returns:")
            # Use log returns for accurate monthly compounding
            log_returns = self.calculator.get_log_returns()
            
            # Group by month and sum log returns, then convert back to simple returns
            monthly_log_returns = log_returns.resample('M').sum()
            monthly_returns = np.exp(monthly_log_returns) - 1
            
            # Format monthly returns table
            for date, ret in monthly_returns.items():
                report.append(f"{date.strftime('%Y-%m')}: {ret:.2%}")
        
        # Add drawdown analysis
        drawdown_stats = self.calculator.calculate_metrics(['drawdown_stats'])
        report.append("\nDrawdown Analysis:")
        report.append(f"Maximum Drawdown: {drawdown_stats['max_drawdown']:.2%}")
        report.append(f"Average Drawdown: {drawdown_stats['avg_drawdown']:.2%}")
        report.append(f"Maximum Drawdown Duration: {drawdown_stats['max_drawdown_duration']} periods")
        
        # Add trade analysis if trades are available
        if self.calculator.trades:
            report.append("\nTrade Analysis:")
            trades = self.calculator.trades
            
            # Calculate trade holding times if timestamps are available
            if len(trades) > 0 and 'timestamp' in trades[0]:
                trade_durations = []
                for i in range(1, len(trades)):
                    if trades[i-1]['direction'] != trades[i]['direction']:  # Direction changed, implying open->close
                        try:
                            duration = (trades[i]['timestamp'] - trades[i-1]['timestamp']).total_seconds() / (60*60*24)  # Convert to days
                            trade_durations.append(duration)
                        except (TypeError, AttributeError):
                            pass  # Skip if timestamps aren't proper datetime objects
                
                if trade_durations:
                    avg_duration = sum(trade_durations) / len(trade_durations)
                    report.append(f"Average Trade Duration: {avg_duration:.2f} days")
            
            # Trade win streaks
            win_streak = 0
            max_win_streak = 0
            loss_streak = 0
            max_loss_streak = 0
            
            for trade in trades:
                pnl = trade.get('pnl', 0)
                if pnl > 0:
                    win_streak += 1
                    loss_streak = 0
                    max_win_streak = max(max_win_streak, win_streak)
                elif pnl < 0:
                    loss_streak += 1
                    win_streak = 0
                    max_loss_streak = max(max_loss_streak, loss_streak)
            
            report.append(f"Maximum Winning Streak: {max_win_streak}")
            report.append(f"Maximum Losing Streak: {max_loss_streak}")
        
        return "\n".join(report)
    
    def save_report(self, report, filename):
        """
        Save a report to a file.
        
        Args:
            report: Report text
            filename: Output filename
        """
        with open(filename, 'w') as f:
            f.write(report)
    
    def save_reports(self, results, output_dir="./results", timestamp=None):
        """
        Save all report components to files.
        
        Args:
            results: Backtest results dictionary
            output_dir: Directory to save results
            timestamp: Timestamp string (generated if None)
            
        Returns:
            dict: Dictionary with file paths of saved reports
        """
        import os
        import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not results:
            logger.warning("No results to save")
            return {}
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp if not provided
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        saved_files = {}
        
        # Save equity curve
        equity_curve = results.get("equity_curve")
        if equity_curve is not None and not equity_curve.empty:
            equity_file = f"{output_dir}/equity_curve_{timestamp}.csv"
            equity_curve.to_csv(equity_file)
            logger.info(f"Saved equity curve to '{equity_file}'")
            saved_files["equity_curve_file"] = equity_file
        
        # Save detailed report
        detailed_report = results.get("detailed_report", "")
        if detailed_report:
            report_file = f"{output_dir}/backtest_report_{timestamp}.txt"
            with open(report_file, 'w') as f:
                f.write(detailed_report)
            logger.info(f"Saved detailed report to '{report_file}'")
            saved_files["detailed_report_file"] = report_file
        
        # Save trade log if available
        trades = results.get("trades", [])
        if trades:
            try:
                import pandas as pd
                trade_df = pd.DataFrame(trades)
                trade_file = f"{output_dir}/trades_{timestamp}.csv"
                trade_df.to_csv(trade_file, index=False)
                logger.info(f"Saved trade log to '{trade_file}'")
                saved_files["trades_file"] = trade_file
            except (ImportError, Exception) as e:
                logger.warning(f"Could not save trade log: {e}")
        
        # Add file paths to results
        results.update(saved_files)
        
        return saved_files
    
    def print_summary(self, results):
        """
        Print a summary of backtest results to console.
        
        Args:
            results: Backtest results dictionary
        """
        if not results:
            print("\n=== Backtest Failed! ===")
            print("No results were produced.")
            return
        
        # Get key components
        trades = results.get("trades", [])
        metrics = results.get("metrics", {})
        
        # Print header
        print("\n=== Backtest Results ===")
        print(f"Trades executed: {len(trades)}")
        
        # Print key metrics
        key_metrics = [
            ('total_return', 'Total Return', True),
            ('sharpe_ratio', 'Sharpe Ratio', False),
            ('sortino_ratio', 'Sortino Ratio', False),
            ('max_drawdown', 'Maximum Drawdown', True),
            ('win_rate', 'Win Rate', True),
            ('profit_factor', 'Profit Factor', False),
            ('avg_trade', 'Average Trade', False)
        ]
        
        for metric_key, metric_name, is_percentage in key_metrics:
            if metric_key in metrics:
                value = metrics[metric_key]
                if isinstance(value, float):
                    if is_percentage:
                        print(f"{metric_name}: {value:.2%}")
                    else:
                        print(f"{metric_name}: {value:.4f}")
                else:
                    print(f"{metric_name}: {value}")
        
        # Print locations of saved files if available
        detailed_report_file = results.get("detailed_report_file")
        if detailed_report_file:
            print(f"\nDetailed report saved to: {detailed_report_file}")
        
        equity_curve_file = results.get("equity_curve_file")
        if equity_curve_file:
            print(f"Equity curve saved to: {equity_curve_file}")
    
    def generate_log_returns_report(self):
        """
        Generate a specialized report focused on log returns analysis.
        
        Returns:
            str: Report text focusing on log returns
        """
        if not self.calculator or self.calculator.equity_curve is None:
            return "No performance data available."
        
        # Get log returns
        log_returns = self.calculator.get_log_returns()
        
        if len(log_returns) == 0:
            return "No return data available for analysis."
        
        # Format report
        report = []
        report.append("Log Returns Analysis")
        report.append("=" * 50)
        
        # Basic statistics
        mean_return = log_returns.mean()
        volatility = log_returns.std()
        annualized_mean = mean_return * 252
        annualized_vol = volatility * np.sqrt(252)
        
        report.append("\nDaily Log Returns:")
        report.append(f"Mean: {mean_return*100:.4f}%")
        report.append(f"Std Dev: {volatility*100:.4f}%")
        report.append(f"Min: {log_returns.min()*100:.4f}%")
        report.append(f"Max: {log_returns.max()*100:.4f}%")
        
        report.append("\nAnnualized Metrics:")
        report.append(f"Expected Return: {annualized_mean*100:.2f}%")
        report.append(f"Volatility: {annualized_vol*100:.2f}%")
        report.append(f"Sharpe Ratio (0% risk-free): {annualized_mean/annualized_vol:.2f}")
        
        # Distribution analysis
        if hasattr(log_returns, 'skew') and hasattr(log_returns, 'kurtosis'):
            skewness = log_returns.skew()
            kurtosis = log_returns.kurtosis()
            
            report.append("\nReturn Distribution:")
            report.append(f"Skewness: {skewness:.4f}")
            report.append(f"Excess Kurtosis: {kurtosis:.4f}")
            
            # Interpret skewness and kurtosis
            if skewness < -0.5:
                report.append("The returns show significant negative skew (more extreme negative returns).")
            elif skewness > 0.5:
                report.append("The returns show significant positive skew (more extreme positive returns).")
            else:
                report.append("The returns show approximately symmetric distribution.")
                
            if kurtosis > 3:
                report.append("The returns show fat tails (more extreme events than a normal distribution).")
            elif kurtosis < -0.5:
                report.append("The returns show thin tails (fewer extreme events than a normal distribution).")
            else:
                report.append("The return distribution has approximately normal tails.")
        
        # Time-based analysis
        if len(log_returns) > 100:  # Only if we have enough data
            # Calculate rolling metrics
            rolling_window = min(20, len(log_returns) // 5)  # Use 20 days or 1/5 of data, whichever is smaller
            
            rolling_mean = log_returns.rolling(window=rolling_window).mean()
            rolling_vol = log_returns.rolling(window=rolling_window).std()
            
            # Report recent metrics
            recent_mean = rolling_mean.iloc[-rolling_window:].mean() if len(rolling_mean) >= rolling_window else rolling_mean.mean()
            recent_vol = rolling_vol.iloc[-rolling_window:].mean() if len(rolling_vol) >= rolling_window else rolling_vol.mean()
            
            report.append(f"\nRecent {rolling_window}-day Metrics:")
            report.append(f"Mean Return: {recent_mean*100:.4f}%")
            report.append(f"Volatility: {recent_vol*100:.4f}%")
            report.append(f"Annualized Mean: {recent_mean*252*100:.2f}%")
            report.append(f"Annualized Vol: {recent_vol*np.sqrt(252)*100:.2f}%")
        
        return "\n".join(report)
