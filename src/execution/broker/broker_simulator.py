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
    
    def __init__(self, event_bus=None, name="simulated_broker"):
        """
        Initialize simulated broker.
        
        Args:
            event_bus: Event bus for communication
            name: Broker name
        """
        super().__init__(name)
        self.event_bus = event_bus
        
        # Default parameters
        self.slippage = 0.0  # Percentage slippage
        self.commission = 0.0  # Percentage commission
        
        # Tracking for processed orders to avoid duplicates
        self.processed_order_ids = set()
        
        # NEW: Add pending orders queue for order->fill coordination
        self.pending_orders = {}  # order_id -> (order_event, timestamp)
        
        # Register for events if event bus provided
        if self.event_bus:
            self.event_bus.register(EventType.ORDER, self.on_order)
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
            logger.debug(f"Broker extracted order_id: {order_id}")
        
        # Skip if no order ID
        if not order_id:
            logger.warning("Order event missing order_id, cannot process")
            return
            
        # Skip if already processed this order
        if order_id in self.processed_order_ids:
            logger.debug(f"Order {order_id} already processed by broker, skipping")
            return
        
        # NEW: Add to pending orders queue
        self.pending_orders[order_id] = (order_event, datetime.datetime.now())
        logger.debug(f"Added order {order_id} to pending queue, waiting for confirmation")
    
    def on_portfolio_update(self, event):
        """
        Handle portfolio events to detect when order manager has stored an order.
        This uses portfolio status update events as confirmation.
        """
        # Check if this is a status update
        if (hasattr(event, 'data') and isinstance(event.data, dict) and 
                event.data.get('status_update') and 'order_id' in event.data):
            order_id = event.data['order_id']
            
            # Check if this order is in our pending queue
            if order_id in self.pending_orders:
                logger.debug(f"Received confirmation for order {order_id}, processing now")
                # Now we can process it
                order_event, _ = self.pending_orders.pop(order_id)
                fill_event = self.process_order(order_event)
                
                # Emit fill event if created
                if fill_event and self.event_bus:
                    # Keep track of order ID to prevent duplicate processing
                    self.processed_order_ids.add(order_id)
                    
                    # Make sure fill has the order ID for tracing
                    if hasattr(fill_event, 'data') and isinstance(fill_event.data, dict):
                        if 'order_id' not in fill_event.data:
                            fill_event.data['order_id'] = order_id
                        
                    # Emit the fill event
                    logger.info(f"Broker emitting fill event for {fill_event.get_symbol()}")
                    self.event_bus.emit(fill_event)

    def process_order(self, order_event):
        """
        Process an order event.

        Args:
            order_event: Order event to process

        Returns:
            Fill event or None
        """
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
        # Clear processed order IDs and pending orders
        self.processed_order_ids.clear()
        self.pending_orders.clear()

        # Reset statistics without calling super
        self.stats = {
            'orders_processed': 0,
            'fills_generated': 0,
            'errors': 0
        }

        logger.debug(f"Reset broker {self.name}")
