"""
Simple Regime Ensemble Strategy Implementation.

This is a simplified version of the RegimeEnsembleStrategy, designed to be more
easily compatible with the optimizer by reducing the required dependencies.
"""
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

from src.core.component import Component
from src.core.events.event_types import EventType, Event
from src.data.data_types import Bar
from src.strategy.strategy import Strategy

logger = logging.getLogger(__name__)

# Regime types
class MarketRegime:
    """Market regime types."""
    TREND = "trend"
    MEAN_REVERSION = "mean_reversion"
    VOLATILE = "volatile"
    NEUTRAL = "neutral"

class SimpleRegimeEnsembleStrategy(Strategy):
    """
    Simplified regime-aware ensemble strategy that combines multiple trading rules
    and adapts their weights based on detected market regimes.
    
    This version is designed to be more compatible with the optimizer.
    """
    
    # Flag to identify this as a strategy
    is_strategy = True
    
    def __init__(self, name, volatility_window=60, volatility_threshold=0.002,
                trend_ma_window=120, trend_threshold=0.01, fast_ma_window=20,
                slow_ma_window=60, rsi_window=30, rsi_overbought=70,
                rsi_oversold=30, breakout_window=60, breakout_multiplier=1.5):
        """
        Initialize the Simple Regime Ensemble strategy.
        
        Args:
            name: Strategy name
            volatility_window: Window for volatility calculation
            volatility_threshold: Threshold for volatile regime
            trend_ma_window: Window for trend moving average
            trend_threshold: Threshold for trending regime
            fast_ma_window: Window for fast moving average
            slow_ma_window: Window for slow moving average
            rsi_window: Window for RSI calculation
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
            breakout_window: Window for volatility breakout calculation
            breakout_multiplier: Multiplier for ATR in breakout strategy
        """
        # Call parent constructor
        super().__init__(name)
        
        # Store parameters
        self.volatility_window = volatility_window
        self.volatility_threshold = volatility_threshold
        self.trend_ma_window = trend_ma_window
        self.trend_threshold = trend_threshold
        
        self.fast_ma_window = fast_ma_window
        self.slow_ma_window = slow_ma_window
        
        self.rsi_window = rsi_window
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        
        self.breakout_window = breakout_window
        self.breakout_multiplier = breakout_multiplier
        
        # Default regime weights
        self.regime_weights = {
            MarketRegime.TREND: {
                'trend_following': 1.0,
                'mean_reversion': 0.2,
                'volatility_breakout': 0.5
            },
            MarketRegime.MEAN_REVERSION: {
                'trend_following': 0.2,
                'mean_reversion': 1.0,
                'volatility_breakout': 0.3
            },
            MarketRegime.VOLATILE: {
                'trend_following': 0.3,
                'mean_reversion': 0.3,
                'volatility_breakout': 1.0
            },
            MarketRegime.NEUTRAL: {
                'trend_following': 0.5,
                'mean_reversion': 0.5,
                'volatility_breakout': 0.5
            }
        }
        
        # Internal state
        self.data = {}
        self.current_regimes = {}
        self.signal_count = 0
        self.symbols = []
        
        logger.info(f"Simple Regime Ensemble strategy initialized: {name}")
    
    def initialize(self, context):
        """Initialize strategy with context."""
        super().initialize(context)
        
        # Get data handler from context
        self.data_handler = context.get('data_handler')
        
        # Get symbols from context or data handler
        if 'symbols' in context:
            self.symbols = context['symbols']
        elif self.data_handler and hasattr(self.data_handler, 'get_symbols'):
            self.symbols = self.data_handler.get_symbols()
        else:
            self.symbols = ['SPY']  # Default if not specified
        
        # Initialize state for each symbol
        self.data = {symbol: [] for symbol in self.symbols}
        self.current_regimes = {symbol: MarketRegime.NEUTRAL for symbol in self.symbols}
        
        logger.info(f"Regime Ensemble strategy initialized with {len(self.symbols)} symbols")
    
    def calculate_signals(self, bar: Bar) -> None:
        """
        Calculate trading signals based on the current bar.
        
        Args:
            bar: Current bar
        """
        symbol = bar.symbol
        
        # Skip if not in our symbol list
        if symbol not in self.symbols and len(self.symbols) > 0:
            self.symbols.append(symbol)
        
        # Store data for this symbol
        if symbol not in self.data:
            self.data[symbol] = []
        
        # Store bar data
        self.data[symbol].append({
            'timestamp': bar.timestamp,
            'close': bar.close,
            'high': bar.high,
            'low': bar.low
        })
        
        # We need enough data for the longest window
        min_bars_needed = max(
            self.volatility_window,
            self.trend_ma_window,
            self.slow_ma_window,
            self.rsi_window,
            self.breakout_window
        )
        
        # Check if we have enough data
        if len(self.data[symbol]) <= min_bars_needed:
            if len(self.data[symbol]) % 10 == 0:
                logger.debug(f"Collecting data for {symbol}: {len(self.data[symbol])}/{min_bars_needed} bars")
            return
        
        # Detect market regime first
        regime = self._detect_regime(symbol)
        
        # If regime changed, log it
        if regime != self.current_regimes.get(symbol):
            logger.info(f"Regime change for {symbol}: {self.current_regimes.get(symbol)} -> {regime}")
            self.current_regimes[symbol] = regime
        
        # Get weights for current regime
        weights = self.regime_weights.get(regime, self.regime_weights[MarketRegime.NEUTRAL])
        
        # Calculate rule signals
        trend_signal = self._calculate_trend_signal(symbol) * weights['trend_following']
        mean_reversion_signal = self._calculate_mean_reversion_signal(symbol) * weights['mean_reversion']
        volatility_signal = self._calculate_volatility_signal(symbol) * weights['volatility_breakout']
        
        # Combine signals (simple weighted average)
        total_weight = sum(weights.values())
        if total_weight > 0:
            combined_signal = (trend_signal + mean_reversion_signal + volatility_signal) / total_weight
        else:
            combined_signal = 0
        
        # Threshold for signal generation: must be at least 0.5 in either direction
        # and we convert to -1, 0, or 1
        signal_value = 0
        if combined_signal >= 0.5:
            signal_value = 1
        elif combined_signal <= -0.5:
            signal_value = -1
        
        # Generate and emit signal event if we have a signal
        if signal_value != 0:
            self.signal_count += 1
            
            # Log detailed signal information
            logger.info(f"Signal for {symbol} ({regime} regime): Combined={combined_signal:.2f} -> {signal_value}")
            logger.info(f"  Components: Trend={trend_signal:.2f}, MeanRev={mean_reversion_signal:.2f}, Vol={volatility_signal:.2f}")
            
            # Direction string for the signal
            direction = "BUY" if signal_value > 0 else "SELL"
            
            # Emit signal with strength based on the combined value
            self.emit_signal(
                signal_type="ENTRY", 
                symbol=symbol, 
                direction=signal_value,
                strength=abs(combined_signal),
                metadata={'regime': regime}
            )
    
    def _detect_regime(self, symbol):
        """
        Detect the current market regime.
        
        Args:
            symbol: Symbol to detect regime for
            
        Returns:
            Detected regime type
        """
        # Get historical prices
        data = self.data[symbol]
        closes = [bar['close'] for bar in data]
        
        # Calculate trend indicator: price vs long-term MA
        trend_ma = sum(closes[-self.trend_ma_window:]) / self.trend_ma_window
        current_price = closes[-1]
        recent_prices = closes[-20:]  # Last 20 bars
        
        # Trend calculation: % difference from MA and recent direction
        trend_diff_pct = (current_price - trend_ma) / trend_ma
        recent_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        
        # Volatility calculation: standard deviation of returns
        returns = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
        recent_returns = returns[-self.volatility_window:]
        volatility = np.std(recent_returns)
        
        # Determine regime based on volatility and trend
        if volatility > self.volatility_threshold:
            # High volatility indicates volatile regime
            regime = MarketRegime.VOLATILE
        elif abs(trend_diff_pct) > self.trend_threshold and np.sign(trend_diff_pct) == np.sign(recent_trend):
            # Strong trend in consistent direction
            regime = MarketRegime.TREND
        elif abs(trend_diff_pct) < self.trend_threshold * 0.5:
            # Price near moving average, likely mean-reverting
            regime = MarketRegime.MEAN_REVERSION
        else:
            # Default if no clear pattern
            regime = MarketRegime.NEUTRAL
        
        return regime
    
    def _calculate_trend_signal(self, symbol):
        """
        Calculate trend following signal (-1.0 to 1.0).
        
        Args:
            symbol: Symbol to calculate for
            
        Returns:
            Signal value between -1.0 and 1.0
        """
        # Get historical prices
        data = self.data[symbol]
        closes = [bar['close'] for bar in data]
        
        # Calculate moving averages
        fast_ma = sum(closes[-self.fast_ma_window:]) / self.fast_ma_window
        slow_ma = sum(closes[-self.slow_ma_window:]) / self.slow_ma_window
        
        # Previous MAs (for crossover detection)
        fast_ma_prev = sum(closes[-(self.fast_ma_window+1):-1]) / self.fast_ma_window
        slow_ma_prev = sum(closes[-(self.slow_ma_window+1):-1]) / self.slow_ma_window
        
        # Crossover logic with distance factor
        ma_diff = (fast_ma - slow_ma) / slow_ma  # Normalized difference
        
        # Detect crossovers with stronger signal for more decisive crossovers
        if fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma:
            # Bullish crossover with strength based on difference
            return min(1.0, 0.5 + 10.0 * ma_diff)  # Cap at 1.0
            
        elif fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma:
            # Bearish crossover with strength based on difference
            return max(-1.0, -0.5 + 10.0 * ma_diff)  # Cap at -1.0
            
        else:
            # No crossover, but still provide directional bias
            return np.clip(5.0 * ma_diff, -0.4, 0.4)  # Weaker signal without crossover
    
    def _calculate_mean_reversion_signal(self, symbol):
        """
        Calculate mean reversion signal (-1.0 to 1.0) based on RSI.
        """
        # Get historical prices
        data = self.data[symbol]
        closes = [bar['close'] for bar in data]
        
        # Calculate RSI
        rsi = self._calculate_rsi(closes, self.rsi_window)
        
        # Enhanced RSI signal with stronger values at extremes
        if rsi >= self.rsi_overbought:
            # Overbought - sell signal, stronger as RSI goes higher
            signal_strength = min(1.0, (rsi - self.rsi_overbought) / (100 - self.rsi_overbought))
            return -0.5 - 0.5 * signal_strength  # -0.5 to -1.0
            
        elif rsi <= self.rsi_oversold:
            # Oversold - buy signal, stronger as RSI goes lower
            signal_strength = min(1.0, (self.rsi_oversold - rsi) / self.rsi_oversold)
            return 0.5 + 0.5 * signal_strength  # 0.5 to 1.0
            
        else:
            # Neutral zone - weak reversion signal based on distance from midpoint
            midpoint = (self.rsi_overbought + self.rsi_oversold) / 2
            normalized_distance = (rsi - midpoint) / (self.rsi_overbought - midpoint)
            return -0.3 * normalized_distance  # Small signal, opposite to direction
    
    def _calculate_volatility_signal(self, symbol):
        """
        Calculate volatility breakout signal (-1.0 to 1.0).
        """
        # Get historical data
        data = self.data[symbol]
        highs = [bar['high'] for bar in data]
        lows = [bar['low'] for bar in data]
        closes = [bar['close'] for bar in data]
        
        # Current price
        current_close = closes[-1]
        
        # Calculate Average True Range (ATR) for volatility measure
        atr = self._calculate_atr(highs, lows, closes, self.breakout_window)
        
        # Calculate recent price channel
        recent_highs = highs[-self.breakout_window:-1]  # Exclude current bar
        recent_lows = lows[-self.breakout_window:-1]    # Exclude current bar
        channel_high = max(recent_highs)
        channel_low = min(recent_lows)
        
        # Dynamic breakout levels using ATR
        breakout_high = channel_high + self.breakout_multiplier * atr
        breakout_low = channel_low - self.breakout_multiplier * atr
        
        # Calculate signal
        if current_close > breakout_high:
            # Bullish breakout - signal strength based on how far above
            signal_strength = min(1.0, (current_close - breakout_high) / (breakout_high - channel_high))
            return min(1.0, 0.5 + 0.5 * signal_strength)  # 0.5 to 1.0
            
        elif current_close < breakout_low:
            # Bearish breakout - signal strength based on how far below
            signal_strength = min(1.0, (breakout_low - current_close) / (channel_low - breakout_low))
            return max(-1.0, -0.5 - 0.5 * signal_strength)  # -0.5 to -1.0
            
        else:
            # No breakout
            return 0.0
    
    def _calculate_rsi(self, prices, window):
        """
        Calculate Relative Strength Index (RSI).
        """
        if len(prices) <= window:
            return 50  # Default value if not enough data
        
        # Calculate price changes
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Calculate average gains and losses
        recent_changes = changes[-(window+1):]  # +1 for calculations
        gains = [max(0, change) for change in recent_changes]
        losses = [max(0, -change) for change in recent_changes]
        
        # Calculate average gain and loss
        avg_gain = sum(gains[-window:]) / window
        avg_loss = sum(losses[-window:]) / window
        
        # Handle zero losses
        if avg_loss == 0:
            return 100
        
        # Calculate RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_atr(self, highs, lows, closes, window):
        """
        Calculate Average True Range (ATR).
        """
        if len(closes) <= window:
            return 0.01 * closes[-1]  # Default 1% if not enough data
        
        # Calculate true ranges
        tr = []
        for i in range(1, len(closes)):
            high = highs[i]
            low = lows[i]
            prev_close = closes[i-1]
            
            tr1 = high - low  # Current high - low
            tr2 = abs(high - prev_close)  # Current high - previous close
            tr3 = abs(low - prev_close)  # Current low - previous close
            
            tr.append(max(tr1, tr2, tr3))
        
        # Calculate ATR as simple average of true ranges
        recent_tr = tr[-window:]
        atr = sum(recent_tr) / window
        
        return atr
    
    def reset(self):
        """Reset the strategy state."""
        # Reset internal state
        self.data = {symbol: [] for symbol in self.symbols}
        self.current_regimes = {symbol: MarketRegime.NEUTRAL for symbol in self.symbols}
        self.signal_count = 0
        
        logger.info(f"Simple Regime Ensemble strategy {self.name} reset")