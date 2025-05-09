"""
Simulated broker for backtesting that works with the improved architecture.

This implementation simulates order execution and generates fills
for the backtest system.
"""

from src.core.component import Component
from src.core.events.event_bus import Event, EventType
from src.core.data_model import Fill

class SimulatedBroker(Component):
    """
    Simulates order execution for backtesting.
    
    This component processes orders and generates fills based on
    market data in the backtest environment.
    """
    
    def __init__(self, name, commission_model=None):
        """
        Initialize the simulated broker.
        
        Args:
            name (str): Component name
            commission_model (callable, optional): Function to calculate commissions
        """
        super().__init__(name)
        self.commission_model = commission_model or self._default_commission
        self.latest_prices = {}  # symbol -> latest price
        self.pending_orders = []  # Orders waiting to be processed
        
    def initialize(self, context):
        """
        Initialize with dependencies.
        
        Args:
            context (dict): Context containing dependencies
        """
        super().initialize(context)
        
        # Get event bus from context
        self.event_bus = context.get('event_bus')
        
        if not self.event_bus:
            raise ValueError("SimulatedBroker requires event_bus in context")
            
        # Subscribe to events
        self.event_bus.subscribe(EventType.BAR, self.on_bar)
        self.event_bus.subscribe(EventType.ORDER, self.on_order)
        
    def reset(self):
        """Reset the broker state."""
        super().reset()
        self.latest_prices = {}
        self.pending_orders = []
        
    def on_bar(self, event):
        """
        Handle bar events by updating prices and processing orders.
        
        Args:
            event (Event): Bar event
        """
        bar_data = event.get_data()
        symbol = bar_data.get('symbol')
        
        # Update latest price
        self.latest_prices[symbol] = {
            'open': bar_data.get('open'),
            'high': bar_data.get('high'),
            'low': bar_data.get('low'),
            'close': bar_data.get('close'),
            'timestamp': bar_data.get('timestamp')
        }
        
        # Process pending orders for this symbol
        self._process_orders(symbol)
        
    def on_order(self, event):
        """
        Handle order events by adding to pending orders.
        
        Args:
            event (Event): Order event
        """
        order_data = event.get_data()
        
        # Only process new orders
        if order_data.get('status') == 'CREATED':
            # Update status to SUBMITTED
            order_data['status'] = 'SUBMITTED'
            
            # Add to pending orders
            self.pending_orders.append(order_data)
            
            # Process immediately if we have price data
            symbol = order_data.get('symbol')
            if symbol in self.latest_prices:
                self._process_orders(symbol)
                
    def _process_orders(self, symbol):
        """
        Process pending orders for a symbol.
        
        Args:
            symbol (str): Symbol to process orders for
        """
        if symbol not in self.latest_prices:
            return
            
        # Get latest price data
        price_data = self.latest_prices[symbol]
        
        # Find orders for this symbol
        orders_to_process = [o for o in self.pending_orders if o.get('symbol') == symbol]
        
        # Process each order
        for order in orders_to_process:
            # Check if order can be filled
            can_fill, fill_price = self._check_fill_conditions(order, price_data)
            
            if can_fill:
                # Generate fill
                fill_data = self._create_fill(order, fill_price, price_data.get('timestamp'))
                
                # Remove from pending orders
                self.pending_orders.remove(order)
                
                # Publish fill event
                self.event_bus.publish(Event(
                    EventType.FILL,
                    fill_data
                ))
                
    def _check_fill_conditions(self, order, price_data):
        """
        Check if an order can be filled with the current price data.
        
        Args:
            order (dict): Order to check
            price_data (dict): Current price data
            
        Returns:
            tuple: (can_fill, fill_price)
        """
        order_type = order.get('order_type')
        
        # For market orders, always fill at the current price
        if order_type == 'MARKET':
            return True, price_data.get('close')
            
        # For limit orders, check price conditions
        elif order_type == 'LIMIT':
            limit_price = order.get('price')
            direction = order.get('direction')
            
            if direction == 'LONG' and price_data.get('low') <= limit_price:
                # Long limit order - can fill if price goes below limit
                return True, min(price_data.get('open'), limit_price)
                
            elif direction == 'SHORT' and price_data.get('high') >= limit_price:
                # Short limit order - can fill if price goes above limit
                return True, max(price_data.get('open'), limit_price)
                
        # For stop orders, check price conditions
        elif order_type == 'STOP':
            stop_price = order.get('price')
            direction = order.get('direction')
            
            if direction == 'LONG' and price_data.get('high') >= stop_price:
                # Long stop order - can fill if price goes above stop
                return True, max(price_data.get('open'), stop_price)
                
            elif direction == 'SHORT' and price_data.get('low') <= stop_price:
                # Short stop order - can fill if price goes below stop
                return True, min(price_data.get('open'), stop_price)
                
        # Default - cannot fill
        return False, None
        
    def _create_fill(self, order, fill_price, timestamp):
        """
        Create a fill for an order.
        
        Args:
            order (dict): Order being filled
            fill_price (float): Price of the fill
            timestamp (datetime): Time of the fill
            
        Returns:
            dict: Fill data
        """
        # Calculate commission
        commission = self.commission_model(order, fill_price)
        
        # Create fill data
        fill_data = {
            'id': f"fill_{order.get('id')}",
            'order_id': order.get('id'),
            'symbol': order.get('symbol'),
            'direction': order.get('direction'),
            'quantity': order.get('quantity'),
            'price': fill_price,
            'timestamp': timestamp,
            'commission': commission
        }
        
        # Apply standardized field names
        fill_data = Fill.from_dict(fill_data)
        
        return fill_data
        
    def _default_commission(self, order, fill_price):
        """
        Default commission model.
        
        Args:
            order (dict): Order being filled
            fill_price (float): Price of the fill
            
        Returns:
            float: Commission amount
        """
        # Simple percentage commission
        commission_rate = 0.001  # 0.1%
        commission = order.get('quantity', 0) * fill_price * commission_rate
        return commission
