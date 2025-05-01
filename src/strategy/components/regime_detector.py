"""
Market Regime Detector Implementation.

This module provides components for detecting market regimes such as trending, 
mean-reverting, volatile, and choppy markets. These detectors can be used by
strategies to adapt to changing market conditions.
"""
import logging
import numpy as np
from enum import Enum
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Enumeration of market regime types."""
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    VOLATILE = "volatile"
    NEUTRAL = "neutral"

class RegimeDetector(ABC):
    """Base class for market regime detectors."""
    
    def __init__(self, name=None, parameters=None):
        """
        Initialize the regime detector.
        
        Args:
            name: Optional detector name
            parameters: Initial detector parameters
        """
        self.name = name or self.__class__.__name__
        self.parameters = parameters or {}
        
    def configure(self, config):
        """
        Configure the detector with parameters.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        self.parameters.update(config_dict)
        logger.info(f"Regime detector {self.name} configured with parameters: {config_dict}")
    
    @abstractmethod
    def detect_regime(self, symbol: str, data: List[Dict[str, Any]]) -> str:
        """
        Detect market regime from price data.
        
        Args:
            symbol: Symbol to detect regime for
            data: List of price data dictionaries
            
        Returns:
            str: Detected regime as string
        """
        pass
    
    def reset(self):
        """Reset detector state."""
        logger.info(f"Regime detector {self.name} reset")


class TrendStrengthDetector(RegimeDetector):
    """
    Trend strength detector using ADX (Average Directional Index).
    
    This detector evaluates trend strength using a calculation similar to ADX.
    It classifies markets as trending, mean-reverting, or neutral based on
    directional movement over a specified period.
    """
    
    def __init__(self, name=None, parameters=None):
        """
        Initialize the trend strength detector.
        
        Args:
            name: Optional detector name
            parameters: Initial detector parameters
        """
        super().__init__(name, parameters)
        
        # Extract parameters with defaults
        self.period = self.parameters.get('period', 14)
        self.trending_threshold = self.parameters.get('trending_threshold', 25)
        self.mean_reverting_threshold = self.parameters.get('mean_reverting_threshold', 15)
        self.smooth_period = self.parameters.get('smooth_period', 3)
        
        # Internal state
        self._adx_values = {}  # symbol -> list of ADX values
        
    def configure(self, config):
        """Configure the detector with parameters."""
        super().configure(config)
        
        # Update parameters
        self.period = self.parameters.get('period', self.period)
        self.trending_threshold = self.parameters.get('trending_threshold', self.trending_threshold)
        self.mean_reverting_threshold = self.parameters.get('mean_reverting_threshold', self.mean_reverting_threshold)
        self.smooth_period = self.parameters.get('smooth_period', self.smooth_period)
        
        # Reset state
        self._adx_values = {}
        
    def _calculate_adx(self, data: List[Dict[str, Any]]) -> float:
        """
        Calculate ADX (Average Directional Index) for trend strength.
        
        This is a simplified ADX calculation that captures the essence of the 
        indicator without full implementation details.
        
        Args:
            data: Price data including high, low, price (close)
            
        Returns:
            float: ADX value
        """
        if len(data) < self.period + 1:
            return 0
        
        # Prepare arrays for calculation
        high = np.array([bar['high'] for bar in data])
        low = np.array([bar['low'] for bar in data])
        close = np.array([bar['price'] for bar in data])
        
        # Calculate True Range (TR)
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        # Calculate Directional Movement
        up_move = high[1:] - high[:-1]
        down_move = low[:-1] - low[1:]
        
        plus_dm = np.zeros_like(up_move)
        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
        
        minus_dm = np.zeros_like(down_move)
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]
        
        # Smooth the TR and DM values
        tr_smooth = np.zeros(len(tr) - self.period + 1)
        plus_dm_smooth = np.zeros(len(plus_dm) - self.period + 1)
        minus_dm_smooth = np.zeros(len(minus_dm) - self.period + 1)
        
        # First value is sum of first period elements
        tr_smooth[0] = np.sum(tr[:self.period])
        plus_dm_smooth[0] = np.sum(plus_dm[:self.period])
        minus_dm_smooth[0] = np.sum(minus_dm[:self.period])
        
        # Rest of values use Wilder's smoothing
        for i in range(1, len(tr_smooth)):
            tr_smooth[i] = tr_smooth[i-1] - (tr_smooth[i-1] / self.period) + tr[i + self.period - 1]
            plus_dm_smooth[i] = plus_dm_smooth[i-1] - (plus_dm_smooth[i-1] / self.period) + plus_dm[i + self.period - 1]
            minus_dm_smooth[i] = minus_dm_smooth[i-1] - (minus_dm_smooth[i-1] / self.period) + minus_dm[i + self.period - 1]
        
        # Calculate Directional Indicators
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)
        
        # Calculate Directional Index
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # Calculate Average Directional Index with smoothing
        if len(dx) < self.smooth_period:
            return 0
            
        adx = np.mean(dx[-self.smooth_period:])
        return adx
    
    def detect_regime(self, symbol: str, data: List[Dict[str, Any]]) -> str:
        """
        Detect market regime based on trend strength.
        
        Args:
            symbol: Symbol to detect regime for
            data: List of price data dictionaries
            
        Returns:
            str: Detected regime as string
        """
        if len(data) < self.period + 1:
            logger.debug(f"Insufficient data for {symbol} regime detection, defaulting to neutral")
            return MarketRegime.NEUTRAL.value
        
        # Calculate ADX
        adx = self._calculate_adx(data)
        
        # Track ADX values for this symbol
        if symbol not in self._adx_values:
            self._adx_values[symbol] = []
        
        self._adx_values[symbol].append(adx)
        
        # Keep only recent ADX values
        max_history = 100  # Limit history to prevent memory leaks
        if len(self._adx_values[symbol]) > max_history:
            self._adx_values[symbol] = self._adx_values[symbol][-max_history:]
        
        # Determine regime based on ADX value
        if adx > self.trending_threshold:
            regime = MarketRegime.TRENDING.value
        elif adx < self.mean_reverting_threshold:
            regime = MarketRegime.MEAN_REVERTING.value
        else:
            regime = MarketRegime.NEUTRAL.value
        
        logger.debug(f"Detected regime for {symbol}: {regime} (ADX: {adx:.2f})")
        return regime


