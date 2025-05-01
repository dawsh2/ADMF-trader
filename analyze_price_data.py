#!/usr/bin/env python
"""
Script to analyze price data for potential MA crossover points.
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def calculate_ma(prices, window):
    """Calculate moving average."""
    return prices.rolling(window=window).mean()

def find_crossovers(fast_ma, slow_ma):
    """Find crossover points."""
    crossovers = []
    
    # Ensure series are aligned
    aligned = pd.concat([fast_ma, slow_ma], axis=1)
    aligned.columns = ['fast', 'slow']
    aligned = aligned.dropna()
    
    # Look for crossovers
    prev_diff = None
    for idx, row in aligned.iterrows():
        curr_diff = row['fast'] - row['slow']
        
        if prev_diff is not None:
            # Crossing above (buy signal)
            if prev_diff <= 0 and curr_diff > 0:
                crossovers.append({
                    'timestamp': idx,
                    'type': 'BUY',
                    'fast_ma': row['fast'],
                    'slow_ma': row['slow'],
                    'diff': curr_diff
                })
            # Crossing below (sell signal)
            elif prev_diff >= 0 and curr_diff < 0:
                crossovers.append({
                    'timestamp': idx,
                    'type': 'SELL',
                    'fast_ma': row['fast'],
                    'slow_ma': row['slow'],
                    'diff': curr_diff
                })
        
        prev_diff = curr_diff
    
    return crossovers

def analyze_file(file_path, price_col, fast_window, slow_window, plot=False):
    """Analyze CSV file for MA crossovers."""
    # Load data
    df = pd.read_csv(file_path)
    
    # Set index if timestamp column exists
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    elif 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
    
    # Check if price column exists or needs to be adapted
    price_column = None
    if price_col in df.columns:
        price_column = price_col
    elif price_col.lower() in df.columns:
        price_column = price_col.lower()
    elif price_col.capitalize() in df.columns:
        price_column = price_col.capitalize()
    elif price_col.upper() in df.columns:
        price_column = price_col.upper()
    
    if not price_column:
        print(f"Price column '{price_col}' not found in columns: {list(df.columns)}")
        return None
    
    # Calculate MAs
    prices = df[price_column]
    fast_ma = calculate_ma(prices, fast_window)
    slow_ma = calculate_ma(prices, slow_window)
    
    # Find crossovers
    crossovers = find_crossovers(fast_ma, slow_ma)
    
    # Basic stats about the data
    print(f"\nData Analysis for {os.path.basename(file_path)}:")
    print(f"Total bars: {len(df)}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    print(f"Price range: {prices.min():.2f} to {prices.max():.2f}")
    print(f"Price volatility (std dev): {prices.std():.4f}")
    print(f"Fast MA window: {fast_window}")
    print(f"Slow MA window: {slow_window}")
    
    # Print column information
    print("\nColumn names in the file:")
    for col in df.columns:
        print(f"  {col}")
    
    # Print first few rows
    print("\nFirst 5 rows with mapped price column:")
    print(df[[price_column]].head())
    
    # Print crossover points
    print(f"\nFound {len(crossovers)} crossovers:")
    for i, xover in enumerate(crossovers[:10]):  # First 10
        print(f"  {i+1}. {xover['type']} signal at {xover['timestamp']}, "
              f"fast MA: {xover['fast_ma']:.2f}, slow MA: {xover['slow_ma']:.2f}, "
              f"diff: {xover['diff']:.4f}")
    
    if len(crossovers) > 10:
        print(f"  ... and {len(crossovers) - 10} more")
    
    # Plot if requested
    if plot:
        plt.figure(figsize=(12, 6))
        plt.plot(prices, label='Price')
        plt.plot(fast_ma, label=f'Fast MA ({fast_window})')
        plt.plot(slow_ma, label=f'Slow MA ({slow_window})')
        
        # Mark crossovers
        buy_points = [x['timestamp'] for x in crossovers if x['type'] == 'BUY']
        sell_points = [x['timestamp'] for x in crossovers if x['type'] == 'SELL']
        
        if buy_points:
            buy_values = [prices.loc[t] for t in buy_points]
            plt.scatter(buy_points, buy_values, marker='^', color='green', s=100, label='Buy Signal')
            
        if sell_points:
            sell_values = [prices.loc[t] for t in sell_points]
            plt.scatter(sell_points, sell_values, marker='v', color='red', s=100, label='Sell Signal')
        
        plt.title(f'MA Crossover Analysis - {os.path.basename(file_path)}')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        
        # Save plot
        plot_file = f"ma_crossover_{os.path.basename(file_path).split('.')[0]}.png"
        plt.savefig(plot_file)
        print(f"\nPlot saved to {plot_file}")
        
        # Show plot if in interactive mode
        plt.show()
    
    return crossovers

def main():
    parser = argparse.ArgumentParser(description="Analyze price data for MA crossovers")
    parser.add_argument("--file", required=True, help="CSV file to analyze")
    parser.add_argument("--price-col", default="close", help="Price column name")
    parser.add_argument("--fast-window", type=int, default=5, help="Fast MA window")
    parser.add_argument("--slow-window", type=int, default=15, help="Slow MA window")
    parser.add_argument("--plot", action="store_true", help="Generate plot")
    args = parser.parse_args()
    
    # Analyze file
    crossovers = analyze_file(
        args.file, 
        args.price_col,
        args.fast_window,
        args.slow_window,
        args.plot
    )
    
    if crossovers is None:
        return False
    
    print(f"\nTotal expected signals: {len(crossovers)}")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
