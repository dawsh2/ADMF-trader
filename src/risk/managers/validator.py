"""
Order validation utilities for risk management.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple, Union

logger = logging.getLogger(__name__)

class OrderValidator:
    """Validator for trade orders."""
    
    def __init__(self, portfolio_manager, limit_manager=None):
        """
        Initialize order validator.
        
        Args:
            portfolio_manager: Portfolio manager instance
            limit_manager: Optional limit manager
        """
        self.portfolio = portfolio_manager
        self.limit_manager = limit_manager
        self.configured = False
    
    def configure(self, config):
        """
        Configure the validator.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        # Nothing to configure at this level currently
        self.configured = True
    
    def validate_order(self, order) -> Tuple[bool, str]:
        """
        Validate an order.
        
        Args:
            order: Order to validate
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        # Basic validation
        is_valid, reason = self._validate_basic(order)
        if not is_valid:
            return False, reason
        
        # Margin validation
        is_valid, reason = self._validate_margin(order)
        if not is_valid:
            return False, reason
        
        # Limits validation
        if self.limit_manager:
            is_valid, reason = self.limit_manager.validate_order(order, self.portfolio)
            if not is_valid:
                return False, reason
        
        return True, ""
    
    def _validate_basic(self, order) -> Tuple[bool, str]:
        """
        Perform basic order validation.
        
        Args:
            order: Order to validate
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        # Validate order direction
        direction = order.get_direction()
        if direction not in ['BUY', 'SELL']:
            return False, f"Invalid order direction: {direction}"
        
        # Validate order quantity
        quantity = order.get_quantity()
        if quantity <= 0:
            return False, f"Invalid order quantity: {quantity}"
        
        # Validate order type
        order_type = order.get_order_type()
        if order_type not in ['MARKET', 'LIMIT', 'STOP']:
            return False, f"Invalid order type: {order_type}"
        
        # Validate price for limit and stop orders
        if order_type in ['LIMIT', 'STOP']:
            price = order.get_price()
            if not price or price <= 0:
                return False, f"Invalid {order_type} price: {price}"
        
        return True, ""
    
    def _validate_margin(self, order) -> Tuple[bool, str]:
        """
        Validate order against available margin/cash.
        
        Args:
            order: Order to validate
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        # Only validate buy orders for cash
        direction = order.get_direction()
        if direction != 'BUY':
            return True, ""
        
        # Calculate order value
        symbol = order.get_symbol()
        quantity = order.get_quantity()
        price = order.get_price()
        
        # If no price provided (market order), use last price
        if not price:
            position = self.portfolio.get_position(symbol)
            if position:
                price = position.current_price
            else:
                # Can't validate without price
                return True, ""
        
        order_value = quantity * price
        
        # Check if enough cash is available
        if order_value > self.portfolio.cash:
            return False, f"Insufficient cash: need ${order_value:.2f}, have ${self.portfolio.cash:.2f}"
        
        return True, ""


class OrderModifier:
    """Modifier for adjusting orders to comply with risk limits."""
    
    def __init__(self, portfolio_manager, limit_manager=None):
        """
        Initialize order modifier.
        
        Args:
            portfolio_manager: Portfolio manager instance
            limit_manager: Optional limit manager
        """
        self.portfolio = portfolio_manager
        self.limit_manager = limit_manager
        self.validator = OrderValidator(portfolio_manager, limit_manager)
        self.configured = False
    
    def configure(self, config):
        """
        Configure the modifier.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        # Configure validator
        self.validator.configure(config)
        self.configured = True
    
    def modify_order(self, order):
        """
        Modify an order to comply with risk limits.
        
        Args:
            order: Order to modify
            
        Returns:
            Modified order or None if order cannot be made valid
        """
        # Check if order is already valid
        is_valid, reason = self.validator.validate_order(order)
        if is_valid:
            return order
        
        # Try to adjust order quantity for margin/cash constraints
        symbol = order.get_symbol()
        direction = order.get_direction()
        quantity = order.get_quantity()
        price = order.get_price()
        order_type = order.get_order_type()
        
        # If it's a buy order limited by cash
        if direction == 'BUY' and "Insufficient cash" in reason:
            # Calculate maximum affordable quantity
            max_quantity = int(self.portfolio.cash / price) if price > 0 else 0
            
            if max_quantity > 0:
                # Create new order with adjusted quantity
                from core.events.event_utils import create_order_event
                modified_order = create_order_event(
                    symbol=symbol,
                    order_type=order_type,
                    direction=direction,
                    quantity=max_quantity,
                    price=price,
                    timestamp=order.get_timestamp()
                )
                
                logger.info(f"Modified order: reduced quantity from {quantity} to {max_quantity}")
                
                # Validate the modified order
                is_valid, new_reason = self.validator.validate_order(modified_order)
                if is_valid:
                    return modified_order
                else:
                    logger.warning(f"Modified order still invalid: {new_reason}")
        
        # If no modifications worked, return None
        return None
