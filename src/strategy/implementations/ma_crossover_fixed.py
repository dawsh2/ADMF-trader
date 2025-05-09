"""
Fixed Moving Average Crossover Strategy Implementation.

This version includes fixes to automatically add symbols from incoming bar events.
"""
import logging
from src.strategy.strategy_base import Strategy
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event
import traceback

logger = logging.getLogger(__name__)

class MACrossoverStrategy(Strategy):
    """
    Moving Average Crossover strategy implementation with auto-symbol detection.
    
    This version will automatically add symbols from incoming bar events
    to ensure no events are lost due to symbol configuration issues.
    """
    
    # Define name as a class variable for easier discovery
    name = "ma_crossover"
    
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
        
        # Extract parameters with defaults
        self.fast_window = self.parameters.get('fast_window', 5)
        self.slow_window = self.parameters.get('slow_window', 15)
        self.price_key = self.parameters.get('price_key', 'close')
        
        # Get symbols from data handler if available
        self.symbols = self.parameters.get('symbols', [])
        
        # Try multiple sources for symbols
        if not self.symbols:
            # Try data handler's get_symbols method
            if hasattr(data_handler, 'get_symbols') and callable(data_handler.get_symbols):
                try:
                    handler_symbols = data_handler.get_symbols()
                    if handler_symbols:
                        self.symbols = handler_symbols
                        logger.info(f"Got symbols from data handler: {self.symbols}")
                except Exception as e:
                    logger.warning(f"Error getting symbols from data handler: {e}")
            
            # Try data handler's data dictionary
            if not self.symbols and hasattr(data_handler, 'data') and isinstance(data_handler.data, dict):
                self.symbols = list(data_handler.data.keys())
                logger.info(f"Got symbols from data handler data keys: {self.symbols}")
            
            # Try data handler's config sources
            if not self.symbols and hasattr(data_handler, 'data_config'):
                config = data_handler.data_config
                if isinstance(config, dict) and 'sources' in config:
                    sources = config['sources']
                    if isinstance(sources, list):
                        self.symbols = [s.get('symbol') for s in sources if s.get('symbol')]
                        logger.info(f"Got symbols from data config sources: {self.symbols}")
            
            # Default to HEAD if still no symbols
            if not self.symbols:
                self.symbols = ["HEAD"]
                logger.info(f"Using default symbol: {self.symbols}")
        
        logger.info(f"Strategy initialized with symbols: {self.symbols}")
        
        # Internal state for data storage
        self.data = {symbol: [] for symbol in self.symbols}
        self.fast_ma = {symbol: [] for symbol in self.symbols}
        self.slow_ma = {symbol: [] for symbol in self.symbols}
        self.current_position = {symbol: 0 for symbol in self.symbols}
        
        # Register for events
        if self.event_bus:
            if hasattr(self.event_bus, 'register'):
                self.event_bus.register(EventType.BAR, self.on_bar)
                logger.info("Registered strategy for BAR events using register method")
            elif hasattr(self.event_bus, 'subscribe'): 
                self.event_bus.subscribe(EventType.BAR, self.on_bar)
                logger.info("Registered strategy for BAR events using subscribe method")
            else:
                logger.warning("Could not register for BAR events - no register/subscribe method")
            
        logger.info(f"MA Crossover strategy initialized with fast_window={self.fast_window}, "
                   f"slow_window={self.slow_window}")
    
    def initialize(self, context):
        """
        Initialize the strategy with backtest components.
        
        Args:
            context (dict): Context containing dependencies
        """
        self.event_bus = context.get('event_bus')
        self.data_handler = context.get('data_handler')
        
        # Try to get symbols from all sources again
        if not self.symbols:
            # Try data handler's get_symbols method
            if hasattr(self.data_handler, 'get_symbols') and callable(self.data_handler.get_symbols):
                try:
                    handler_symbols = self.data_handler.get_symbols()
                    if handler_symbols:
                        self.symbols = handler_symbols
                        logger.info(f"Updated symbols from data handler in initialize: {self.symbols}")
                except Exception as e:
                    logger.warning(f"Error getting symbols from data handler in initialize: {e}")
            
            # Try config symbols
            if not self.symbols and 'config' in context and isinstance(context['config'], dict):
                config_symbols = context['config'].get('symbols')
                if config_symbols:
                    self.symbols = config_symbols
                    logger.info(f"Updated symbols from context config: {self.symbols}")
            
            # Try backtest symbols
            if not self.symbols and 'backtest' in context and isinstance(context['backtest'], dict):
                backtest_symbols = context['backtest'].get('symbols')
                if backtest_symbols:
                    self.symbols = backtest_symbols
                    logger.info(f"Updated symbols from backtest config: {self.symbols}")
            
            # Default to HEAD if still no symbols
            if not self.symbols:
                self.symbols = ["HEAD"]
                logger.info(f"Using default symbol in initialize: {self.symbols}")
            
            # Reinitialize data structures with the new symbols
            self.data = {symbol: [] for symbol in self.symbols}
            self.fast_ma = {symbol: [] for symbol in self.symbols}
            self.slow_ma = {symbol: [] for symbol in self.symbols}
            self.current_position = {symbol: 0 for symbol in self.symbols}
        
        # Register for events if we have an event bus
        if self.event_bus:
            if hasattr(self.event_bus, 'subscribe'):
                self.event_bus.subscribe(EventType.BAR, self.on_bar)
                logger.info("Subscribed strategy to BAR events in initialize")
            elif hasattr(self.event_bus, 'register'):
                self.event_bus.register(EventType.BAR, self.on_bar)
                logger.info("Registered strategy for BAR events in initialize")
            else:
                logger.warning("Could not register for BAR events - no subscribe/register method")
            
        logger.info(f"MA Crossover strategy initialized with event bus from context")
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        # Call parent configure first
        super().configure(config)
        
        # Update strategy-specific parameters
        self.fast_window = self.parameters.get('fast_window', 5)
        self.slow_window = self.parameters.get('slow_window', 15)
        self.price_key = self.parameters.get('price_key', 'close')
        
        # Reset data for all configured symbols
        self.reset()
        
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
        try:
            # Extract data from bar event
            symbol = bar_event.get_symbol()
            logger.debug(f"Bar event symbol: {symbol}")
            
            # Set log level for more detailed output
            logger.setLevel(logging.DEBUG)
            
            # Auto-add symbol if not already in our list
            if symbol not in self.symbols:
                try:
                    # Debug the symbol not in the list
                    logger.debug(f"Symbol {symbol} not in strategy symbols list: {self.symbols}")
                    
                    # Add the symbol to our tracking lists
                    self.symbols.append(symbol)
                    self.data[symbol] = []
                    self.fast_ma[symbol] = []
                    self.slow_ma[symbol] = []
                    self.current_position[symbol] = 0
                    
                    logger.info(f"Auto-added new symbol: {symbol}")
                except Exception as e:
                    logger.error(f"Error in auto-adding symbol {symbol}: {e}")
            
            # Debug - log the complete bar event
            logger.debug(f"Received bar event: {bar_event}")
            
            # Extract price data
            price = bar_event.get_close()
            timestamp = bar_event.get_timestamp()
            
            logger.debug(f"Bar data: symbol={symbol}, price={price}, timestamp={timestamp}")
            
            # Store data for this symbol
            self.data[symbol].append({
                'timestamp': timestamp,
                'price': price
            })
        
            # Check if we have enough data
            if len(self.data[symbol]) <= self.slow_window:
                logger.debug(f"Not enough data for {symbol}: have {len(self.data[symbol])} bars, need {self.slow_window+1}")
                return None
            
            # Calculate moving averages
            prices = [bar['price'] for bar in self.data[symbol]]
            
            # Calculate fast MA - current and previous
            fast_ma = sum(prices[-self.fast_window:]) / self.fast_window
            fast_ma_prev = sum(prices[-(self.fast_window+1):-1]) / self.fast_window
            
            # Calculate slow MA - current and previous
            slow_ma = sum(prices[-self.slow_window:]) / self.slow_window
            slow_ma_prev = sum(prices[-(self.slow_window+1):-1]) / self.slow_window
            
            # Log MA values for debugging
            logger.debug(f"MAs for {symbol}: Fast={fast_ma:.2f} (prev={fast_ma_prev:.2f}), Slow={slow_ma:.2f} (prev={slow_ma_prev:.2f})")
            
            # Determine signal based on crossover
            signal_value = 0
            signal_reason = "No crossover"
            
            # Buy signal: fast MA crosses above slow MA
            if fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma:
                signal_value = 1
                signal_reason = "BUY: fast MA crossed above slow MA"
                logger.info(f"BUY signal for {symbol}: fast MA ({fast_ma:.2f}) crossed above slow MA ({slow_ma:.2f})")
            
            # Sell signal: fast MA crosses below slow MA
            elif fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma:
                signal_value = -1
                signal_reason = "SELL: fast MA crossed below slow MA"
                logger.info(f"SELL signal for {symbol}: fast MA ({fast_ma:.2f}) crossed below slow MA ({slow_ma:.2f})")
            
            # No crossover
            else:
                logger.debug(f"No crossover for {symbol}: fast_prev={fast_ma_prev:.2f}, slow_prev={slow_ma_prev:.2f}, fast={fast_ma:.2f}, slow={slow_ma:.2f}")
            
            # If we have a signal, create a signal event
            if signal_value != 0:
                try:
                    # Create a signal event
                    signal = create_signal_event(
                        signal_value=signal_value,
                        price=price,
                        symbol=symbol,
                        timestamp=timestamp,
                        rule_id=f"ma_crossover_{symbol}_{signal_value}_{timestamp.strftime('%Y%m%d_%H%M')}"
                    )
                    
                    # Debug the signal
                    logger.info(f"Created signal: {signal.__class__.__name__}, signal_value={signal_value}")
                    
                    # Emit signal if we have an event bus
                    if self.event_bus:
                        try:
                            if hasattr(self.event_bus, 'publish'):
                                self.event_bus.publish(signal)
                                logger.info(f"Published signal for {symbol} using publish method")
                            elif hasattr(self.event_bus, 'emit'):
                                self.event_bus.emit(signal)
                                logger.info(f"Emitted signal for {symbol} using emit method")
                            else:
                                logger.warning(f"No publish/emit method available on event_bus")
                            
                            logger.info(f"Signal sent for {symbol}: {signal_value}, timestamp={timestamp}")
                        except Exception as e:
                            logger.error(f"Error sending signal via event bus: {e}")
                            logger.error(traceback.format_exc())
                    else:
                        logger.warning(f"No event_bus available to send signal for {symbol}")
                    
                    return signal
                except Exception as e:
                    logger.error(f"Error creating signal: {e}")
                    logger.error(traceback.format_exc())
            
            return None
        except Exception as e:
            logger.error(f"Error in on_bar: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def reset(self):
        """Reset the strategy state."""
        # First call the parent reset which resets self.data
        super().reset()
        
        # Then explicitly reset strategy-specific state
        self.fast_ma = {symbol: [] for symbol in self.symbols}
        self.slow_ma = {symbol: [] for symbol in self.symbols}
        self.current_position = {symbol: 0 for symbol in self.symbols}
        
        logger.info(f"MA Crossover strategy {self.name} reset")
