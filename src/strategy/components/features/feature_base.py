# src/strategies/components/features/feature_base.py
from ..component_base import Component
from abc import abstractmethod
import pandas as pd
from typing import Any, Dict, List, Optional

class Feature(Component):
    """
    Base class for features.
    
    Features transform raw data or indicators into more meaningful inputs.
    """
    
    @abstractmethod
    def extract(self, data: pd.DataFrame, indicators: Dict[str, pd.Series] = None) -> pd.Series:
        """
        Extract feature from data and indicators.
        
        Args:
            data: DataFrame with market data
            indicators: Optional dict of indicator name -> values
            
        Returns:
            Series with feature values
        """
        pass
