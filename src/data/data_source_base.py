from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class DataSourceBase(ABC):
    """Base interface for all data sources."""
    
    @abstractmethod
    def get_data(self, symbol: str, start_date=None, end_date=None, timeframe: str = '1d') -> Any:
        """
        Get data for a symbol within a date range.
        
        Args:
            symbol: Instrument symbol
            start_date: Start date
            end_date: End date
            timeframe: Data timeframe
            
        Returns:
            Data container (DataFrame, etc.)
        """
        pass
    
    @abstractmethod
    def is_available(self, symbol: str, start_date=None, end_date=None, timeframe: str = '1d') -> bool:
        """
        Check if data is available for the specified parameters.
        
        Args:
            symbol: Instrument symbol
            start_date: Start date
            end_date: End date
            timeframe: Data timeframe
            
        Returns:
            True if data is available, False otherwise
        """
        pass
    
    @property
    def name(self) -> str:
        """Get data source name."""
        return getattr(self, '_name', self.__class__.__name__)
    
    @name.setter
    def name(self, value: str) -> None:
        """Set data source name."""
        self._name = value

class DataHandlerBase(ABC):
    """Base interface for all data handlers."""
    
    @abstractmethod
    def load_data(self, symbols, start_date=None, end_date=None, timeframe: str = '1d') -> None:
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
    
    @property
    def name(self) -> str:
        """Get data handler name."""
        return getattr(self, '_name', self.__class__.__name__)
    
    @name.setter
    def name(self, value: str) -> None:
        """Set data handler name."""
        self._name = value
