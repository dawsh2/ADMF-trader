from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import logging
import datetime 

from src.core.events.event_types import BarEvent

logger = logging.getLogger(__name__)


class DataHandlerBase(ABC):
    """Base interface for all data handlers."""
    
    def __init__(self, name=None, data_source=None):
        """
        Initialize the data handler.
        
        Args:
            name: Optional handler name
            data_source: Optional data source
        """
        self._name = name or self.__class__.__name__
        self._data_source = data_source
        self._event_bus = None
        self.stats = {
            'bars_processed': 0,
            'symbols_loaded': 0,
            'errors': 0
        }
    
    @abstractmethod
    def load_data(self, symbols: Union[str, List[str]], 
                 start_date=None, end_date=None, 
                 timeframe: str = '1d') -> None:
        """
        Load data for the specified symbols.
        
        Args:
            symbols: Symbol or list of symbols
            start_date: Start date
            end_date: End date
            timeframe: Data timeframe
        """
        pass
    
    @abstractmethod
    def get_next_bar(self, symbol: str) -> Optional[Any]:
        """
        Get the next bar for a symbol.
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Bar data or None if no more data
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset the data handler state."""
        pass
    
    def set_event_bus(self, event_bus) -> None:
        """
        Set the event bus for emitting events.
        
        Args:
            event_bus: Event bus instance
        """
        self._event_bus = event_bus
    
    def set_data_source(self, data_source) -> None:
        """
        Set the data source.
        
        Args:
            data_source: Data source instance
        """
        self._data_source = data_source
    
    def get_data_source(self) -> Any:
        """Get the current data source."""
        return self._data_source
    
    def get_symbols(self) -> List[str]:
        """Get the list of loaded symbols."""
        # Implement in concrete classes
        return []
    
    def get_latest_bar(self, symbol: str) -> Optional[Any]:
        """
        Get the latest bar for a symbol.
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Latest bar or None if not available
        """
        # Implement in concrete classes
        return None
    
    def get_latest_bars(self, symbol: str, N: int = 1) -> List[Any]:
        """
        Get the latest N bars for a symbol.
        
        Args:
            symbol: Instrument symbol
            N: Number of bars to get
            
        Returns:
            List of up to N latest bars
        """
        # Implement in concrete classes
        return []
    
    def get_bar_count(self, symbol: str) -> int:
        """
        Get the number of bars for a symbol.
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Number of bars
        """
        # Implement in concrete classes
        return 0
    
    def get_timeframe(self) -> str:
        """Get the current timeframe."""
        # Implement in concrete classes
        return '1d'
    
    def reset_stats(self) -> None:
        """Reset handler statistics."""
        self.stats = {
            'bars_processed': 0,
            'symbols_loaded': 0,
            'errors': 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return self.stats.copy()
    
    @property
    def name(self) -> str:
        """Get data handler name."""
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        """Set data handler name."""
        self._name = value
