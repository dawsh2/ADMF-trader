#!/usr/bin/env python
"""
Example script demonstrating how to generate backtest reports
using the new analytics module.

This script shows how to:
1. Load backtest results from CSV files
2. Create a PerformanceAnalyzer with the results
3. Generate different types of reports (text and HTML)
"""

import os
import sys
import pandas as pd
from datetime import datetime
import argparse
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analytics.analysis.performance import PerformanceAnalyzer
from src.analytics.reporting.text_report import TextReportBuilder
from src.analytics.reporting.html_report import HTMLReportBuilder


def load_backtest_results(equity_path, trades_path=None):
    """
    Load backtest results from CSV files.
    
    Args:
        equity_path: Path to equity curve CSV file
        trades_path: Optional path to trades CSV file
        
    Returns:
        tuple: (equity_curve, trades)
    """
    # Load equity curve
    equity_curve = pd.read_csv(equity_path)
    
    # Convert date column to datetime and set as index
    if 'date' in equity_curve.columns:
        equity_curve['date'] = pd.to_datetime(equity_curve['date'])
        equity_curve.set_index('date', inplace=True)
    else:
        # If no date column, try common date column names
        for date_col in ['timestamp', 'time', 'datetime']:
            if date_col in equity_curve.columns:
                equity_curve['date'] = pd.to_datetime(equity_curve[date_col])
                equity_curve.set_index('date', inplace=True)
                break
        else:
            # If still no date column found, create a simple index
            equity_curve['date'] = pd.date_range(
                start=datetime.now().strftime("%Y-%m-%d"),
                periods=len(equity_curve),
                freq='D'
            )
            equity_curve.set_index('date', inplace=True)
    
    # Load trades if provided
    trades = []
    if trades_path and os.path.exists(trades_path):
        trades_df = pd.read_csv(trades_path)
        
        # Convert trades DataFrame to list of dictionaries
        for _, row in trades_df.iterrows():
            trade = row.to_dict()
            
            # Convert dates if present
            for date_field in ['entry_time', 'exit_time', 'entry_date', 'exit_date']:
                if date_field in trade:
                    try:
                        trade[date_field] = pd.to_datetime(trade[date_field])
                    except:
                        pass
            
            trades.append(trade)
    
    return equity_curve, trades


def generate_reports(equity_curve, trades, strategy_name, output_dir, risk_free_rate=0.0):
    """
    Generate performance reports using the analytics module.
    
    Args:
        equity_curve: DataFrame with equity curve data
        trades: List of trade dictionaries
        strategy_name: Name of the strategy
        output_dir: Directory to save reports
        risk_free_rate: Annualized risk-free rate
        
    Returns:
        dict: Paths to generated reports
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Initialize performance analyzer
    analyzer = PerformanceAnalyzer(equity_curve, trades)
    analyzer.analyze_performance(risk_free_rate=risk_free_rate)
    
    # Generate text report
    text_builder = TextReportBuilder(
        analyzer=analyzer,
        title=f"{strategy_name} Performance Report",
        description=f"Detailed performance analysis for {strategy_name}"
    )
    
    text_file = os.path.join(output_dir, f"{strategy_name.lower().replace(' ', '_')}_{timestamp}.txt")
    text_builder.save(text_file)
    
    # Generate HTML report
    html_builder = HTMLReportBuilder(
        analyzer=analyzer,
        title=f"{strategy_name} Performance Report",
        description=f"Detailed performance analysis for {strategy_name} with visualizations"
    )
    
    html_file = os.path.join(output_dir, f"{strategy_name.lower().replace(' ', '_')}_{timestamp}.html")
    html_builder.save(html_file)
    
    return {
        'text_report': text_file,
        'html_report': html_file
    }


def main():
    """Main function to parse arguments and generate reports."""
    parser = argparse.ArgumentParser(description='Generate backtest reports from results')
    
    parser.add_argument('--equity', required=True, help='Path to equity curve CSV file')
    parser.add_argument('--trades', help='Path to trades CSV file (optional)')
    parser.add_argument('--name', default='Backtest Strategy', help='Strategy name')
    parser.add_argument('--output', default='./reports', help='Output directory for reports')
    parser.add_argument('--risk-free-rate', type=float, default=0.0, help='Annualized risk-free rate')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Load backtest results
    logging.info(f"Loading equity curve from {args.equity}")
    equity_curve, trades = load_backtest_results(args.equity, args.trades)
    
    logging.info(f"Loaded equity curve with {len(equity_curve)} data points")
    if trades:
        logging.info(f"Loaded {len(trades)} trades")
    
    # Generate reports
    logging.info(f"Generating reports for {args.name}")
    report_paths = generate_reports(
        equity_curve, 
        trades, 
        args.name, 
        args.output, 
        args.risk_free_rate
    )
    
    logging.info(f"Reports generated successfully:")
    for report_type, report_path in report_paths.items():
        logging.info(f"  - {report_type}: {report_path}")


if __name__ == "__main__":
    main()