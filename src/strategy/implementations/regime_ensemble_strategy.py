"""
Regime-Aware Ensemble Strategy Implementation.

This advanced strategy combines multiple trading rules and adapts their weights
based on detected market regimes. The strategy includes:
1. Trend Following (MA Crossover)
2. Mean Reversion (RSI Oversold/Overbought)
3. Volatility Breakout
4. Regime Detection and Rule Weighting
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event
from src.strategy.strategy_base import Strategy

logger = logging.getLogger(__name__)

# Regime types
class MarketRegime:
    """Market regime types."""
    TREND = "trend"
    MEAN_REVERSION = "mean_reversion"
    VOLATILE = "volatile"
    NEUTRAL = "neutral"


class RegimeEnsembleStrategy(Strategy):
    """
    Regime-aware ensemble strategy that combines multiple trading rules
    and adapts their weights based on detected market regimes.
    """
    
    # Define name as a class variable
    name = "regime_ensemble"
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        """
        Initialize the Regime Ensemble strategy.
        
        Args:
            event_bus: Event bus for communication
            data_handler: Data handler for market data
            name: Optional strategy name override
            parameters: Initial strategy parameters
        """
        # Call parent constructor with name from class or override
        super().__init__(event_bus, data_handler, name or self.name, parameters)
        
        # Extract parameters with defaults
        self._set_default_parameters()
        
        # Internal state
        self.data = {symbol: [] for symbol in self.symbols}
        self.current_regimes = {symbol: MarketRegime.NEUTRAL for symbol in self.symbols}
        self.signal_count = 0
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
            
        logger.info(f"Regime Ensemble strategy initialized with {len(self.symbols)} symbols")
    
    def _set_default_parameters(self):
        """Set default parameter values."""
        # Regime detection parameters
        self.volatility_window = self.parameters.get('volatility_window', 20)
        self.volatility_threshold = self.parameters.get('volatility_threshold', 0.015)  # 1.5% daily
        self.trend_ma_window = self.parameters.get('trend_ma_window', 50)
        self.trend_threshold = self.parameters.get('trend_threshold', 0.05)  # 5% trend
        
        # Trend following parameters (MA Crossover)
        self.fast_ma_window = self.parameters.get('fast_ma_window', 10)
        self.slow_ma_window = self.parameters.get('slow_ma_window', 30)
        
        # Mean reversion parameters (RSI)
        self.rsi_window = self.parameters.get('rsi_window', 14)
        self.rsi_overbought = self.parameters.get('rsi_overbought', 70)
        self.rsi_oversold = self.parameters.get('rsi_oversold', 30)
        
        # Volatility breakout parameters
        self.breakout_window = self.parameters.get('breakout_window', 20)
        self.breakout_multiplier = self.parameters.get('breakout_multiplier', 2.0)
        
        # Rule weights for each regime
        self.regime_weights = self.parameters.get('regime_weights', {
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
        })
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        # Call parent configure first
        super().configure(config)
        
        # Update strategy-specific parameters
        self._set_default_parameters()
        
        # Reset data for all configured symbols
        self.data = {symbol: [] for symbol in self.symbols}
        self.current_regimes = {symbol: MarketRegime.NEUTRAL for symbol in self.symbols}
        
        logger.info(f"Regime Ensemble strategy configured with {len(self.symbols)} symbols")
    
    def on_bar(self, bar_event):
        """
        Process a bar event and generate signals.
        
        Args:
            bar_event: Market data bar event
            
        Returns:
            Optional signal event
        """
        # Extract data from bar event
        symbol = bar_event.get_symbol()
        
        # Skip if not in our symbol list
        if symbol not in self.symbols:
            return None
        
        # Extract price data
        timestamp = bar_event.get_timestamp()
        close_price = bar_event.get_close()
        high_price = bar_event.get_high()
        low_price = bar_event.get_low()
        
        # Store data for this symbol
        if symbol not in self.data:
            self.data[symbol] = []
        
        self.data[symbol].append({
            'timestamp': timestamp,
            'close': close_price,
            'high': high_price,
            'low': low_price
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
            return None
        
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
            
            # Create actual signal event
            signal = create_signal_event(
                signal_value=signal_value,
                price=close_price,
                symbol=symbol,
                rule_id=f"{self.name}_{self.signal_count}",
                timestamp=timestamp,
                metadata={'regime': regime}  # Include regime info in metadata
            )
            
            # Emit signal if we have an event bus
            if self.event_bus:
                self.event_bus.emit(signal)
            
            return signal
        
        return None
    
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
        
        Args:
            symbol: Symbol to calculate for
            
        Returns:
            Signal value between -1.0 and 1.0
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
        
        Args:
            symbol: Symbol to calculate for
            
        Returns:
            Signal value between -1.0 and 1.0
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
        
        Args:
            prices: List of price values
            window: RSI period
            
        Returns:
            RSI value (0-100)
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
        
        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            window: ATR period
            
        Returns:
            ATR value
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
        
        logger.info(f"Regime Ensemble strategy {self.name} reset")
