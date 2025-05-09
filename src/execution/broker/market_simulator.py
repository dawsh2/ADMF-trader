"""
Market simulator for simulating market conditions in backtesting.

This module provides components for simulating market conditions
and order filling logic in a backtesting environment.
"""
import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable

from src.core.component import Component
from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType

logger = logging.getLogger(__name__)

class MarketSimulator(Component):
    """
    Simulates market conditions for backtesting.
    
    This component simulates market behavior for testing strategies,
    including price movement, liquidity, and other market conditions.
    """
    
    def __init__(self, name: str = "market_simulator", config: Optional[Dict[str, Any]] = None):
        """
        Initialize market simulator.
        
        Args:
            name: Component name
            config: Optional configuration dictionary
        """
        super().__init__(name)
        self.config = config or {}
        
        # Market state
        self.current_prices = {}  # symbol -> {open, high, low, close, volume, timestamp}
        self.historical_prices = {}  # symbol -> List[price_dict]
        self.market_stats = {}  # symbol -> {volatility, liquidity, spread, etc.}
        
        # Configuration parameters
        self.max_price_impact = self.config.get('max_price_impact', 0.01)  # 1% max impact
        self.liquidity_factor = self.config.get('liquidity_factor', 1.0)
        self.enable_gaps = self.config.get('enable_gaps', True)
        self.randomize_fills = self.config.get('randomize_fills', True)
        
        # Custom fill handlers
        self.fill_handlers = {}  # order_type -> handler_function
        
        # Register default handlers
        self._register_default_handlers()
    
    def initialize(self, context: Dict[str, Any]) -> None:
        """
        Initialize with dependencies.
        
        Args:
            context: Context containing dependencies
        """
        super().initialize(context)
        
        # Get event bus from context
        self.event_bus = context.get('event_bus')
        
        if not self.event_bus:
            raise ValueError("MarketSimulator requires event_bus in context")
        
        # Get data handler from context if available for direct data access
        data_handler = context.get('data_handler')
        if data_handler and hasattr(data_handler, 'get_latest_bar'):
            self._initialize_from_data_handler(data_handler)
            
        # Subscribe to bar events
        self.event_bus.subscribe(EventType.BAR, self.on_bar)
        
    def _initialize_from_data_handler(self, data_handler):
        """Initialize price data directly from data handler.
        
        Args:
            data_handler: Data handler instance with access to latest bars
        """
        # Get symbols from data handler if available
        symbols = data_handler.get_symbols() if hasattr(data_handler, 'get_symbols') else []
        
        # Log initialization attempt
        logger.info(f"Initializing market simulator with {len(symbols)} symbols from data handler")
        
        # Initialize price data for each symbol
        for symbol in symbols:
            bar = data_handler.get_latest_bar(symbol)
            if bar:
                self.update_price_data(symbol, bar)
                logger.info(f"Initialized price data for {symbol}")
                
    def update_price_data(self, symbol, bar):
        """
        Update price data from a bar directly.
        
        Args:
            symbol: Symbol to update
            bar: Bar object or dictionary with price data
        """
        # Create price data dictionary from bar
        if hasattr(bar, 'to_dict'):
            bar_data = bar.to_dict()
        else:
            bar_data = bar
            
        try:
            # Extract price data and ensure all values are numeric
            # FIXED: ensure all values are properly converted to float
            try:
                open_price = float(bar_data.get('open', 0.0))
                high_price = float(bar_data.get('high', 0.0))
                low_price = float(bar_data.get('low', 0.0))
                close_price = float(bar_data.get('close', 0.0))
                volume = float(bar_data.get('volume', 0))
            except (ValueError, TypeError) as e:
                logger.warning(f"Error converting price data for {symbol}: {e}")
                logger.warning(f"Bar data: {bar_data}")
                # Try to recover with defaults if conversion fails
                open_price = float(bar_data.get('open', 0.0)) if bar_data.get('open') is not None else 0.0
                high_price = float(bar_data.get('high', 0.0)) if bar_data.get('high') is not None else 0.0
                low_price = float(bar_data.get('low', 0.0)) if bar_data.get('low') is not None else 0.0
                close_price = float(bar_data.get('close', 0.0)) if bar_data.get('close') is not None else 0.0
                volume = float(bar_data.get('volume', 0)) if bar_data.get('volume') is not None else 0
            
            timestamp = bar_data.get('timestamp', datetime.datetime.now())
            
            price_data = {
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'timestamp': timestamp
            }
            
            # Store the price data and log more details for debugging
            self.current_prices[symbol] = price_data
            logger.info(f"Updated price data for {symbol}: close={close_price:.4f}")
            
            # Add to historical prices
            if symbol not in self.historical_prices:
                self.historical_prices[symbol] = []
            
            self.historical_prices[symbol].append(price_data.copy())
            
            # Keep only the most recent N bars
            max_history = self.config.get('max_history_bars', 100)
            if len(self.historical_prices[symbol]) > max_history:
                self.historical_prices[symbol] = self.historical_prices[symbol][-max_history:]
                
            # Update market statistics
            self._update_market_stats(symbol)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating price data for {symbol}: {e}", exc_info=True)
            return False
    
    def reset(self) -> None:
        """Reset the market simulator state."""
        super().reset()
        
        # Clear state
        self.current_prices = {}
        self.historical_prices = {}
        self.market_stats = {}
        
        logger.info("Market simulator reset")
    
    def on_bar(self, event: Event) -> None:
        """
        Process bar events to update market state.
        
        Args:
            event: Bar event
        """
        # Handle both direct data access and get_data() method
        if hasattr(event, 'get_data') and callable(event.get_data):
            bar_data = event.get_data()
        elif hasattr(event, 'data'):
            bar_data = event.data
        else:
            logger.warning("Received bar event with no data, skipping")
            return
        
        # Extract symbol safely
        symbol = bar_data.get('symbol')
        if not symbol:
            logger.warning("Received bar event without symbol, skipping")
            return
        
        # Log bar data for debugging
        if 'close' in bar_data:
            try:
                close_value = float(bar_data.get('close', 0))
                logger.info(f"Market simulator received bar for {symbol} with close={close_value:.4f}")
            except (ValueError, TypeError):
                logger.warning(f"Market simulator received bar for {symbol} with invalid close value: {bar_data.get('close')}")
        else:
            logger.warning(f"Market simulator received bar for {symbol} without close value")
        
        # FIXED: Check bar data structure before passing to update_price_data
        required_fields = ['open', 'high', 'low', 'close']
        missing_fields = [field for field in required_fields if field not in bar_data]
        
        if missing_fields:
            logger.warning(f"Bar data missing required fields: {missing_fields} for {symbol}")
            # Try to recover with a more complete lookup if possible
            # For instance, if we have a data handler, we can try to get the latest bar
            data_handler = getattr(self, 'data_handler', None)
            if data_handler and hasattr(data_handler, 'get_latest_bar'):
                complete_bar = data_handler.get_latest_bar(symbol)
                if complete_bar:
                    logger.info(f"Recovered complete bar data for {symbol} from data handler")
                    self.update_price_data(symbol, complete_bar)
                    return
            
            # If we couldn't recover a complete bar, update with what we have
            logger.warning(f"Proceeding with incomplete bar data for {symbol}")
        
        # Use the common update method to handle both direct bars and events
        success = self.update_price_data(symbol, bar_data)
        
        if not success:
            logger.warning(f"Failed to update price data for {symbol}")
        
        # Verify price data was stored
        if symbol not in self.current_prices:
            logger.error(f"Price data for {symbol} not stored in current_prices after update")
        else:
            logger.info(f"Verified price data for {symbol} in current_prices: {self.current_prices[symbol]['close']:.4f}")
    
    def check_fill_conditions(self, order: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Check if an order can be filled with current market conditions.
        
        Args:
            order: Order to check
            
        Returns:
            Tuple of (can_fill, fill_price)
        """
        order_type = order.get('order_type', 'MARKET')
        symbol = order.get('symbol')
        direction = order.get('direction')
        
        # Log more detailed order information for debugging
        logger.info(f"Checking fill conditions for {order_type} order: {symbol} {direction}")
        
        # Validate inputs
        if not symbol or not direction:
            logger.warning(f"Invalid order missing symbol or direction: {order}")
            return False, 0.0
        
        # Check if we have price data for this symbol
        if symbol not in self.current_prices:
            # FIXED: Add more detailed diagnostics
            logger.warning(f"No price data for {symbol}, cannot fill order")
            logger.info(f"Available price data symbols: {list(self.current_prices.keys())}")
            
            # Try to automatically recover price data if possible
            data_handler = getattr(self, 'data_handler', None)
            if data_handler and hasattr(data_handler, 'get_latest_bar'):
                bar = data_handler.get_latest_bar(symbol)
                if bar:
                    logger.info(f"Recovered price data for {symbol} from data handler, updating")
                    self.update_price_data(symbol, bar)
                    # Now check if we have the data
                    if symbol in self.current_prices:
                        logger.info(f"Successfully recovered price data for {symbol}")
                    else:
                        logger.error(f"Failed to recover price data for {symbol}")
                        return False, 0.0
                else:
                    logger.warning(f"Could not recover price data for {symbol} from data handler")
                    return False, 0.0
            else:
                logger.warning("No data handler available to recover price data")
                return False, 0.0
        
        price_data = self.current_prices[symbol]
        logger.info(f"Using price data for {symbol}: open={price_data['open']:.4f}, high={price_data['high']:.4f}, "
                   f"low={price_data['low']:.4f}, close={price_data['close']:.4f}")
        
        # Use custom handler if available for this order type
        if order_type in self.fill_handlers:
            logger.debug(f"Using custom fill handler for {order_type}")
            return self.fill_handlers[order_type](order, price_data, self.market_stats.get(symbol, {}))
        
        # Default handling for common order types
        if order_type == 'MARKET':
            # Market orders always fill at current price
            fill_price = price_data['close']
            logger.info(f"Market order can fill at price: {fill_price:.4f}")
            return True, fill_price
            
        elif order_type == 'LIMIT':
            limit_price = order.get('price', 0.0)
            
            # Validate limit price
            if limit_price <= 0:
                logger.warning(f"Invalid limit price: {limit_price}")
                return False, 0.0
            
            if direction == 'BUY':
                # Buy limit: can fill if price goes below limit
                can_fill = price_data['low'] <= limit_price
                # Fill at the better of limit price or open price
                fill_price = max(min(price_data['open'], limit_price), price_data['low'])
                logger.info(f"Buy limit order at {limit_price:.4f} - can fill: {can_fill}, fill price: {fill_price:.4f}")
            else:
                # Sell limit: can fill if price goes above limit
                can_fill = price_data['high'] >= limit_price
                # Fill at the better of limit price or open price
                fill_price = min(max(price_data['open'], limit_price), price_data['high'])
                logger.info(f"Sell limit order at {limit_price:.4f} - can fill: {can_fill}, fill price: {fill_price:.4f}")
            
            return can_fill, fill_price
            
        elif order_type == 'STOP':
            stop_price = order.get('price', 0.0)
            
            # Validate stop price
            if stop_price <= 0:
                logger.warning(f"Invalid stop price: {stop_price}")
                return False, 0.0
            
            if direction == 'BUY':
                # Buy stop: can fill if price goes above stop
                can_fill = price_data['high'] >= stop_price
                # Fill at the worse of stop price or open price
                fill_price = max(price_data['open'], stop_price)
                logger.info(f"Buy stop order at {stop_price:.4f} - can fill: {can_fill}, fill price: {fill_price:.4f}")
            else:
                # Sell stop: can fill if price goes below stop
                can_fill = price_data['low'] <= stop_price
                # Fill at the worse of stop price or open price
                fill_price = min(price_data['open'], stop_price)
                logger.info(f"Sell stop order at {stop_price:.4f} - can fill: {can_fill}, fill price: {fill_price:.4f}")
            
            return can_fill, fill_price
            
        elif order_type == 'STOP_LIMIT':
            stop_price = order.get('stop_price', 0.0)
            limit_price = order.get('limit_price', 0.0)
            
            # Validate prices
            if stop_price <= 0 or limit_price <= 0:
                logger.warning(f"Invalid stop or limit price: stop={stop_price}, limit={limit_price}")
                return False, 0.0
            
            if direction == 'BUY':
                # First check if stop is triggered
                stop_triggered = price_data['high'] >= stop_price
                
                if stop_triggered:
                    # Then check if limit can fill
                    can_fill = price_data['low'] <= limit_price
                    fill_price = min(max(price_data['open'], stop_price), limit_price)
                else:
                    can_fill = False
                    fill_price = 0.0
                    
                logger.info(f"Buy stop-limit order (stop={stop_price:.4f}, limit={limit_price:.4f}) - "
                           f"stop triggered: {stop_triggered}, can fill: {can_fill}, fill price: {fill_price:.4f}")
            else:
                # First check if stop is triggered
                stop_triggered = price_data['low'] <= stop_price
                
                if stop_triggered:
                    # Then check if limit can fill
                    can_fill = price_data['high'] >= limit_price
                    fill_price = max(min(price_data['open'], stop_price), limit_price)
                else:
                    can_fill = False
                    fill_price = 0.0
                    
                logger.info(f"Sell stop-limit order (stop={stop_price:.4f}, limit={limit_price:.4f}) - "
                           f"stop triggered: {stop_triggered}, can fill: {can_fill}, fill price: {fill_price:.4f}")
            
            return can_fill, fill_price
        
        else:
            logger.warning(f"Unsupported order type: {order_type}")
            return False, 0.0
    
    def calculate_market_impact(self, order: Dict[str, Any], base_price: float) -> float:
        """
        Calculate market impact for large orders.
        
        Args:
            order: Order to calculate impact for
            base_price: Base fill price
            
        Returns:
            float: Price with market impact applied
        """
        symbol = order.get('symbol')
        quantity = order.get('quantity', 0.0)
        direction = order.get('direction')
        
        # Skip if no quantity or invalid inputs
        if not symbol or not quantity or not direction:
            return base_price
        
        # Get market statistics
        market_stat = self.market_stats.get(symbol, {})
        liquidity = market_stat.get('liquidity', 10000.0)  # Default to high liquidity
        volatility = market_stat.get('volatility', 0.01)  # Default to 1% volatility
        
        # Calculate impact based on order size relative to liquidity
        impact_factor = min(abs(quantity) / liquidity, self.max_price_impact)
        
        # Scale by volatility (higher volatility = higher impact)
        impact_factor *= (1.0 + volatility * 10.0)
        
        # Apply direction to impact
        if direction == 'BUY':
            # Buys push price up
            impact_price = base_price * (1.0 + impact_factor)
        else:
            # Sells push price down
            impact_price = base_price * (1.0 - impact_factor)
        
        logger.debug(f"Market impact: base={base_price:.4f}, adjusted={impact_price:.4f}, impact={impact_factor*100:.2f}%")
        
        return impact_price
    
    def register_fill_handler(self, order_type: str, handler: Callable) -> None:
        """
        Register custom fill handler for order type.
        
        Args:
            order_type: Order type to handle
            handler: Handler function that takes (order, price_data, market_stats) and returns (can_fill, fill_price)
        """
        self.fill_handlers[order_type] = handler
        logger.info(f"Registered custom fill handler for order type: {order_type}")
    
    def _register_default_handlers(self) -> None:
        """Register default fill handlers."""
        # This method can be extended to add more sophisticated handlers
        pass
    
    def _update_market_stats(self, symbol: str) -> None:
        """
        Update market statistics for a symbol.
        
        Args:
            symbol: Symbol to update statistics for
        """
        if not symbol or symbol not in self.historical_prices:
            return
        
        # Get price history
        price_history = self.historical_prices[symbol]
        
        if len(price_history) < 2:
            return
        
        # Calculate volatility (using close prices)
        closes = [bar['close'] for bar in price_history]
        
        # Simple volatility calculation (standard deviation of returns)
        returns = [(closes[i] / closes[i-1]) - 1.0 for i in range(1, len(closes))]
        
        if returns:
            import statistics
            
            try:
                volatility = statistics.stdev(returns)
            except statistics.StatisticsError:
                volatility = 0.01  # Default if calculation fails
                
            # Calculate average volume (proxy for liquidity)
            avg_volume = sum(bar.get('volume', 0) for bar in price_history) / len(price_history)
            
            # Calculate average spread if high/low available
            avg_spread = sum((bar['high'] - bar['low']) / bar['close'] for bar in price_history) / len(price_history)
            
            # Store statistics
            self.market_stats[symbol] = {
                'volatility': volatility,
                'liquidity': max(avg_volume, 1.0),  # Avoid division by zero
                'spread': avg_spread,
                'last_update': datetime.datetime.now()
            }
    
    def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get current price data for a symbol.
        
        Args:
            symbol: Symbol to get price for
            
        Returns:
            dict: Price data or empty dict if not found
        """
        return self.current_prices.get(symbol, {})
    
    def get_market_stats(self, symbol: str) -> Dict[str, Any]:
        """
        Get market statistics for a symbol.
        
        Args:
            symbol: Symbol to get statistics for
            
        Returns:
            dict: Market statistics or empty dict if not found
        """
        return self.market_stats.get(symbol, {})