class VolatilityRegimeDetector(RegimeDetector):
    """
    Volatility regime detector using price volatility measures.
    
    This detector classifies markets as volatile, trending, or mean-reverting
    based on price volatility and patterns.
    """
    
    def __init__(self, name=None, parameters=None):
        """
        Initialize the volatility regime detector.
        
        Args:
            name: Optional detector name
            parameters: Initial detector parameters
        """
        super().__init__(name, parameters)
        
        # Extract parameters with defaults
        self.window = self.parameters.get('window', 20)
        self.volatile_threshold = self.parameters.get('volatile_threshold', 1.5)
        self.trend_threshold = self.parameters.get('trend_threshold', 0.8)
        self.use_rolling = self.parameters.get('use_rolling', True)
        
        # Internal state
        self._volatility_history = {}  # symbol -> list of volatility values
        
    def configure(self, config):
        """Configure the detector with parameters."""
        super().configure(config)
        
        # Update parameters
        self.window = self.parameters.get('window', self.window)
        self.volatile_threshold = self.parameters.get('volatile_threshold', self.volatile_threshold)
        self.trend_threshold = self.parameters.get('trend_threshold', self.trend_threshold)
        self.use_rolling = self.parameters.get('use_rolling', self.use_rolling)
        
        # Reset state
        self._volatility_history = {}
        
    def _calculate_volatility(self, prices: np.array) -> float:
        """
        Calculate price volatility (standard deviation / mean).
        
        Args:
            prices: Array of price data
            
        Returns:
            float: Volatility measure
        """
        if len(prices) < 2:
            return 0
            
        # Calculate price returns
        returns = np.diff(prices) / prices[:-1]
        
        # Calculate volatility as standard deviation of returns
        volatility = np.std(returns)
        
        return volatility
    
    def _calculate_normalized_volatility(self, data: List[Dict[str, Any]]) -> float:
        """
        Calculate normalized volatility relative to historical levels.
        
        Args:
            data: Price data
            
        Returns:
            float: Normalized volatility
        """
        if len(data) < self.window:
            return 0
            
        # Extract price data
        prices = np.array([bar['price'] for bar in data])
        
        # Calculate current volatility
        current_volatility = self._calculate_volatility(prices[-self.window:])
        
        if self.use_rolling and len(data) >= self.window * 2:
            # Calculate historical volatility for comparison
            windows = len(data) - self.window
            historical_volatilities = []
            
            for i in range(windows):
                window_prices = prices[i:i+self.window]
                vol = self._calculate_volatility(window_prices)
                historical_volatilities.append(vol)
            
            # Calculate average historical volatility
            avg_historical_volatility = np.mean(historical_volatilities)
            
            # Normalize current volatility against historical average
            if avg_historical_volatility > 0:
                normalized_volatility = current_volatility / avg_historical_volatility
            else:
                normalized_volatility = 1.0
                
        else:
            # Without enough history, just use the current volatility
            normalized_volatility = current_volatility * 10  # Scale for comparison
        
        return normalized_volatility
    
    def detect_regime(self, symbol: str, data: List[Dict[str, Any]]) -> str:
        """
        Detect market regime based on volatility.
        
        Args:
            symbol: Symbol to detect regime for
            data: List of price data dictionaries
            
        Returns:
            str: Detected regime as string
        """
        if len(data) < self.window:
            logger.debug(f"Insufficient data for {symbol} regime detection, defaulting to neutral")
            return MarketRegime.NEUTRAL.value
        
        # Calculate normalized volatility
        normalized_volatility = self._calculate_normalized_volatility(data)
        
        # Track volatility for this symbol
        if symbol not in self._volatility_history:
            self._volatility_history[symbol] = []
        
        self._volatility_history[symbol].append(normalized_volatility)
        
        # Keep only recent volatility values
        max_history = 100  # Limit history to prevent memory leaks
        if len(self._volatility_history[symbol]) > max_history:
            self._volatility_history[symbol] = self._volatility_history[symbol][-max_history:]
        
        # Calculate directional tendency from recent prices
        prices = np.array([bar['price'] for bar in data[-self.window:]])
        price_changes = np.diff(prices)
        pos_changes = np.sum(price_changes > 0)
        neg_changes = np.sum(price_changes < 0)
        
        directional_ratio = abs(pos_changes - neg_changes) / len(price_changes)
        
        # Determine regime based on volatility and directional ratio
        if normalized_volatility > self.volatile_threshold:
            regime = MarketRegime.VOLATILE.value
        elif directional_ratio > self.trend_threshold:
            regime = MarketRegime.TRENDING.value
        else:
            regime = MarketRegime.MEAN_REVERTING.value
        
        logger.debug(f"Detected regime for {symbol}: {regime} (Volatility: {normalized_volatility:.2f}, DirectionalRatio: {directional_ratio:.2f})")
        return regime


