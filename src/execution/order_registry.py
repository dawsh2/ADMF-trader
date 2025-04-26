"""
Centralized Order Registry for tracking all orders in the system.
"""
import datetime
import logging
import uuid
from typing import Dict, Any, List, Tuple, Optional, Set

from src.core.events.event_types import EventType, Event
from src.core.events.event_utils import create_fill_event
from src.execution.order_manager import OrderStatus, Order

logger = logging.getLogger(__name__)

class OrderRegistry:
    """Central registry for tracking all orders in the system."""
    
    def __init__(self, event_bus=None):
        """
        Initialize the order registry.
        
        Args:
            event_bus: Event bus for communication
        """
        self.event_bus = event_bus
        self.orders = {}  # order_id -> Order
        self.state_changes = []  # Ordered history of state changes
        self.processed_events = set()  # Set of processed event IDs to prevent duplicates
        
        # Register for events if event bus provided
        if self.event_bus:
            self._register_handlers()
    
    def set_event_bus(self, event_bus):
        """Set the event bus and register handlers."""
        self.event_bus = event_bus
        self._register_handlers()
    
    def _register_handlers(self):
        """Register event handlers for order-related events."""
        self.event_bus.register(EventType.ORDER, self.on_order)
        self.event_bus.register(EventType.FILL, self.on_fill)
        # Add handler for cancel events when implemented
        # self.event_bus.register(EventType.ORDER_CANCEL, self.on_cancel)
    
    def register_order(self, order: Order) -> bool:
        """
        Register a new order in the system.
        
        Args:
            order: Order to register
            
        Returns:
            bool: True if registered successfully, False otherwise
        """
        # Check if already registered
        if order.order_id in self.orders:
            logger.warning(f"Order {order.order_id} already registered")
            return False
            
        # Validate order
        if not self._validate_order(order):
            logger.warning(f"Invalid order: {order}")
            return False
            
        # Store order and emit state change event
        self.orders[order.order_id] = order
        self._emit_state_change(order, "REGISTERED")
        logger.info(f"Registered order: {order.order_id}")
        return True
    
    def update_order_status(self, order_id: str, new_status: OrderStatus, **details) -> bool:
        """
        Update an order's status with validation.
        
        Args:
            order_id: ID of order to update
            new_status: New order status
            **details: Additional details to update
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        if order_id not in self.orders:
            logger.warning(f"Cannot update non-existent order: {order_id}")
            return False
            
        order = self.orders[order_id]
        
        # Validate state transition
        if not self._valid_transition(order.status, new_status):
            logger.warning(f"Invalid state transition: {order.status} -> {new_status}")
            return False
            
        # Update order status
        old_status = order.status
        order.status = new_status
        
        # Update additional details (e.g., fill information)
        for key, value in details.items():
            if hasattr(order, key):
                setattr(order, key, value)
                
        # Record and emit state change
        self._emit_state_change(order, f"{old_status.value} -> {new_status.value}")
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get an order by ID with safe error handling.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order or None if not found
        """
        return self.orders.get(order_id)
    
    def _valid_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """
        Validate state transitions using a state machine.
        
        Args:
            current_status: Current order status
            new_status: New order status
            
        Returns:
            bool: True if transition is valid, False otherwise
        """
        # State machine for order lifecycle
        valid_transitions = {
            OrderStatus.CREATED: [OrderStatus.PENDING, OrderStatus.CANCELED],
            OrderStatus.PENDING: [OrderStatus.PARTIAL, OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELED],
            OrderStatus.PARTIAL: [OrderStatus.FILLED, OrderStatus.CANCELED],
            OrderStatus.FILLED: [],  # Terminal state
            OrderStatus.CANCELED: [],  # Terminal state
            OrderStatus.REJECTED: [],  # Terminal state
            OrderStatus.EXPIRED: [],   # Terminal state
        }
        
        return new_status in valid_transitions.get(current_status, [])
    
    def _emit_state_change(self, order: Order, transition_description: str) -> None:
        """
        Emit an event for order state change.
        
        Args:
            order: Order that changed state
            transition_description: Description of state transition
        """
        if not self.event_bus:
            return
            
        # Create state change event
        event = Event(
            EventType.PORTFOLIO,  # Using PORTFOLIO type for now until ORDER_STATE_CHANGE is added
            {
                'order_state_change': True,  # Marker to identify state change events
                'order_id': order.order_id,
                'status': order.status.value,
                'transition': transition_description,
                'timestamp': datetime.datetime.now(),
                'order_data': order.to_dict()
            }
        )
        
        # Record in history
        self.state_changes.append((order.order_id, transition_description, datetime.datetime.now()))
        
        # Emit event
        logger.debug(f"Emitting state change: {order.order_id} - {transition_description}")
        self.event_bus.emit(event)
    
    def _validate_order(self, order: Order) -> bool:
        """
        Validate order attributes.
        
        Args:
            order: Order to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Simple validation logic
        if not order.symbol or not order.order_type or not order.direction:
            logger.warning(f"Order missing required fields: {order}")
            return False
            
        if order.quantity <= 0:
            logger.warning(f"Order has invalid quantity: {order.quantity}")
            return False
            
        if order.order_type in ['LIMIT', 'STOP'] and order.price is None:
            logger.warning(f"LIMIT/STOP order missing price: {order}")
            return False
            
        return True
    
    # Event handlers
    def on_order(self, order_event: Event) -> None:
        """
        Handle order events.
        
        Args:
            order_event: Order event to process
        """
        # Skip duplicates
        event_id = order_event.get_id()
        if event_id in self.processed_events:
            logger.debug(f"Skipping already processed order event: {event_id}")
            return
            
        self.processed_events.add(event_id)
        
        # Extract order ID from the event
        order_id = None
        if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
            order_id = order_event.data.get('order_id')
            
        if not order_id:
            logger.warning("Order event missing order_id")
            return
            
        # Check if order already exists
        if order_id in self.orders:
            logger.debug(f"Order {order_id} already exists, updating status")
            return
            
        # Extract order details
        try:
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
                price=price,
                status=OrderStatus.CREATED,
                order_id=order_id
            )
            
            # Register the order
            if self.register_order(order):
                # Update status to PENDING
                self.update_order_status(order_id, OrderStatus.PENDING)
                
        except Exception as e:
            logger.error(f"Error processing order event: {e}", exc_info=True)
    
    def on_fill(self, fill_event: Event) -> None:
        """
        Handle fill events.
        
        Args:
            fill_event: Fill event to process
        """
        # Skip duplicates
        event_id = fill_event.get_id()
        if event_id in self.processed_events:
            logger.debug(f"Skipping already processed fill event: {event_id}")
            return
            
        self.processed_events.add(event_id)
        
        # Extract order ID from the event
        order_id = None
        if hasattr(fill_event, 'data') and isinstance(fill_event.data, dict):
            order_id = fill_event.data.get('order_id')
            
        if not order_id:
            logger.warning("Fill event missing order_id")
            return
            
        # Get the order
        order = self.get_order(order_id)
        if not order:
            logger.warning(f"Fill for unknown order: {order_id}")
            return
            
        # Extract fill details
        try:
            quantity = fill_event.get_quantity()
            price = fill_event.get_price()
            
            # Add to filled quantity
            order.filled_quantity += quantity
            
            # Calculate average fill price
            if order.average_fill_price == 0:
                order.average_fill_price = price
            else:
                total_quantity = order.filled_quantity
                prev_quantity = total_quantity - quantity
                
                if total_quantity > 0:
                    order.average_fill_price = (
                        (order.average_fill_price * prev_quantity) + (price * quantity)
                    ) / total_quantity
            
            # Update order status based on fill
            if order.filled_quantity >= order.quantity:
                new_status = OrderStatus.FILLED
            elif order.filled_quantity > 0:
                new_status = OrderStatus.PARTIAL
            else:
                return  # No change needed
                
            # Update the order status
            self.update_order_status(
                order_id, 
                new_status,
                filled_quantity=order.filled_quantity,
                average_fill_price=order.average_fill_price,
                fill_time=datetime.datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error processing fill event: {e}", exc_info=True)
    
    def reset(self) -> None:
        """Reset registry state."""
        self.orders.clear()
        self.state_changes.clear()
        self.processed_events.clear()
        logger.info("Order registry reset")
        
    def get_active_orders(self) -> List[Order]:
        """
        Get all active orders.
        
        Returns:
            List of active orders
        """
        return [order for order in self.orders.values() if order.is_active()]
    
    def get_completed_orders(self) -> List[Order]:
        """
        Get all completed orders.
        
        Returns:
            List of completed orders
        """
        return [order for order in self.orders.values() if order.is_filled()]
        
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """
        Get orders by status.
        
        Args:
            status: Order status to filter by
            
        Returns:
            List of orders with the specified status
        """
        return [order for order in self.orders.values() if order.status == status]
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get registry statistics.
        
        Returns:
            Dict with statistics
        """
        stats = {status.name: 0 for status in OrderStatus}
        
        for order in self.orders.values():
            stats[order.status.name] += 1
            
        stats['total'] = len(self.orders)
        stats['active'] = len(self.get_active_orders())
        stats['state_changes'] = len(self.state_changes)
        
        return stats
