"""
Risk limits for order validation and risk management.

This module provides classes for enforcing various risk limits and constraints
on trading operations.
"""
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class RiskLimit(ABC):
    """
    Abstract base class for risk limits.
    
    Risk limits validate orders against risk constraints and can reject or
    modify orders that exceed risk thresholds.
    """
    
    def __init__(self, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize risk limit.
        
        Args:
            name: Risk limit name
            params: Risk limit parameters
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
        Configure the risk limit.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        self.params.update(config_dict)
        self.configured = True
        logger.info(f"Configured risk limit: {self._name}")
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get risk limit parameters.
        
        Returns:
            Dict with parameters
        """
        return dict(self.params)
    
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """
        Set risk limit parameters.
        
        Args:
            params: New parameters
        """
        self.params.update(params)
    
    @property
    def name(self):
        """Get risk limit name."""
        return self._name


class MaxPositionSizeLimit(RiskLimit):
    """
    Maximum position size limit.
    
    Limits the size of a single position to a maximum quantity.
    """
    
    def __init__(self, max_quantity: int = 1000, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize maximum position size limit.
        
        Args:
            max_quantity: Maximum position size
            name: Risk limit name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['max_quantity'] = max_quantity
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum position size limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_quantity = int(self.params.get('max_quantity', 1000))
        
        # Get order details
        symbol = order.get_symbol()
        direction = order.get_direction()
        quantity = order.get_quantity()
        
        # Get current position
        position = portfolio.get_position(symbol)
        current_quantity = position.quantity if position else 0
        
        # Calculate resulting position size
        if direction == 'BUY':
            resulting_quantity = current_quantity + quantity
        else:  # SELL
            resulting_quantity = current_quantity - quantity
        
        # Check if resulting position exceeds limit
        if abs(resulting_quantity) > max_quantity:
            return False, f"Position size of {abs(resulting_quantity)} exceeds maximum of {max_quantity}"
        
        return True, ""


class MaxExposureLimit(RiskLimit):
    """
    Maximum exposure limit.
    
    Limits the total market exposure as a percentage of portfolio equity.
    """
    
    def __init__(self, max_exposure: float = 1.0, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize maximum exposure limit.
        
        Args:
            max_exposure: Maximum exposure ratio (1.0 = 100% of equity)
            name: Risk limit name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['max_exposure'] = max_exposure
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum exposure limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_exposure = float(self.params.get('max_exposure', 1.0))
        
        # Get order details
        symbol = order.get_symbol()
        direction = order.get_direction()
        quantity = order.get_quantity()
        price = order.get_price()
        
        # Calculate order value
        order_value = quantity * price
        
        # Get current portfolio exposure
        positions = portfolio.get_all_positions()
        
        current_exposure = sum(abs(pos.get_market_value()) for pos in positions.values())
        
        # Calculate current exposure ratio
        current_ratio = current_exposure / portfolio.equity if portfolio.equity > 0 else 0
        
        # Calculate additional exposure from this order
        # For existing positions, we need to handle position increases/decreases/flips
        additional_exposure = 0
        position = portfolio.get_position(symbol)
        
        if position:
            current_value = position.get_market_value()
            
            if direction == 'BUY':
                if position.quantity < 0:
                    # Reducing or flipping short position
                    reduction = min(quantity, abs(position.quantity))
                    additional_exposure = (quantity - reduction) * price - abs(current_value)
                else:
                    # Increasing long position
                    additional_exposure = quantity * price
            else:  # SELL
                if position.quantity > 0:
                    # Reducing or flipping long position
                    reduction = min(quantity, position.quantity)
                    additional_exposure = (quantity - reduction) * price - abs(current_value)
                else:
                    # Increasing short position
                    additional_exposure = quantity * price
        else:
            # New position
            additional_exposure = order_value
        
        # Calculate new exposure ratio
        new_exposure = current_exposure + additional_exposure
        new_ratio = new_exposure / portfolio.equity if portfolio.equity > 0 else float('inf')
        
        # Check if new ratio exceeds limit
        if new_ratio > max_exposure:
            return False, f"Exposure ratio of {new_ratio:.2%} exceeds maximum of {max_exposure:.2%}"
        
        return True, ""


class MaxDrawdownLimit(RiskLimit):
    """
    Maximum drawdown limit.
    
    Suspends trading when drawdown exceeds maximum threshold.
    """
    
    def __init__(self, max_drawdown: float = 0.20, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize maximum drawdown limit.
        
        Args:
            max_drawdown: Maximum drawdown before suspending trading (0.20 = 20%)
            name: Risk limit name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['max_drawdown'] = max_drawdown
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum drawdown limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_drawdown = float(self.params.get('max_drawdown', 0.20))
        
        # Calculate current drawdown
        current_equity = portfolio.equity
        peak_equity = portfolio.peak_equity if hasattr(portfolio, 'peak_equity') else current_equity
        
        if peak_equity <= 0:
            return True, ""  # Can't calculate drawdown with zero/negative peak
        
        current_drawdown = (peak_equity - current_equity) / peak_equity
        
        # Check if drawdown exceeds limit
        if current_drawdown > max_drawdown:
            return False, f"Current drawdown of {current_drawdown:.2%} exceeds maximum of {max_drawdown:.2%}"
        
        return True, ""


class MaxLossLimit(RiskLimit):
    """
    Maximum loss limit.
    
    Suspends trading when absolute loss exceeds maximum threshold.
    """
    
    def __init__(self, max_loss: float = 10000.0, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize maximum loss limit.
        
        Args:
            max_loss: Maximum absolute loss before suspending trading
            name: Risk limit name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['max_loss'] = max_loss
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum loss limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_loss = float(self.params.get('max_loss', 10000.0))
        
        # Calculate total loss
        current_equity = portfolio.equity
        initial_equity = portfolio.initial_cash
        
        total_loss = initial_equity - current_equity
        
        # Check if loss exceeds limit
        if total_loss > max_loss:
            return False, f"Current loss of ${total_loss:.2f} exceeds maximum of ${max_loss:.2f}"
        
        return True, ""


class MaxPositionsLimit(RiskLimit):
    """
    Maximum positions limit.
    
    Limits the total number of open positions.
    """
    
    def __init__(self, max_positions: int = 10, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize maximum positions limit.
        
        Args:
            max_positions: Maximum number of open positions
            name: Risk limit name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['max_positions'] = max_positions
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum positions limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_positions = int(self.params.get('max_positions', 10))
        
        # Get order details
        symbol = order.get_symbol()
        
        # Count current open positions
        open_positions = len(portfolio.get_all_positions())
        
        # Check if this is a new position
        position = portfolio.get_position(symbol)
        is_new_position = not position or position.quantity == 0
        
        # Check if new position would exceed limit
        if is_new_position and open_positions >= max_positions:
            return False, f"Maximum number of positions ({max_positions}) already reached"
        
        return True, ""


class MaxDailyLossLimit(RiskLimit):
    """
    Maximum daily loss limit.
    
    Suspends trading when daily loss exceeds maximum threshold.
    """
    
    def __init__(self, max_daily_loss: float = 1000.0, name: str = None, params: Dict[str, Any] = None):
        """
        Initialize maximum daily loss limit.
        
        Args:
            max_daily_loss: Maximum daily loss before suspending trading
            name: Risk limit name
            params: Additional parameters
        """
        super().__init__(name=name, params=params or {})
        self.params['max_daily_loss'] = max_daily_loss
        
        # Track start-of-day equity
        self.start_of_day_equity = None
    
    def validate(self, order, portfolio) -> Tuple[bool, str]:
        """
        Validate order against maximum daily loss limit.
        
        Args:
            order: Order to validate
            portfolio: Portfolio manager instance
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        max_daily_loss = float(self.params.get('max_daily_loss', 1000.0))
        
        # Initialize start-of-day equity if not set
        if self.start_of_day_equity is None:
            self.start_of_day_equity = portfolio.equity
        
        # Calculate daily loss
        current_equity = portfolio.equity
        daily_loss = self.start_of_day_equity - current_equity
        
        # Check if daily loss exceeds limit
        if daily_loss > max_daily_loss:
            return False, f"Daily loss of ${daily_loss:.2f} exceeds maximum of ${max_daily_loss:.2f}"
        
        return True, ""
    
    def reset_day(self, portfolio) -> None:
        """
        Reset daily tracking.
        
        Args:
            portfolio: Portfolio manager instance
        """
        self.start_of_day_equity = portfolio.equity


class LimitManager:
    """
    Manager for multiple risk limits.
    
    Aggregates and applies multiple risk limits to validate orders.
    """
    
    def __init__(self, limits: List[RiskLimit] = None):
        """
        Initialize limit manager.
        
        Args:
            limits: List of risk limits
        """
        self.limits = limits or []
        self.configured = False
    
    def add_limit(self, limit: RiskLimit) -> None:
        """
        Add a risk limit.
        
        Args:
            limit: Risk limit to add
        """
        self.limits.append(limit)
    
    def remove_limit(self, limit_name: str) -> None:
        """
        Remove a risk limit by name.
        
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
            Tuple of (is_valid, reason_if_invalid)
        """
        for limit in self.limits:
            is_valid, reason = limit.validate(order, portfolio)
            if not is_valid:
                return False, reason
        
        return True, ""
    
    def configure(self, config):
        """
        Configure all limits.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        # Configure each limit
        for limit in self.limits:
            if limit.name.lower() in config_dict:
                limit.configure(config_dict[limit.name.lower()])
        
        self.configured = True
        logger.info(f"Configured {len(self.limits)} risk limits")
    
    def get_limit_usage(self, portfolio) -> Dict[str, float]:
        """
        Get current limit usage.
        
        Args:
            portfolio: Portfolio manager instance
            
        Returns:
            Dict mapping limit names to usage ratios
        """
        usage = {}
        
        # Calculate usage for each limit type
        for limit in self.limits:
            if isinstance(limit, MaxExposureLimit):
                # Calculate exposure ratio
                positions = portfolio.get_all_positions()
                exposure = sum(abs(pos.get_market_value()) for pos in positions.values())
                max_exposure = float(limit.params.get('max_exposure', 1.0))
                
                if portfolio.equity > 0:
                    usage[limit.name] = exposure / (portfolio.equity * max_exposure)
                else:
                    usage[limit.name] = 1.0  # Fully used if equity is zero or negative
                    
            elif isinstance(limit, MaxDrawdownLimit):
                # Calculate drawdown ratio
                peak_equity = portfolio.peak_equity if hasattr(portfolio, 'peak_equity') else portfolio.equity
                
                if peak_equity > 0:
                    current_drawdown = (peak_equity - portfolio.equity) / peak_equity
                    max_drawdown = float(limit.params.get('max_drawdown', 0.20))
                    
                    usage[limit.name] = current_drawdown / max_drawdown
                else:
                    usage[limit.name] = 0.0
                    
            elif isinstance(limit, MaxLossLimit):
                # Calculate loss ratio
                initial_equity = portfolio.initial_cash
                total_loss = initial_equity - portfolio.equity
                max_loss = float(limit.params.get('max_loss', 10000.0))
                
                usage[limit.name] = total_loss / max_loss if max_loss > 0 else 0.0
                
            elif isinstance(limit, MaxPositionsLimit):
                # Calculate positions ratio
                open_positions = len(portfolio.get_all_positions())
                max_positions = int(limit.params.get('max_positions', 10))
                
                usage[limit.name] = open_positions / max_positions if max_positions > 0 else 0.0
                
            else:
                # Default to zero usage for unknown limit types
                usage[limit.name] = 0.0
        
        return usage


class LimitManagerFactory:
    """Factory for creating limit managers."""
    
    @staticmethod
    def create_default() -> LimitManager:
        """
        Create a default limit manager.
        
        Returns:
            LimitManager: Limit manager with default limits
        """
        limits = [
            MaxPositionSizeLimit(),
            MaxExposureLimit(),
            MaxDrawdownLimit(),
            MaxLossLimit(),
            MaxPositionsLimit()
        ]
        
        return LimitManager(limits)
    
    @staticmethod
    def create_from_config(config) -> LimitManager:
        """
        Create a limit manager from configuration.
        
        Args:
            config: Configuration dictionary or ConfigSection
            
        Returns:
            LimitManager: Configured limit manager
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        limits = []
        
        # Create limits based on configuration
        for limit_name, limit_config in config_dict.items():
            if limit_name == 'max_position_size':
                if isinstance(limit_config, dict):
                    max_quantity = limit_config.get('value', 1000)
                else:
                    max_quantity = limit_config
                    
                limits.append(MaxPositionSizeLimit(max_quantity=max_quantity))
                
            elif limit_name == 'max_exposure':
                if isinstance(limit_config, dict):
                    max_exposure = limit_config.get('value', 1.0)
                else:
                    max_exposure = limit_config
                    
                limits.append(MaxExposureLimit(max_exposure=max_exposure))
                
            elif limit_name == 'max_drawdown':
                if isinstance(limit_config, dict):
                    max_drawdown = limit_config.get('value', 0.20)
                else:
                    max_drawdown = limit_config
                    
                limits.append(MaxDrawdownLimit(max_drawdown=max_drawdown))
                
            elif limit_name == 'max_loss':
                if isinstance(limit_config, dict):
                    max_loss = limit_config.get('value', 10000.0)
                else:
                    max_loss = limit_config
                    
                limits.append(MaxLossLimit(max_loss=max_loss))
                
            elif limit_name == 'max_positions':
                if isinstance(limit_config, dict):
                    max_positions = limit_config.get('value', 10)
                else:
                    max_positions = limit_config
                    
                limits.append(MaxPositionsLimit(max_positions=max_positions))
                
            elif limit_name == 'max_daily_loss':
                if isinstance(limit_config, dict):
                    max_daily_loss = limit_config.get('value', 1000.0)
                else:
                    max_daily_loss = limit_config
                    
                limits.append(MaxDailyLossLimit(max_daily_loss=max_daily_loss))
        
        # Create limit manager
        manager = LimitManager(limits)
        
        return manager