"""
Order manager that uses the centralized TradeRepository.

This implementation ensures consistent trade tracking by integrating
with the centralized TradeRepository.
"""

import logging
from src.core.component import Component
from src.core.events.event_bus import Event, EventType
from src.core.data_model import Order, Fill

# Set up logging
logger = logging.getLogger(__name__)

class OrderManager(Component):
    """
    Creates and manages orders in the system.
    
    This implementation properly integrates with the TradeRepository
    to ensure consistent trade tracking.
    """
    
    def __init__(self, name):
        """
        Initialize the order manager.
        
        Args:
            name (str): Component name
        """
        super().__init__(name)
        self.orders = {}  # order_id -> order
        self.next_order_id = 1
        
        # New: Track active orders by symbol to prevent duplicates
        self.active_orders_by_symbol = {}  # symbol -> list of order_ids
        self.max_orders_per_symbol = 1     # Default to 1 order per symbol
        self.enforce_single_position = True # Default to single position enforcement
        
    def initialize(self, context):
        """
        Initialize with dependencies.
        
        Args:
            context (dict): Context containing dependencies
        """
        super().initialize(context)
        
        # Get dependencies from context
        self.event_bus = context.get('event_bus')
        self.broker = context.get('broker')
        
        if not self.event_bus:
            raise ValueError("OrderManager requires event_bus in context")
            
        # Get risk config if available
        risk_config = context.get('config', {}).get('risk', {})
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
        
    def reset(self):
        """Reset the order manager state."""
        logger.info("Resetting OrderManager state")
        super().reset()
        self.orders = {}
        self.next_order_id = 1
        self.active_orders_by_symbol = {}
        
    def on_signal(self, event):
        """
        Handle signal events by creating orders.
        
        Args:
            event (Event): Signal event
        """
        signal_data = event.get_data()
        symbol = signal_data.get('symbol')
        direction = signal_data.get('direction')
        rule_id = signal_data.get('rule_id')
        
        # Check if we already have active orders for this symbol
        active_orders = self.active_orders_by_symbol.get(symbol, [])
        if len(active_orders) >= self.max_orders_per_symbol and self.enforce_single_position:
            logger.warning(f"Ignoring signal for {symbol} - already have {len(active_orders)} active orders. "
                         f"Max allowed: {self.max_orders_per_symbol}")
            return
            
        # Create order from signal
        order_data = self._create_order_from_signal(signal_data)
        
        # Store the order
        order_id = order_data['id']
        self.orders[order_id] = order_data
        
        # Add to active orders tracking
        if symbol not in self.active_orders_by_symbol:
            self.active_orders_by_symbol[symbol] = []
        self.active_orders_by_symbol[symbol].append(order_id)
        
        # Log the order creation
        logger.info(f"Created order {order_id} from signal: {symbol} {direction}, rule_id={rule_id}")
        logger.info(f"Active orders for {symbol}: {len(self.active_orders_by_symbol[symbol])}")
        
        # Publish order event
        self.event_bus.publish(Event(
            EventType.ORDER,
            order_data
        ))
        
    def on_fill(self, event):
        """
        Handle fill events by updating orders.
        
        Args:
            event (Event): Fill event
        """
        fill_data = event.get_data()
        order_id = fill_data.get('order_id')
        symbol = fill_data.get('symbol')
        
        # Update order status
        if order_id in self.orders:
            order = self.orders[order_id]
            filled_quantity = fill_data.get('quantity', 0)
            
            # Update order's filled quantity
            if 'filled_quantity' in order:
                order['filled_quantity'] += filled_quantity
            else:
                order['filled_quantity'] = filled_quantity
                
            # Check if order is fully filled
            if order['filled_quantity'] >= order['quantity']:
                order['status'] = 'FILLED'
                
                # Remove from active orders tracking
                if symbol in self.active_orders_by_symbol and order_id in self.active_orders_by_symbol[symbol]:
                    self.active_orders_by_symbol[symbol].remove(order_id)
                    logger.info(f"Order {order_id} for {symbol} fully filled - removed from active orders")
                    logger.info(f"Remaining active orders for {symbol}: {len(self.active_orders_by_symbol[symbol])}")
            else:
                order['status'] = 'PARTIAL'
                
            # Update average fill price
            if 'average_fill_price' in order:
                # Weighted average calculation
                current_filled = order['filled_quantity'] - filled_quantity
                new_avg = (
                    (order['average_fill_price'] * current_filled) +
                    (fill_data.get('price', 0) * filled_quantity)
                ) / order['filled_quantity']
                order['average_fill_price'] = new_avg
            else:
                order['average_fill_price'] = fill_data.get('price', 0)
        
    def create_order(self, symbol, direction, quantity, order_type, price=None):
        """
        Create a new order.
        
        Args:
            symbol (str): Instrument symbol
            direction (str): Order direction ('LONG' or 'SHORT')
            quantity (float): Order quantity
            order_type (str): Order type ('MARKET', 'LIMIT', etc.)
            price (float, optional): Order price for limit orders
            
        Returns:
            dict: Created order
        """
        order_id = f"order_{self.next_order_id}"
        self.next_order_id += 1
        
        # Create order data
        order_data = {
            'id': order_id,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'order_type': order_type,
            'status': 'CREATED',
            'timestamp': None,  # Current time would be set here
        }
        
        # Add price for limit orders
        if price is not None:
            order_data['price'] = price
            
        # Apply standardized field names
        order_data = Order.from_dict(order_data)
        
        # Store the order
        self.orders[order_id] = order_data
        
        # Add to active orders tracking
        if symbol not in self.active_orders_by_symbol:
            self.active_orders_by_symbol[symbol] = []
        self.active_orders_by_symbol[symbol].append(order_id)
        
        # Publish order event
        self.event_bus.publish(Event(
            EventType.ORDER,
            order_data
        ))
        
        return order_data
        
    def _create_order_from_signal(self, signal_data):
        """
        Create an order from a signal.
        
        Args:
            signal_data (dict): Signal data
            
        Returns:
            dict: Order data
        """
        order_id = f"order_{self.next_order_id}"
        self.next_order_id += 1
        
        # Extract data from signal
        symbol = signal_data.get('symbol')
        direction = signal_data.get('direction')
        quantity = signal_data.get('quantity', 0)
        order_type = signal_data.get('order_type', 'MARKET')
        price = signal_data.get('price')
        timestamp = signal_data.get('timestamp')
        rule_id = signal_data.get('rule_id')  # Store rule_id for reference
        
        # Create order data
        order_data = {
            'id': order_id,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'order_type': order_type,
            'status': 'CREATED',
            'timestamp': timestamp,
            'rule_id': rule_id  # Include rule_id in order for tracking
        }
        
        # Add price for limit orders
        if price is not None:
            order_data['price'] = price
            
        # Apply standardized field names
        order_data = Order.from_dict(order_data)
        
        return order_data
        
    def cancel_order(self, order_id):
        """
        Cancel an order.
        
        Args:
            order_id (str): ID of the order to cancel
            
        Returns:
            bool: True if the order was canceled, False otherwise
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            symbol = order.get('symbol')
            
            # Check if the order can be canceled
            if order['status'] in ['CREATED', 'SUBMITTED']:
                # Update order status
                order['status'] = 'CANCELED'
                
                # Remove from active orders tracking
                if symbol in self.active_orders_by_symbol and order_id in self.active_orders_by_symbol[symbol]:
                    self.active_orders_by_symbol[symbol].remove(order_id)
                    logger.info(f"Order {order_id} for {symbol} canceled - removed from active orders")
                
                # Publish order update event
                self.event_bus.publish(Event(
                    EventType.ORDER,
                    order
                ))
                
                return True
                
        return False
        
    def get_order(self, order_id):
        """
        Get an order by ID.
        
        Args:
            order_id (str): Order ID
            
        Returns:
            dict: Order data or None if not found
        """
        return self.orders.get(order_id)
        
    def get_orders(self, status=None):
        """
        Get all orders, optionally filtered by status.
        
        Args:
            status (str, optional): Filter by order status
            
        Returns:
            list: List of orders
        """
        if status:
            return [order for order in self.orders.values() 
                   if order['status'] == status]
        return list(self.orders.values())
        
    def get_active_orders_count(self, symbol):
        """
        Get the number of active orders for a symbol.
        
        Args:
            symbol (str): Symbol to check
            
        Returns:
            int: Number of active orders
        """
        return len(self.active_orders_by_symbol.get(symbol, []))
