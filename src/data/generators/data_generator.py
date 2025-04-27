#!/usr/bin/env python
"""
Synthetic data generator for ADMF-Trader system.

This module provides functions to generate synthetic market data 
with various characteristics for testing trading strategies:
- Trending markets (up and down)
- Mean-reverting markets
- Volatile markets
- Random/neutral markets
- Multi-regime data with regime transitions
"""
import os
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)

def create_trending_data(periods, direction="up", trend_strength=0.0005, noise_level=0.001, seed=None):
    """
    Create trending price data.
    
    Args:
        periods: Number of periods
        direction: "up" or "down"
        trend_strength: Daily trend factor
        noise_level: Standard deviation of random component
        seed: Random seed
        
    Returns:
        Series of prices
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Set trend direction
    if direction == "down":
        trend_strength = -trend_strength
    
    # Create daily returns with trend and noise
    daily_returns = np.random.normal(trend_strength, noise_level, periods)
    
    # Convert to price series starting at 100
    price = 100
    prices = [price]
    
    for ret in daily_returns:
        price = price * (1 + ret)
        prices.append(price)
    
    return prices[:-1]  # Remove last element to match periods

def create_mean_reverting_data(periods, base_price=100, reversion_strength=0.05, 
                             noise_level=0.001, seed=None):
    """
    Create mean-reverting price data.
    
    Args:
        periods: Number of periods
        base_price: Mean price to revert to
        reversion_strength: Strength of mean reversion (0-1)
        noise_level: Standard deviation of random component
        seed: Random seed
        
    Returns:
        Series of prices
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Initialize price series
    prices = [base_price]
    
    # Generate price series with mean reversion
    for _ in range(periods-1):
        # Calculate distance from mean
        distance = prices[-1] - base_price
        
        # Mean reversion component (cap at reasonable value to avoid extreme values)
        reversion = np.clip(-reversion_strength * distance / base_price, -0.1, 0.1)
        
        # Random component
        noise = np.random.normal(0, noise_level)
        
        # New price (ensure it stays positive)
        new_price = max(0.1, prices[-1] * (1 + reversion + noise))
        prices.append(new_price)
    
    return prices

def create_volatile_data(periods, base_price=100, volatility=0.02, 
                        volatility_of_volatility=0.3, seed=None):
    """
    Create volatile price data with changing volatility.
    
    Args:
        periods: Number of periods
        base_price: Starting price
        volatility: Base volatility level
        volatility_of_volatility: How much volatility itself changes
        seed: Random seed
        
    Returns:
        Series of prices
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Initialize price and volatility series
    prices = [base_price]
    current_volatility = volatility
    
    # Generate price series with changing volatility
    for _ in range(periods-1):
        # Update volatility (with bounds)
        volatility_change = np.random.normal(0, volatility_of_volatility * current_volatility)
        current_volatility = max(0.001, current_volatility + volatility_change)
        
        # Generate return with current volatility
        ret = np.random.normal(0, current_volatility)
        
        # New price
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)
    
    return prices

def create_random_data(periods, base_price=100, daily_vol=0.01, seed=None):
    """
    Create random walk price data.
    
    Args:
        periods: Number of periods
        base_price: Starting price
        daily_vol: Daily volatility
        seed: Random seed
        
    Returns:
        Series of prices
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Generate random returns
    returns = np.random.normal(0, daily_vol, periods-1)
    
    # Convert to price series
    price = base_price
    prices = [price]
    
    for ret in returns:
        price = price * (1 + ret)
        prices.append(price)
    
    return prices

