"""
Simulated broker implementation that works with the event bus.
"""
import logging
import datetime
from typing import Dict, List, Any, Optional

from src.core.events.event_types import EventType, Event

logger = logging.getLogger(__name__)

class SimulatedBroker:
    """
    Simulated broker for backtesting with event bus integration.
    
    This implementation relies on the event bus for deduplication
    instead of a separate order registry.
    """
    
    def __init__(self, event_bus, order_registry=None):
        """
        Initialize the simulated broker.
        
        Args:
            event_bus: Event bus for event processing
            order_registry: Optional order registry (for backward compatibility)
        """
        self.event_bus = event_bus
        self.slippage = 0.0
        self.commission = 0.0
        self.fills = {}
        self.positions = {}
        self.stats = {
            'orders_received': 0,
            'orders_filled': 0,
            'orders_rejected': 0
        }
        
        # Register event handlers
        self._register_handlers()
        
        logger.info("Simulated broker initialized")
        
    def set_event_bus(self, event_bus):
        """
        Set the event bus.
        
        Args:
            event_bus: Event bus to use
        """
        self.event_bus = event_bus
        self._register_handlers()
        
    def set_order_registry(self, order_registry):
        """
        Set order registry (for backward compatibility).
        
        Args:
            order_registry: Order registry to use
        """
        # This method exists for backward compatibility but does nothing
        # as we now use the event bus directly for order tracking
        pass
        
    def process_order(self, order_event):
        """
        Process an order event.
        
        Args:
            order_event: Order event to process
            
        Returns:
            bool: True if processed, False otherwise
        """
        # Extract order data
        order_data = order_event.data
        order_id = order_data.get('order_id')
        
        # CRITICAL FIX: Generate order_id if missing rather than error
        if not order_id:
            import uuid
            order_id = f"order_{uuid.uuid4().hex[:8]}"
            order_data['order_id'] = order_id
            logger.info(f"Generated missing order_id: {order_id}")
        
        # Update stats
        self.stats['orders_received'] += 1
        
        # Check if this is a duplicate order (using rule_id)
        rule_id = order_data.get('rule_id')
        if rule_id and self._is_duplicate_order(rule_id, order_id):
            logger.info(f"Broker blocking duplicate order with rule_id: {rule_id}")
            return False
            
        # Apply simulated slippage to order price
        direction = order_data.get('direction', 'BUY')  # Default to BUY if missing
        price = order_data.get('price', 0.0)
        symbol = order_data.get('symbol', 'UNKNOWN')  # Default to UNKNOWN if missing
        size = order_data.get('size', 1)  # Default to 1 if missing
        
        # Log warning if any required fields were missing
        if 'direction' not in order_data or 'price' not in order_data or 'symbol' not in order_data or 'size' not in order_data:
            logger.warning(f"Order {order_id} missing required fields. Using defaults: direction={direction}, "
                          f"price={price}, symbol={symbol}, size={size}")
        
        # Calculate fill price with slippage
        fill_price = self._apply_slippage(price, direction)
        
        # Create fill data
        fill_data = order_data.copy()
        
        # Ensure all required fields exist in fill data
        fill_data['direction'] = direction
        fill_data['symbol'] = symbol
        fill_data['size'] = size
        fill_data['fill_price'] = fill_price
        fill_data['fill_time'] = datetime.datetime.now()
        fill_data['commission'] = self._calculate_commission(fill_price, size)
        
        # Store fill
        self.fills[order_id] = fill_data
        
        # Update position
        self._update_position(symbol, direction, size, fill_price)
        
        # Create fill event
        fill_event = Event(EventType.FILL, fill_data)
        
        # Set consumed flag to prevent duplicate processing
        fill_event.consumed = False
        
        logger.info(f"Broker processed order: {direction} {size} {symbol} @ {price}")
        logger.info(f"Fill event created with order_id: {order_id}")
        
        # Emit fill event
        self.event_bus.emit(fill_event)
        logger.debug(f"Fill event emitted for {symbol} with order_id: {order_id}")
        
        # Update stats
        self.stats['orders_filled'] += 1
        
        return True
        
    def cancel_order(self, order_id):
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            bool: True if cancelled, False otherwise
        """
        # In simulated broker, we don't have pending orders
        # The order is either filled immediately or rejected
        logger.info(f"Cancel request for order {order_id} ignored (orders are filled immediately)")
        return False
        
    def reject_order(self, order_id, reason="Unknown rejection reason"):
        """
        Reject an order.
        
        Args:
            order_id: Order ID to reject
            reason: Rejection reason
            
        Returns:
            bool: True if rejected, False otherwise
        """
        # Check if order exists in event bus registry
        if self.event_bus and hasattr(self.event_bus, 'get_event_by_id'):
            order_event = self.event_bus.get_event_by_id(order_id)
            if not order_event or order_event.get('type') != EventType.ORDER:
                logger.warning(f"Cannot reject unknown order: {order_id}")
                return False
                
            # Create rejection data
            reject_data = order_event.get('data', {}).copy()
            reject_data['status'] = 'REJECTED'
            reject_data['reject_reason'] = reason
            
            # Create reject event
            reject_event = Event(EventType.REJECT, reject_data)
            
            # Emit reject event
            self.event_bus.emit(reject_event)
            
            # Update stats
            self.stats['orders_rejected'] += 1
            
            return True
            
        return False
        
    def get_position(self, symbol):
        """
        Get position for a symbol.
        
        Args:
            symbol: Symbol to get position for
            
        Returns:
            Dict: Position data
        """
        return self.positions.get(symbol, {'symbol': symbol, 'size': 0, 'avg_price': 0.0})
        
    def get_positions(self):
        """
        Get all positions.
        
        Returns:
            Dict: Positions by symbol
        """
        return self.positions.copy()
        
    def get_fill(self, order_id):
        """
        Get fill for an order.
        
        Args:
            order_id: Order ID to get fill for
            
        Returns:
            Dict: Fill data if found, None otherwise
        """
        return self.fills.get(order_id)
        
    def get_stats(self):
        """
        Get broker statistics.
        
        Returns:
            Dict: Broker statistics
        """
        return self.stats.copy()
        
    def reset(self):
        """Reset the broker state."""
        self.fills.clear()
        self.positions.clear()
        self.stats = {
            'orders_received': 0,
            'orders_filled': 0,
            'orders_rejected': 0
        }
        
        logger.info("Broker reset")
        
    def _apply_slippage(self, price, direction):
        """
        Apply slippage to price.
        
        Args:
            price: Base price
            direction: Order direction (BUY/SELL)
            
        Returns:
            float: Price with slippage
        """
        if not price:
            return 0.0
            
        # For buys, slippage increases price
        # For sells, slippage decreases price
        slippage_factor = 1.0 + (self.slippage if direction == "BUY" else -self.slippage)
        
        return price * slippage_factor
        
    def _calculate_commission(self, price, size):
        """
        Calculate commission for a trade.
        
        Args:
            price: Trade price
            size: Trade size
            
        Returns:
            float: Commission amount
        """
        return price * size * self.commission
        
    def _update_position(self, symbol, direction, size, price):
        """
        Update position for a symbol.
        
        Args:
            symbol: Symbol to update
            direction: Order direction (BUY/SELL)
            size: Order size
            price: Fill price
        """
        if not symbol:
            return
            
        # Get current position
        position = self.get_position(symbol)
        current_size = position.get('size', 0)
        current_avg_price = position.get('avg_price', 0.0)
        
        # Calculate new position
        if direction == "BUY":
            # Buying increases position
            new_size = current_size + size
            
            # Calculate new average price (weighted average)
            if new_size > 0:
                new_avg_price = ((current_size * current_avg_price) + (size * price)) / new_size
            else:
                new_avg_price = 0.0
                
        else:  # SELL
            # Selling decreases position
            new_size = current_size - size
            
            # Keep average price if we still have a position
            if new_size > 0:
                new_avg_price = current_avg_price
            else:
                new_avg_price = 0.0
                
        # Update position
        self.positions[symbol] = {
            'symbol': symbol,
            'size': new_size,
            'avg_price': new_avg_price
        }
        
    def _is_duplicate_order(self, rule_id, order_id):
        """
        Check if an order is a duplicate.
        
        Uses the event bus to check if an order with the same
        rule ID has already been processed.
        
        Args:
            rule_id: Rule ID to check
            order_id: Order ID to check
            
        Returns:
            bool: True if duplicate, False otherwise
        """
        # Skip check if no rule ID
        if not rule_id:
            return False
            
        # Skip check if no event bus
        if not self.event_bus or not hasattr(self.event_bus, 'processed_events'):
            return False
            
        # Check if rule ID exists in processed orders
        if EventType.ORDER in self.event_bus.processed_events:
            processed_orders = self.event_bus.processed_events[EventType.ORDER]
            
            # Check if rule ID exists and is not the current order
            if rule_id in processed_orders:
                processed_order = processed_orders[rule_id]
                return processed_order.get('event_id') != order_id
                
        return False
        
    def _register_handlers(self):
        """Register event handlers."""
        if self.event_bus:
            # Register for order events
            self.event_bus.register(EventType.ORDER, self.handle_order)
            
    def handle_order(self, order_event):
        """
        Handle an order event.
        
        Args:
            order_event: Order event to handle
        """
        # Check if this event has already been processed to avoid double-processing
        if hasattr(order_event, 'consumed') and order_event.consumed:
            logger.debug(f"Skipping already consumed order event: {order_event.data.get('order_id')}")
            return
            
        # Process the order
        processed = self.process_order(order_event)
        
        # Mark event as consumed to prevent duplicate processing
        if processed and hasattr(order_event, 'consumed'):
            order_event.consumed = True
