"""
Base class for technical indicators.
"""
from abc import abstractmethod
import pandas as pd
from typing import Any, Dict, List, Optional

from ..component_base import Component

class Indicator(Component):
    """Base class for technical indicators."""
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate indicator values.
        
        Args:
            data: DataFrame with market data
            
        Returns:
            Series with indicator values
        """
        pass
