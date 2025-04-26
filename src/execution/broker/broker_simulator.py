# src/execution/broker/broker_simulator.py
import logging
import datetime
from typing import Dict, Any, Optional

from src.core.events.event_types import EventType
from src.core.events.event_utils import create_fill_event
from src.execution.broker.broker_base import BrokerBase
from src.execution.order_manager import OrderStatus

logger = logging.getLogger(__name__)

class SimulatedBroker(BrokerBase):
    """Simulated broker for executing orders in backtests with OrderRegistry integration."""
    
    def __init__(self, event_bus=None, order_registry=None, name="simulated_broker"):
        """
        Initialize simulated broker.
        
        Args:
            event_bus: Event bus for communication
            order_registry: Optional order registry for centralized tracking
            name: Broker name
        """
        super().__init__(name)
        self.event_bus = event_bus
        self.order_registry = order_registry
        
        # Default parameters
        self.slippage = 0.0  # Percentage slippage
        self.commission = 0.0  # Percentage commission
        
        # Tracking for processed orders to avoid duplicates
        self.processed_order_ids = set()
        
        # Register for events if event bus provided
        if self.event_bus:
            self.event_bus.register(EventType.ORDER, self.on_order)
            # Register for portfolio events to catch order state changes
            self.event_bus.register(EventType.PORTFOLIO, self.on_portfolio_update)
    
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
        if self.event_bus:
            self.event_bus.register(EventType.ORDER, self.on_order)
            self.event_bus.register(EventType.PORTFOLIO, self.on_portfolio_update)
    
    def set_order_registry(self, order_registry):
        """
        Set the order registry.
        
        Args:
            order_registry: Order registry instance
        """
        self.order_registry = order_registry
    
    def on_order(self, order_event):
        """
        Handle order events.
        
        Args:
            order_event: Order event to process
        """
        # Extract order ID
        order_id = None
        if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
            order_id = order_event.data.get('order_id')
        
        # Skip if no order ID
        if not order_id:
            logger.warning("Order event missing order_id, cannot process")
            return
            
        # Skip if already processed this order
        if order_id in self.processed_order_ids:
            logger.debug(f"Order {order_id} already processed by broker, skipping")
            return
        
        # If using OrderRegistry, check if order is registered before processing
        if self.order_registry:
            # Get order from registry
            registry_order = self.order_registry.get_order(order_id)
            if not registry_order:
                logger.debug(f"Order {order_id} not yet in registry, will be processed after registration")
                return
                
            # Order is in registry - check status
            if registry_order.status.value == 'PENDING':
                logger.debug(f"Processing order {order_id} from registry with PENDING status")
                # Process the order using registry data
                fill_event = self._process_registry_order(registry_order)
                
                # Emit fill event if created
                if fill_event and self.event_bus:
                    # Keep track of order ID to prevent duplicate processing
                    self.processed_order_ids.add(order_id)
                    
                    # Emit the fill event
                    logger.info(f"Broker emitting fill event for {fill_event.get_symbol()}")
                    self.event_bus.emit(fill_event)
        else:
            # No OrderRegistry - process directly (legacy mode)
            try:
                # Get symbols, directions from event directly
                symbol = order_event.get_symbol()
                direction = order_event.get_direction()
                quantity = order_event.get_quantity()
                price = order_event.get_price()

                # Process the order
                fill_event = self.process_order(symbol, direction, quantity, price, order_id)
                
                # Emit fill event if created
                if fill_event and self.event_bus:
                    # Keep track of order ID to prevent duplicate processing
                    self.processed_order_ids.add(order_id)
                    
                    # Emit the fill event
                    logger.info(f"Broker emitting fill event for {fill_event.get_symbol()}")
                    self.event_bus.emit(fill_event)
            except Exception as e:
                logger.error(f"Error processing order event: {e}", exc_info=True)
                self.stats['errors'] += 1
    
    def on_portfolio_update(self, event):
        """
        Listen for order state changes from the registry.
        
        Args:
            event: Portfolio event
        """
        # Only interested in order state change events
        if not (hasattr(event, 'data') and 
                isinstance(event.data, dict) and 
                event.data.get('order_state_change')):
            return
            
        # Extract order info
        order_id = event.data.get('order_id')
        if not order_id:
            return
            
        # Skip if already processed this order
        if order_id in self.processed_order_ids:
            return
            
        # Check if this is a PENDING order that we should process
        status = event.data.get('status')
        if status == 'PENDING' and order_id not in self.processed_order_ids:
            logger.debug(f"Processing PENDING order {order_id} from state change")
            
            # Get order from registry
            if self.order_registry:
                registry_order = self.order_registry.get_order(order_id)
                if registry_order:
                    # Process the order using registry data
                    fill_event = self._process_registry_order(registry_order)
                    
                    # Emit fill event if created
                    if fill_event and self.event_bus:
                        # Keep track of order ID to prevent duplicate processing
                        self.processed_order_ids.add(order_id)
                        
                        # Emit the fill event
                        logger.info(f"Broker emitting fill event for {fill_event.get_symbol()} after state change")
                        self.event_bus.emit(fill_event)

    def _process_registry_order(self, order):
        """
        Process an order from the registry.
        
        Args:
            order: Order object from registry
        
        Returns:
            Fill event or None
        """
        try:
            # Process the order using order data
            return self.process_order(
                order.symbol, 
                order.direction, 
                order.quantity, 
                order.price, 
                order.order_id
            )
        except Exception as e:
            logger.error(f"Error processing registry order: {e}", exc_info=True)
            self.stats['errors'] += 1
            return None

    def process_order(self, symbol, direction, quantity, price, order_id=None):
        """
        Process an order.

        Args:
            symbol: Instrument symbol
            direction: Trade direction ('BUY' or 'SELL')
            quantity: Order quantity
            price: Order price
            order_id: Optional order ID

        Returns:
            Fill event or None
        """
        self.stats['orders_processed'] += 1

        try:
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
        # Clear processed order IDs
        self.processed_order_ids.clear()

        # Reset statistics without calling super
        self.stats = {
            'orders_processed': 0,
            'fills_generated': 0,
            'errors': 0
        }

        logger.debug(f"Reset broker {self.name}")
