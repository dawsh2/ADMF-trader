"""
Mean Reversion Strategy Implementation.

This strategy generates signals based on price deviations from a moving average:
- Buy signal (1): when price drops significantly below moving average (oversold)
- Sell signal (-1): when price rises significantly above moving average (overbought)
- Neutral (0): when price is within normal bounds of the moving average

Following the refactored architecture, this strategy only focuses on signal generation
and does NOT track position state or handle trading decisions.
"""
import logging
import numpy as np
from src.strategy.strategy_base import Strategy
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event

logger = logging.getLogger(__name__)

class MeanReversionStrategy(Strategy):
    """
    Mean Reversion strategy implementation with clean separation of concerns.
    
    This strategy identifies overbought and oversold conditions based on price
    deviations from a moving average, generating signals for mean reversion opportunities.
    """
    
    # Define name as a class variable for easier discovery
    name = "mean_reversion"
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        """
        Initialize the Mean Reversion strategy.
        
        Args:
            event_bus: Event bus for communication
            data_handler: Data handler for market data
            name: Optional strategy name override
            parameters: Initial strategy parameters
        """
        # Call parent constructor with name from class or override
        super().__init__(event_bus, data_handler, name or self.name, parameters)
        
        # Extract parameters with defaults
        self.window = self.parameters.get('window', 20)
        self.std_dev_multiplier = self.parameters.get('std_dev_multiplier', 2.0)
        self.price_key = self.parameters.get('price_key', 'close')
        self.use_atr = self.parameters.get('use_atr', False)
        self.atr_multiplier = self.parameters.get('atr_multiplier', 1.5)
        self.atr_period = self.parameters.get('atr_period', 14)
        
        # Internal state for data storage only
        self.data = {symbol: [] for symbol in self.symbols}
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
            
        logger.info(f"Mean Reversion strategy initialized with window={self.window}, "
                   f"std_dev_multiplier={self.std_dev_multiplier}")
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        # Call parent configure first
        super().configure(config)
        
        # Update strategy-specific parameters
        self.window = self.parameters.get('window', 20)
        self.std_dev_multiplier = self.parameters.get('std_dev_multiplier', 2.0)
        self.price_key = self.parameters.get('price_key', 'close')
        self.use_atr = self.parameters.get('use_atr', False)
        self.atr_multiplier = self.parameters.get('atr_multiplier', 1.5)
        self.atr_period = self.parameters.get('atr_period', 14)
        
        # Reset data for all configured symbols
        self.data = {symbol: [] for symbol in self.symbols}
        
        logger.info(f"Mean Reversion strategy configured with parameters: "
                   f"window={self.window}, std_dev_multiplier={self.std_dev_multiplier}")
    
    def _calculate_atr(self, data, period):
        """
        Calculate Average True Range (ATR) for volatility-based thresholds.
        
        Args:
            data: List of price data dictionaries
            period: ATR calculation period
            
        Returns:
            float: ATR value
        """
        if len(data) < period + 1:
            return None
        
        true_ranges = []
        for i in range(1, len(data)):
            high = data[i]['high']
            low = data[i]['low']
            prev_close = data[i-1]['price']  # Using 'price' as close
            
            # True Range is the greatest of:
            # 1. Current High - Current Low
            # 2. |Current High - Previous Close|
            # 3. |Current Low - Previous Close|
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            true_range = max(tr1, tr2, tr3)
            
            true_ranges.append(true_range)
            
        # Use only the last 'period' number of true ranges
        true_ranges = true_ranges[-period:]
        
        # Calculate ATR as simple average of true ranges
        atr = sum(true_ranges) / len(true_ranges)
        return atr
    
    def on_bar(self, bar_event):
        """
        Process a bar event and generate mean reversion signals.
        
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
            'price': price,
            'high': bar_event.get_high(),
            'low': bar_event.get_low()
        })
        
        # Check if we have enough data
        if len(self.data[symbol]) < self.window:
            return None
        
        # Keep only the most recent window + some buffer for calculations
        max_data_points = max(self.window * 2, self.window + 20)
        if len(self.data[symbol]) > max_data_points:
            self.data[symbol] = self.data[symbol][-max_data_points:]
        
        # Calculate moving average
        prices = [bar['price'] for bar in self.data[symbol][-self.window:]]
        moving_avg = sum(prices) / len(prices)
        
        # Calculate price deviation threshold
        if self.use_atr and len(self.data[symbol]) > self.atr_period:
            # Use ATR-based threshold
            atr = self._calculate_atr(self.data[symbol], self.atr_period)
            if atr is None:
                return None
                
            threshold = atr * self.atr_multiplier
            
        else:
            # Use standard deviation-based threshold
            std_dev = np.std(prices)
            threshold = std_dev * self.std_dev_multiplier
        
        # Calculate price deviation from moving average
        deviation = price - moving_avg
        
        # Determine signal based on deviation
        signal_value = 0
        
        # Buy signal: price is below moving average by threshold
        if deviation < -threshold:
            signal_value = 1
            logger.info(f"BUY signal for {symbol}: price {price:.2f} below MA {moving_avg:.2f} by {-deviation:.2f} (threshold: {threshold:.2f})")
        
        # Sell signal: price is above moving average by threshold
        elif deviation > threshold:
            signal_value = -1
            logger.info(f"SELL signal for {symbol}: price {price:.2f} above MA {moving_avg:.2f} by {deviation:.2f} (threshold: {threshold:.2f})")
        
        # If we have a signal, create a signal event
        if signal_value != 0:
            # Create a unique rule ID
            rule_id = f"mean_reversion_dev{deviation:.2f}_ma{moving_avg:.2f}_{symbol}_{timestamp}"
            
            # Create a signal event
            signal = create_signal_event(
                signal_value=signal_value,
                price=price,
                symbol=symbol,
                timestamp=timestamp,
                rule_id=rule_id
            )
            
            # Add additional metadata about the signal if supported
            if hasattr(signal, 'data') and isinstance(signal.data, dict):
                signal.data['moving_avg'] = moving_avg
                signal.data['deviation'] = deviation
                signal.data['threshold'] = threshold
                signal.data['strategy_type'] = 'mean_reversion'
            
            # Emit signal if we have an event bus
            if self.event_bus:
                self.event_bus.emit(signal)
                logger.info(f"Signal emitted for {symbol}: {signal_value}, deviation: {deviation:.2f}")
            
            return signal
        
        return None
    
    def reset(self):
        """Reset the strategy state."""
        # Reset strategy-specific state
        self.data = {symbol: [] for symbol in self.symbols}
        
        logger.info(f"Mean Reversion strategy {self.name} reset")