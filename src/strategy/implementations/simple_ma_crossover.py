"""
Simple Moving Average Crossover Strategy implementation.

This strategy generates buy signals when a fast moving average crosses above
a slow moving average, and sell signals when the fast MA crosses below the slow MA.
"""

import numpy as np
import pandas as pd
import logging
from src.core.component import Component
from src.core.events.event_bus import Event, EventType

# Set up logging
logger = logging.getLogger(__name__)

class SimpleMACrossoverStrategy(Component):
    """
    Simple Moving Average Crossover Strategy.
    
    This class implements a simple moving average crossover strategy
    that is fully compatible with the optimizer.
    """
    
    # Flag to identify this as a strategy
    is_strategy = True
    
    def __init__(self, name, fast_period=10, slow_period=30, position_size=100, 
                use_trailing_stop=False, stop_loss_pct=0.05):
        """
        Initialize the strategy.
        
        Args:
            name (str): Component name
            fast_period (int): Fast moving average period
            slow_period (int): Slow moving average period
            position_size (float): Position size in shares
            use_trailing_stop (bool): Whether to use trailing stop
            stop_loss_pct (float): Stop loss percentage
        """
        super().__init__(name)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.position_size = position_size
        self.use_trailing_stop = use_trailing_stop
        self.stop_loss_pct = stop_loss_pct
        
        # Internal data
        self.prices = {}  # symbol -> list of prices
        self.positions = {}  # symbol -> current position
        self.trailing_stops = {}  # symbol -> trailing stop level
        
        # New: Add state tracking to prevent duplicate signals and leakage
        self.active_signals = {}  # symbol -> current signal direction
        self.active_orders = {}   # symbol -> list of active order IDs
        self.signal_count = 0     # Counter for generating unique signal IDs
        
        logger.info(f"SimpleMACrossoverStrategy initialized with fast_period={fast_period}, slow_period={slow_period}")
        
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
            raise ValueError("Strategy requires event_bus in context")
            
        # New: Get risk config if available
        risk_config = context.get('config', {}).get('risk', {})
        position_manager_config = risk_config.get('position_manager', {})
        
        # Apply risk management settings if provided
        if position_manager_config:
            if 'fixed_quantity' in position_manager_config:
                self.position_size = position_manager_config['fixed_quantity']
                logger.info(f"Using fixed position size from config: {self.position_size}")
                
        # Subscribe to events
        self.event_bus.subscribe(EventType.BAR, self.on_bar)
        self.event_bus.subscribe(EventType.PORTFOLIO_UPDATE, self.on_portfolio_update)
        self.event_bus.subscribe(EventType.FILL, self.on_fill)
        
        logger.info(f"SimpleMACrossoverStrategy initialized with position_size={self.position_size}")
        
    def reset(self):
        """Reset the strategy state."""
        logger.info("Resetting SimpleMACrossoverStrategy state")
        super().reset()
        self.prices = {}
        self.positions = {}
        self.trailing_stops = {}
        
        # New: Reset state tracking
        self.active_signals = {}
        self.active_orders = {}
        self.signal_count = 0
        
    def on_bar(self, event):
        """
        Handle bar events by updating indicators and generating signals.
        
        Args:
            event (Event): Bar event
        """
        # Extract bar data
        bar_data = event.get_data()
        symbol = bar_data.get('symbol')
        close_price = bar_data.get('close')
        timestamp = bar_data.get('timestamp')
        
        # Initialize data structures for this symbol if needed
        if symbol not in self.prices:
            self.prices[symbol] = []
            self.positions[symbol] = 0
            self.active_signals[symbol] = None  # No active signal yet
            self.active_orders[symbol] = []     # No active orders yet
            
        # Add price to history
        self.prices[symbol].append(close_price)
        
        # Wait until we have enough data
        if len(self.prices[symbol]) < self.slow_period:
            return
            
        # Calculate moving averages
        fast_ma = np.mean(self.prices[symbol][-self.fast_period:])
        slow_ma = np.mean(self.prices[symbol][-self.slow_period:])
        
        # Previous moving averages
        prev_prices = self.prices[symbol][:-1]
        prev_fast_ma = np.mean(prev_prices[-self.fast_period:]) if len(prev_prices) >= self.fast_period else None
        prev_slow_ma = np.mean(prev_prices[-self.slow_period:]) if len(prev_prices) >= self.slow_period else None
        
        # Debug log moving averages
        prev_fast_str = f"{prev_fast_ma:.2f}" if prev_fast_ma is not None else "None"
        prev_slow_str = f"{prev_slow_ma:.2f}" if prev_slow_ma is not None else "None"
        logger.debug(f"Symbol: {symbol}, Price: {close_price}, Fast MA: {fast_ma:.2f}, Slow MA: {slow_ma:.2f}, " +
                    f"Prev Fast: {prev_fast_str}, Prev Slow: {prev_slow_str}")
        
        # New: Check if we already have active orders for this symbol
        if len(self.active_orders[symbol]) > 0:
            logger.debug(f"Symbol {symbol} already has {len(self.active_orders[symbol])} active orders, " + 
                        f"position: {self.positions[symbol]}. Skipping signal generation.")
            return
            
        # Check for crossover (if we have previous values)
        if prev_fast_ma is not None and prev_slow_ma is not None:
            # Long signal: fast MA crosses above slow MA
            if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
                # Only enter if not already long and no active signal
                if self.positions[symbol] <= 0 and self.active_signals[symbol] != 'LONG':
                    logger.info(f"LONG signal generated for {symbol}: Fast MA ({fast_ma:.2f}) crossed above Slow MA ({slow_ma:.2f})")
                    self._generate_signal(symbol, 'LONG', close_price, timestamp)
                    
            # Short signal: fast MA crosses below slow MA
            elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
                # Only enter if not already short and no active signal
                if self.positions[symbol] >= 0 and self.active_signals[symbol] != 'SHORT':
                    logger.info(f"SHORT signal generated for {symbol}: Fast MA ({fast_ma:.2f}) crossed below Slow MA ({slow_ma:.2f})")
                    self._generate_signal(symbol, 'SHORT', close_price, timestamp)
        
    def on_portfolio_update(self, event):
        """
        Handle portfolio update events by tracking positions.
        
        Args:
            event (Event): Portfolio update event
        """
        portfolio_data = event.get_data()
        positions = portfolio_data.get('positions', {})
        
        # Update positions
        for symbol, position in positions.items():
            old_position = self.positions.get(symbol, 0)
            self.positions[symbol] = position
            
            # Log position changes
            if old_position != position:
                logger.info(f"Position update for {symbol}: {old_position} → {position}")
                
                # Clear active signal if position is flat (zero)
                if position == 0 and symbol in self.active_signals:
                    logger.info(f"Clearing active signal for {symbol} as position is now flat")
                    self.active_signals[symbol] = None
                
    def on_fill(self, event):
        """
        Handle fill events by tracking orders.
        
        Args:
            event (Event): Fill event
        """
        fill_data = event.get_data()
        order_id = fill_data.get('order_id')
        symbol = fill_data.get('symbol')
        
        # Remove order from active orders if it's in our tracking
        if symbol in self.active_orders and order_id in self.active_orders[symbol]:
            logger.info(f"Order {order_id} for {symbol} has been filled, removing from active orders")
            self.active_orders[symbol].remove(order_id)
            
    def _generate_signal(self, symbol, direction, price, timestamp):
        """
        Generate a trading signal.
        
        Args:
            symbol (str): Instrument symbol
            direction (str): Signal direction ('LONG' or 'SHORT')
            price (float): Current price
            timestamp (datetime): Signal timestamp
        """
        # Calculate quantity based on position size and current position
        quantity = self.position_size
        if direction == 'SHORT' and self.positions.get(symbol, 0) > 0:
            # Closing long position
            quantity = abs(self.positions.get(symbol, 0))
        elif direction == 'LONG' and self.positions.get(symbol, 0) < 0:
            # Closing short position
            quantity = abs(self.positions.get(symbol, 0))
            
        # Generate a unique rule_id for this signal
        self.signal_count += 1
        rule_id = f"{self.name}_{symbol}_{direction}_{self.signal_count}"
            
        # Create signal data
        signal_data = {
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'timestamp': timestamp,
            'order_type': 'MARKET',
            'rule_id': rule_id  # Add rule_id for better tracking
        }
        
        # Update active signal tracking
        self.active_signals[symbol] = direction
        
        # Log the signal with more details
        logger.info(f"Signal generated: {symbol} {direction}, quantity={quantity}, " +
                  f"price={price}, rule_id={rule_id}")
        
        # Publish signal event
        self.event_bus.publish(Event(
            EventType.SIGNAL,
            signal_data
        ))
        
        # Set up trailing stop if entering new position
        if self.use_trailing_stop:
            if direction == 'LONG':
                self.trailing_stops[symbol] = price * (1 - self.stop_loss_pct)
            elif direction == 'SHORT':
                self.trailing_stops[symbol] = price * (1 + self.stop_loss_pct)
