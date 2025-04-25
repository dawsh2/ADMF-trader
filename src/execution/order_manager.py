"""
Order management system for tracking and processing orders.
"""
import logging
import uuid
import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union

from core.events.event_types import EventType, Event
from core.events.event_utils import create_order_event, EventTracker

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order status enum."""
    CREATED = 'CREATED'  # Initial state
    PENDING = 'PENDING'  # Sent to broker
    PARTIAL = 'PARTIAL'  # Partially filled
    FILLED = 'FILLED'    # Completely filled
    CANCELED = 'CANCELED'  # Canceled by user or system
    REJECTED = 'REJECTED'  # Rejected by broker
    EXPIRED = 'EXPIRED'  # Order expired

class Order:
    """Class representing a trading order."""
    
    def __init__(self, symbol: str, order_type: str, direction: str, 
                quantity: float, price: Optional[float] = None, 
                time_in_force: str = 'DAY', status: OrderStatus = OrderStatus.CREATED,
                order_id: Optional[str] = None):
        """
        Initialize an order.
        
        Args:
            symbol: Instrument symbol
            order_type: Type of order ('MARKET', 'LIMIT', 'STOP', etc.)
            direction: Trade direction ('BUY' or 'SELL')
            quantity: Order quantity
            price: Optional price for limit or stop orders
            time_in_force: Order time in force ('DAY', 'GTC', 'IOC', etc.)
            status: Initial order status
            order_id: Optional order ID (generated if not provided)
        """
        self.symbol = symbol
        self.order_type = order_type
        self.direction = direction
        self.quantity = quantity
        self.price = price
        self.time_in_force = time_in_force
        self.status = status
        self.order_id = order_id or str(uuid.uuid4())
        self.created_time = datetime.datetime.now()
        self.updated_time = self.created_time
        self.filled_quantity = 0.0
        self.average_fill_price = 0.0
        self.fill_time = None
        self.metadata = {}  # Additional order metadata
    
    def update_status(self, status: OrderStatus, fill_quantity: float = 0.0, 
                     fill_price: float = 0.0):
        """
        Update order status and fill information.
        
        Args:
            status: New order status
            fill_quantity: Quantity filled in this update
            fill_price: Price at which the fill occurred
        """
        self.status = status
        self.updated_time = datetime.datetime.now()
        
        if fill_quantity > 0:
            # Calculate weighted average fill price
            total_filled = self.filled_quantity + fill_quantity
            if total_filled > 0:
                self.average_fill_price = (
                    (self.average_fill_price * self.filled_quantity) + 
                    (fill_price * fill_quantity)
                ) / total_filled
            
            self.filled_quantity += fill_quantity
            
            # Set fill time if this is the first fill
            if self.fill_time is None:
                self.fill_time = self.updated_time
            
            # Update status based on fill
            if self.filled_quantity >= self.quantity:
                self.status = OrderStatus.FILLED
            elif self.filled_quantity > 0:
                self.status = OrderStatus.PARTIAL
    
    def cancel(self):
        """Cancel the order."""
        if self.status in [OrderStatus.CREATED, OrderStatus.PENDING, OrderStatus.PARTIAL]:
            self.status = OrderStatus.CANCELED
            self.updated_time = datetime.datetime.now()
            return True
        return False
    
    def is_active(self):
        """Check if the order is still active."""
        return self.status in [OrderStatus.CREATED, OrderStatus.PENDING, OrderStatus.PARTIAL]
    
    def is_filled(self):
        """Check if the order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    def is_canceled(self):
        """Check if the order is canceled."""
        return self.status == OrderStatus.CANCELED
    
    def get_remaining_quantity(self):
        """Get remaining quantity to be filled."""
        return self.quantity - self.filled_quantity
    
    def to_dict(self):
        """
        Convert order to dictionary.
        
        Returns:
            Dict: Order as dictionary
        """
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'order_type': self.order_type,
            'direction': self.direction,
            'quantity': self.quantity,
            'price': self.price,
            'time_in_force': self.time_in_force,
            'status': self.status.value,
            'created_time': self.created_time.isoformat(),
            'updated_time': self.updated_time.isoformat(),
            'filled_quantity': self.filled_quantity,
            'average_fill_price': self.average_fill_price,
            'fill_time': self.fill_time.isoformat() if self.fill_time else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Create order from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Order: Reconstructed order
        """
        # Create order with required fields
        order = cls(
            symbol=data['symbol'],
            order_type=data['order_type'],
            direction=data['direction'],
            quantity=data['quantity'],
            price=data.get('price'),
            time_in_force=data.get('time_in_force', 'DAY'),
            status=OrderStatus(data.get('status', 'CREATED')),
            order_id=data.get('order_id')
        )
        
        # Set additional fields
        if 'created_time' in data:
            order.created_time = datetime.datetime.fromisoformat(data['created_time'])
        if 'updated_time' in data:
            order.updated_time = datetime.datetime.fromisoformat(data['updated_time'])
        if 'filled_quantity' in data:
            order.filled_quantity = data['filled_quantity']
        if 'average_fill_price' in data:
            order.average_fill_price = data['average_fill_price']
        if 'fill_time' in data and data['fill_time']:
            order.fill_time = datetime.datetime.fromisoformat(data['fill_time'])
        if 'metadata' in data:
            order.metadata = data['metadata']
        
        return order
    
    def __str__(self):
        return (f"Order({self.order_id}, {self.symbol}, {self.direction}, "
                f"{self.quantity}, {self.status.value})")


class OrderManager:
    """Manager for tracking and processing orders."""
    
    def __init__(self, event_bus=None, broker=None):
        """
        Initialize order manager.
        
        Args:
            event_bus: Event bus for communication
            broker: Broker for order execution
        """
        self.event_bus = event_bus
        self.broker = broker
        self.orders = {}  # order_id -> Order
        self.active_orders = set()  # Set of active order IDs
        self.order_history = []  # List of completed orders
        self.configured = False
        
        # Statistics
        self.stats = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_rejected': 0,
            'orders_expired': 0
        }
        
        # Event tracker
        self.event_tracker = EventTracker("order_manager")
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.ORDER, self.on_order)
            self.event_bus.register(EventType.FILL, self.on_fill)
    
    def configure(self, config):
        """
        Configure the order manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        # Nothing to configure at this level currently
        self.configured = True
    
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
            self.event_bus.register(EventType.FILL, self.on_fill)
    
    def set_broker(self, broker):
        """
        Set the broker.
        
        Args:
            broker: Broker instance
        """
        self.broker = broker
    
    def on_order(self, order_event):
        """
        Handle order events.
        
        Args:
            order_event: Order event to process
        """
        # Track the event
        self.event_tracker.track_event(order_event)
        
        # Extract order details
        symbol = order_event.get_symbol()
        order_type = order_event.get_order_type()
        direction = order_event.get_direction()
        quantity = order_event.get_quantity()
        price = order_event.get_price()
        
        # Create order object
        order = Order(
            symbol=symbol,
            order_type=order_type,
            direction=direction,
            quantity=quantity,
            price=price
        )
        
        # Track the order
        self.orders[order.order_id] = order
        self.active_orders.add(order.order_id)
        
        # Update statistics
        self.stats['orders_created'] += 1
        
        # Process the order using broker if available
        if self.broker:
            # Update order status to pending
            order.status = OrderStatus.PENDING
            
            # Send to broker
            fill_event = self.broker.process_order(order_event)
            
            # If broker returned a fill event, process it
            if fill_event:
                self.on_fill(fill_event)
        
        # Emit order status event
        self._emit_order_status_event(order)
        
        logger.info(f"Created order: {order}")
    
    def on_fill(self, fill_event):
        """
        Handle fill events.
        
        Args:
            fill_event: Fill event to process
        """
        # Track the event
        self.event_tracker.track_event(fill_event)
        
        # Extract fill details
        symbol = fill_event.get_symbol()
        direction = fill_event.get_direction()
        quantity = fill_event.get_quantity()
        price = fill_event.get_price()
        order_id = fill_event.data.get('order_id')
        
        # Find the order
        if order_id and order_id in self.orders:
            order = self.orders[order_id]
        else:
            # Try to match by symbol and direction
            matching_orders = [
                o for o in [self.orders[oid] for oid in self.active_orders]
                if o.symbol == symbol and o.direction == direction
            ]
            
            if matching_orders:
                # Use the oldest matching order
                order = min(matching_orders, key=lambda o: o.created_time)
                order_id = order.order_id
            else:
                logger.warning(f"No matching order found for fill: {fill_event}")
                return
        
        # Update order with fill information
        order.update_status(
            status=OrderStatus.FILLED if quantity >= order.get_remaining_quantity() else OrderStatus.PARTIAL,
            fill_quantity=quantity,
            fill_price=price
        )
        
        # Check if order is now complete
        if order.is_filled():
            self.active_orders.remove(order_id)
            self.order_history.append(order)
            self.stats['orders_filled'] += 1
        
        # Emit order status event
        self._emit_order_status_event(order)
        
        logger.info(f"Updated order with fill: {order}")
    
    def create_order(self, symbol, order_type, direction, quantity, price=None):
        """
        Create and submit a new order.
        
        Args:
            symbol: Instrument symbol
            order_type: Type of order ('MARKET', 'LIMIT', 'STOP', etc.)
            direction: Trade direction ('BUY' or 'SELL')
            quantity: Order quantity
            price: Optional price for limit or stop orders
            
        Returns:
            str: Order ID
        """
        # Create order event
        order_event = create_order_event(
            symbol=symbol,
            order_type=order_type,
            direction=direction,
            quantity=quantity,
            price=price
        )
        
        # Process the order event
        if self.event_bus:
            self.event_bus.emit(order_event)
        else:
            self.on_order(order_event)
        
        # Find the order ID (the last created order for this symbol/direction)
        matching_orders = [
            o for o in self.orders.values()
            if o.symbol == symbol and o.direction == direction
        ]
        
        if matching_orders:
            # Get the most recently created order
            order = max(matching_orders, key=lambda o: o.created_time)
            return order.order_id
        
        return None
    
    def cancel_order(self, order_id):
        """
        Cancel an order.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            bool: True if canceled, False otherwise
        """
        if order_id not in self.orders:
            logger.warning(f"Order not found: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        # Check if order can be canceled
        if not order.is_active():
            logger.warning(f"Cannot cancel inactive order: {order}")
            return False
        
        # Cancel through broker if available
        if self.broker and hasattr(self.broker, 'cancel_order'):
            result = self.broker.cancel_order(order_id)
            if not result:
                logger.warning(f"Broker failed to cancel order: {order}")
                return False
        
        # Update order status
        order.cancel()
        
        # Remove from active orders
        if order_id in self.active_orders:
            self.active_orders.remove(order_id)
            self.order_history.append(order)
        
        # Update statistics
        self.stats['orders_canceled'] += 1
        
        # Emit order status event
        self._emit_order_status_event(order)
        
        logger.info(f"Canceled order: {order}")
        return True
    
    def cancel_all_orders(self, symbol=None):
        """
        Cancel all active orders, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol to filter orders
            
        Returns:
            int: Number of orders canceled
        """
        orders_to_cancel = [
            order_id for order_id in self.active_orders
            if symbol is None or self.orders[order_id].symbol == symbol
        ]
        
        canceled_count = 0
        for order_id in orders_to_cancel:
            if self.cancel_order(order_id):
                canceled_count += 1
        
        return canceled_count
    
    def get_order(self, order_id):
        """
        Get an order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order or None if not found
        """
        return self.orders.get(order_id)
    
    def get_active_orders(self, symbol=None):
        """
        Get all active orders, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol to filter orders
            
        Returns:
            List of active orders
        """
        active_orders = [self.orders[order_id] for order_id in self.active_orders]
        
        if symbol:
            return [order for order in active_orders if order.symbol == symbol]
        
        return active_orders
    
    def get_order_history(self, symbol=None, limit=None):
        """
        Get order history, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol to filter orders
            limit: Optional maximum number of orders to return
            
        Returns:
            List of historical orders
        """
        if symbol:
            history = [order for order in self.order_history if order.symbol == symbol]
        else:
            history = list(self.order_history)
        
        # Sort by created time (newest first)
        history.sort(key=lambda o: o.created_time, reverse=True)
        
        if limit:
            return history[:limit]
        
        return history
    
    def _emit_order_status_event(self, order):
        """
        Emit an order status event.
        
        Args:
            order: Order to emit status for
        """
        if not self.event_bus:
            return
        
        # Create a custom order status event
        status_event = Event(
            event_type=EventType.ORDER,  # Use ORDER type for status updates
            data={
                'type': 'STATUS',
                'order_id': order.order_id,
                'symbol': order.symbol,
                'status': order.status.value,
                'filled_quantity': order.filled_quantity,
                'remaining_quantity': order.get_remaining_quantity(),
                'average_fill_price': order.average_fill_price
            },
            timestamp=datetime.datetime.now()
        )
        
        # Emit the event
        self.event_bus.emit(status_event)
    
    def get_stats(self):
        """
        Get order manager statistics.
        
        Returns:
            Dict with statistics
        """
        # Update active order count
        self.stats['active_orders'] = len(self.active_orders)
        
        return dict(self.stats)
    
    def reset(self):
        """Reset order manager state."""
        self.orders = {}
        self.active_orders = set()
        self.order_history = []
        
        # Reset statistics
        self.stats = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_rejected': 0,
            'orders_expired': 0
        }
        
        # Reset event tracker
        self.event_tracker.reset()
        
        logger.info("Reset order manager")


# Factory for creating order managers
class OrderManagerFactory:
    """Factory for creating order managers."""
    
    @staticmethod
    def create(event_bus=None, broker=None, config=None):
        """
        Create an order manager.
        
        Args:
            event_bus: Optional event bus
            broker: Optional broker
            config: Optional configuration
            
        Returns:
            OrderManager: Order manager instance
        """
        # Create order manager
        manager = OrderManager(event_bus, broker)
        
        # Configure if config provided
        if config:
            manager.configure(config)
            
        return manager
