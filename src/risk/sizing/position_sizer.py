"""
Position sizing module for risk management.

This module provides classes for calculating appropriate position sizes based on 
various methods and risk parameters.
"""
import math
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class PositionSizer(ABC):
    """
    Abstract base class for position sizing.
    
    Position sizers calculate appropriate position sizes based on portfolio state,
    risk parameters, and market conditions.
    """
    
    def __init__(self, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize position sizer.
        
        Args:
            name: Position sizer name
            params: Position sizing parameters
        """
        self._name = name or self.__class__.__name__
        self.params = params or {}
        self.configured = False
    
    @abstractmethod
    def calculate_position_size(self, symbol: str, direction: str, price: float, 
                             portfolio, context: Dict = None) -> float:
        """
        Calculate position size.
        
        Args:
            symbol: Instrument symbol
            direction: Trade direction ('BUY' or 'SELL')
            price: Current price
            portfolio: Portfolio manager instance
            context: Additional context (optional)
            
        Returns:
            float: Position size
        """
        pass
    
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
        
        self.params.update(config_dict)
        self.configured = True
        logger.info(f"Configured position sizer: {self._name}")
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get position sizer parameters.
        
        Returns:
            Dict with parameters
        """
        return dict(self.params)
    
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """
        Set position sizer parameters.
        
        Args:
            params: New parameters
        """
        self.params.update(params)
    
    @property
    def name(self):
        """Get position sizer name."""
        return self._name


class FixedSizer(PositionSizer):
    """
    Fixed position sizer.
    
    Returns a fixed number of contracts or shares per trade.
    """
    
    def __init__(self, size: int = 100, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize fixed sizer.
        
        Args:
            size: Fixed position size
            name: Position sizer name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['size'] = size
    
    def calculate_position_size(self, symbol: str, direction: str, price: float, 
                              portfolio, context: Dict = None) -> float:
        """
        Calculate fixed position size.
        
        Args:
            symbol: Instrument symbol
            direction: Trade direction ('BUY' or 'SELL')
            price: Current price
            portfolio: Portfolio manager instance
            context: Additional context (optional)
            
        Returns:
            float: Fixed position size
        """
        size = float(self.params.get('size', 100))
        
        # Adjust for current position if needed
        position = portfolio.get_position(symbol)
        
        if position:
            # If position exists, check if we're closing or flipping
            current_qty = position.quantity
            
            if current_qty > 0 and direction == 'SELL':
                # Closing long position - return current size
                return current_qty
            elif current_qty < 0 and direction == 'BUY':
                # Closing short position - return current size
                return abs(current_qty)
        
        # Apply size adjustments from context
        if context:
            adjustment = context.get('size_adjustment', 1.0)
            size *= adjustment
        
        # Apply direction
        if direction == 'SELL':
            size = -size
            
        return size


class PercentEquitySizer(PositionSizer):
    """
    Percent of equity position sizer.
    
    Calculates position size as a percentage of account equity.
    """
    
    def __init__(self, percent: float = 0.01, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize percent equity sizer.
        
        Args:
            percent: Percentage of equity to risk (decimal)
            name: Position sizer name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['percent'] = percent
    
    def calculate_position_size(self, symbol: str, direction: str, price: float, 
                              portfolio, context: Dict = None) -> float:
        """
        Calculate position size based on percentage of equity.
        
        Args:
            symbol: Instrument symbol
            direction: Trade direction ('BUY' or 'SELL')
            price: Current price
            portfolio: Portfolio manager instance
            context: Additional context (optional)
            
        Returns:
            float: Position size
        """
        percent = float(self.params.get('percent', 0.01))
        min_size = float(self.params.get('min_size', 1))
        max_size = float(self.params.get('max_size', float('inf')))
        
        # Calculate position value
        equity = portfolio.equity
        position_value = equity * percent
        
        # Apply size adjustments from context
        if context:
            adjustment = context.get('size_adjustment', 1.0)
            position_value *= adjustment
            
            # Apply confidence adjustment if available
            confidence = context.get('signal_confidence', 1.0)
            position_value *= confidence
        
        # Convert to quantity
        if price <= 0:
            logger.warning(f"Invalid price: {price}, using default size")
            return min_size if direction == 'BUY' else -min_size
        
        size = position_value / price
        
        # Apply size limits
        size = max(min_size, min(max_size, size))
        
        # Handle existing position
        position = portfolio.get_position(symbol)
        
        if position:
            current_qty = position.quantity
            
            if current_qty > 0 and direction == 'SELL':
                # Closing long position - return current size
                return current_qty
            elif current_qty < 0 and direction == 'BUY':
                # Closing short position - return current size
                return abs(current_qty)
        
        # Apply direction
        if direction == 'SELL':
            size = -size
            
        return size


class PercentRiskSizer(PositionSizer):
    """
    Percent risk position sizer.
    
    Calculates position size based on percentage of equity risked and stop loss distance.
    """
    
    def __init__(self, risk_percent: float = 0.01, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize percent risk sizer.
        
        Args:
            risk_percent: Percentage of equity to risk (decimal)
            name: Position sizer name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['risk_percent'] = risk_percent
        
        # Default ATR multiplier for stop distance if not using explicit stops
        self.params['atr_multiplier'] = params.get('atr_multiplier', 2.0) if params else 2.0
        
        # Default to using percentage of price for stop distance if ATR not available
        self.params['default_stop_percent'] = params.get('default_stop_percent', 0.02) if params else 0.02
    
    def calculate_position_size(self, symbol: str, direction: str, price: float, 
                              portfolio, context: Dict = None) -> float:
        """
        Calculate position size based on percentage of equity risked.
        
        Args:
            symbol: Instrument symbol
            direction: Trade direction ('BUY' or 'SELL')
            price: Current price
            portfolio: Portfolio manager instance
            context: Additional context (optional)
            
        Returns:
            float: Position size
        """
        risk_percent = float(self.params.get('risk_percent', 0.01))
        min_size = float(self.params.get('min_size', 1))
        max_size = float(self.params.get('max_size', float('inf')))
        
        # Calculate risk amount
        equity = portfolio.equity
        risk_amount = equity * risk_percent
        
        # Apply size adjustments from context
        if context:
            adjustment = context.get('size_adjustment', 1.0)
            risk_amount *= adjustment
            
            # Apply confidence adjustment if available
            confidence = context.get('signal_confidence', 1.0)
            risk_amount *= confidence
        
        # Determine stop loss price
        stop_price = None
        
        # Try to get stop price from context
        if context:
            stop_price = context.get('stop_price')
        
        # If stop price not provided, try to calculate from ATR
        if stop_price is None and context and 'atr' in context:
            atr = context['atr']
            atr_multiplier = float(self.params.get('atr_multiplier', 2.0))
            
            if direction == 'BUY':
                stop_price = price - (atr * atr_multiplier)
            else:
                stop_price = price + (atr * atr_multiplier)
        
        # If still no stop price, use default percentage
        if stop_price is None:
            default_stop_percent = float(self.params.get('default_stop_percent', 0.02))
            
            if direction == 'BUY':
                stop_price = price * (1 - default_stop_percent)
            else:
                stop_price = price * (1 + default_stop_percent)
        
        # Calculate risk per share
        risk_per_share = abs(price - stop_price)
        
        # Convert to quantity
        if risk_per_share <= 0:
            logger.warning(f"Invalid risk per share: {risk_per_share}, using default size")
            return min_size if direction == 'BUY' else -min_size
        
        size = risk_amount / risk_per_share
        
        # Apply size limits
        size = max(min_size, min(max_size, size))
        
        # Handle existing position
        position = portfolio.get_position(symbol)
        
        if position:
            current_qty = position.quantity
            
            if current_qty > 0 and direction == 'SELL':
                # Closing long position - return current size
                return current_qty
            elif current_qty < 0 and direction == 'BUY':
                # Closing short position - return current size
                return abs(current_qty)
        
        # Apply direction
        if direction == 'SELL':
            size = -size
            
        return size


class KellySizer(PositionSizer):
    """
    Kelly criterion position sizer.
    
    Calculates position size based on win rate and win/loss ratio.
    """
    
    def __init__(self, fraction: float = 0.5, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize Kelly sizer.
        
        Args:
            fraction: Fraction of full Kelly to use (0.5 = half Kelly)
            name: Position sizer name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['fraction'] = fraction
        
        # Set default win rate and win/loss ratio
        self.params['win_rate'] = params.get('win_rate', 0.5) if params else 0.5
        self.params['win_loss_ratio'] = params.get('win_loss_ratio', 1.5) if params else 1.5
    
    def calculate_position_size(self, symbol: str, direction: str, price: float, 
                              portfolio, context: Dict = None) -> float:
        """
        Calculate position size based on Kelly criterion.
        
        Args:
            symbol: Instrument symbol
            direction: Trade direction ('BUY' or 'SELL')
            price: Current price
            portfolio: Portfolio manager instance
            context: Additional context (optional)
            
        Returns:
            float: Position size
        """
        fraction = float(self.params.get('fraction', 0.5))
        min_size = float(self.params.get('min_size', 1))
        max_size = float(self.params.get('max_size', float('inf')))
        
        # Get win rate and win/loss ratio
        win_rate = float(self.params.get('win_rate', 0.5))
        win_loss_ratio = float(self.params.get('win_loss_ratio', 1.5))
        
        # Use context values if provided
        if context:
            if 'win_rate' in context:
                win_rate = context['win_rate']
            if 'win_loss_ratio' in context:
                win_loss_ratio = context['win_loss_ratio']
            
            # Apply size adjustments
            adjustment = context.get('size_adjustment', 1.0)
            fraction *= adjustment
        
        # Calculate Kelly percentage
        # Kelly formula: f* = (p*b - q) / b
        # where p = win probability, q = loss probability (1-p), b = win/loss ratio
        loss_rate = 1.0 - win_rate
        kelly_pct = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio
        
        # Apply fraction and safety limits
        kelly_pct = kelly_pct * fraction
        kelly_pct = max(0.0, min(kelly_pct, 0.2))  # Cap at 20% of equity
        
        # Calculate position value
        equity = portfolio.equity
        position_value = equity * kelly_pct
        
        # Convert to quantity
        if price <= 0:
            logger.warning(f"Invalid price: {price}, using default size")
            return min_size if direction == 'BUY' else -min_size
        
        size = position_value / price
        
        # Apply size limits
        size = max(min_size, min(max_size, size))
        
        # Handle existing position
        position = portfolio.get_position(symbol)
        
        if position:
            current_qty = position.quantity
            
            if current_qty > 0 and direction == 'SELL':
                # Closing long position - return current size
                return current_qty
            elif current_qty < 0 and direction == 'BUY':
                # Closing short position - return current size
                return abs(current_qty)
        
        # Apply direction
        if direction == 'SELL':
            size = -size
            
        return size


class VolatilitySizer(PositionSizer):
    """
    Volatility-based position sizer.
    
    Adjusts position size based on asset volatility to maintain consistent risk.
    """
    
    def __init__(self, target_volatility: float = 0.01, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize volatility sizer.
        
        Args:
            target_volatility: Target daily portfolio volatility (decimal)
            name: Position sizer name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['target_volatility'] = target_volatility
    
    def calculate_position_size(self, symbol: str, direction: str, price: float, 
                              portfolio, context: Dict = None) -> float:
        """
        Calculate position size based on volatility.
        
        Args:
            symbol: Instrument symbol
            direction: Trade direction ('BUY' or 'SELL')
            price: Current price
            portfolio: Portfolio manager instance
            context: Additional context (optional)
            
        Returns:
            float: Position size
        """
        target_volatility = float(self.params.get('target_volatility', 0.01))
        min_size = float(self.params.get('min_size', 1))
        max_size = float(self.params.get('max_size', float('inf')))
        
        # Need volatility from context
        if not context or 'volatility' not in context:
            logger.warning("Volatility not provided in context, using default size")
            return min_size if direction == 'BUY' else -min_size
        
        asset_volatility = context['volatility']
        
        if asset_volatility <= 0:
            logger.warning(f"Invalid volatility: {asset_volatility}, using default size")
            return min_size if direction == 'BUY' else -min_size
        
        # Calculate position value
        equity = portfolio.equity
        target_value = (target_volatility / asset_volatility) * equity
        
        # Apply size adjustments from context
        if context:
            adjustment = context.get('size_adjustment', 1.0)
            target_value *= adjustment
            
            # Apply confidence adjustment if available
            confidence = context.get('signal_confidence', 1.0)
            target_value *= confidence
        
        # Convert to quantity
        if price <= 0:
            logger.warning(f"Invalid price: {price}, using default size")
            return min_size if direction == 'BUY' else -min_size
        
        size = target_value / price
        
        # Apply size limits
        size = max(min_size, min(max_size, size))
        
        # Handle existing position
        position = portfolio.get_position(symbol)
        
        if position:
            current_qty = position.quantity
            
            if current_qty > 0 and direction == 'SELL':
                # Closing long position - return current size
                return current_qty
            elif current_qty < 0 and direction == 'BUY':
                # Closing short position - return current size
                return abs(current_qty)
        
        # Apply direction
        if direction == 'SELL':
            size = -size
            
        return size


class PositionSizerFactory:
    """Factory for creating position sizers."""
    
    @staticmethod
    def create(method: str, **params) -> PositionSizer:
        """
        Create a position sizer.
        
        Args:
            method: Position sizing method
            **params: Position sizing parameters
            
        Returns:
            PositionSizer: Position sizer instance
        """
        sizers = {
            'fixed': FixedSizer,
            'percent_equity': PercentEquitySizer,
            'percent_risk': PercentRiskSizer,
            'kelly': KellySizer,
            'volatility': VolatilitySizer
        }
        
        if method in sizers:
            return sizers[method](**params)
        else:
            logger.warning(f"Unknown position sizing method: {method}, using fixed sizer")
            return FixedSizer(**params)
    
    @staticmethod
    def create_default() -> PositionSizer:
        """
        Create a default position sizer (fixed size).
        
        Returns:
            PositionSizer: Position sizer instance
        """
        return FixedSizer(size=100)