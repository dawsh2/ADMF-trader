"""
Moving Average Crossover Strategy Implementation - Simplified Version.

This strategy generates signals based purely on moving average crossovers:
- Buy signal (1): when a fast moving average crosses above a slow moving average
- Sell signal (-1): when a fast moving average crosses below a slow moving average
- Neutral (0): no crossover detected

This implementation follows the refactored architecture with clean separation
between signal generation and position management.
"""
import logging
from src.strategy.strategy_base import Strategy
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event

logger = logging.getLogger(__name__)

class SimpleMACrossoverStrategy(Strategy):
    """
    Simple Moving Average Crossover Strategy.
    
    Generates directional signals (1, -1, 0) based on the crossing of two moving averages.
    Strategies are responsible for analyzing market data and generating directional signals.
    Strategies should NOT track position state or handle trading decisions.
    """
    
    # Define name as a class variable for easier discovery
    name = "simple_ma_crossover"
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        """
        Initialize the MA Crossover strategy.
        
        Args:
            event_bus: Event bus for communication
            data_handler: Data handler for market data
            name: Optional strategy name override
            parameters: Initial strategy parameters
        """
        # Call parent constructor with name from class or override
        super().__init__(event_bus, data_handler, name or self.name, parameters)
        
        # Extract parameters with defaults - using smaller windows for more signals
        self.fast_window = self.parameters.get('fast_window', 5)
        self.slow_window = self.parameters.get('slow_window', 15)
        self.price_key = self.parameters.get('price_key', 'close')
        
        # Internal state for data storage only
        # Note: No position tracking - that's the risk manager's job
        self.data = {symbol: [] for symbol in self.symbols}
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
            
        logger.info(f"MA Crossover strategy initialized with fast_window={self.fast_window}, "
                   f"slow_window={self.slow_window}")
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        # Call parent configure first
        super().configure(config)
        
        # Update strategy-specific parameters
        self.fast_window = self.parameters.get('fast_window', 5)
        self.slow_window = self.parameters.get('slow_window', 15)
        self.price_key = self.parameters.get('price_key', 'close')
        
        # Reset data for all configured symbols
        self.data = {symbol: [] for symbol in self.symbols}
        
        logger.info(f"MA Crossover strategy configured with parameters: "
                   f"fast_window={self.fast_window}, slow_window={self.slow_window}")
    
    def on_bar(self, bar_event):
        """
        Process a bar event and generate directional signals based on moving average analysis.
        
        Args:
            bar_event: Market data bar event
            
        Returns:
            Optional signal event with directional value (1, -1, 0)
        """
        # Extract data from bar event
        symbol = bar_event.get_symbol()
        
        # Skip if not in our symbol list
        if symbol not in self.symbols:
            return None
        
        # Extract price data
        price = bar_event.get_close()
        timestamp = bar_event.get_timestamp()
        
        # Store data for this symbol
        if symbol not in self.data:
            self.data[symbol] = []
        
        self.data[symbol].append({
            'timestamp': timestamp,
            'price': price
        })
        
        # Check if we have enough data for both current and previous MAs
        # We need at least slow_window + 1 bars to calculate both current and previous slow MA
        required_bars = self.slow_window + 1
        if len(self.data[symbol]) < required_bars:
            logger.debug(f"Not enough data for {symbol}: have {len(self.data[symbol])}, need {required_bars}")
            return None
        
        # Calculate moving averages
        prices = [bar['price'] for bar in self.data[symbol]]
        
        # Calculate fast MA - current and previous
        # Ensure we have enough data for fast MA calculations
        if len(prices) < self.fast_window + 1:
            return None
            
        fast_ma = sum(prices[-self.fast_window:]) / self.fast_window
        fast_ma_prev = sum(prices[-(self.fast_window+1):-1]) / self.fast_window
        
        # Calculate slow MA - current and previous
        # This is safe now because we've verified we have enough data
        slow_ma = sum(prices[-self.slow_window:]) / self.slow_window
        slow_ma_prev = sum(prices[-(self.slow_window+1):-1]) / self.slow_window
        
        # Log MA values for debugging
        logger.debug(f"Symbol: {symbol}, Fast MA: {fast_ma:.2f}, Slow MA: {slow_ma:.2f}, " +
                   f"Prev Fast: {fast_ma_prev:.2f}, Prev Slow: {slow_ma_prev:.2f}")
        
        # Determine signal based on crossover
        signal_value = 0
        
        # Buy signal: fast MA crosses above slow MA
        if fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma:
            signal_value = 1
            logger.info(f"BUY signal for {symbol}: fast MA crossed above slow MA")
        
        # Sell signal: fast MA crosses below slow MA
        elif fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma:
            signal_value = -1
            logger.info(f"SELL signal for {symbol}: fast MA crossed below slow MA")
        
        # If we have a signal, create a signal event
        if signal_value != 0:
            # Create a signal event
            signal = create_signal_event(
                signal_value=signal_value,
                price=price,
                symbol=symbol,
                timestamp=timestamp
            )
            
            # Emit signal if we have an event bus
            if self.event_bus:
                self.event_bus.emit(signal)
                logger.info(f"Signal emitted for {symbol}: {signal_value}, timestamp={timestamp}")
            
            return signal
        
        return None
    
    def reset(self):
        """Reset the strategy state."""
        # Reset strategy-specific state
        self.data = {symbol: [] for symbol in self.symbols}
        
        logger.info(f"Simple MA Crossover strategy {self.name} reset")
