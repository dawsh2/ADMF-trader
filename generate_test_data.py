#!/usr/bin/env python
"""
Generate test data for backtesting.

This script creates synthetic price data for a list of symbols using
sine waves to create predictable patterns for testing strategies.
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_test_data(symbols, start_date, end_date, output_dir="./data", timeframe="1d"):
    """
    Generate test data for the specified symbols.
    
    Args:
        symbols: List of symbols to generate data for
        start_date: Start date for data
        end_date: End date for data
        output_dir: Directory to save CSV files
        timeframe: Data timeframe (used in filename)
        
    Returns:
        bool: True if successful
    """
    print(f"Generating test data for {len(symbols)} symbols")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert dates to datetime objects if needed
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    # Generate date range
    if timeframe == "1d":
        dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
    elif timeframe == "1h":
        dates = pd.date_range(start=start_date, end=end_date, freq='H')
    else:
        # Default to daily
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    for symbol in symbols:
        # Set base price according to symbol
        if symbol == 'AAPL':
            base_price = 150.0
            amplitude = 15.0
        elif symbol == 'MSFT':
            base_price = 200.0
            amplitude = 20.0
        elif symbol == 'GOOG':
            base_price = 1000.0
            amplitude = 100.0
        else:
            base_price = 100.0
            amplitude = 10.0
        
        # Create synthetic price data with multiple sine waves for crossovers
        prices = []
        
        # Create a sine wave pattern for predictable crossovers
        for i in range(len(dates)):
            t = i / len(dates)
            
            # Create multiple frequency components
            fast_component = amplitude * 0.6 * np.sin(t * 20 * np.pi)
            slow_component = amplitude * 0.4 * np.sin(t * 5 * np.pi)
            
            # Add slight trend and random component
            trend = i * 0.01 * base_price
            noise = np.random.normal(0, amplitude * 0.05)
            
            # Combine components
            price = base_price + fast_component + slow_component + trend + noise
            prices.append(max(price, 1.0))  # Ensure positive prices
        
        # Generate OHLCV data
        data = []
        for i, date in enumerate(dates):
            close = prices[i]
            high = close * (1 + abs(np.random.normal(0, 0.01)))
            low = close * (1 - abs(np.random.normal(0, 0.01)))
            open_price = low + (high - low) * np.random.random()
            volume = int(np.random.exponential(100000))
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Save to CSV
        filename = os.path.join(output_dir, f"{symbol}_{timeframe}.csv")
        df.to_csv(filename, index=False)
        print(f"Created test data for {symbol} with {len(data)} bars, saved to {filename}")
    
    return True

def main():
    """Generate test data from command line arguments."""
    parser = argparse.ArgumentParser(description="Generate test data for ADMF-Trader")
    parser.add_argument("--symbols", default="AAPL,MSFT,GOOG", help="Comma-separated list of symbols")
    parser.add_argument("--start-date", default="2023-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2023-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", default="./data", help="Output directory")
    parser.add_argument("--timeframe", default="1d", help="Data timeframe")
    args = parser.parse_args()
    
    # Parse symbols list
    symbols = args.symbols.split(",")
    
    # Generate data
    success = generate_test_data(
        symbols=symbols,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        timeframe=args.timeframe
    )
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
