#!/usr/bin/env python
"""
Example script demonstrating how to use the analytics module.

This script shows how to:
1. Load backtest results (equity curve and trades)
2. Analyze performance using the PerformanceAnalyzer
3. Generate reports in text and HTML formats

When run with --generate-sample, it creates sample backtest data for demonstration.
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analytics.analysis.performance import PerformanceAnalyzer
from src.analytics.reporting.text_report import TextReportBuilder
from src.analytics.reporting.html_report import HTMLReportBuilder


def generate_sample_data(output_dir):
    """Generate sample backtest data for demonstration purposes."""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate sample equity curve
    print("Generating sample equity curve...")
    start_date = datetime(2025, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(100)]
    
    # Create a sample equity curve with some volatility
    initial_equity = 10000
    daily_returns = np.random.normal(0.0005, 0.005, 100)  # Mean 0.05% daily, 0.5% volatility
    
    # Add a drawdown period
    daily_returns[30:40] = np.random.normal(-0.002, 0.005, 10)  # Drawdown period
    
    # Create cumulative equity
    cumulative_returns = np.cumprod(1 + daily_returns)
    equity = initial_equity * cumulative_returns
    
    # Create DataFrame
    equity_df = pd.DataFrame({
        'date': dates,
        'equity': equity,
        'returns': daily_returns
    })
    
    # Save to CSV
    equity_file = os.path.join(output_dir, 'sample_equity_curve.csv')
    equity_df.to_csv(equity_file, index=False)
    print(f"Sample equity curve saved to: {equity_file}")
    
    # Generate sample trades
    print("Generating sample trades...")
    trades = []
    
    # Create a mix of winning and losing trades
    for i in range(40):
        # Alternate between winning and losing trades with 65% win rate
        is_win = (i % 10) < 6.5  # 65% win rate
        
        # Create entry date within simulation period
        entry_day = np.random.randint(0, 95)  # Keep 5 days at the end for exits
        entry_date = start_date + timedelta(days=entry_day)
        
        # Create exit date 1-5 days after entry
        holding_period = np.random.randint(1, 6)
        exit_date = entry_date + timedelta(days=holding_period)
        
        # Create random symbols
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'FB']
        symbol = symbols[i % len(symbols)]
        
        # Create entry and exit prices
        entry_price = 100 + np.random.randint(-5, 6)
        
        # Set profit or loss based on win/loss status
        if is_win:
            pnl = np.random.uniform(50, 200)  # Winners between $50-$200
            exit_price = entry_price * (1 + pnl/1000)  # Proportional price change
        else:
            pnl = np.random.uniform(-150, -20)  # Losers between -$20 and -$150
            exit_price = entry_price * (1 + pnl/1000)  # Proportional price change
        
        # Create trade record
        trade = {
            'id': f"trade_{i+1}",
            'symbol': symbol,
            'entry_time': entry_date,
            'exit_time': exit_date,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': 10,
            'direction': 'BUY',
            'pnl': pnl,
            'status': 'CLOSED'
        }
        
        trades.append(trade)
    
    # Convert to DataFrame
    trades_df = pd.DataFrame(trades)
    
    # Save to CSV
    trades_file = os.path.join(output_dir, 'sample_trades.csv')
    trades_df.to_csv(trades_file, index=False)
    print(f"Sample trades saved to: {trades_file}")
    
    return equity_file, trades_file


def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Analyze backtest results')
    parser.add_argument('--equity', help='Path to equity curve CSV')
    parser.add_argument('--trades', help='Path to trades CSV (optional)')
    parser.add_argument('--output-dir', default='./results/analytics', help='Output directory')
    parser.add_argument('--text', action='store_true', help='Generate text report')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    parser.add_argument('--risk-free-rate', type=float, default=0.0, help='Risk-free rate (annual)')
    parser.add_argument('--generate-sample', action='store_true', help='Generate sample data instead of loading from files')
    args = parser.parse_args()

    # Ensure output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # Generate sample data if requested
    if args.generate_sample:
        equity_file, trades_file = generate_sample_data(args.output_dir)
    else:
        equity_file = args.equity
        trades_file = args.trades
    
    # Check if we have an equity file
    if not equity_file:
        print("Error: No equity curve file specified. Use --equity or --generate-sample.")
        return 1

    # Load equity curve
    print(f"Loading equity curve from {equity_file}")
    equity_curve = pd.read_csv(equity_file)
    
    # Try to convert date column to datetime and set as index
    date_columns = ['date', 'timestamp', 'time', 'datetime']
    for col in date_columns:
        if col in equity_curve.columns:
            equity_curve[col] = pd.to_datetime(equity_curve[col])
            equity_curve.set_index(col, inplace=True)
            break

    # Load trades if available
    trades = []
    if trades_file:
        print(f"Loading trades from {trades_file}")
        trades_df = pd.read_csv(trades_file)
        
        # Convert trades DataFrame to list of dictionaries
        for _, row in trades_df.iterrows():
            trade = row.to_dict()
            
            # Convert date fields to datetime
            date_fields = ['entry_time', 'exit_time', 'entry_date', 'exit_date']
            for field in date_fields:
                if field in trade and trade[field]:
                    try:
                        trade[field] = pd.to_datetime(trade[field])
                    except:
                        pass
            
            trades.append(trade)

    # Create analyzer
    analyzer = PerformanceAnalyzer(
        equity_curve=equity_curve,
        trades=trades
    )
    
    # Run analysis
    print("Analyzing performance...")
    metrics = analyzer.analyze_performance(risk_free_rate=args.risk_free_rate)
    
    # Print summary metrics
    print("\nPerformance Summary:")
    print(f"Total Return: {metrics.get('total_return', 0.0):.2%}")
    print(f"Annualized Return: {metrics.get('annualized_return', 0.0):.2%}")
    print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0.0):.2f}")
    print(f"Max Drawdown: {metrics.get('max_drawdown', 0.0):.2%}")
    
    if 'trade_metrics' in metrics:
        trade_metrics = metrics['trade_metrics']
        print(f"Win Rate: {trade_metrics.get('win_rate', 0.0):.2%}")
        print(f"Profit Factor: {trade_metrics.get('profit_factor', 0.0):.2f}")
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Generate reports
    if args.text or not (args.text or args.html):  # Default to text if none specified
        text_builder = TextReportBuilder(
            analyzer=analyzer,
            title="Trading Strategy Performance Report"
        )
        text_file = os.path.join(args.output_dir, f"performance_report_{timestamp}.txt")
        text_builder.save(text_file)
        print(f"Text report saved to: {text_file}")
    
    if args.html:
        html_builder = HTMLReportBuilder(
            analyzer=analyzer,
            title="Trading Strategy Performance Report",
            description="Detailed analysis of trading strategy performance"
        )
        html_file = os.path.join(args.output_dir, f"performance_report_{timestamp}.html")
        html_builder.save(html_file)
        print(f"HTML report saved to: {html_file}")
    
    print("Analysis complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())