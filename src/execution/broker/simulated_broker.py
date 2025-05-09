"""
Simulated broker for backtesting that works with the improved architecture.

This implementation simulates order execution and generates fills
for the backtest system.
"""

import logging
import uuid
import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

from src.core.component import Component
from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType
from src.execution.broker.slippage_model import FixedSlippageModel
from src.execution.broker.commission_model import CommissionModel

# Set up logging
logger = logging.getLogger(__name__)

class SimulatedBroker(Component):
    """
    Simulates order execution for backtesting.
    
    This component processes orders and generates fills based on
    market data in the backtest environment.
    """
    
    def __init__(self, name="simulated_broker", config=None):
        """
        Initialize the simulated broker.
        
        Args:
            name: Component name
            config: Optional configuration dictionary
        """
        super().__init__(name)
        self.config = config or {}
        
        # Initialize models
        self.commission_model = CommissionModel()
        self.slippage_model = FixedSlippageModel()
        
        # Trading state
        self.latest_prices = {}  # symbol -> price data
        self.pending_orders = []  # Orders waiting to be processed
        self.filled_orders = {}  # order_id -> fill_data
        self.rejected_orders = {}  # order_id -> reject_reason
        
        # Stats tracking
        self.stats = {
            'orders_received': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'partial_fills': 0,
            'total_commission': 0.0
        }
        
        # Configure from config
        if self.config:
            self._configure_from_dict(self.config)
        
    def initialize(self, context):
        """
        Initialize with dependencies.
        
        Args:
            context: Context dictionary containing dependencies
        """
        super().initialize(context)
        
        # Get event bus from context
        self.event_bus = context.get('event_bus')
        
        # Get market simulator if available
        self.market_simulator = context.get('market_simulator')
        
        # Get portfolio from context if available (for convenience)
        self.portfolio = context.get('portfolio')
        
        if not self.event_bus:
            raise ValueError("SimulatedBroker requires event_bus in context")
            
        # Subscribe to events
        self.event_bus.subscribe(EventType.BAR, self.on_bar)
        self.event_bus.subscribe(EventType.ORDER, self.on_order)
        
        # Initialize stats tracking
        self.stats = {
            'orders_received': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'partial_fills': 0,
            'total_commission': 0.0
        }
        
    def reset(self):
        """Reset the broker state."""
        super().reset()
        self.latest_prices = {}
        self.pending_orders = []
        self.filled_orders = {}
        self.rejected_orders = {}
        
        # Reset stats
        self.stats = {
            'orders_received': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'partial_fills': 0,
            'total_commission': 0.0
        }
        
        logger.info(f"{self.name} reset completed")
        
    def on_bar(self, event):
        """
        Handle bar events by updating prices and processing orders.
        
        Args:
            event: Bar event
        """
        # Get bar data from event (handles both actual events and mocks)
        if hasattr(event, 'get_data') and callable(event.get_data):
            bar_data = event.get_data()
        elif hasattr(event, 'data'):
            bar_data = event.data
        else:
            logger.warning("Received bar event with no data")
            return
            
        # Get symbol from bar data
        symbol = bar_data.get('symbol')
        if not symbol:
            logger.warning("Received bar data without symbol")
            return
            
        try:
            # Convert any numeric strings to floats, handling errors
            open_price = float(bar_data.get('open', 0.0)) if bar_data.get('open') is not None else None
            high_price = float(bar_data.get('high', 0.0)) if bar_data.get('high') is not None else None
            low_price = float(bar_data.get('low', 0.0)) if bar_data.get('low') is not None else None
            close_price = float(bar_data.get('close', 0.0)) if bar_data.get('close') is not None else None
            
            # Update latest price
            self.latest_prices[symbol] = {
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'timestamp': bar_data.get('timestamp')
            }
            
            # Log the price update
            if close_price is not None:
                logger.info(f"Updated price for {symbol}: close={close_price:.4f}")
            else:
                logger.warning(f"Updated price for {symbol} with missing close price")
                
            # Also update market simulator directly if available
            if self.market_simulator and hasattr(self.market_simulator, 'update_price_data'):
                # Ensure data is passed to market simulator for consistent price state
                self.market_simulator.update_price_data(symbol, bar_data)
                logger.debug(f"Forwarded price update to market simulator for {symbol}")
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Error converting price data for {symbol}: {e}")
            logger.warning(f"Bar data: {bar_data}")
        
        # Process pending orders for this symbol
        self._process_orders(symbol)
        
    def on_order(self, event):
        """
        Handle order events by adding to pending orders.
        
        Args:
            event: Order event
        """
        # Get order data from event (handles both actual events and mocks)
        if hasattr(event, 'get_data') and callable(event.get_data):
            order_data = event.get_data()
        elif hasattr(event, 'data'):
            order_data = event.data
        else:
            logger.warning("Received order event with no data")
            return
            
        # Update stats
        self.stats['orders_received'] += 1
        
        # Only process new orders
        if order_data.get('status', 'CREATED') == 'CREATED':
            # Update status to SUBMITTED
            order_data['status'] = 'SUBMITTED'
            
            # Add to pending orders
            self.pending_orders.append(order_data)
            
            # Process immediately if we have price data
            symbol = order_data.get('symbol')
            if symbol and symbol in self.latest_prices:
                self._process_orders(symbol)
                
    def _process_orders(self, symbol):
        """
        Process pending orders for a symbol.
        
        Args:
            symbol: Symbol to process orders for
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
            if self.market_simulator and hasattr(self.market_simulator, 'check_fill_conditions'):
                # Use market simulator for more sophisticated fill logic
                can_fill, fill_price = self.market_simulator.check_fill_conditions(order)
            else:
                # Use default fill logic
                can_fill, fill_price = self._check_fill_conditions(order, price_data)
            
            if can_fill:
                # Apply slippage to fill price
                quantity = order.get('quantity', 0)
                direction = order.get('direction', 'BUY')
                fill_price = self.slippage_model.apply_slippage(fill_price, quantity, direction)
                
                # Generate fill
                fill_data = self._create_fill(order, fill_price, price_data.get('timestamp'))
                
                # Store fill for reference
                self.filled_orders[order.get('id')] = fill_data
                
                # Remove from pending orders
                self.pending_orders.remove(order)
                
                # Update stats
                self.stats['orders_filled'] += 1
                self.stats['total_commission'] += fill_data.get('commission', 0.0)
                
                # Publish fill event
                self.event_bus.publish(Event(EventType.FILL, fill_data))
                
    def _check_fill_conditions(self, order, price_data):
        """
        Check if an order can be filled with the current price data.
        
        Args:
            order (dict): Order to check
            price_data (dict): Current price data
            
        Returns:
            tuple: (can_fill, fill_price)
        """
        # If we have a market simulator, use it instead
        if hasattr(self, 'market_simulator') and self.market_simulator:
            return self.market_simulator.check_fill_conditions(order)
            
        # Fallback to simple checks if no market simulator available
        order_type = order.get('order_type')
        
        # For market orders, always fill at the current price
        if order_type == 'MARKET':
            return True, price_data.get('close')
            
        # For limit orders, check price conditions
        elif order_type == 'LIMIT':
            limit_price = order.get('price')
            direction = order.get('direction')
            
            if direction == 'BUY' and price_data.get('low') <= limit_price:
                # Buy limit order - can fill if price goes below limit
                return True, min(price_data.get('open'), limit_price)
                
            elif direction == 'SELL' and price_data.get('high') >= limit_price:
                # Sell limit order - can fill if price goes above limit
                return True, max(price_data.get('open'), limit_price)
                
        # For stop orders, check price conditions
        elif order_type == 'STOP':
            stop_price = order.get('price')
            direction = order.get('direction')
            
            if direction == 'BUY' and price_data.get('high') >= stop_price:
                # Buy stop order - can fill if price goes above stop
                return True, max(price_data.get('open'), stop_price)
                
            elif direction == 'SELL' and price_data.get('low') <= stop_price:
                # Sell stop order - can fill if price goes below stop
                return True, min(price_data.get('open'), stop_price)
                
        # Default - cannot fill
        return False, None
        
    def _create_fill(self, order, fill_price, timestamp):
        """
        Create a fill for an order.
        
        Args:
            order: Order being filled
            fill_price: Price of the fill
            timestamp: Time of the fill
            
        Returns:
            dict: Fill data
        """
        # Extract order details
        order_id = order.get('id')
        symbol = order.get('symbol')
        direction = order.get('direction')
        quantity = order.get('quantity')
        rule_id = order.get('rule_id')
        
        # Make sure we have a timestamp
        timestamp = timestamp or datetime.datetime.now()
        
        # Calculate commission
        commission = self.commission_model.calculate(fill_price, quantity)
        
        # Create fill data
        fill_data = {
            'id': f"fill_{order_id}",
            'order_id': order_id,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': fill_price,
            'timestamp': timestamp,
            'commission': commission,
            'rule_id': rule_id
        }
        
        logger.info(f"Created fill for order {order_id}: {direction} {quantity} {symbol} @ {fill_price:.4f}")
        
        return fill_data
        
    def configure(self, config):
        """
        Configure the broker with parameters.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        self._configure_from_dict(config_dict)
        
        logger.info(f"{self.name} configured successfully")
    
    def _configure_from_dict(self, config_dict):
        """
        Configure from dictionary.
        
        Args:
            config_dict: Configuration dictionary
        """
        # Configure commission model
        if 'commission' in config_dict:
            self.commission_model.configure(config_dict['commission'])
        
        # Configure slippage model
        if 'slippage' in config_dict:
            slippage_config = config_dict['slippage']
            
            # Check if we need to create a different slippage model
            if 'model' in slippage_config:
                model_type = slippage_config['model']
                if model_type == 'variable':
                    from src.execution.broker.slippage_model import VariableSlippageModel
                    self.slippage_model = VariableSlippageModel()
            
            # Configure the slippage model
            self.slippage_model.configure(slippage_config)
    
    def cancel_order(self, order_id):
        """
        Cancel an order.
        
        Args:
            order_id: ID of the order to cancel
            
        Returns:
            bool: True if canceled, False otherwise
        """
        # Find the order in pending orders
        for i, order in enumerate(self.pending_orders):
            if order.get('id') == order_id:
                # Remove from pending orders
                removed_order = self.pending_orders.pop(i)
                
                # Create canceled order event
                canceled_data = removed_order.copy()
                canceled_data['status'] = 'CANCELED'
                canceled_data['cancel_time'] = datetime.datetime.now()
                
                # Publish order update event
                self.event_bus.publish(Event(EventType.ORDER_UPDATE, canceled_data))
                
                logger.info(f"Canceled order {order_id}")
                return True
        
        logger.warning(f"Could not cancel order {order_id} - not found in pending orders")
        return False
    
    def reject_order(self, order_id, reason="Order rejected by broker"):
        """
        Reject an order.
        
        Args:
            order_id: ID of the order to reject
            reason: Rejection reason
            
        Returns:
            bool: True if rejected, False otherwise
        """
        # Find the order in pending orders
        for i, order in enumerate(self.pending_orders):
            if order.get('id') == order_id:
                # Remove from pending orders
                removed_order = self.pending_orders.pop(i)
                
                # Store rejection
                self.rejected_orders[order_id] = {
                    'order': removed_order,
                    'reason': reason,
                    'timestamp': datetime.datetime.now()
                }
                
                # Create rejected order event
                rejected_data = removed_order.copy()
                rejected_data['status'] = 'REJECTED'
                rejected_data['reject_reason'] = reason
                rejected_data['reject_time'] = datetime.datetime.now()
                
                # Publish order update event
                self.event_bus.publish(Event(EventType.ORDER_UPDATE, rejected_data))
                
                # Update stats
                self.stats['orders_rejected'] += 1
                
                logger.info(f"Rejected order {order_id}: {reason}")
                return True
        
        logger.warning(f"Could not reject order {order_id} - not found in pending orders")
        return False
    
    def get_fill(self, order_id):
        """
        Get fill information for an order.
        
        Args:
            order_id: ID of the order
            
        Returns:
            dict: Fill data or None if not filled
        """
        return self.filled_orders.get(order_id)
    
    def get_stats(self):
        """
        Get broker statistics.
        
        Returns:
            dict: Broker statistics
        """
        return dict(self.stats)
