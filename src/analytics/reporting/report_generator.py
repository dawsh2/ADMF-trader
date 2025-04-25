# src/core/analytics/reporting/report_generator.py
import pandas as pd
from typing import Dict, List, Any, Optional

class ReportGenerator:
    """Generator for performance reports."""
    
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
        
        # Risk metrics section
        report.append("\nRisk Metrics:")
        report.append(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        report.append(f"Sortino Ratio: {metrics['sortino_ratio']:.2f}")
        report.append(f"Maximum Drawdown: {metrics['max_drawdown']:.2%}")
        report.append(f"Calmar Ratio: {metrics['calmar_ratio']:.2f}")
        
        # Trade statistics (if available)
        if 'win_rate' in metrics:
            report.append("\nTrade Statistics:")
            report.append(f"Total Trades: {metrics.get('total_trades', 0)}")
            report.append(f"Win Rate: {metrics['win_rate']:.2%}")
            report.append(f"Profit Factor: {metrics['profit_factor']:.2f}")
            report.append(f"Average Trade: {metrics['avg_trade']:.2f}")
            report.append(f"Average Win: {metrics['avg_win']:.2f}")
            report.append(f"Average Loss: {metrics['avg_loss']:.2f}")
            report.append(f"Win/Loss Ratio: {metrics['win_loss_ratio']:.2f}")
        
        return "\n".join(report)
    
    def generate_detailed_report(self):
        """
        Generate a detailed performance report.
        
        Returns:
            str: Report text
        """
        summary = self.generate_summary_report()
        
        if summary == "No performance data available.":
            return summary
            
        # Add equity curve statistics
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
        
        # Monthly returns if enough data
        if len(equity_curve) > 20:  # Arbitrary threshold
            report.append("\nMonthly Returns:")
            returns = self.calculator.get_returns()
            monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
            
            # Format monthly returns table
            for date, ret in monthly_returns.items():
                report.append(f"{date.strftime('%Y-%m')}: {ret:.2%}")
        
        # Add drawdown analysis
        drawdown_stats = self.calculator.calculate_metrics(['drawdown_stats'])
        report.append("\nDrawdown Analysis:")
        report.append(f"Maximum Drawdown: {drawdown_stats['max_drawdown']:.2%}")
        report.append(f"Average Drawdown: {drawdown_stats['avg_drawdown']:.2%}")
        report.append(f"Maximum Drawdown Duration: {drawdown_stats['max_drawdown_duration']} periods")
        
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
