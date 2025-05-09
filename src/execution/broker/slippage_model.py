"""
Slippage models for simulating execution costs.

This module provides classes for modeling price slippage
during order execution in simulated environments.
"""
import logging
import random
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class SlippageModel(ABC):
    """Base class for all slippage models."""
    
    def __init__(self):
        """Initialize the slippage model."""
        pass
    
    @abstractmethod
    def apply_slippage(self, price: float, quantity: float, direction: str, 
                       market_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate price after slippage.
        
        Args:
            price: Base price
            quantity: Order quantity
            direction: Order direction ('BUY' or 'SELL')
            market_data: Optional additional market data
            
        Returns:
            float: Price after slippage
        """
        pass
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the slippage model.
        
        Args:
            config: Configuration dictionary
        """
        pass


class FixedSlippageModel(SlippageModel):
    """
    Fixed percentage slippage model.
    
    Applies a fixed percentage slippage to all orders.
    """
    
    def __init__(self, slippage_percent: float = 0.1):
        """
        Initialize with fixed slippage.
        
        Args:
            slippage_percent: Slippage percentage (0.1 = 0.1%)
        """
        super().__init__()
        self.slippage_percent = slippage_percent / 100.0  # Convert to decimal
    
    def apply_slippage(self, price: float, quantity: float, direction: str, 
                      market_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Apply fixed slippage to price.
        
        Args:
            price: Base price
            quantity: Order quantity
            direction: Order direction ('BUY' or 'SELL')
            market_data: Optional additional market data
            
        Returns:
            float: Price after slippage
        """
        # For buys, slippage increases price
        # For sells, slippage decreases price
        slippage_factor = 1.0 + (self.slippage_percent if direction == "BUY" else -self.slippage_percent)
        
        return price * slippage_factor
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the fixed slippage model.
        
        Args:
            config: Configuration dictionary
        """
        if 'slippage_percent' in config:
            self.slippage_percent = float(config['slippage_percent']) / 100.0


class VariableSlippageModel(SlippageModel):
    """
    Variable slippage model based on order size and volatility.
    
    Calculates slippage based on order size, market volatility,
    and random factors to simulate more realistic execution costs.
    """
    
    def __init__(self, base_slippage_percent: float = 0.05, 
                size_impact: float = 0.01, volatility_impact: float = 0.5,
                random_factor: float = 0.2):
        """
        Initialize with variable slippage parameters.
        
        Args:
            base_slippage_percent: Base slippage percentage
            size_impact: How much order size affects slippage
            volatility_impact: How much volatility affects slippage
            random_factor: Maximum random factor to apply
        """
        super().__init__()
        self.base_slippage = base_slippage_percent / 100.0  # Convert to decimal
        self.size_impact = size_impact
        self.volatility_impact = volatility_impact
        self.random_factor = random_factor
    
    def apply_slippage(self, price: float, quantity: float, direction: str, 
                      market_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Apply variable slippage to price.
        
        Args:
            price: Base price
            quantity: Order quantity
            direction: Order direction ('BUY' or 'SELL')
            market_data: Optional market data (should include 'volatility' if available)
            
        Returns:
            float: Price after slippage
        """
        # Get volatility if available, otherwise use default
        volatility = 0.01  # Default 1% volatility
        if market_data and 'volatility' in market_data:
            volatility = market_data['volatility']
        
        # Calculate size factor (larger orders have more slippage)
        # This is a simple model - in reality would depend on average daily volume
        size_factor = 1.0 + (abs(quantity) * self.size_impact / 10000.0)
        
        # Calculate volatility factor
        volatility_factor = 1.0 + (volatility * self.volatility_impact)
        
        # Random factor to simulate market unpredictability
        random_component = 1.0 + random.uniform(-self.random_factor, self.random_factor)
        
        # Combined slippage factor
        slippage_percent = self.base_slippage * size_factor * volatility_factor * random_component
        
        # Direction factor
        direction_factor = 1.0 if direction == "BUY" else -1.0
        
        # Calculate slippage price
        slippage_price = price * (1.0 + slippage_percent * direction_factor)
        
        logger.debug(f"Variable slippage calculated: base={price:.4f}, after={slippage_price:.4f}, " +
                   f"percent={slippage_percent*100:.4f}%, direction={direction}")
        
        return slippage_price
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the variable slippage model.
        
        Args:
            config: Configuration dictionary
        """
        if 'base_slippage_percent' in config:
            self.base_slippage = float(config['base_slippage_percent']) / 100.0
        
        if 'size_impact' in config:
            self.size_impact = float(config['size_impact'])
        
        if 'volatility_impact' in config:
            self.volatility_impact = float(config['volatility_impact'])
        
        if 'random_factor' in config:
            self.random_factor = float(config['random_factor'])