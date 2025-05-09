"""
Order management system for handling orders.

This module provides classes for:
- Order creation and tracking
- Order status updates
- Order cancellation
"""
import logging
import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

from src.core.component import Component
from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType

logger = logging.getLogger(__name__)

class OrderManager(Component):
    """
    Order Manager for creating and managing orders.
    
    Responsible for:
    - Receiving signals and creating orders
    - Tracking order status
    - Handling fills
    - Preventing duplicate orders
    """
    
    def __init__(self, name=None, config=None):
        """
        Initialize order manager.
        
        Args:
            name: Optional component name
            config: Optional configuration dictionary
        """
        super().__init__(name or "order_manager")
        self.config = config or {}
        
        # Order tracking
        self.orders = {}  # order_id -> order
        self.order_history = []  # All orders (including completed)
        self.next_order_id = 1
        self.active_orders_by_symbol = {}  # symbol -> list of order_ids
        
        # Configuration
        self.max_orders_per_symbol = self.config.get('max_orders_per_symbol', 1)
        self.enforce_single_position = self.config.get('enforce_single_position', True)
        
        # State tracking
        self.state = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_rejected': 0
        }
        
        # Dependencies
        self.event_bus = None
        self.broker = None
        
        # Deduplication tracking
        self._processed_signal_ids = set()
    
    def initialize(self, context):
        """
        Initialize with dependencies.
        
        Args:
            context: Context dictionary containing dependencies
        """
        super().initialize(context)
        
        # Get dependencies from context
        self.event_bus = context.get('event_bus')
        self.broker = context.get('broker')
        
        if not self.event_bus:
            raise ValueError("OrderManager requires event_bus in context")
        
        # Get risk configuration if available
        risk_config = context.get('config', {}).get('risk', {})
        if isinstance(risk_config, dict):
            position_manager_config = risk_config.get('position_manager', {})
            
            # Apply risk management settings if provided
            if position_manager_config:
                if 'max_positions' in position_manager_config:
                    self.max_orders_per_symbol = position_manager_config['max_positions']
                    logger.info(f"Using max_orders_per_symbol from config: {self.max_orders_per_symbol}")
                    
                if 'enforce_single_position' in position_manager_config:
                    self.enforce_single_position = position_manager_config['enforce_single_position']
                    logger.info(f"Using enforce_single_position from config: {self.enforce_single_position}")
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.SIGNAL, self.on_signal)
        self.event_bus.subscribe(EventType.FILL, self.on_fill)
        
        logger.info(f"OrderManager initialized with max_orders_per_symbol={self.max_orders_per_symbol}")
    
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
        
        # Update configuration
        self.config.update(config_dict)
        
        # Apply configuration settings
        self.max_orders_per_symbol = self.config.get('max_orders_per_symbol', self.max_orders_per_symbol)
        self.enforce_single_position = self.config.get('enforce_single_position', self.enforce_single_position)
        
        logger.info(f"OrderManager reconfigured with max_orders_per_symbol={self.max_orders_per_symbol}")
    
    def reset(self):
        """Reset the order manager state."""
        super().reset()
        
        # Clear order tracking
        self.orders = {}
        self.order_history = []
        self.next_order_id = 1
        self.active_orders_by_symbol = {}
        
        # Reset state tracking
        self.state = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_rejected': 0
        }
        
        # Clear deduplication tracking
        self._processed_signal_ids = set()
        
        logger.info("OrderManager reset complete")
    
    def on_signal(self, event):
        """
        Process a signal event and create an order.
        
        Args:
            event: Signal event to process
        """
        # Extract signal data
        signal_data = event.data if hasattr(event, 'data') else {}
        
        # Get signal metadata
        symbol = signal_data.get('symbol')
        direction = signal_data.get('direction')
        quantity = signal_data.get('quantity', 0.0)
        
        # Skip invalid signals
        if not symbol or not direction or quantity <= 0:
            logger.warning(f"Skipping invalid signal: symbol={symbol}, direction={direction}, quantity={quantity}")
            return
        
        # Handle deduplication with rule_id
        rule_id = signal_data.get('rule_id')
        if rule_id:
            if rule_id in self._processed_signal_ids:
                logger.info(f"Skipping duplicate signal with rule_id: {rule_id}")
                return
            
            # Add to processed set
            self._processed_signal_ids.add(rule_id)
        
        # Check if we already have active orders for this symbol
        active_orders = self.active_orders_by_symbol.get(symbol, [])
        if len(active_orders) >= self.max_orders_per_symbol and self.enforce_single_position:
            logger.warning(f"Ignoring signal for {symbol} - already have {len(active_orders)} active orders. "
                          f"Max allowed: {self.max_orders_per_symbol}")
            self.state['orders_rejected'] += 1
            return
        
        # Create order from signal
        order = self._create_order_from_signal(signal_data)
        
        # Log the order creation
        logger.info(f"Created order {order['id']} from signal: {symbol} {direction}, quantity={quantity}")
        
        # Add to order tracking
        self.orders[order['id']] = order
        self.order_history.append(order.copy())
        
        # Add to active orders tracking
        if symbol not in self.active_orders_by_symbol:
            self.active_orders_by_symbol[symbol] = []
        self.active_orders_by_symbol[symbol].append(order['id'])
        
        # Update state
        self.state['orders_created'] += 1
        
        # Publish order event
        if self.event_bus:
            order_event = Event(EventType.ORDER, order)
            self.event_bus.publish(order_event)
    
    def on_fill(self, event):
        """
        Process a fill event and update order status.
        
        Args:
            event: Fill event to process
        """
        # Extract fill data
        fill_data = event.data if hasattr(event, 'data') else {}
        
        # Get fill metadata
        order_id = fill_data.get('order_id')
        symbol = fill_data.get('symbol')
        quantity = fill_data.get('quantity', 0.0)
        price = fill_data.get('price', 0.0)
        
        # Skip invalid fills
        if not order_id or not symbol or quantity <= 0 or price <= 0:
            logger.warning(f"Skipping invalid fill: order_id={order_id}, symbol={symbol}, "
                          f"quantity={quantity}, price={price}")
            return
        
        # Update order status
        if order_id in self.orders:
            order = self.orders[order_id]
            
            # Update filled quantity
            if 'filled_quantity' in order:
                order['filled_quantity'] += quantity
            else:
                order['filled_quantity'] = quantity
            
            # Update average fill price
            if 'average_fill_price' in order:
                # Weighted average calculation
                current_filled = order['filled_quantity'] - quantity
                new_avg = (
                    (order['average_fill_price'] * current_filled) +
                    (price * quantity)
                ) / order['filled_quantity']
                order['average_fill_price'] = new_avg
            else:
                order['average_fill_price'] = price
            
            # Check if order is fully filled
            if order['filled_quantity'] >= order['quantity']:
                order['status'] = 'FILLED'
                
                # Remove from active orders
                if symbol in self.active_orders_by_symbol and order_id in self.active_orders_by_symbol[symbol]:
                    self.active_orders_by_symbol[symbol].remove(order_id)
                
                # Update state
                self.state['orders_filled'] += 1
            else:
                order['status'] = 'PARTIAL'
            
            # Publish order update event
            if self.event_bus:
                order_event = Event(EventType.ORDER_UPDATE, order)
                self.event_bus.publish(order_event)
            
            logger.info(f"Updated order {order_id} with fill: quantity={quantity}, price={price}")
        else:
            logger.warning(f"Received fill for unknown order: {order_id}")
    
    def _create_order_from_signal(self, signal_data):
        """
        Create an order from a signal.
        
        Args:
            signal_data: Signal data dictionary
            
        Returns:
            dict: Order data
        """
        # Generate order ID
        order_id = f"order_{self.next_order_id}"
        self.next_order_id += 1
        
        # Extract signal fields
        symbol = signal_data.get('symbol')
        direction = signal_data.get('direction')
        quantity = signal_data.get('quantity', 0.0)
        price = signal_data.get('price', 0.0)
        order_type = signal_data.get('order_type', 'MARKET')
        rule_id = signal_data.get('rule_id')
        timestamp = signal_data.get('timestamp', datetime.datetime.now())
        
        # Create order object
        order = {
            'id': order_id,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'order_type': order_type,
            'rule_id': rule_id,
            'timestamp': timestamp,
            'status': 'CREATED',
            'filled_quantity': 0.0
        }
        
        # Include additional fields from signal if present
        for field in ['stop_price', 'limit_price', 'time_in_force', 'account_id']:
            if field in signal_data:
                order[field] = signal_data[field]
        
        return order
    
    def create_order(self, symbol, direction, quantity, price=0.0, order_type='MARKET'):
        """
        Create a new order directly.
        
        Args:
            symbol: Instrument symbol
            direction: Order direction ('BUY' or 'SELL')
            quantity: Order quantity
            price: Order price (for limit orders)
            order_type: Order type ('MARKET', 'LIMIT', etc.)
            
        Returns:
            dict: Created order
        """
        # Check if we can create an order for this symbol
        active_orders = self.active_orders_by_symbol.get(symbol, [])
        if len(active_orders) >= self.max_orders_per_symbol and self.enforce_single_position:
            logger.warning(f"Cannot create order for {symbol} - already have {len(active_orders)} active orders. "
                          f"Max allowed: {self.max_orders_per_symbol}")
            return None
        
        # Create order data
        order = {
            'id': f"order_{self.next_order_id}",
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'order_type': order_type,
            'timestamp': datetime.datetime.now(),
            'status': 'CREATED',
            'filled_quantity': 0.0
        }
        
        # Update counter
        self.next_order_id += 1
        
        # Add to order tracking
        self.orders[order['id']] = order
        self.order_history.append(order.copy())
        
        # Add to active orders tracking
        if symbol not in self.active_orders_by_symbol:
            self.active_orders_by_symbol[symbol] = []
        self.active_orders_by_symbol[symbol].append(order['id'])
        
        # Update state
        self.state['orders_created'] += 1
        
        # Publish order event
        if self.event_bus:
            order_event = Event(EventType.ORDER, order)
            self.event_bus.publish(order_event)
        
        logger.info(f"Created order {order['id']}: {symbol} {direction}, quantity={quantity}")
        
        return order
    
    def cancel_order(self, order_id):
        """
        Cancel an order.
        
        Args:
            order_id: ID of the order to cancel
            
        Returns:
            bool: True if canceled, False otherwise
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            
            # Check if order can be canceled
            if order['status'] not in ['FILLED', 'CANCELED', 'REJECTED']:
                # Update status
                order['status'] = 'CANCELED'
                
                # Remove from active orders
                symbol = order['symbol']
                if symbol in self.active_orders_by_symbol and order_id in self.active_orders_by_symbol[symbol]:
                    self.active_orders_by_symbol[symbol].remove(order_id)
                
                # Update state
                self.state['orders_canceled'] += 1
                
                # Publish order update event
                if self.event_bus:
                    order_event = Event(EventType.ORDER_UPDATE, order)
                    self.event_bus.publish(order_event)
                
                logger.info(f"Canceled order {order_id}")
                
                return True
        
        logger.warning(f"Could not cancel order {order_id} - not found or already filled/canceled")
        return False
    
    def get_order(self, order_id):
        """
        Get an order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            dict: Order data or None if not found
        """
        return self.orders.get(order_id)
    
    def get_orders(self, status=None, symbol=None):
        """
        Get orders filtered by status and/or symbol.
        
        Args:
            status: Optional status filter
            symbol: Optional symbol filter
            
        Returns:
            list: Filtered list of orders
        """
        filtered = self.orders.values()
        
        if status:
            filtered = [order for order in filtered if order['status'] == status]
        
        if symbol:
            filtered = [order for order in filtered if order['symbol'] == symbol]
        
        return list(filtered)
    
    def get_order_history(self):
        """
        Get complete order history.
        
        Returns:
            list: All orders processed
        """
        return self.order_history
    
    def get_active_orders(self, symbol=None):
        """
        Get all active (non-filled, non-canceled) orders.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            list: Active orders
        """
        active_statuses = ['CREATED', 'SUBMITTED', 'PARTIAL']
        filtered = [order for order in self.orders.values() if order['status'] in active_statuses]
        
        if symbol:
            filtered = [order for order in filtered if order['symbol'] == symbol]
        
        return filtered
    
    def get_active_order_count(self, symbol=None):
        """
        Get count of active orders.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            int: Number of active orders
        """
        if symbol:
            return len(self.active_orders_by_symbol.get(symbol, []))
        
        return sum(len(orders) for orders in self.active_orders_by_symbol.values())
    
    def get_stats(self):
        """
        Get order manager statistics.
        
        Returns:
            dict: Statistics dictionary
        """
        # Calculate additional stats
        total_orders = self.state['orders_created']
        active_orders = self.get_active_order_count()
        
        # Build stats dictionary
        stats = dict(self.state)
        stats.update({
            'total_orders': total_orders,
            'active_orders': active_orders,
            'orders_pending': active_orders,
            'fill_rate': self.state['orders_filled'] / total_orders if total_orders > 0 else 0.0,
            'cancel_rate': self.state['orders_canceled'] / total_orders if total_orders > 0 else 0.0,
            'rejection_rate': self.state['orders_rejected'] / total_orders if total_orders > 0 else 0.0
        })
        
        return stats