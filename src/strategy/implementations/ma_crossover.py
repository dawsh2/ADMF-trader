from src.core.events.event_types import EventType
from src.core.events.event_utils import create_event
from src.strategy.abstract_strategy import AbstractStrategy
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MovingAverageCrossoverStrategy(AbstractStrategy):
    """
    Moving Average Crossover Strategy
    
    Generates buy signals when fast MA crosses above slow MA
    Generates sell signals when fast MA crosses below slow MA
    """
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        """
        Initialize the Moving Average Crossover strategy
        
        Args:
            event_bus: Event bus for publishing events
            data_handler: Data handler for accessing market data
            name: Strategy name
            parameters: Strategy parameters dictionary
        """
        super().__init__(event_bus, data_handler, name or "MA_Crossover")
        
        # Initialize parameters
        self.parameters = parameters or {}
        
        # Get fast and slow windows
        self.fast_window = self.parameters.get('fast_window', 5)
        self.slow_window = self.parameters.get('slow_window', 20)
        
        # Initialize symbols list
        self.symbols = self.parameters.get('symbols', [])
        
        # Initialize data for each symbol
        self.data = {}
        
        logger.info(f"Initialized {self.name} strategy with fast_window={self.fast_window}, slow_window={self.slow_window}")
    
    def on_bar(self, event):
        """
        Process bar data and generate signals
        
        Args:
            event: Bar event containing market data
        """
        symbol = event.data.get('symbol')
        price = event.data.get('close')
        timestamp = event.data.get('timestamp')
        
        # Check if symbol is in our list
        if symbol not in self.symbols:
            logger.warning(f"Symbol {symbol} not in strategy symbols list: {self.symbols}")
            return
        
        # Initialize data for this symbol if not already done
        if symbol not in self.data:
            self.data[symbol] = {
                'prices': [],
                'timestamps': []
            }
        
        # Add price data
        self.data[symbol]['prices'].append(price)
        self.data[symbol]['timestamps'].append(timestamp)
        
        # Need at least slow_window + 1 data points to calculate signal
        if len(self.data[symbol]['prices']) <= self.slow_window:
            return
        
        # Calculate moving averages
        prices = np.array(self.data[symbol]['prices'])
        fast_ma = np.mean(prices[-self.fast_window:])
        slow_ma = np.mean(prices[-self.slow_window:])
        
        # Calculate previous moving averages
        if len(prices) > self.slow_window + 1:
            prev_prices = prices[:-1]
            prev_fast_ma = np.mean(prev_prices[-self.fast_window:])
            prev_slow_ma = np.mean(prev_prices[-self.slow_window:])
            
            # Determine signal
            signal_value = 0
            
            # Buy signal: fast MA crosses above slow MA
            if fast_ma > slow_ma and prev_fast_ma <= prev_slow_ma:
                signal_value = 1
                logger.info(f"BUY signal for {symbol} at {price}")
            
            # Sell signal: fast MA crosses below slow MA
            elif fast_ma < slow_ma and prev_fast_ma >= prev_slow_ma:
                signal_value = -1
                logger.info(f"SELL signal for {symbol} at {price}")
            
            # Generate signal event if needed
            if signal_value != 0:
                signal_data = {
                    'symbol': symbol,
                    'value': signal_value,
                    'strategy': self.name,
                    'timestamp': timestamp,
                    'price': price
                }
                
                signal_event = create_event(EventType.SIGNAL, signal_data)
                self.event_bus.publish(signal_event)
                logger.debug(f"Published signal event: {signal_data}")
    
    def on_tick(self, event):
        """
        Process tick data (not used in this strategy)
        
        Args:
            event: Tick event
        """
        pass