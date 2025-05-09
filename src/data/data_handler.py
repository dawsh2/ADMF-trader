"""
Data handler interface for ADMF-Trader.

This module defines the DataHandler interface and related base classes
for loading and managing market data.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union, Iterator

from src.core.component import Component
from src.core.event_system import Event, EventType
from src.data.data_types import Bar, Tick, Timeframe

logger = logging.getLogger(__name__)

class DataHandler(Component, ABC):
    """
    Interface for data handling components.
    
    DataHandler is responsible for:
    - Loading data from sources
    - Serving data to strategy and other components
    - Emitting bar events
    - Managing data splits for training/testing
    """
    
    def __init__(self, name: str):
        """
        Initialize the data handler.
        
        Args:
            name: Component name
        """
        super().__init__(name)
        self.symbols = []
        self.timeframe = Timeframe.DAY_1
        
    @abstractmethod
    def load_data(self, symbols: List[str], start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None, timeframe: Union[str, Timeframe] = Timeframe.DAY_1) -> bool:
        """
        Load data for the specified symbols and time range.
        
        Args:
            symbols: List of symbols to load
            start_date: Start date for data, or None for all available
            end_date: End date for data, or None for all available
            timeframe: Timeframe for data
            
        Returns:
            bool: True if data loaded successfully, False otherwise
        """
        pass
        
    @abstractmethod
    def get_latest_bar(self, symbol: str) -> Optional[Bar]:
        """
        Get the latest bar for a symbol.
        
        Args:
            symbol: Symbol to get bar for
            
        Returns:
            Optional[Bar]: Latest bar or None if not available
        """
        pass
        
    @abstractmethod
    def get_latest_bars(self, symbol: str, n: int = 1) -> List[Bar]:
        """
        Get the latest n bars for a symbol.
        
        Args:
            symbol: Symbol to get bars for
            n: Number of bars to get
            
        Returns:
            List[Bar]: List of bars (may be empty)
        """
        pass
        
    @abstractmethod
    def get_all_bars(self, symbol: str) -> List[Bar]:
        """
        Get all bars for a symbol.
        
        Args:
            symbol: Symbol to get bars for
            
        Returns:
            List[Bar]: List of all bars (may be empty)
        """
        pass
        
    @abstractmethod
    def update_bars(self):
        """Update bars and emit bar events."""
        pass
        
    @abstractmethod
    def split_data(self, train_ratio: float = 0.7) -> Tuple[Dict[str, List[Bar]], Dict[str, List[Bar]]]:
        """
        Split data into training and testing sets.
        
        Args:
            train_ratio: Ratio of data to use for training (0.0-1.0)
            
        Returns:
            Tuple[Dict[str, List[Bar]], Dict[str, List[Bar]]]: Training and testing data
        """
        pass
        
    def get_symbols(self) -> List[str]:
        """
        Get list of loaded symbols.
        
        Returns:
            List[str]: List of symbols
        """
        return self.symbols.copy()
        
    def emit_bar_event(self, bar: Bar) -> None:
        """
        Emit a bar event.
        
        Args:
            bar: Bar to emit
        """
        if not self.event_bus:
            logger.warning("Cannot emit bar event: event bus not set")
            return
            
        # Create bar event
        event = Event(EventType.BAR, bar.to_dict())
        
        # Publish event
        self.event_bus.publish(event)
        
    def reset(self) -> None:
        """Reset the data handler."""
        super().reset()
        self.logger.info(f"Data handler {self.name} reset")