# src/backtesting/market_simulator.py
import pandas as pd
import numpy as np
import datetime
from typing import Dict, Any, List, Optional

class MarketSimulator:
    """
    Market simulator for generating market data for backtests.
    
    This can be used to generate synthetic market data or to transform
    existing market data for different test scenarios.
    """
    
    def __init__(self, seed=None):
        """
        Initialize market simulator.
        
        Args:
            seed: Optional random seed for reproducibility
        """
        self.seed = seed
        self.rng = np.random.RandomState(seed)
    
    def generate_random_walk(self, start_price=100.0, volatility=0.01, 
                           drift=0.0, days=252, include_volume=True):
        """
        Generate a random walk price series.
        
        Args:
            start_price: Starting price
            volatility: Daily volatility
            drift: Daily drift (expected return)
            days: Number of days to generate
            include_volume: Whether to include volume data
            
        Returns:
            DataFrame with OHLCV data
        """
        # Generate random daily returns
        daily_returns = self.rng.normal(drift, volatility, days)
        
        # Calculate price series
        prices = start_price * np.cumprod(1 + daily_returns)
        
        # Generate OHLC data
        data = []
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(days):
            date = today - datetime.timedelta(days=days-i)
            close = prices[i]
            
            # Generate intraday volatility for high/low
            intraday_vol = volatility * close
            high = close + self.rng.uniform(0, 2.0 * intraday_vol)
            low = close - self.rng.uniform(0, 2.0 * intraday_vol)
            
            # Ensure low <= open <= high
            open_price = self.rng.uniform(low, high)
            
            # Generate volume if requested
            volume = int(self.rng.exponential(100000)) if include_volume else 0
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('date', inplace=True)
        
        return df
    
    def generate_mean_reverting(self, mean_price=100.0, volatility=0.01, 
                              reversion_rate=0.1, days=252, include_volume=True):
        """
        Generate a mean-reverting price series.
        
        Args:
            mean_price: Mean price to revert to
            volatility: Daily volatility
            reversion_rate: Rate of mean reversion
            days: Number of days to generate
            include_volume: Whether to include volume data
            
        Returns:
            DataFrame with OHLCV data
        """
        # Generate mean-reverting series
        prices = [mean_price]
        
        for i in range(1, days):
            # Mean reversion factor
            mean_reversion = reversion_rate * (mean_price - prices[-1])
            # Random shock
            shock = self.rng.normal(0, volatility * prices[-1])
            # New price
            new_price = prices[-1] * (1 + mean_reversion + shock)
            prices.append(new_price)
        
        # Generate OHLC data (similar to random walk)
        data = []
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(days):
            date = today - datetime.timedelta(days=days-i)
            close = prices[i]
            
            # Generate intraday volatility for high/low
            intraday_vol = volatility * close
            high = close + self.rng.uniform(0, 2.0 * intraday_vol)
            low = close - self.rng.uniform(0, 2.0 * intraday_vol)
            
            # Ensure low <= open <= high
            open_price = self.rng.uniform(low, high)
            
            # Generate volume if requested
            volume = int(self.rng.exponential(100000)) if include_volume else 0
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('date', inplace=True)
        
        return df
    
    def add_market_impacts(self, data, impacts):
        """
        Add market impacts to existing data.
        
        Args:
            data: DataFrame with OHLCV data
            impacts: List of dictionaries with date and price_impact
            
        Returns:
            DataFrame with modified prices
        """
        # Create copy to avoid modifying original
        result = data.copy()
        
        # Add impacts
        for impact in impacts:
            date = impact['date']
            price_impact = impact['price_impact']
            
            if date in result.index:
                # Apply price impact
                result.loc[date, 'open'] *= (1 + price_impact)
                result.loc[date, 'high'] *= (1 + price_impact)
                result.loc[date, 'low'] *= (1 + price_impact)
                result.loc[date, 'close'] *= (1 + price_impact)
                
                # Optionally adjust volume
                if 'volume_impact' in impact and 'volume' in result.columns:
                    result.loc[date, 'volume'] *= (1 + impact['volume_impact'])
        
        return result
    
    def add_regime_effects(self, data, regimes):
        """
        Add regime effects to existing data.
        
        Args:
            data: DataFrame with OHLCV data
            regimes: List of dictionaries with start_date, end_date, volatility_factor
            
        Returns:
            DataFrame with modified prices
        """
        # Create copy to avoid modifying original
        result = data.copy()
        
        # Apply regime effects
        for regime in regimes:
            start_date = regime['start_date']
            end_date = regime['end_date']
            volatility_factor = regime.get('volatility_factor', 1.0)
            drift_factor = regime.get('drift_factor', 1.0)
            
            # Get mask for dates in this regime
            mask = (result.index >= start_date) & (result.index <= end_date)
            
            if mask.any():
                # Calculate daily returns
                daily_returns = result.loc[mask, 'close'].pct_change().fillna(0)
                
                # Adjust returns for regime
                adjusted_returns = daily_returns * volatility_factor + drift_factor / 252
                
                # Start with close price before regime
                start_idx = result.index.get_loc(start_date)
                start_price = result.iloc[start_idx - 1]['close'] if start_idx > 0 else result.iloc[0]['close']
                
                # Recalculate prices within regime
                new_closes = start_price * np.cumprod(1 + adjusted_returns)
                
                # Update close prices
                result.loc[mask, 'close'] = new_closes
                
                # Adjust other prices proportionally
                for date, new_close in zip(result.loc[mask].index, new_closes):
                    old_close = data.loc[date, 'close']
                    factor = new_close / old_close
                    
                    result.loc[date, 'open'] *= factor
                    result.loc[date, 'high'] *= factor
                    result.loc[date, 'low'] *= factor
        
        return result