def create_multi_regime_data(symbol, start_date, regime_blocks, output_dir="./data", 
                            plot=False, seed=None):
    """
    Create price data with multiple regimes in sequence.
    
    Args:
        symbol: Symbol name
        start_date: Start date
        regime_blocks: List of (regime, periods) tuples
        output_dir: Output directory
        plot: Whether to plot the data
        seed: Random seed
        
    Returns:
        DataFrame with OHLCV data
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Initialize list for the final combined price data
    all_prices = []
    regime_labels = []
    
    # Process each regime block
    current_price = 100  # Starting price
    
    for i, (regime, periods) in enumerate(regime_blocks):
        logger.info(f"Generating {periods} periods of {regime} regime data")
        
        # Generate regime-specific prices
        if regime == "trending_up":
            prices = create_trending_data(
                periods, direction="up", 
                trend_strength=0.0008, noise_level=0.008,
                seed=seed+i if seed else None
            )
        elif regime == "trending_down":
            prices = create_trending_data(
                periods, direction="down", 
                trend_strength=0.0008, noise_level=0.008,
                seed=seed+i if seed else None
            )
        elif regime == "mean_reverting":
            prices = create_mean_reverting_data(
                periods, base_price=current_price,
                reversion_strength=0.08, noise_level=0.008,
                seed=seed+i if seed else None
            )
        elif regime == "volatile":
            prices = create_volatile_data(
                periods, base_price=current_price,
                volatility=0.02, volatility_of_volatility=0.3,
                seed=seed+i if seed else None
            )
        else:  # random/neutral
            prices = create_random_data(
                periods, base_price=current_price,
                daily_vol=0.01, 
                seed=seed+i if seed else None
            )
        
        # Scale to match the last price of previous block
        if all_prices and prices[0] > 0:
            # Safely calculate scale factor to avoid division by zero or very small numbers
            scale_factor = current_price / max(0.1, prices[0])
            prices = [p * scale_factor for p in prices]
        
        # Update current price for next block (ensure it's positive)
        current_price = max(0.1, prices[-1])
        
        # Append to combined data
        all_prices.extend(prices)
        regime_labels.extend([regime] * periods)
    
    # Generate dates
    start_dt = pd.to_datetime(start_date)
    dates = [start_dt + timedelta(days=i) for i in range(len(all_prices))]
    
    # Create OHLCV data
    data = []
    for i, close_price in enumerate(all_prices):
        # Ensure price is positive
        close_price = max(0.1, close_price)
        
        # Add some randomness to OHLC relationship
        daily_range = close_price * np.random.uniform(0.005, 0.015)
        high_price = close_price + daily_range / 2
        low_price = max(0.01, close_price - daily_range / 2)  # Ensure low price is positive
        open_price = low_price + np.random.random() * daily_range
        
        # Generate volume with some correlation to price movement
        if i > 0:
            price_change = abs(close_price - all_prices[i-1])
            # Safe division with floor to avoid extreme values
            volume_factor = 1.0 + min(5.0, 5.0 * price_change / max(0.1, close_price))
        else:
            volume_factor = 1.0
            
        volume = int(max(1, np.random.exponential(100000) * volume_factor))
        
        data.append({
            'date': dates[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume,
            'regime': regime_labels[i]  # Include regime label
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Safety check: replace any NaN values
    if df.isna().any().any():
        logger.warning(f"Found NaN values in generated data for {symbol}, replacing with sensible defaults")
        # Fill NaN values with appropriate defaults
        df['open'] = df['open'].fillna(100.0)
        df['high'] = df['high'].fillna(df['open'] * 1.01)
        df['low'] = df['low'].fillna(df['open'] * 0.99)
        df['close'] = df['close'].fillna(df['open'])
        df['volume'] = df['volume'].fillna(100000)
    
    # Plot if requested
    if plot:
        plt.figure(figsize=(12, 8))
        
        # Plot prices
        ax1 = plt.subplot(2, 1, 1)
        for regime in set(regime_labels):
            regime_data = df[df['regime'] == regime]
            ax1.plot(regime_data.index, regime_data['close'], label=regime)
        
        # Add regime background colors
        regime_changes = [0]
        current_regime = regime_labels[0]
        for i, regime in enumerate(regime_labels[1:], 1):
            if regime != current_regime:
                regime_changes.append(i)
                current_regime = regime
        
        regime_changes.append(len(regime_labels))
        
        colors = {
            'trending_up': 'lightgreen',
            'trending_down': 'lightcoral',
            'mean_reverting': 'lightskyblue',
            'volatile': 'plum',
            'random': 'lightgray'
        }
        
        for i in range(len(regime_changes) - 1):
            start_idx = regime_changes[i]
            end_idx = regime_changes[i+1]
            regime = regime_labels[start_idx]
            ax1.axvspan(start_idx, end_idx, alpha=0.2, color=colors.get(regime, 'lightgray'))
        
        ax1.set_title(f'{symbol} Price with Regime Periods')
        ax1.set_ylabel('Price')
        ax1.legend()
        
        # Plot returns
        ax2 = plt.subplot(2, 1, 2)
        returns = df['close'].pct_change()
        ax2.plot(returns.index[1:], returns[1:])
        ax2.set_title('Daily Returns')
        ax2.set_xlabel('Day')
        ax2.set_ylabel('Return')
        
        plt.tight_layout()
        
        # Save plot
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(f"{output_dir}/{symbol}_regimes.png")
        plt.close()
    
    # Save CSV
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{symbol}_1d.csv")
    df.to_csv(filename, index=False)
    logger.info(f"Saved {len(df)} bars to {filename}")
    
    return df

def generate_multi_regime_data(output_dir="./data", start_date="2023-01-01", plot=False, seed=42):
    """
    Generate multi-regime test data for multiple symbols.
    
    Args:
        output_dir: Directory to save generated data
        start_date: Start date for the data
        plot: Whether to plot the data
        seed: Random seed for reproducibility
    
    Returns:
        Dictionary mapping symbols to DataFrames
    """
    # Define regime sequences for different symbols
    regime_sequences = {
        # Symbol with all regimes in sequence
        "AAPL": [
            ("trending_up", 50),
            ("volatile", 30),
            ("trending_down", 50),
            ("mean_reverting", 40),
            ("random", 30),
            ("trending_up", 40)
        ],
        
        # Symbol with different sequence
        "MSFT": [
            ("mean_reverting", 40),
            ("trending_up", 60),
            ("volatile", 40),
            ("random", 30),
            ("trending_down", 40),
            ("trending_up", 30)
        ],
        
        # Symbol with more pronounced regimes
        "GOOGL": [
            ("volatile", 50),
            ("trending_down", 40),
            ("mean_reverting", 50),
            ("random", 20),
            ("trending_up", 80)
        ]
    }
    
    results = {}
    
    # Generate data for each symbol
    for symbol, regime_blocks in regime_sequences.items():
        df = create_multi_regime_data(
            symbol=symbol,
            start_date=start_date,
            regime_blocks=regime_blocks,
            output_dir=output_dir,
            plot=plot,
            seed=seed
        )
        results[symbol] = df
    
    logger.info("Data generation complete!")
    return results
