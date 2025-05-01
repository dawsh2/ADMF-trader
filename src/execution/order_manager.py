"""
Order manager for handling orders without a separate order registry.
"""
import logging
import uuid
from typing import Dict, List, Optional, Any

from src.core.events.event_types import EventType, Event

logger = logging.getLogger(__name__)

class OrderManager:
    """
    Order manager that processes orders using the event bus.
    
    This implementation eliminates the need for a separate order registry
    by leveraging the event tracking capabilities of the event bus.
    """
    
    def __init__(self, event_bus, broker=None, order_registry=None):
        """
        Initialize the order manager.
        
        Args:
            event_bus: Event bus for event processing
            broker: Optional broker for order execution
            order_registry: Optional order registry (for backward compatibility)
        """
        self.event_bus = event_bus
        self.broker = broker
        self.active_orders = {}  # Local cache of active orders
        self.stats = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_cancelled': 0,
            'orders_rejected': 0
        }
        
        # Register event handlers
        self._register_handlers()
        
        logger.info("Order manager initialized")
        
    def create_order_from_params(self, symbol, order_type, direction, quantity, price=None, rule_id=None):
        """
        Create an order with explicit parameters rather than from a signal.
        
        Args:
            symbol: Instrument symbol
            order_type: Order type ('MARKET', 'LIMIT', etc.)
            direction: Order direction ('BUY', 'SELL')
            quantity: Order quantity (always positive)
            price: Optional price for limit orders
            rule_id: Optional rule ID for deduplication
            
        Returns:
            str: Order ID
        """
        # Generate order ID
        order_id = str(uuid.uuid4())
        
        # Ensure quantity is positive
        quantity = abs(quantity)
        
        # Create order data
        order_data = {
            'order_id': order_id,
            'symbol': symbol,
            'direction': direction,
            'size': quantity,  # Explicitly set size field
            'price': price,
            'status': 'PENDING',
        }
        
        # Add rule_id if provided
        if rule_id:
            order_data['rule_id'] = rule_id
        
        # Create order event
        order_event = Event(EventType.ORDER, order_data)
        
        # Emit order event
        self.event_bus.emit(order_event)
        
        # Update stats
        self.stats['orders_created'] += 1
        
        logger.info(f"Emitting order event with size {quantity}: {order_id}")
        return order_id
        
    def set_event_bus(self, event_bus):
        """
        Set the event bus.
        
        Args:
            event_bus: Event bus to use
        """
        self.event_bus = event_bus
        self._register_handlers()
        
    def set_broker(self, broker):
        """
        Set the broker.
        
        Args:
            broker: Broker to use
        """
        self.broker = broker
        
    def set_order_registry(self, order_registry):
        """
        Set order registry (for backward compatibility).
        
        Args:
            order_registry: Order registry to use
        """
        # This method exists for backward compatibility but does nothing
        # as we now use the event bus directly for order tracking
        pass
        
    def create_order(self, symbol, order_type='MARKET', direction='BUY', quantity=1, price=None, rule_id=None):
        """
        Create an order directly (with error handling for order size).
        
        Args:
            symbol: Instrument symbol
            order_type: Order type (MARKET, LIMIT, etc.)
            direction: Order direction (BUY, SELL)
            quantity: Order quantity
            price: Order price
            rule_id: Optional rule ID for tracking signal groups
            
        Returns:
            str: Order ID
        """
        # Validate quantity is an integer and positive
        if not isinstance(quantity, int) or quantity <= 0:
            logger.warning(f"Invalid quantity '{quantity}', adjusting to 1")
            quantity = 1
            
        # Generate order ID
        import uuid
        order_id = str(uuid.uuid4())
        
        # Create order data
        order_data = {
            'order_id': order_id,
            'symbol': symbol,
            'order_type': order_type,
            'direction': direction,
            'size': quantity,  # CRITICAL: Use 'size' for consistency
            'quantity': quantity,  # Add 'quantity' too for redundancy
            'price': price,
            'status': 'PENDING'
        }
        
        # Add rule_id if provided - CRITICAL for correct signal tracking
        if rule_id:
            order_data['rule_id'] = rule_id
            logger.info(f"Order {order_id} created with rule_id: {rule_id}")
        
        # Create order event
        order_event = Event(EventType.ORDER, order_data)
        
        # Track the order in active orders
        self.active_orders[order_id] = order_data
        
        # Emit order event
        if self.event_bus:
            self.event_bus.emit(order_event)
            
        # Update stats
        self.stats['orders_created'] += 1
        
        rule_id_str = f", rule_id: {rule_id}" if rule_id else ""
        logger.info(f"Emitting order event: {order_id} ({direction} {quantity} {symbol} @ {price}{rule_id_str})")
        return order_id
        
    def cancel_order(self, order_id):
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            bool: True if cancelled, False otherwise
        """
        # Check if order exists
        if order_id not in self.active_orders:
            logger.warning(f"Cannot cancel unknown order: {order_id}")
            return False
            
        # Get order data
        order_data = self.active_orders[order_id].copy()
        order_data['status'] = 'CANCELLED'
        
        # Create cancel event
        cancel_event = Event(EventType.ORDER_CANCEL, order_data)
        
        # Emit cancel event
        self.event_bus.emit(cancel_event)
        
        # Update stats
        self.stats['orders_cancelled'] += 1
        
        return True
        
    def handle_order(self, order_event):
        """
        Handle an order event.
        
        This method processes both complete orders and trading decisions from the risk manager.
        If the order_id is missing, it treats the event as a trading decision and adds the needed fields.
        
        Args:
            order_event: Order event to handle
        """
        # Check if this event has already been processed to avoid double-processing
        if hasattr(order_event, 'consumed') and order_event.consumed:
            logger.debug(f"Skipping already consumed order event")
            return
            
        order_data = order_event.data
        order_id = order_data.get('order_id')
        
        # If order_id is missing, treat this as a trading decision from the risk manager
        if order_id is None:
            # Generate a new order ID
            import uuid
            order_id = f"order_{uuid.uuid4().hex[:8]}"
            order_data['order_id'] = order_id
            
            # Add default order type if missing
            if 'order_type' not in order_data:
                order_data['order_type'] = 'MARKET'
                
            # Set status to PENDING
            order_data['status'] = 'PENDING'
            
            logger.info(f"Converting trading decision to order: {order_id} ({order_data.get('direction')} " +
                      f"{order_data.get('quantity')} {order_data.get('symbol')} @ {order_data.get('price')})")
        
        # Check if order is already being tracked to prevent duplicates
        if order_id in self.active_orders:
            # If already tracked and not PENDING, skip processing
            if self.active_orders[order_id].get('status') != 'PENDING':
                logger.debug(f"Order {order_id} already processed with status {self.active_orders[order_id].get('status')}")
                return
        # Ensure symbol exists
        if 'symbol' not in order_data:
            logger.warning(f"Order {order_id} missing 'symbol' field, adding default")
            order_data['symbol'] = 'UNKNOWN'
        
        # Ensure direction exists
        if 'direction' not in order_data:
            logger.warning(f"Order {order_id} missing 'direction' field, adding default BUY")
            order_data['direction'] = 'BUY'
        
        # Ensure size exists - check both size and quantity fields
        if 'size' not in order_data:
            # Check if quantity exists instead
            if 'quantity' in order_data:
                order_data['size'] = order_data['quantity']
                logger.info(f"Order {order_id} using quantity field {order_data['quantity']} for size")
            else:
                logger.warning(f"Order {order_id} missing 'size' field, adding default 1")
                order_data['size'] = 1
        
        # Ensure quantity field exists for backward compatibility
        if 'quantity' not in order_data and 'size' in order_data:
            order_data['quantity'] = order_data['size']
        
        # Track the order
        self.active_orders[order_id] = order_data
        
        # If broker is set, forward the order
        if self.broker:
            # Mark the event as consumed before forwarding to broker to prevent circular references
            if hasattr(order_event, 'consumed'):
                order_event.consumed = True
                
            self.broker.process_order(order_event)
            
    def handle_fill(self, fill_event):
        """
        Handle a fill event.
        
        Args:
            fill_event: Fill event to handle
        """
        # Check if this event has already been processed to avoid double-processing
        if hasattr(fill_event, 'consumed') and fill_event.consumed:
            logger.debug(f"Skipping already consumed fill event")
            return
            
        fill_data = fill_event.data
        order_id = fill_data.get('order_id')
        
        # Debug logging for fill event
        logger.info(f"Processing fill event for order_id: {order_id}")
        if fill_data:
            logger.debug(f"Fill data: {fill_data}")
        else:
            logger.warning(f"Empty fill data in fill event")
        
        # Update the order status
        if order_id in self.active_orders:
            # Get existing order
            order = self.active_orders[order_id]
            
            # Skip if already filled to prevent duplicate processing
            if order.get('status') == 'FILLED':
                logger.debug(f"Order {order_id} already filled, skipping duplicate fill event")
                return
            
            # Update order with fill information
            order['status'] = 'FILLED'
            order['fill_price'] = fill_data.get('fill_price')
            order['fill_time'] = fill_data.get('fill_time')
            
            # Make sure size exists (could be missing in some orders)
            if 'size' not in order:
                order['size'] = fill_data.get('size', 1)  # Default to 1 if not specified
                logger.warning(f"Order {order_id} missing 'size' field, using {order['size']}")
            
            # Safely log using get() to avoid KeyError
            logger.info(f"Updated order with fill: Order({order_id}, {order.get('symbol', 'UNKNOWN')}, "
                       f"{order.get('direction', 'UNKNOWN')}, {order.get('size', 0)}, FILLED)")
                       
            # Update stats
            self.stats['orders_filled'] += 1
            
            # Mark event as consumed
            if hasattr(fill_event, 'consumed'):
                fill_event.consumed = True
        else:
            logger.warning(f"Fill for unknown order: {order_id}")
            
    def handle_cancel(self, cancel_event):
        """
        Handle a cancel event.
        
        Args:
            cancel_event: Cancel event to handle
        """
        cancel_data = cancel_event.data
        order_id = cancel_data.get('order_id')
        
        # Update the order status
        if order_id in self.active_orders:
            self.active_orders[order_id]['status'] = 'CANCELLED'
            logger.info(f"Order cancelled: {order_id}")
        else:
            logger.warning(f"Cancel for unknown order: {order_id}")
            
    def handle_reject(self, reject_event):
        """
        Handle a reject event.
        
        Args:
            reject_event: Reject event to handle
        """
        reject_data = reject_event.data
        order_id = reject_data.get('order_id')
        
        # Update the order status
        if order_id in self.active_orders:
            self.active_orders[order_id]['status'] = 'REJECTED'
            self.active_orders[order_id]['reject_reason'] = reject_data.get('reason')
            logger.info(f"Order rejected: {order_id}, reason: {reject_data.get('reason')}")
            
            # Update stats
            self.stats['orders_rejected'] += 1
        else:
            logger.warning(f"Reject for unknown order: {order_id}")
            
    def get_active_orders(self):
        """
        Get all active orders.
        
        Returns:
            Dict: Active orders by order ID
        """
        return {order_id: data.copy() for order_id, data in self.active_orders.items() 
                if data.get('status') == 'PENDING'}
                
    def get_order(self, order_id):
        """
        Get an order by ID.
        
        Args:
            order_id: Order ID to get
            
        Returns:
            Dict: Order data if found, None otherwise
        """
        # First check local cache
        if order_id in self.active_orders:
            return self.active_orders[order_id].copy()
            
        # Then check event bus registry
        if self.event_bus and hasattr(self.event_bus, 'get_event_by_id'):
            return self.event_bus.get_event_by_id(order_id)
            
        return None
        
    def get_orders_by_rule_id(self, rule_id):
        """
        Get orders by rule ID.
        
        Args:
            rule_id: Rule ID to filter by
            
        Returns:
            List: Orders with the given rule ID
        """
        return [order for order in self.active_orders.values() if order.get('rule_id') == rule_id]
        
    def get_orders_by_symbol(self, symbol):
        """
        Get orders by symbol.
        
        Args:
            symbol: Symbol to filter by
            
        Returns:
            List: Orders for the given symbol
        """
        return [order for order in self.active_orders.values() if order.get('symbol') == symbol]
        
    def get_stats(self):
        """
        Get order manager statistics.
        
        Returns:
            Dict: Order manager statistics
        """
        # Update stats with current counts
        self.stats['active_orders'] = len(self.get_active_orders())
        self.stats['total_orders'] = len(self.active_orders)
        
        return self.stats.copy()
        
    def reset(self):
        """Reset the order manager state."""
        self.active_orders.clear()
        self.stats = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_cancelled': 0,
            'orders_rejected': 0
        }
        
        logger.info("Reset order manager")
        
    def _register_handlers(self):
        """Register event handlers."""
        if self.event_bus:
            # Register for order events (high priority)
            self.event_bus.register(EventType.ORDER, self.handle_order, priority=100)
            
            # Register for fill events
            self.event_bus.register(EventType.FILL, self.handle_fill)
            
            # Register for cancel events
            self.event_bus.register(EventType.ORDER_CANCEL, self.handle_cancel)
            
            # Register for reject events if available
            if hasattr(EventType, 'REJECT'):
                self.event_bus.register(EventType.REJECT, self.handle_reject)
