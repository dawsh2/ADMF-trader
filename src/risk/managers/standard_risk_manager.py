"""
Standard risk manager implementation.

This module provides a standard risk manager that implements common risk management
strategies including position sizing, risk limits, and order generation.
"""
import logging
from typing import Dict, Any, List, Optional, Union, Tuple

from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType
from src.risk.managers.risk_manager_base import RiskManagerBase
from src.risk.sizing.position_sizer import PositionSizerFactory
from src.risk.limits.risk_limits import LimitManagerFactory

logger = logging.getLogger(__name__)

class StandardRiskManager(RiskManagerBase):
    """
    Standard risk manager with comprehensive risk controls.
    
    Features:
    - Multiple position sizing methods
    - Risk limits and constraints
    - Drawdown-based risk adjustment
    - Order validation and modification
    """
    
    def __init__(self, portfolio_manager, event_bus=None, 
               position_sizer=None, limit_manager=None, name=None):
        """
        Initialize standard risk manager.
        
        Args:
            portfolio_manager: Portfolio manager instance
            event_bus: Optional event bus for communication
            position_sizer: Optional position sizer
            limit_manager: Optional limit manager
            name: Optional risk manager name
        """
        super().__init__(portfolio_manager, event_bus, name)
        
        # Create components if not provided
        self.position_sizer = position_sizer or PositionSizerFactory.create_default()
        self.limit_manager = limit_manager or LimitManagerFactory.create_default()
        
        # Risk state tracking
        self.risk_state = {
            'active': True,  # Whether risk manager is active
            'drawdown_adjustment': 1.0,  # Adjustment factor based on drawdown
            'rejected_orders': 0,  # Count of rejected orders
            'modified_orders': 0,  # Count of modified orders
        }
        
        # Configuration defaults
        self.config = {
            'drawdown_control': {
                'enabled': False,
                'threshold': 0.05,  # 5% drawdown threshold
                'reduction': 0.5,  # 50% size reduction
                'cutoff': 0.20,  # 20% drawdown stops trading
            },
            'order_modification': {
                'enabled': True,  # Whether to try modifying invalid orders
                'max_reduction': 0.75  # Maximum reduction in order size (75%)
            }
        }
    
    def configure(self, config):
        """
        Configure the risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        super().configure(config)
        
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        # Update configuration
        for section, section_config in config_dict.items():
            if section in self.config and isinstance(section_config, dict):
                self.config[section].update(section_config)
            elif section in self.config:
                self.config[section] = section_config
        
        # Configure position sizer if present in config
        if 'position_sizing' in config_dict:
            self.position_sizer.configure(config_dict['position_sizing'])
        
        # Configure limit manager if present in config
        if 'limits' in config_dict:
            self.limit_manager.configure(config_dict['limits'])
        
        logger.info(f"Configured standard risk manager: {self.name}")
    
    def on_signal(self, signal_event):
        """
        Process a signal event and generate an order if appropriate.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            Generated order event or None
        """
        # Update statistics
        self.stats['signals_processed'] += 1
        
        # Check if risk manager is active
        if not self.risk_state['active']:
            logger.info(f"Risk manager {self.name} is inactive, ignoring signal")
            self.stats['signals_filtered'] += 1
            return None
        
        # Extract signal information
        symbol = signal_event.data.get('symbol')
        direction = signal_event.data.get('direction')
        price = signal_event.data.get('price', 0.0)
        
        # Skip signals with invalid parameters
        if not symbol or not direction:
            logger.warning(f"Signal missing required parameters: symbol={symbol}, direction={direction}")
            self.stats['signals_filtered'] += 1
            return None
        
        # Apply drawdown control if enabled
        if self.config['drawdown_control']['enabled']:
            self._apply_drawdown_control()
            
            # Check if trading is suspended due to drawdown
            if not self.risk_state['active']:
                logger.warning(f"Trading suspended due to excessive drawdown")
                self.stats['signals_filtered'] += 1
                return None
        
        # Size the position
        quantity = self.size_position(signal_event)
        
        # Skip if quantity is zero
        if quantity == 0:
            logger.info(f"Signal for {symbol} resulted in zero quantity, skipping")
            self.stats['signals_filtered'] += 1
            return None
        
        # Create order data
        order_data = {
            'symbol': symbol,
            'direction': direction,
            'quantity': abs(quantity),  # Ensure quantity is positive
            'price': price,
            'order_type': 'MARKET',  # Default to market order
            'rule_id': signal_event.data.get('rule_id'),
            'timestamp': signal_event.timestamp if hasattr(signal_event, 'timestamp') else None
        }
        
        # Add optional fields if present
        for field in ['stop_price', 'limit_price', 'time_in_force', 'account_id']:
            if field in signal_event.data:
                order_data[field] = signal_event.data[field]
        
        # Create order event
        order_event = Event(
            EventType.ORDER,
            order_data
        )
        
        # Validate order against risk limits
        is_valid, reason = self.limit_manager.validate_order(order_event, self.portfolio_manager)
        
        if not is_valid:
            logger.warning(f"Order validation failed: {reason}")
            
            if self.config['order_modification']['enabled']:
                # Try to modify order to comply with limits
                modified_order = self._modify_order(order_event, reason)
                
                if modified_order:
                    logger.info(f"Order modified to comply with risk limits")
                    self.risk_state['modified_orders'] += 1
                    order_event = modified_order
                else:
                    logger.warning(f"Order couldn't be modified to comply with risk limits")
                    self.risk_state['rejected_orders'] += 1
                    self.stats['signals_filtered'] += 1
                    return None
            else:
                # Reject order
                self.risk_state['rejected_orders'] += 1
                self.stats['signals_filtered'] += 1
                return None
        
        # Emit order event
        if self.event_bus:
            self.event_bus.publish(order_event)
            self.stats['orders_generated'] += 1
            logger.info(f"Generated order: {direction} {order_data['quantity']} {symbol} @ {price:.2f}")
        
        return order_event
    
    def size_position(self, signal_event):
        """
        Calculate position size for a signal.
        
        Args:
            signal_event: Signal event to size
            
        Returns:
            float: Calculated position size
        """
        # Extract signal information
        symbol = signal_event.data.get('symbol')
        direction = signal_event.data.get('direction')
        price = signal_event.data.get('price', 0.0)
        
        # Skip signals with invalid parameters
        if not symbol or not direction or price <= 0:
            logger.warning(f"Cannot size position with invalid parameters: symbol={symbol}, direction={direction}, price={price}")
            return 0
        
        # Prepare context for position sizer
        context = {
            'signal_metadata': signal_event.data.get('metadata', {}),
            'confidence': signal_event.data.get('confidence', 1.0)
        }
        
        # Add drawdown adjustment if applicable
        if self.config['drawdown_control']['enabled']:
            context['size_adjustment'] = self.risk_state['drawdown_adjustment']
        
        # Calculate position size
        size = self.position_sizer.calculate_position_size(
            symbol=symbol,
            direction=direction,
            price=price,
            portfolio=self.portfolio_manager,
            context=context
        )
        
        return size
    
    def evaluate_trade(self, symbol, direction, quantity, price):
        """
        Evaluate if a trade complies with risk rules.
        
        Args:
            symbol: Instrument symbol
            direction: Trade direction
            quantity: Trade quantity
            price: Trade price
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        # Create mock order for validation
        order_data = {
            'symbol': symbol,
            'direction': direction,
            'quantity': abs(quantity),
            'price': price,
            'order_type': 'MARKET'
        }
        
        order_event = Event(
            EventType.ORDER,
            order_data
        )
        
        # Validate against risk limits
        return self.limit_manager.validate_order(order_event, self.portfolio_manager)
    
    def _apply_drawdown_control(self):
        """Apply drawdown-based risk control."""
        # Get current drawdown
        if not hasattr(self.portfolio_manager, 'peak_equity'):
            return  # Can't calculate drawdown without peak equity
        
        current_equity = self.portfolio_manager.equity
        peak_equity = self.portfolio_manager.peak_equity
        
        if peak_equity <= 0:
            return  # Can't calculate drawdown with zero or negative peak
        
        current_drawdown = (peak_equity - current_equity) / peak_equity
        
        # Get configuration parameters
        threshold = self.config['drawdown_control']['threshold']
        reduction = self.config['drawdown_control']['reduction']
        cutoff = self.config['drawdown_control']['cutoff']
        
        # Apply rules
        if current_drawdown >= cutoff:
            # Stop trading
            self.risk_state['active'] = False
            self.risk_state['drawdown_adjustment'] = 0.0
            logger.warning(f"Trading suspended due to drawdown of {current_drawdown:.2%} exceeding cutoff of {cutoff:.2%}")
            
        elif current_drawdown >= threshold:
            # Reduce size
            # Linear reduction between threshold and cutoff
            if cutoff > threshold:
                # Calculate adjustment factor (1.0 at threshold, reduction at cutoff)
                factor = 1.0 - ((current_drawdown - threshold) / (cutoff - threshold)) * (1.0 - reduction)
                factor = max(reduction, min(1.0, factor))  # Clamp to [reduction, 1.0]
            else:
                factor = reduction
                
            self.risk_state['active'] = True
            self.risk_state['drawdown_adjustment'] = factor
            logger.info(f"Position sizing reduced to {factor:.2%} due to drawdown of {current_drawdown:.2%}")
            
        else:
            # Normal trading
            self.risk_state['active'] = True
            self.risk_state['drawdown_adjustment'] = 1.0
    
    def _modify_order(self, order_event, reason):
        """
        Modify an order to comply with risk limits.
        
        Args:
            order_event: Order event to modify
            reason: Validation failure reason
            
        Returns:
            Modified order event or None if modification not possible
        """
        max_reduction = self.config['order_modification']['max_reduction']
        
        # Extract order details
        symbol = order_event.data.get('symbol')
        direction = order_event.data.get('direction')
        quantity = order_event.data.get('quantity')
        price = order_event.data.get('price', 0.0)
        
        # Check reason to determine modification strategy
        if "exposure" in reason.lower():
            # Reduce size to comply with exposure limits
            # Calculate current exposure
            positions = self.portfolio_manager.get_positions_summary()
            current_exposure = sum(abs(float(pos.get('market_value', 0))) for pos in positions)
            
            # Get max exposure limit
            for limit in self.limit_manager.limits:
                if hasattr(limit, 'params') and 'max_exposure' in limit.params:
                    max_exposure = float(limit.params['max_exposure'])
                    break
            else:
                max_exposure = 1.0  # Default if not found
            
            # Calculate maximum additional exposure
            max_additional = (max_exposure * self.portfolio_manager.equity) - current_exposure
            
            if max_additional <= 0:
                # No room for additional exposure
                return None
            
            # Calculate reduced quantity
            if price > 0:
                reduced_quantity = max_additional / price
                reduced_quantity = min(quantity, reduced_quantity)
                
                if reduced_quantity / quantity < (1.0 - max_reduction):
                    # Reduction too large, reject order
                    return None
                
                # Create modified order
                modified_data = order_event.data.copy()
                modified_data['quantity'] = reduced_quantity
                
                return Event(
                    EventType.ORDER,
                    modified_data
                )
            
        elif "position size" in reason.lower():
            # Reduce to maximum allowed position size
            # Extract max position size from reason or use default
            import re
            max_size_match = re.search(r'maximum of (\d+)', reason)
            
            if max_size_match:
                max_size = int(max_size_match.group(1))
            else:
                # Check limit manager for max size
                for limit in self.limit_manager.limits:
                    if hasattr(limit, 'params') and 'max_quantity' in limit.params:
                        max_size = int(limit.params['max_quantity'])
                        break
                else:
                    max_size = int(quantity * 0.75)  # 75% of original size if not found
            
            # Get current position
            position = self.portfolio_manager.get_position(symbol)
            current_quantity = position.quantity if position else 0
            
            # Calculate maximum additional quantity
            if direction == 'BUY':
                max_additional = max_size - current_quantity
            else:  # SELL
                max_additional = max_size + current_quantity
            
            if max_additional <= 0:
                # No room for additional quantity
                return None
            
            # Calculate reduced quantity
            reduced_quantity = min(quantity, max_additional)
            
            if reduced_quantity / quantity < (1.0 - max_reduction):
                # Reduction too large, reject order
                return None
            
            # Create modified order
            modified_data = order_event.data.copy()
            modified_data['quantity'] = reduced_quantity
            
            return Event(
                EventType.ORDER,
                modified_data
            )
            
        # For other reasons, can't modify
        return None
    
    def reset(self):
        """Reset risk manager state."""
        super().reset()
        
        # Reset risk state
        self.risk_state = {
            'active': True,
            'drawdown_adjustment': 1.0,
            'rejected_orders': 0,
            'modified_orders': 0,
        }
        
        logger.info(f"Reset risk manager: {self.name}")
    
    def get_stats(self):
        """
        Get risk manager statistics.
        
        Returns:
            Dict with statistics
        """
        # Get base stats
        stats = super().get_stats()
        
        # Add risk state stats
        stats.update({
            'active': self.risk_state['active'],
            'drawdown_adjustment': self.risk_state['drawdown_adjustment'],
            'rejected_orders': self.risk_state['rejected_orders'],
            'modified_orders': self.risk_state['modified_orders'],
        })
        
        # Add limit usage if available
        if hasattr(self.limit_manager, 'get_limit_usage'):
            stats['limit_usage'] = self.limit_manager.get_limit_usage(self.portfolio_manager)
        
        return stats