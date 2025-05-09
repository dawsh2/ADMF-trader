"""
Data types for ADMF-Trader.

This module defines the standard data types used across the system,
including bar data, tick data, and other market data structures.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Any, Optional, List, Union

class Timeframe(Enum):
    """Standard timeframes for bar data."""
    TICK = auto()
    SECOND = auto()
    MINUTE_1 = auto()
    MINUTE_5 = auto()
    MINUTE_15 = auto()
    MINUTE_30 = auto()
    HOUR_1 = auto()
    HOUR_4 = auto()
    DAY_1 = auto()
    WEEK_1 = auto()
    MONTH_1 = auto()
    
    @classmethod
    def from_string(cls, timeframe_str: str) -> 'Timeframe':
        """
        Convert a string to a Timeframe enum.
        
        Args:
            timeframe_str: String representation (e.g., '1m', '1d')
            
        Returns:
            Timeframe: Corresponding enum value
            
        Raises:
            ValueError: If string is invalid
        """
        # Map of string representations to enum values
        mapping = {
            'tick': cls.TICK,
            's': cls.SECOND,
            '1m': cls.MINUTE_1,
            '5m': cls.MINUTE_5,
            '15m': cls.MINUTE_15,
            '30m': cls.MINUTE_30,
            '1h': cls.HOUR_1,
            '4h': cls.HOUR_4,
            '1d': cls.DAY_1,
            '1w': cls.WEEK_1,
            '1M': cls.MONTH_1,
            
            # Alternative formats
            'minute': cls.MINUTE_1,
            'hour': cls.HOUR_1,
            'day': cls.DAY_1,
            'week': cls.WEEK_1,
            'month': cls.MONTH_1,
            
            # Common aliases
            'min': cls.MINUTE_1,
            'd': cls.DAY_1,
            'h': cls.HOUR_1,
            'w': cls.WEEK_1,
            'M': cls.MONTH_1
        }
        
        # Try direct lookup
        if timeframe_str.lower() in mapping:
            return mapping[timeframe_str.lower()]
            
        # Try composite format (e.g., "1min", "15m")
        import re
        match = re.match(r'(\d+)([a-zA-Z]+)', timeframe_str)
        if match:
            value, unit = match.groups()
            value = int(value)
            
            if unit.lower() in ('m', 'min', 'minute', 'minutes'):
                if value == 1:
                    return cls.MINUTE_1
                elif value == 5:
                    return cls.MINUTE_5
                elif value == 15:
                    return cls.MINUTE_15
                elif value == 30:
                    return cls.MINUTE_30
            elif unit.lower() in ('h', 'hour', 'hours'):
                if value == 1:
                    return cls.HOUR_1
                elif value == 4:
                    return cls.HOUR_4
            elif unit.lower() in ('d', 'day', 'days'):
                if value == 1:
                    return cls.DAY_1
            elif unit.lower() in ('w', 'week', 'weeks'):
                if value == 1:
                    return cls.WEEK_1
            elif unit.lower() in ('M', 'month', 'months'):
                if value == 1:
                    return cls.MONTH_1
        
        raise ValueError(f"Invalid timeframe string: {timeframe_str}")
        
    def to_string(self) -> str:
        """
        Convert enum to string representation.
        
        Returns:
            str: String representation
        """
        mapping = {
            self.TICK: 'tick',
            self.SECOND: '1s',
            self.MINUTE_1: '1m',
            self.MINUTE_5: '5m',
            self.MINUTE_15: '15m',
            self.MINUTE_30: '30m',
            self.HOUR_1: '1h',
            self.HOUR_4: '4h',
            self.DAY_1: '1d',
            self.WEEK_1: '1w',
            self.MONTH_1: '1M'
        }
        return mapping[self]
        
    def to_seconds(self) -> int:
        """
        Convert timeframe to seconds.
        
        Returns:
            int: Number of seconds
            
        Raises:
            ValueError: If timeframe is TICK (not fixed duration)
        """
        if self == self.TICK:
            raise ValueError("Tick timeframe does not have a fixed duration")
            
        mapping = {
            self.SECOND: 1,
            self.MINUTE_1: 60,
            self.MINUTE_5: 300,
            self.MINUTE_15: 900,
            self.MINUTE_30: 1800,
            self.HOUR_1: 3600,
            self.HOUR_4: 14400,
            self.DAY_1: 86400,
            self.WEEK_1: 604800,
            self.MONTH_1: 2592000  # Approximation (30 days)
        }
        return mapping[self]

@dataclass
class Bar:
    """
    OHLCV bar data with timestamp.
    
    This class represents a standard OHLCV (Open, High, Low, Close, Volume)
    bar with a timestamp.
    """
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0
    timeframe: Union[Timeframe, str] = Timeframe.DAY_1
    
    def __post_init__(self):
        """Convert timeframe string to enum if needed."""
        if isinstance(self.timeframe, str):
            self.timeframe = Timeframe.from_string(self.timeframe)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dict: Dictionary representation
        """
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'timeframe': self.timeframe.to_string()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bar':
        """
        Create a Bar from a dictionary.
        
        Args:
            data: Dictionary with bar data
            
        Returns:
            Bar: Bar instance
        """
        # Copy the dictionary to avoid modifying the original
        data_copy = data.copy()
        
        # Convert timeframe string to enum if needed
        if 'timeframe' in data_copy and isinstance(data_copy['timeframe'], str):
            data_copy['timeframe'] = Timeframe.from_string(data_copy['timeframe'])
            
        return cls(**data_copy)

@dataclass
class Tick:
    """
    Tick data with timestamp.
    
    This class represents a single tick with timestamp, price, and volume.
    """
    timestamp: datetime
    symbol: str
    price: float
    volume: float = 0
    bid: Optional[float] = None
    ask: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dict: Dictionary representation
        """
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'price': self.price,
            'volume': self.volume,
            'bid': self.bid,
            'ask': self.ask
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tick':
        """
        Create a Tick from a dictionary.
        
        Args:
            data: Dictionary with tick data
            
        Returns:
            Tick: Tick instance
        """
        return cls(**data)