"""
Commission models for simulating trading costs.

This module provides components for calculating trade commissions
during backtest simulations.
"""
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class CommissionModel:
    """
    Base class for commission models.
    
    This class provides an interface for calculating trading commissions
    based on configurable parameters.
    """
    
    def __init__(self, commission_type: str = 'percentage', rate: float = 0.1,
                min_commission: float = 1.0, max_commission: Optional[float] = None):
        """
        Initialize the commission model.
        
        Args:
            commission_type: Type of commission ('percentage', 'fixed', 'tiered')
            rate: Commission rate (percentage or fixed amount)
            min_commission: Minimum commission amount
            max_commission: Optional maximum commission amount
        """
        self.commission_type = commission_type.lower()
        self.rate = rate
        self.min_commission = min_commission
        self.max_commission = max_commission
        
        # For tiered model
        self.tiers = []
        
        logger.info(f"Commission model initialized: type={commission_type}, rate={rate}")
    
    def calculate(self, price: float, quantity: float, **kwargs) -> float:
        """
        Calculate commission for a trade.
        
        Args:
            price: Trade price
            quantity: Trade quantity
            **kwargs: Additional arguments for specific commission models
            
        Returns:
            float: Commission amount
        """
        trade_value = abs(price * quantity)
        
        if self.commission_type == 'percentage':
            # Percentage of trade value
            commission = trade_value * (self.rate / 100.0)
        
        elif self.commission_type == 'fixed':
            # Fixed amount per trade
            commission = self.rate
        
        elif self.commission_type == 'per_share':
            # Fixed amount per share/contract (rate is per share, not percentage)
            # For per_share type, price is ignored, only quantity matters
            # The rate here is in $ per share, not percentage
            if trade_value == 0:
                commission = 0.0
            else:
                commission = abs(quantity) * self.rate
        
        elif self.commission_type == 'tiered':
            # Tiered based on trade value
            commission = self._calculate_tiered(trade_value)
        
        else:
            logger.warning(f"Unknown commission type: {self.commission_type}, using percentage")
            commission = trade_value * (self.rate / 100.0)
        
        # Apply minimum commission
        if commission < self.min_commission:
            commission = self.min_commission
        
        # Apply maximum commission if specified
        if self.max_commission is not None and commission > self.max_commission:
            commission = self.max_commission
        
        logger.debug(f"Commission calculated: {commission:.2f} (value: {trade_value:.2f}, type: {self.commission_type})")
        
        return commission
    
    def _calculate_tiered(self, trade_value: float) -> float:
        """
        Calculate tiered commission.
        
        Args:
            trade_value: Value of the trade
            
        Returns:
            float: Commission amount
        """
        if not self.tiers:
            # Default to percentage if no tiers defined
            return trade_value * (self.rate / 100.0)
        
        # Find the appropriate tier
        for tier_min, tier_max, tier_rate in sorted(self.tiers):
            if tier_min <= trade_value < tier_max:
                return trade_value * (tier_rate / 100.0)
        
        # Use the last tier if above all tiers
        return trade_value * (self.tiers[-1][2] / 100.0)
    
    def add_tier(self, min_value: float, max_value: float, rate: float) -> None:
        """
        Add a commission tier.
        
        Args:
            min_value: Minimum trade value for this tier
            max_value: Maximum trade value for this tier
            rate: Commission rate for this tier (percentage)
        """
        self.tiers.append((min_value, max_value, rate))
        # Sort tiers by min_value
        self.tiers.sort(key=lambda x: x[0])
        
        logger.debug(f"Added commission tier: {min_value} - {max_value}: {rate}%")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the commission model.
        
        Args:
            config: Configuration dictionary
        """
        if 'commission_type' in config:
            self.commission_type = config['commission_type'].lower()
        
        if 'rate' in config:
            self.rate = float(config['rate'])
        
        if 'min_commission' in config:
            self.min_commission = float(config['min_commission'])
        
        if 'max_commission' in config:
            self.max_commission = (float(config['max_commission']) 
                                 if config['max_commission'] is not None else None)
        
        # Configure tiers if provided
        if 'tiers' in config and isinstance(config['tiers'], list):
            self.tiers = []
            for tier in config['tiers']:
                if len(tier) == 3:
                    self.add_tier(tier[0], tier[1], tier[2])
        
        logger.info(f"Commission model configured: type={self.commission_type}, rate={self.rate}")
    
    def __call__(self, price: float, quantity: float, **kwargs) -> float:
        """
        Calculate commission (callable interface).
        
        Args:
            price: Trade price
            quantity: Trade quantity
            **kwargs: Additional parameters
            
        Returns:
            float: Commission amount
        """
        return self.calculate(price, quantity, **kwargs)