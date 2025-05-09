#!/usr/bin/env python3
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
