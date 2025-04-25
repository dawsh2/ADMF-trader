"""
Standard risk manager implementation.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple, Union

from core.events.event_types import EventType
from core.events.event_utils import create_order_event

from .risk_manager_base import RiskManagerBase
from .sizing import PositionSizer, PositionSizerFactory
from .limits import LimitManager, LimitManagerFactory
from .validation import OrderValidator, OrderModifier

logger = logging.getLogger(__name__)

class StandardRiskManager(RiskManagerBase):
    """
    Standard risk manager with fixed or percentage-based sizing.
    
    This risk manager supports:
    - Multiple position sizing methods
    - Risk limits
    - Order validation
    - Drawdown-based risk adjustment
    """
    
    def __init__(self, event_bus, portfolio_manager, 
                position_sizer=None, limit_manager=None, name=None):
        """
        Initialize risk manager.
        
        Args:
            event_bus: Event bus for communication
            portfolio_manager: Portfolio for position information
            position_sizer: Optional position sizer
            limit_manager: Optional limit manager
            name: Optional risk manager name
        """
        super().__init__(event_bus, portfolio_manager, name)
        
        # Create components if not provided
        self.position_sizer = position_sizer or PositionSizerFactory.create_default()
        self.limit_manager = limit_manager or LimitManagerFactory.create_default_manager()
        
        # Create validator and modifier
        self.validator = OrderValidator(portfolio_manager, self.limit_manager)
        self.modifier = OrderModifier(portfolio_manager, self.limit_manager)
        
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
                'enabled': True  # Whether to try modifying invalid orders
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
            if section in self.config:
                if isinstance(section_config, dict):
                    self.config[section].update(section_config)
                else:
                    self.config[section] = section_config
        
        # Configure position sizer if present in config
        if 'position_sizing' in config_dict:
            self.position_sizer.configure(config_dict['position_sizing'])
        
        # Configure limit manager if present in config
        if 'limits' in config_dict:
            self.limit_manager.configure(config_dict['limits'])
        
        # Configure validator and modifier
        self.validator.configure(config_dict.get('validation', {}))
        self.modifier.configure(config_dict.get('modification', {}))
        
        logger.info(f"Configured standard risk manager: {self.name}")
    
    def on_signal(self, signal_event):
        """
        Handle signal events and create orders.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            Order event or None
        """
        # Track the event
        self.event_tracker.track_event(signal_event)
        
        # Check if risk manager is active
        if not self.risk_state['active']:
            logger.info(f"Risk manager {self.name} is inactive, ignoring signal")
            return None
        
        # Extract signal details
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        timestamp = signal_event.get_timestamp()
        confidence = signal_event.data.get('confidence', 1.0)
        
        # Determine direction from signal
        if signal_value > 0:
            direction = 'BUY'
        elif signal_value < 0:
            direction = 'SELL'
        else:
            # Neutral signal, no action
            return None
        
        # Collect context for position sizing
        context = {
            'signal_confidence': confidence,
            'signal_metadata': signal_event.data.get('metadata', {})
        }
        
        # Apply drawdown control if enabled
        if self.config['drawdown_control']['enabled']:
            self._apply_drawdown_control()
            
            # Check if we've hit the cutoff
            if not self.risk_state['active']:
                logger.warning(f"Trading stopped due to excessive drawdown")
                return None
            
            # Apply drawdown adjustment to context
            context['size_adjustment'] = self.risk_state['drawdown_adjustment']
        
        # Calculate position size
        size = self.position_sizer.calculate_position_size(
            symbol=symbol,
            direction=direction, 
            price=price,
            portfolio=self.portfolio_manager,
            context=context
        )
        
        # Skip if size is zero
        if size == 0:
            logger.info(f"Signal for {symbol} resulted in zero size, skipping")
            return None
        
        # Create order event
        order = create_order_event(
            symbol=symbol,
            order_type='MARKET',  # Default to market orders
            direction=direction,
            quantity=abs(size),  # Quantity is always positive
            price=price,
            timestamp=timestamp
        )
        
        # Validate order against risk limits
        is_valid, reason = self.validator.validate_order(order)
        
        if not is_valid:
            logger.warning(f"Order validation failed: {reason}")
            
            if self.config['order_modification']['enabled']:
                # Try to modify order to make it valid
                modified_order = self.modifier.modify_order(order)
                
                if modified_order:
                    logger.info(f"Order modified to comply with risk limits")
                    self.risk_state['modified_orders'] += 1
                    order = modified_order
                else:
                    logger.warning(f"Order couldn't be modified to comply with risk limits")
                    self.risk_state['rejected_orders'] += 1
                    return None
            else:
                self.risk_state['rejected_orders'] += 1
                return None
        
        # Emit order event
        if self.event_bus:
            self.event_bus.emit(order)
            logger.info(f"Emitted order: {direction} {abs(size)} {symbol} @ {price:.2f}")
        
        return order
    
    def _apply_drawdown_control(self):
        """Apply drawdown-based risk control."""
        # Get equity curve from portfolio
        equity_curve = self.portfolio_manager.get_equity_curve_df()
        
        if equity_curve.empty:
            return  # No data to calculate drawdown
        
        # Calculate drawdown
        peak_equity = equity_curve['equity'].max()
        current_equity = self.portfolio_manager.equity
        
        if peak_equity == 0:
            return  # Avoid division by zero
        
        current_drawdown = (peak_equity - current_equity) / peak_equity
        
        # Get drawdown control parameters
        threshold = self.config['drawdown_control']['threshold']
        reduction = self.config['drawdown_control']['reduction']
        cutoff = self.config['drawdown_control']['cutoff']
        
        # Apply drawdown control
        if current_drawdown >= cutoff:
            # Stop trading completely
            self.risk_state['active'] = False
            self.risk_state['drawdown_adjustment'] = 0.0
            logger.warning(f"Trading stopped: drawdown of {current_drawdown:.2%} exceeds cutoff of {cutoff:.2%}")
        elif current_drawdown >= threshold:
            # Reduce position size
            self.risk_state['active'] = True
            # Linear interpolation between 1.0 and reduction based on drawdown
            factor = 1.0 - ((current_drawdown - threshold) / (cutoff - threshold)) * (1.0 - reduction)
            self.risk_state['drawdown_adjustment'] = max(reduction, factor)
            logger.info(f"Position size reduced to {self.risk_state['drawdown_adjustment']:.2%} due to drawdown")
        else:
            # Normal trading
            self.risk_state['active'] = True
            self.risk_state['drawdown_adjustment'] = 1.0
    
    def size_position(self, signal_event):
        """
        Calculate position size for a signal.
        
        Args:
            signal_event: Signal event to size
            
        Returns:
            int: Position size (positive or negative)
        """
        # Extract signal details
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        confidence = signal_event.data.get('confidence', 1.0)
        
        # Determine direction from signal
        direction = 'BUY' if signal_value > 0 else 'SELL' if signal_value < 0 else None
        
        if not direction:
            return 0  # Neutral signal
        
        # Context for position sizing
        context = {
            'signal_confidence': confidence,
            'signal_metadata': signal_event.data.get('metadata', {})
        }
        
        # Apply drawdown adjustment if active
        if self.config['drawdown_control']['enabled']:
            context['size_adjustment'] = self.risk_state['drawdown_adjustment']
        
        # Calculate size using position sizer
        size = self.position_sizer.calculate_position_size(
            symbol=symbol,
            direction=direction,
            price=price,
            portfolio=self.portfolio_manager,
            context=context
        )
        
        return size
    
    def get_risk_state(self):
        """
        Get current risk state.
        
        Returns:
            Dict: Risk state
        """
        return dict(self.risk_state)
    
    def set_risk_state(self, state_key, value):
        """
        Set risk state parameter.
        
        Args:
            state_key: State parameter key
            value: New value
        """
        if state_key in self.risk_state:
            self.risk_state[state_key] = value
    
    def get_parameters(self):
        """
        Get current parameter values.
        
        Returns:
            Dict: Parameter values
        """
        return {
            'config': dict(self.config),
            'position_sizer': self.position_sizer.get_parameters(),
            'risk_state': self.get_risk_state()
        }
    
    def set_parameters(self, params):
        """
        Set parameters.
        
        Args:
            params: Parameter dictionary
        """
        if 'config' in params:
            for section, section_config in params['config'].items():
                if section in self.config:
                    if isinstance(section_config, dict):
                        self.config[section].update(section_config)
                    else:
                        self.config[section] = section_config
        
        if 'position_sizer' in params:
            self.position_sizer.set_parameters(params['position_sizer'])
            
        if 'risk_state' in params:
            for key, value in params['risk_state'].items():
                self.set_risk_state(key, value)
    
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
    
    def to_dict(self):
        """
        Convert to dictionary.
        
        Returns:
            Dict: Dictionary representation
        """
        return {
            'name': self.name,
            'config': dict(self.config),
            'position_sizer': self.position_sizer.to_dict(),
            'risk_state': self.get_risk_state(),
            'stats': self.get_stats()
        }


# Factory for creating risk managers
class StandardRiskManagerFactory:
    """Factory for creating standard risk managers."""
    
    @staticmethod
    def create(event_bus, portfolio_manager, config=None):
        """
        Create a standard risk manager.
        
        Args:
            event_bus: Event bus
            portfolio_manager: Portfolio manager
            config: Optional configuration
            
        Returns:
            StandardRiskManager: Risk manager instance
        """
        # Create position sizer
        position_sizer = None
        if config and 'position_sizing' in config:
            position_sizer = PositionSizerFactory.create(config=config['position_sizing'])
        else:
            position_sizer = PositionSizerFactory.create('fixed')
        
        # Create limit manager
        limit_manager = None
        if config and 'limits' in config:
            limit_manager = LimitManagerFactory.create_from_config(config['limits'])
        else:
            limit_manager = LimitManagerFactory.create_default_manager()
        
        # Create risk manager
        risk_manager = StandardRiskManager(
            event_bus=event_bus,
            portfolio_manager=portfolio_manager,
            position_sizer=position_sizer,
            limit_manager=limit_manager
        )
        
        # Configure if config provided
        if config:
            risk_manager.configure(config)
            
        return risk_manager
