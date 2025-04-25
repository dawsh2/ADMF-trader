"""
Position sizing strategies for risk management.
"""
import math
import logging
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod

from core.events.utils import ObjectRegistry

logger = logging.getLogger(__name__)

class PositionSizer:
    """
    Position sizer that supports multiple sizing strategies.
    
    Strategies include:
    - Fixed: Fixed quantity
    - Percent equity: Percentage of portfolio equity
    - Percent risk: Risk a percentage of equity (using stop loss)
    - Volatility: Position size based on volatility
    - Kelly: Kelly criterion-based sizing
    """
    
    def __init__(self, method: str = 'fixed', **params):
        """
        Initialize position sizer.
        
        Args:
            method: Sizing method ('fixed', 'percent_equity', 'percent_risk', 'volatility', 'kelly')
            **params: Method-specific parameters
        """
        self.method = method
        self.params = params
        self.configured = False
        
        # Validate method
        valid_methods = ['fixed', 'percent_equity', 'percent_risk', 'volatility', 'kelly']
        if method not in valid_methods:
            logger.warning(f"Invalid sizing method: {method}. Using 'fixed' instead.")
            self.method = 'fixed'
            
        # Default parameters for each method
        self.default_params = {
            'fixed': {
                'quantity': 100,
                'max_quantity': 1000
            },
            'percent_equity': {
                'percent': 10.0,  # Percentage of equity
                'max_quantity': 1000
            },
            'percent_risk': {
                'risk_percent': 2.0,  # Risk percentage
                'stop_percent': 2.0,  # Stop loss percentage
                'max_quantity': 1000
            },
            'volatility': {
                'atr_multiple': 1.0,  # Multiple of ATR for position sizing
                'risk_percent': 2.0,  # Risk percentage
                'max_quantity': 1000,
                'lookback': 20  # Lookback period for volatility calculation
            },
            'kelly': {
                'win_rate': 0.5,  # Historical win rate
                'win_loss_ratio': 2.0,  # Ratio of average win to average loss
                'fraction': 0.5,  # Fraction of Kelly to use (0.5 = half-Kelly)
                'max_quantity': 1000
            }
        }
        
        # Update with provided parameters
        self._update_params()
    
    def configure(self, config):
        """
        Configure the position sizer.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        # Set the method
        if 'method' in config_dict:
            self.method = config_dict.pop('method')
            
            # Validate method
            valid_methods = ['fixed', 'percent_equity', 'percent_risk', 'volatility', 'kelly']
            if self.method not in valid_methods:
                logger.warning(f"Invalid sizing method: {self.method}. Using 'fixed' instead.")
                self.method = 'fixed'
        
        # Update parameters
        self.params.update(config_dict)
        self._update_params()
        
        self.configured = True
        logger.info(f"Configured position sizer with method: {self.method}")
    
    def _update_params(self):
        """Update parameters with defaults for current method."""
        method_defaults = self.default_params.get(self.method, {})
        
        # Merge defaults with provided parameters
        for key, value in method_defaults.items():
            if key not in self.params:
                self.params[key] = value
    
    def calculate_position_size(self, symbol: str, direction: str, price: float, 
                               portfolio, context=None):
        """
        Calculate position size based on the selected method.
        
        Args:
            symbol: Instrument symbol
            direction: Trade direction ('BUY' or 'SELL')
            price: Current price
            portfolio: Portfolio manager instance
            context: Optional additional context (e.g., volatility, signal confidence)
            
        Returns:
            float: Calculated position size
        """
        context = context or {}
        
        # Select sizing method
        if self.method == 'fixed':
            size = self._fixed_size(price, portfolio)
        elif self.method == 'percent_equity':
            size = self._percent_equity(price, portfolio)
        elif self.method == 'percent_risk':
            size = self._percent_risk(price, portfolio, symbol, context)
        elif self.method == 'volatility':
            size = self._volatility_based(price, symbol, portfolio, context)
        elif self.method == 'kelly':
            size = self._kelly_criterion(price, portfolio, context)
        else:
            logger.warning(f"Unknown sizing method: {self.method}. Using fixed size.")
            size = self._fixed_size(price, portfolio)
        
        # Ensure integer quantity (can be changed to allow fractional shares)
        size = int(size)
        
        # Apply direction
        if direction == 'SELL':
            size = -size
        
        return size
    
    def _fixed_size(self, price, portfolio):
        """
        Calculate fixed contract/share size.
        
        Args:
            price: Current price
            portfolio: Portfolio manager
            
        Returns:
            float: Position size
        """
        quantity = self.params.get('quantity', 100)
        max_quantity = self.params.get('max_quantity', 1000)
        
        # Apply maximum size constraint
        quantity = min(quantity, max_quantity)
        
        return quantity
    
    def _percent_equity(self, price, portfolio):
        """
        Calculate size based on percentage of equity.
        
        Args:
            price: Current price
            portfolio: Portfolio manager
            
        Returns:
            float: Position size
        """
        percent = self.params.get('percent', 10.0) / 100.0  # Convert to decimal
        max_quantity = self.params.get('max_quantity', 1000)
        
        # Calculate equity allocation
        equity_allocation = portfolio.equity * percent
        
        # Calculate quantity
        quantity = equity_allocation / price if price > 0 else 0
        
        # Apply maximum size constraint
        quantity = min(quantity, max_quantity)
        
        return quantity
    
    def _percent_risk(self, price, portfolio, symbol, context):
        """
        Calculate size based on percentage of equity risked.
        
        Args:
            price: Current price
            portfolio: Portfolio manager
            symbol: Instrument symbol
            context: Additional context
            
        Returns:
            float: Position size
        """
        risk_percent = self.params.get('risk_percent', 2.0) / 100.0  # Convert to decimal
        stop_percent = self.params.get('stop_percent', 2.0) / 100.0  # Convert to decimal
        max_quantity = self.params.get('max_quantity', 1000)
        
        # Calculate risk amount
        risk_amount = portfolio.equity * risk_percent
        
        # Calculate stop loss level
        stop_loss = price * (1 - stop_percent)  # For long positions
        
        # Override stop loss if provided in context
        if 'stop_price' in context:
            stop_loss = context['stop_price']
        
        # Calculate risk per share
        risk_per_share = abs(price - stop_loss)
        
        # Avoid division by zero
        if risk_per_share <= 0:
            logger.warning("Risk per share is zero or negative, using minimum value")
            risk_per_share = price * 0.01  # Use 1% as minimum risk
        
        # Calculate quantity
        quantity = risk_amount / risk_per_share
        
        # Apply maximum size constraint
        quantity = min(quantity, max_quantity)
        
        return quantity
    
    def _volatility_based(self, price, symbol, portfolio, context):
        """
        Calculate size based on volatility.
        
        Args:
            price: Current price
            symbol: Instrument symbol
            portfolio: Portfolio manager
            context: Additional context
            
        Returns:
            float: Position size
        """
        atr_multiple = self.params.get('atr_multiple', 1.0)
        risk_percent = self.params.get('risk_percent', 2.0) / 100.0
        max_quantity = self.params.get('max_quantity', 1000)
        
        # Get ATR from context or use default
        atr = context.get('atr', price * 0.02)  # Default to 2% of price if not provided
        
        # Calculate risk amount
        risk_amount = portfolio.equity * risk_percent
        
        # Calculate stop distance based on ATR
        stop_distance = atr * atr_multiple
        
        # Calculate quantity
        quantity = risk_amount / stop_distance if stop_distance > 0 else 0
        
        # Apply maximum size constraint
        quantity = min(quantity, max_quantity)
        
        return quantity
    
    def _kelly_criterion(self, price, portfolio, context):
        """
        Calculate size based on Kelly criterion.
        
        Args:
            price: Current price
            portfolio: Portfolio manager
            context: Additional context
            
        Returns:
            float: Position size
        """
        win_rate = self.params.get('win_rate', 0.5)
        win_loss_ratio = self.params.get('win_loss_ratio', 2.0)
        fraction = self.params.get('fraction', 0.5)  # Half-Kelly for safety
        max_quantity = self.params.get('max_quantity', 1000)
        
        # Override with context values if provided
        if 'win_rate' in context:
            win_rate = context['win_rate']
        if 'win_loss_ratio' in context:
            win_loss_ratio = context['win_loss_ratio']
        
        # Calculate Kelly fraction
        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        # Limit Kelly to sensible range [0, 1]
        kelly = max(0, min(kelly, 1))
        
        # Apply fraction of Kelly
        kelly_allocation = kelly * fraction
        
        # Calculate equity to risk
        equity_allocation = portfolio.equity * kelly_allocation
        
        # Calculate quantity
        quantity = equity_allocation / price if price > 0 else 0
        
        # Apply maximum size constraint
        quantity = min(quantity, max_quantity)
        
        return quantity
    
    def get_parameters(self):
        """
        Get current parameter values.
        
        Returns:
            Dict: Parameter values
        """
        return {
            'method': self.method,
            **self.params
        }
    
    def set_parameters(self, params):
        """
        Set parameters.
        
        Args:
            params: Parameter dictionary
        """
        if 'method' in params:
            self.method = params.pop('method')
            
            # Validate method
            valid_methods = ['fixed', 'percent_equity', 'percent_risk', 'volatility', 'kelly']
            if self.method not in valid_methods:
                logger.warning(f"Invalid sizing method: {self.method}. Using 'fixed' instead.")
                self.method = 'fixed'
        
        # Update parameters
        self.params.update(params)
        self._update_params()
    
    def to_dict(self):
        """
        Convert to dictionary.
        
        Returns:
            Dict: Dictionary representation
        """
        return {
            'method': self.method,
            'params': dict(self.params),
            'configured': self.configured
        }


# Factory for creating position sizers
class PositionSizerFactory:
    """Factory for creating position sizers."""
    
    @staticmethod
    def create(method=None, config=None):
        """
        Create a position sizer.
        
        Args:
            method: Optional method name
            config: Optional configuration
            
        Returns:
            PositionSizer: Position sizer instance
        """
        # Create base sizer
        sizer = PositionSizer(method=method)
        
        # Configure if config provided
        if config:
            sizer.configure(config)
            
        return sizer
