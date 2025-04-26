"""
Order management system for tracking and processing orders.
"""
import logging
import uuid
import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union

from src.core.events.event_types import EventType, Event
from src.core.events.event_utils import create_order_event, EventTracker

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
    """
    Order manager that integrates with the OrderRegistry for centralized order tracking.
    
    This class is responsible for:
    1. Creating orders from signals or explicit requests
    2. Delegating order tracking to the OrderRegistry
    3. Processing fill events for order updates
    4. Handling cancellations and other order lifecycle events
    """
    
    def __init__(self, event_bus=None, broker=None, order_registry=None):
        """
        Initialize order manager with support for OrderRegistry.
        
        Args:
            event_bus: Event bus for communication
            broker: Broker for order execution
            order_registry: Optional order registry for centralized tracking
        """
        self.event_bus = event_bus
        self.broker = broker
        self.order_registry = order_registry
        
        # Legacy order tracking (used as local cache even with registry)
        self.orders = {}  # order_id -> Order
        self.active_orders = set()  # Set of active order IDs
        self.order_history = []  # List of completed orders
        
        # Configuration state
        self.configured = False
        
        # Event processing tracking to avoid duplicates
        self.processed_events = set()  # Set of processed event IDs
        
        # Statistics
        self.stats = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_rejected': 0,
            'orders_expired': 0,
            'errors': 0
        }
        
        # Event tracker for diagnostics
        self.event_tracker = EventTracker("order_manager")
        
        # Register for events
        if self.event_bus:
            self._register_handlers()
    
    def _register_handlers(self):
        """Register event handlers."""
        if not self.event_bus:
            return
            
        # Register handlers for order-related events
        self.event_bus.register(EventType.SIGNAL, self.on_signal)
        self.event_bus.register(EventType.FILL, self.on_fill)
        self.event_bus.register(EventType.PORTFOLIO, self.on_portfolio_update)
        self.event_bus.register(EventType.ORDER, self.on_order)  # NEW: Also listen for ORDER events from other components
    
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
        self._register_handlers()
    
    def set_broker(self, broker):
        """
        Set the broker.
        
        Args:
            broker: Broker instance
        """
        self.broker = broker
    
    def set_order_registry(self, order_registry):
        """
        Set the order registry.
        
        Args:
            order_registry: Order registry instance
        """
        self.order_registry = order_registry
    
    def on_order(self, order_event):
        """
        Handle order events from other components (like risk manager).
        This is needed to track orders created by components that don't use create_order.
        
        Args:
            order_event: Order event to track
        """
        # Skip if already processed
        event_id = order_event.get_id()
        if event_id in self.processed_events:
            return
            
        self.processed_events.add(event_id)
        
        # Extract order ID
        order_id = None
        if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
            order_id = order_event.data.get('order_id')
        
        if not order_id:
            logger.debug("Order event has no order_id, cannot track it")
            return
        
        # Check if we're already tracking this order
        if order_id in self.orders:
            logger.debug(f"Already tracking order {order_id}")
            return
        
        # If we're using OrderRegistry, check if order exists there
        if self.order_registry:
            registry_order = self.order_registry.get_order(order_id)
            if registry_order:
                # Add to local tracking
                self.orders[order_id] = registry_order
                self.active_orders.add(order_id)
                logger.debug(f"Added registry order {order_id} to local tracking")
                return
        
        # If not in registry (or no registry), create a placeholder order from event data
        try:
            # Extract details from order event
            symbol = order_event.get_symbol()
            order_type = order_event.get_order_type()
            direction = order_event.get_direction()
            quantity = order_event.get_quantity()
            price = order_event.get_price()
            
            # Create and track new order
            order = Order(
                symbol=symbol,
                order_type=order_type,
                direction=direction,
                quantity=quantity,
                price=price,
                status=OrderStatus.PENDING,  # Assume it's pending since it's an order event
                order_id=order_id
            )
            
            self.orders[order_id] = order
            self.active_orders.add(order_id)
            logger.debug(f"Added new order {order_id} from event to tracking")
            
        except Exception as e:
            logger.error(f"Error tracking order {order_id} from event: {e}")
    
    def on_signal(self, signal_event):
        """
        Handle signal events by creating orders.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            str: Order ID or None
        """
        # Skip if already processed
        event_id = signal_event.get_id()
        if event_id in self.processed_events:
            return None
            
        self.processed_events.add(event_id)
        self.event_tracker.track_event(signal_event)
        
        try:
            # Extract signal details
            symbol = signal_event.get_symbol()
            signal_value = signal_event.get_signal_value()
            price = signal_event.get_price()
            
            # Skip neutral signals
            if signal_value == 0:
                return None
            
            # Create order
            direction = 'BUY' if signal_value > 0 else 'SELL'
            
            # Call order creation method
            return self.create_order(
                symbol=symbol,
                order_type='MARKET',
                direction=direction,
                quantity=100,  # Default quantity - in real system this would be calculated
                price=price
            )
            
        except Exception as e:
            logger.error(f"Error processing signal event: {e}", exc_info=True)
            self.stats['errors'] += 1
            return None
    
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
        # Create a unique order ID
        order_id = str(uuid.uuid4())
        
        # Create order object
        order = Order(
            symbol=symbol,
            order_type=order_type,
            direction=direction,
            quantity=quantity,
            price=price,
            status=OrderStatus.CREATED,
            order_id=order_id
        )
        
        # Register with order registry if available
        if self.order_registry:
            self.order_registry.register_order(order)
        
        # Always track locally regardless
        self.orders[order_id] = order
        self.active_orders.add(order_id)
        self.stats['orders_created'] += 1
        
        # Create and emit order event
        order_event = create_order_event(
            symbol=symbol,
            order_type=order_type,
            direction=direction,
            quantity=quantity,
            price=price,
            order_id=order_id  # Include order ID in event
        )
        
        # Explicitly add order ID to event data
        if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
            order_event.data['order_id'] = order_id
        
        # Emit the order event
        if self.event_bus:
            logger.info(f"Emitting order event: {order_id}")
            self.event_bus.emit(order_event)
        
        return order_id
    
    def on_fill(self, fill_event):
        """
        Handle fill events.
        
        This method is now much simpler as order state updates are handled by the registry.
        
        Args:
            fill_event: Fill event to process
        """
        # Skip if already processed
        event_id = fill_event.get_id()
        if event_id in self.processed_events:
            return
            
        self.processed_events.add(event_id)
        self.event_tracker.track_event(fill_event)
        
        # Extract order ID
        order_id = None
        if hasattr(fill_event, 'data') and isinstance(fill_event.data, dict):
            order_id = fill_event.data.get('order_id')
        
        if not order_id:
            logger.warning(f"Fill event missing order_id: {event_id}")
            return
        
        # Check if we know about this order - if not, check registry
        if order_id not in self.orders and self.order_registry:
            registry_order = self.order_registry.get_order(order_id)
            if registry_order:
                # Add to our tracking
                self.orders[order_id] = registry_order
                self.active_orders.add(order_id)
                logger.debug(f"Added registry order {order_id} to local tracking during fill")
        
        # Now process the fill
        if order_id in self.orders:
            order = self.orders[order_id]
            
            # Extract fill details
            quantity = fill_event.get_quantity()
            price = fill_event.get_price()
            
            # Update local order state
            old_status = order.status
            order.update_status(
                status=OrderStatus.FILLED if quantity >= order.get_remaining_quantity() else OrderStatus.PARTIAL,
                fill_quantity=quantity,
                fill_price=price
            )
            
            # Update local tracking
            if order.is_filled() and order_id in self.active_orders:
                self.active_orders.remove(order_id)
                if order not in self.order_history:
                    self.order_history.append(order)
                self.stats['orders_filled'] += 1
                
            logger.info(f"Updated order with fill: {order}")
        else:
            logger.error(f"Order {order_id} not found in order manager")
    
    def on_portfolio_update(self, event):
        """
        Handle portfolio update events which include order state changes.
        
        Args:
            event: Portfolio event to check for order state changes
        """
        # Skip if not an order state change
        if not (hasattr(event, 'data') and 
                isinstance(event.data, dict) and 
                (event.data.get('order_state_change') or event.data.get('status_update'))):
            return
            
        # Skip if already processed
        event_id = event.get_id()
        if event_id in self.processed_events:
            return
            
        self.processed_events.add(event_id)
        
        # Extract order info
        order_id = event.data.get('order_id')
        if not order_id:
            return
            
        # Update local cache if we're tracking this order
        if order_id in self.orders and self.order_registry:
            # Get fresh order state from registry
            registry_order = self.order_registry.get_order(order_id)
            if registry_order:
                # Update our local copy
                self.orders[order_id] = registry_order
                
                # Update tracking collections
                if registry_order.is_filled():
                    if order_id in self.active_orders:
                        self.active_orders.remove(order_id)
                    if registry_order not in self.order_history:
                        self.order_history.append(registry_order)
                    self.stats['orders_filled'] += 1
                elif registry_order.is_canceled():
                    if order_id in self.active_orders:
                        self.active_orders.remove(order_id)
                    self.stats['orders_canceled'] += 1
    
    def cancel_order(self, order_id):
        """
        Cancel an order.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            bool: True if canceled, False otherwise
        """
        # Check if order exists in registry first
        if self.order_registry and self.order_registry.get_order(order_id):
            order = self.order_registry.get_order(order_id)
        elif order_id in self.orders:
            order = self.orders[order_id]
        else:
            logger.warning(f"Order not found: {order_id}")
            return False
        
        # Check if order can be canceled
        if not order.is_active():
            logger.warning(f"Cannot cancel inactive order: {order}")
            return False
        
        # Update order status in registry if available
        if self.order_registry:
            self.order_registry.update_order_status(order_id, OrderStatus.CANCELED)
        
        # Update local order status
        if order_id in self.orders:
            self.orders[order_id].cancel()
            
            # Remove from active orders
            if order_id in self.active_orders:
                self.active_orders.remove(order_id)
                if self.orders[order_id] not in self.order_history:
                    self.order_history.append(self.orders[order_id])
            
        # Update statistics
        self.stats['orders_canceled'] += 1
        
        logger.info(f"Canceled order: {order_id}")
        return True
    
    def cancel_all_orders(self, symbol=None):
        """
        Cancel all active orders, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol to filter orders
            
        Returns:
            int: Number of orders canceled
        """
        # Get active orders from registry if available
        if self.order_registry:
            active_orders = self.order_registry.get_active_orders()
            if symbol:
                active_orders = [o for o in active_orders if o.symbol == symbol]
            
            canceled_count = 0
            for order in active_orders:
                if self.cancel_order(order.order_id):
                    canceled_count += 1
                    
            return canceled_count
        
        # Fallback to local tracking
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
        # Try registry first if available
        if self.order_registry:
            registry_order = self.order_registry.get_order(order_id)
            if registry_order:
                # Sync with local tracking
                if order_id not in self.orders:
                    self.orders[order_id] = registry_order
                    if registry_order.is_active():
                        self.active_orders.add(order_id)
                return registry_order
                
        # Fall back to local cache
        return self.orders.get(order_id)
    
    def get_active_orders(self, symbol=None):
        """
        Get all active orders, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol to filter orders
            
        Returns:
            List of active orders
        """
        # Use registry if available
        if self.order_registry:
            active_orders = self.order_registry.get_active_orders()
            
            # Sync with our local tracking
            for order in active_orders:
                if order.order_id not in self.orders:
                    self.orders[order.order_id] = order
                    self.active_orders.add(order.order_id)
                    
            if symbol:
                return [order for order in active_orders if order.symbol == symbol]
            return active_orders
            
        # Fall back to local tracking
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
        # Use registry if available for completed orders
        if self.order_registry:
            completed = self.order_registry.get_completed_orders()
            
            # Sync with our local tracking
            for order in completed:
                if order.order_id not in self.orders:
                    self.orders[order.order_id] = order
                    if order.order_id in self.active_orders:
                        self.active_orders.remove(order.order_id)
                    if order not in self.order_history:
                        self.order_history.append(order)
            
            if symbol:
                completed = [o for o in completed if o.symbol == symbol]
            
            # Sort by created time (newest first)
            completed.sort(key=lambda o: o.created_time, reverse=True)
            
            if limit:
                return completed[:limit]
            return completed
            
        # Fall back to local history
        if symbol:
            history = [order for order in self.order_history if order.symbol == symbol]
        else:
            history = list(self.order_history)
        
        # Sort by created time (newest first)
        history.sort(key=lambda o: o.created_time, reverse=True)
        
        if limit:
            return history[:limit]
        
        return history
    
    def reset(self):
        """Reset order manager state."""
        # Clear local tracking
        self.orders = {}
        self.active_orders = set()
        self.order_history = []
        self.processed_events.clear()
        
        # Reset statistics
        self.stats = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_rejected': 0,
            'orders_expired': 0,
            'errors': 0
        }
        
        # Reset event tracker
        self.event_tracker.reset()
        
        logger.info("Reset order manager")
    
    def get_stats(self):
        """
        Get order manager statistics.
        
        Returns:
            Dict with statistics
        """
        # Update active order count from latest data
        if self.order_registry:
            self.stats['active_orders'] = len(self.order_registry.get_active_orders())
        else:
            self.stats['active_orders'] = len(self.active_orders)
        
        return dict(self.stats)


# Factory for creating order managers
class OrderManagerFactory:
    """Factory for creating order managers."""
    
    @staticmethod
    def create(event_bus=None, broker=None, order_registry=None, config=None):
        """
        Create an order manager.
        
        Args:
            event_bus: Optional event bus
            broker: Optional broker
            order_registry: Optional order registry
            config: Optional configuration
            
        Returns:
            OrderManager: Order manager instance
        """
        # Create order manager
        manager = OrderManager(event_bus, broker, order_registry)
        
        # Configure if config provided
        if config:
            manager.configure(config)
            
        return manager