class MultiFactorRegimeDetector(RegimeDetector):
    """
    Multi-factor regime detector that combines multiple measures.
    
    This detector uses a combination of trend strength, volatility,
    mean reversion indicators, and other factors to provide a more
    robust regime classification.
    """
    
    def __init__(self, name=None, parameters=None):
        """
        Initialize the multi-factor regime detector.
        
        Args:
            name: Optional detector name
            parameters: Initial detector parameters
        """
        super().__init__(name, parameters)
        
        # Create sub-detectors
        self.trend_detector = TrendStrengthDetector(
            parameters=self.parameters.get('trend_detector', {})
        )
        self.volatility_detector = VolatilityRegimeDetector(
            parameters=self.parameters.get('volatility_detector', {})
        )
        
        # Extract parameters with defaults
        self.window = self.parameters.get('window', 30)
        self.weights = self.parameters.get('weights', {
            'trend': 0.5,
            'volatility': 0.5
        })
        
        # Internal state
        self._regime_history = {}  # symbol -> list of regime values
        
    def configure(self, config):
        """Configure the detector with parameters."""
        super().configure(config)
        
        # Update parameters
        self.window = self.parameters.get('window', self.window)
        self.weights = self.parameters.get('weights', self.weights)
        
        # Configure sub-detectors
        trend_config = self.parameters.get('trend_detector', {})
        volatility_config = self.parameters.get('volatility_detector', {})
        
        self.trend_detector.configure(trend_config)
        self.volatility_detector.configure(volatility_config)
        
        # Reset state
        self._regime_history = {}
        
    def detect_regime(self, symbol: str, data: List[Dict[str, Any]]) -> str:
        """
        Detect market regime using multiple factors.
        
        Args:
            symbol: Symbol to detect regime for
            data: List of price data dictionaries
            
        Returns:
            str: Detected regime as string
        """
        if len(data) < self.window:
            logger.debug(f"Insufficient data for {symbol} regime detection, defaulting to neutral")
            return MarketRegime.NEUTRAL.value
        
        # Get regime from each detector
        trend_regime = self.trend_detector.detect_regime(symbol, data)
        volatility_regime = self.volatility_detector.detect_regime(symbol, data)
        
        # Count votes for each regime
        regime_votes = {
            MarketRegime.TRENDING.value: 0,
            MarketRegime.MEAN_REVERTING.value: 0,
            MarketRegime.VOLATILE.value: 0,
            MarketRegime.NEUTRAL.value: 0
        }
        
        # Add weighted votes from trend detector
        trend_weight = self.weights.get('trend', 0.5)
        regime_votes[trend_regime] += trend_weight
        
        # Add weighted votes from volatility detector
        volatility_weight = self.weights.get('volatility', 0.5)
        regime_votes[volatility_regime] += volatility_weight
        
        # Determine final regime based on votes
        final_regime = max(regime_votes, key=regime_votes.get)
        
        # Track regime history for this symbol
        if symbol not in self._regime_history:
            self._regime_history[symbol] = []
        
        self._regime_history[symbol].append(final_regime)
        
        # Keep only recent regime values
        max_history = 100  # Limit history to prevent memory leaks
        if len(self._regime_history[symbol]) > max_history:
            self._regime_history[symbol] = self._regime_history[symbol][-max_history:]
        
        logger.debug(f"Detected multi-factor regime for {symbol}: {final_regime}")
        logger.debug(f"Regime votes: {regime_votes}")
        
        return final_regime
    
    def reset(self):
        """Reset detector state."""
        super().reset()
        
        # Reset sub-detectors
        self.trend_detector.reset()
        self.volatility_detector.reset()
        
        # Reset internal state
        self._regime_history = {}