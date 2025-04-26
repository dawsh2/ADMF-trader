"""
Report saving and output utilities for ADMF-Trader.
"""
import os
import datetime
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ReportSaver:
    """Helper class for saving reports and printing summaries."""
    
    def __init__(self, report_generator=None):
        """
        Initialize the report saver.
        
        Args:
            report_generator: ReportGenerator instance
        """
        self.report_generator = report_generator
    
    def set_report_generator(self, report_generator):
        """Set report generator."""
        self.report_generator = report_generator
    
    def save_reports(self, results: Dict[str, Any], output_dir: str = "./results", timestamp: Optional[str] = None):
        """
        Save all report components to files.
        
        Args:
            results: Backtest results dictionary
            output_dir: Directory to save results
            timestamp: Timestamp string (generated if None)
        """
        if not results:
            logger.warning("No results to save")
            return False
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp if not provided
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save equity curve
        equity_curve = results.get("equity_curve")
        if equity_curve is not None and not equity_curve.empty:
            equity_file = f"{output_dir}/equity_curve_{timestamp}.csv"
            equity_curve.to_csv(equity_file)
            logger.info(f"Saved equity curve to '{equity_file}'")
        
        # Save detailed report
        detailed_report = results.get("detailed_report", "")
        if detailed_report:
            report_file = f"{output_dir}/backtest_report_{timestamp}.txt"
            with open(report_file, 'w') as f:
                f.write(detailed_report)
            logger.info(f"Saved detailed report to '{report_file}'")
        
        # Save trade log if available
        trades = results.get("trades", [])
        if trades:
            try:
                import pandas as pd
                trade_df = pd.DataFrame(trades)
                trade_file = f"{output_dir}/trades_{timestamp}.csv"
                trade_df.to_csv(trade_file, index=False)
                logger.info(f"Saved trade log to '{trade_file}'")
            except (ImportError, Exception) as e:
                logger.warning(f"Could not save trade log: {e}")
        
        return True
    
    def print_summary(self, results: Dict[str, Any]):
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
        detailed_report = results.get("detailed_report_file")
        if detailed_report:
            print(f"\nDetailed report saved to: {detailed_report}")
        
        equity_curve_file = results.get("equity_curve_file")
        if equity_curve_file:
            print(f"Equity curve saved to: {equity_curve_file}")
