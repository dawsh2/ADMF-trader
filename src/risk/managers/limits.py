"""
Trading limits and risk constraints for order validation.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from abc import ABC, abstractmethod

from core.events.utils import ObjectRegistry

logger = logging.getLogger(__name__)

class LimitBase(ABC):
    """Base class for trading limits."""
    
    def __init__(self, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize trading limit.
        
        Args:
            name: Limit name
            params: Limit parameters
        """
        self._name = name or self.__class__.__name__
        self.params = params or {}
        self.configured = False
    
    @abstractmethod
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate an order against this limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        pass
    
    def configure(self, config):
        """
        Configure the limit.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        self.params.update(config_dict)
        self.configured = True
    
    @property
    def name(self):
        """Get limit name."""
        return self._name


@ObjectRegistry.register
class MaxPositionSizeLimit(LimitBase):
    """Limit on maximum position size for a single instrument."""
    
    def __init__(self, max_quantity: int = 1000, name: str = None):
        """
        Initialize maximum position size limit.
        
        Args:
            max_quantity: Maximum position size
            name: Limit name
        """
        super().__init__(name=name, params={'max_quantity': max_quantity})
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum position size limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_quantity = self.params.get('max_quantity', 1000)
        
        # Get the current position
        symbol = order.get_symbol()
        direction = order.get_direction()
        order_quantity = order.get_quantity()
        
        position = portfolio.get_position(symbol)
        current_quantity = position.quantity if position else 0
        
        # Calculate resulting position size
        if direction == 'BUY':
            resulting_quantity = current_quantity + order_quantity
        else:  # SELL
            resulting_quantity = current_quantity - order_quantity
        
        # Check if resulting position exceeds limit
        if abs(resulting_quantity) > max_quantity:
            return False, f"Position size of {abs(resulting_quantity)} exceeds maximum of {max_quantity}"
        
        return True, ""


@ObjectRegistry.register
class MaxExposureLimit(LimitBase):
    """Limit on maximum portfolio exposure."""
    
    def __init__(self, max_exposure: float = 1.0, name: str = None):
        """
        Initialize maximum exposure limit.
        
        Args:
            max_exposure: Maximum exposure as fraction of equity (1.0 = 100%)
            name: Limit name
        """
        super().__init__(name=name, params={'max_exposure': max_exposure})
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum exposure limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_exposure = self.params.get('max_exposure', 1.0)
        
        # Get order details
        symbol = order.get_symbol()
        direction = order.get_direction()
        order_quantity = order.get_quantity()
        order_price = order.get_price()
        
        # Calculate order value
        order_value = order_quantity * order_price
        
        # Get current portfolio state
        current_exposure = 0
        for pos in portfolio.positions.values():
            current_exposure += abs(pos.market_value)
        
        # Calculate current exposure ratio
        current_exposure_ratio = current_exposure / portfolio.equity if portfolio.equity > 0 else 0
        
        # Calculate new exposure if order is executed
        new_order_exposure = 0
        if direction == 'BUY':
            new_order_exposure = order_value
        elif direction == 'SELL':
            # Check if this is a position reduction
            position = portfolio.get_position(symbol)
            if position and position.quantity > 0:
                # This is closing or reducing a long position
                reduction_amount = min(position.quantity, order_quantity)
                new_order_exposure = -reduction_amount * order_price
                
                # If we're selling more than we own, the remainder is a new short position
                new_short_quantity = order_quantity - reduction_amount
                if new_short_quantity > 0:
                    new_order_exposure += new_short_quantity * order_price
            else:
                # This is opening or increasing a short position
                new_order_exposure = order_value
        
        # Calculate new exposure ratio
        new_exposure = current_exposure + abs(new_order_exposure)
        new_exposure_ratio = new_exposure / portfolio.equity if portfolio.equity > 0 else float('inf')
        
        # Check if new exposure exceeds limit
        if new_exposure_ratio > max_exposure:
            return False, f"Exposure of {new_exposure_ratio:.2f} exceeds maximum of {max_exposure:.2f}"
        
        return True, ""


@ObjectRegistry.register
class MaxDrawdownLimit(LimitBase):
    """Limit trading when drawdown exceeds threshold."""
    
    def __init__(self, max_drawdown: float = 0.10, name: str = None):
        """
        Initialize maximum drawdown limit.
        
        Args:
            max_drawdown: Maximum allowable drawdown as fraction of equity (0.10 = 10%)
            name: Limit name
        """
        super().__init__(name=name, params={'max_drawdown': max_drawdown})
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum drawdown limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_drawdown = self.params.get('max_drawdown', 0.10)
        
        # Get equity curve
        equity_curve = portfolio.get_equity_curve_df()
        
        if equity_curve.empty:
            return True, ""  # No equity history, can't calculate drawdown
        
        # Calculate current drawdown
        current_equity = portfolio.equity
        peak_equity = equity_curve['equity'].max()
        
        if peak_equity == 0:
            return True, ""  # Avoid division by zero
            
        current_drawdown = (peak_equity - current_equity) / peak_equity
        
        # Check if current drawdown exceeds limit
        if current_drawdown > max_drawdown:
            return False, f"Current drawdown of {current_drawdown:.2%} exceeds maximum of {max_drawdown:.2%}"
        
        return True, ""


@ObjectRegistry.register
class MaxLossLimit(LimitBase):
    """Limit trading when loss exceeds threshold."""
    
    def __init__(self, max_loss: float = 1000.0, name: str = None):
        """
        Initialize maximum loss limit.
        
        Args:
            max_loss: Maximum allowable loss in account currency
            name: Limit name
        """
        super().__init__(name=name, params={'max_loss': max_loss})
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum loss limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_loss = self.params.get('max_loss', 1000.0)
        
        # Calculate total P&L
        total_pnl = portfolio.equity - portfolio.initial_cash
        
        # Check if loss exceeds limit
        if total_pnl < -max_loss:
            return False, f"Current loss of ${-total_pnl:.2f} exceeds maximum of ${max_loss:.2f}"
        
        return True, ""


@ObjectRegistry.register
class MaxPositionsLimit(LimitBase):
    """Limit on maximum number of open positions."""
    
    def __init__(self, max_positions: int = 10, name: str = None):
        """
        Initialize maximum positions limit.
        
        Args:
            max_positions: Maximum number of open positions
            name: Limit name
        """
        super().__init__(name=name, params={'max_positions': max_positions})
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum positions limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_positions = self.params.get('max_positions', 10)
        
        # Get order details
        symbol = order.get_symbol()
        direction = order.get_direction()
        
        # Count current open positions
        open_positions = sum(1 for pos in portfolio.positions.values() if pos.quantity != 0)
        
        # Check if this is a new position
        position = portfolio.get_position(symbol)
        is_new_position = position is None or position.quantity == 0
        will_close_position = position is not None and ((position.quantity > 0 and direction == 'SELL') or 
                                                       (position.quantity < 0 and direction == 'BUY'))
        
        # Calculate resulting number of positions
        if is_new_position:
            resulting_positions = open_positions + 1
        elif will_close_position:
            resulting_positions = open_positions - 1
        else:
            resulting_positions = open_positions
        
        # Check if resulting number of positions exceeds limit
        if resulting_positions > max_positions:
            return False, f"Number of positions ({resulting_positions}) exceeds maximum of {max_positions}"
        
        return True, ""


class LimitManager:
    """Manager for applying multiple risk limits."""
    
    def __init__(self, limits: List[LimitBase] = None):
        """
        Initialize limit manager.
        
        Args:
            limits: List of limit objects
        """
        self.limits = limits or []
        self.configured = False
    
    def configure(self, config):
        """
        Configure the limit manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        # Configure each limit if it has matching config section
        for limit in self.limits:
            limit_name = limit.name.lower()
            if limit_name in config_dict:
                limit.configure(config_dict[limit_name])
        
        self.configured = True
    
    def add_limit(self, limit: LimitBase):
        """
        Add a limit to the manager.
        
        Args:
            limit: Limit object to add
        """
        self.limits.append(limit)
    
    def remove_limit(self, limit_name: str):
        """
        Remove a limit by name.
        
        Args:
            limit_name: Name of limit to remove
        """
        self.limits = [limit for limit in self.limits if limit.name != limit_name]
    
    def validate_order(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate an order against all limits.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, first_failure_reason)
        """
        for limit in self.limits:
            is_valid, reason = limit.validate(order, portfolio)
            if not is_valid:
                return False, reason
        
        return True, ""


# Factory for creating limit managers with standard limits
class LimitManagerFactory:
    """Factory for creating limit managers."""
    
    @staticmethod
    def create_default_manager(config=None):
        """
        Create a limit manager with default limits.
        
        Args:
            config: Optional configuration
            
        Returns:
            LimitManager: Limit manager instance
        """
        # Create standard limits
        limits = [
            MaxPositionSizeLimit(),
            MaxExposureLimit(),
            MaxDrawdownLimit(),
            MaxLossLimit(),
            MaxPositionsLimit()
        ]
        
        # Create manager
        manager = LimitManager(limits)
        
        # Configure if config provided
        if config:
            manager.configure(config)
            
        return manager
    
    @staticmethod
    def create_from_config(config):
        """
        Create a limit manager from configuration.
        
        Args:
            config: Configuration
            
        Returns:
            LimitManager: Limit manager instance
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        limits = []
        
        # Create limits based on configuration
        for limit_name, limit_config in config_dict.items():
            if limit_name == 'max_position_size':
                limits.append(MaxPositionSizeLimit(limit_config.get('value', 1000)))
            elif limit_name == 'max_exposure':
                limits.append(MaxExposureLimit(limit_config.get('value', 1.0)))
            elif limit_name == 'max_drawdown':
                limits.append(MaxDrawdownLimit(limit_config.get('value', 0.10)))
            elif limit_name == 'max_loss':
                limits.append(MaxLossLimit(limit_config.get('value', 1000.0)))
            elif limit_name == 'max_positions':
                limits.append(MaxPositionsLimit(limit_config.get('value', 10)))
        
        # Create manager
        manager = LimitManager(limits)
        manager.configured = True
        
        return manager
