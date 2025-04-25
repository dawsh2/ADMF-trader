# src/strategies/components/rules/rule_base.py
from ..component_base import Component
from abc import abstractmethod
import pandas as pd
from typing import Any, Dict, List, Optional

class Rule(Component):
    """Base class for trading rules."""
    
    def __init__(self, name=None, parameters=None):
        super().__init__(name, parameters)
        self.weight = 1.0  # Default weight for rule combination
    
    def configure(self, config):
        """Configure the rule with parameters."""
        super().configure(config)
        # Extract weight if present
        self.weight = self.parameters.get('weight', 1.0)
    
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame, features: Dict[str, pd.Series] = None) -> int:
        """
        Generate trading signal from data and features.
        
        Args:
            data: DataFrame with market data
            features: Optional dict of feature name -> values
            
        Returns:
            Signal value (-1, 0, or 1)
        """
        pass
