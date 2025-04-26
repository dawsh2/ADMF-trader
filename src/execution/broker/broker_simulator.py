# src/execution/broker/broker_simulator.py
import logging
import datetime
from typing import Dict, Any, Optional
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_fill_event
from src.execution.broker.broker_base import BrokerBase

logger = logging.getLogger(__name__)

class SimulatedBroker(BrokerBase):
    """Simulated broker for executing orders in backtests."""
    
    def __init__(self, event_bus=None, order_registry=None, name="simulated_broker"):
        """
        Initialize simulated broker.
        
        Args:
            event_bus: Event bus for communication
            order_registry: Order registry for tracking orders
            name: Broker name
        """
        super().__init__(name)
        self.event_bus = event_bus
        self.order_registry = order_registry
        
        # Default parameters
        self.slippage = 0.0  # Percentage slippage
        self.commission = 0.0  # Percentage commission
        
        # Tracking for processed order state events
        self.processed_state_changes = set()
        
        # Register for events if event bus provided
        if self.event_bus:
            self._register_handlers()
    
    def configure(self, config):
        """
        Configure the broker.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        self.slippage = config_dict.get('slippage', 0.0)
        self.commission = config_dict.get('commission', 0.0)
        self.initialized = True
        
        logger.info(f"Broker configured with slippage={self.slippage}, commission={self.commission}")
    
    def set_event_bus(self, event_bus):
        """
        Set the event bus.
        
        Args:
            event_bus: Event bus instance
        """
        self.event_bus = event_bus
        # Register for events
        self._register_handlers()
    
    def set_order_registry(self, order_registry):
        """
        Set the order registry.
        
        Args:
            order_registry: Order registry instance
        """
        self.order_registry = order_registry
    
    def _register_handlers(self):
        """Register for events."""
        if not self.event_bus:
            return
            
        # No longer register for ORDER events directly
        # Instead, listen for PORTFOLIO events which include state changes
        self.event_bus.register(EventType.PORTFOLIO, self.on_portfolio_update)
    
    def on_portfolio_update(self, event):
        """
        Handle portfolio update events, looking for order state changes.
        
        Args:
            event: Portfolio event to process
        """
        # Skip if not an order state change event
        if not (hasattr(event, 'data') and 
                isinstance(event.data, dict) and 
                event.data.get('order_state_change')):
            return
        
        # Extract state change details
        order_id = event.data.get('order_id')
        transition = event.data.get('transition')
        
        # Generate a unique ID for this state change to prevent duplicate processing
        state_change_id = f"{order_id}_{transition}"
        
        # Skip if already processed
        if state_change_id in self.processed_state_changes:
            return
            
        self.processed_state_changes.add(state_change_id)
        
        # Only process orders that have just transitioned to PENDING
        if transition == "REGISTERED" or "-> PENDING" in transition:
            # Get order from registry
            if not self.order_registry:
                logger.warning("No order registry available")
                return
                
            order = self.order_registry.get_order(order_id)
            if order:
                # Process the order
                self._process_order(order)
                
    def _process_order(self, order):
        """
        Process an order from the registry.
        
        Args:
            order: Order to process
        """
        if not order or not order.is_active():
            return
            
        try:
            self.stats['orders_processed'] += 1
            
            # Extract order details
            symbol = order.symbol
            direction = order.direction
            quantity = order.quantity
            price = order.price
            order_id = order.order_id
            
            # Apply slippage to price
            if direction == 'BUY':
                fill_price = price * (1.0 + self.slippage)
            else:  # SELL
                fill_price = price * (1.0 - self.slippage)
                
            # Calculate commission
            commission = abs(quantity * fill_price) * self.commission
            
            # Create fill event with explicit order_id
            fill_event = create_fill_event(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                price=fill_price,
                commission=commission,
                timestamp=datetime.datetime.now(),
                order_id=order_id
            )
            
            self.stats['fills_generated'] += 1
            logger.info(f"Broker processed order: {direction} {quantity} {symbol} @ {fill_price:.2f}")
            logger.debug(f"Fill event created with order_id: {order_id}")
            
            # Emit fill event
            if self.event_bus:
                self.event_bus.emit(fill_event)
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error processing order: {e}", exc_info=True)
    
    def process_order(self, order_event):
        """
        Legacy method for compatibility.
        
        Args:
            order_event: Order event to process
            
        Returns:
            Fill event or None
        """
        logger.warning("Using legacy process_order method - should use order registry instead")
        self.stats['orders_processed'] += 1

        try:
            # Extract order details
            symbol = order_event.get_symbol()
            direction = order_event.get_direction()
            quantity = order_event.get_quantity()
            price = order_event.get_price()

            # Extract order ID from the event data
            order_id = None
            if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
                order_id = order_event.data.get('order_id')

            # Apply slippage to price
            if direction == 'BUY':
                fill_price = price * (1.0 + self.slippage)
            else:  # SELL
                fill_price = price * (1.0 - self.slippage)

            # Calculate commission
            commission = abs(quantity * fill_price) * self.commission

            # Create fill event with explicit order_id
            fill_event = create_fill_event(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                price=fill_price,
                commission=commission,
                timestamp=order_event.get_timestamp(),
                order_id=order_id
            )

            self.stats['fills_generated'] += 1
            logger.info(f"Broker processed order: {direction} {quantity} {symbol} @ {fill_price:.2f}")
            if order_id:
                logger.info(f"Fill event created with order_id: {order_id}")

            return fill_event

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error processing order: {e}", exc_info=True)
            return None            
    
    def get_account_info(self):
        """
        Get account information.
        
        Returns:
            Dict with account info
        """
        return {
            'broker': self.name,
            'account_id': 'simulated',
            'stats': self.get_stats()
        }

    def reset(self):
        """Reset broker state."""
        # Clear processed state changes
        self.processed_state_changes.clear()

        # Reset statistics without calling super
        self.stats = {
            'orders_processed': 0,
            'fills_generated': 0,
            'errors': 0
        }

        logger.debug(f"Reset broker {self.name}")
