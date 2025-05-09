"""
Simple Moving Average Crossover Strategy implementation.

This strategy generates buy signals when a fast moving average crosses above
a slow moving average, and sell signals when the fast MA crosses below the slow MA.
"""

import numpy as np
import pandas as pd
from src.core.component import Component
from src.core.events.event_bus import Event, EventType

class SimpleMACrossoverStrategy(Component):
    """
    Simple Moving Average Crossover Strategy.
    
    This strategy trades based on moving average crossovers.
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
            
        # Subscribe to events
        self.event_bus.subscribe(EventType.BAR, self.on_bar)
        self.event_bus.subscribe(EventType.PORTFOLIO_UPDATE, self.on_portfolio_update)
        
    def reset(self):
        """Reset the strategy state."""
        super().reset()
        self.prices = {}
        self.positions = {}
        self.trailing_stops = {}
        
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
        
        # Check for crossover (if we have previous values)
        if prev_fast_ma is not None and prev_slow_ma is not None:
            # Long signal: fast MA crosses above slow MA
            if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
                # Only enter if not already long
                if self.positions[symbol] <= 0:
                    self._generate_signal(symbol, 'LONG', close_price, timestamp)
                    
            # Short signal: fast MA crosses below slow MA
            elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
                # Only enter if not already short
                if self.positions[symbol] >= 0:
                    self._generate_signal(symbol, 'SHORT', close_price, timestamp)
                    
        # Check trailing stops if active
        if self.use_trailing_stop and symbol in self.trailing_stops:
            if self.positions[symbol] > 0:  # Long position
                # Update trailing stop
                self.trailing_stops[symbol] = max(
                    self.trailing_stops[symbol],
                    close_price * (1 - self.stop_loss_pct)
                )
                
                # Check if stop is hit
                if close_price < self.trailing_stops[symbol]:
                    self._generate_signal(symbol, 'SHORT', close_price, timestamp)
                    
            elif self.positions[symbol] < 0:  # Short position
                # Update trailing stop
                self.trailing_stops[symbol] = min(
                    self.trailing_stops[symbol],
                    close_price * (1 + self.stop_loss_pct)
                )
                
                # Check if stop is hit
                if close_price > self.trailing_stops[symbol]:
                    self._generate_signal(symbol, 'LONG', close_price, timestamp)
                    
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
            self.positions[symbol] = position
            
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
            
        # Create signal data
        signal_data = {
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'timestamp': timestamp,
            'order_type': 'MARKET'
        }
        
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
