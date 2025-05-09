"""
Composite Strategy with Regime Filtering Implementation.

This strategy combines multiple sub-strategies (e.g., MA Crossover, Mean Reversion)
and applies a regime filter to determine which strategy to activate in different market conditions.
"""
import logging
from typing import Dict, List, Any, Optional
import numpy as np

from src.strategy.strategy_base import Strategy
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event

logger = logging.getLogger(__name__)

class CompositeRegimeStrategy(Strategy):
    """
    Composite strategy with regime filter implementation.
    
    This strategy:
    1. Combines multiple sub-strategies (e.g., MA Crossover, Mean Reversion)
    2. Uses a regime detector to identify market conditions
    3. Activates appropriate sub-strategies based on detected regime
    4. Weights and combines signals from active strategies
    """
    
    # Define name as a class variable for easier discovery
    name = "composite_regime"
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        """
        Initialize the Composite Regime strategy.
        
        Args:
            event_bus: Event bus for communication
            data_handler: Data handler for market data
            name: Optional strategy name override
            parameters: Initial strategy parameters
        """
        # Call parent constructor with name from class or override
        super().__init__(event_bus, data_handler, name or self.name, parameters)
        
        # Initialize sub-strategies and regime detector
        self.sub_strategies = {}  # name -> Strategy instance
        self.regime_detector = None
        self.current_regime = None
        self.regime_history = {symbol: [] for symbol in self.symbols}
        
        # Extract parameters with defaults
        self.regime_map = self.parameters.get('regime_map', {
            'trending': ['ma_crossover'],
            'mean_reverting': ['mean_reversion'],
            'volatile': ['volatility_breakout'],
            'neutral': ['ma_crossover', 'mean_reversion']  # Use both in neutral regime
        })
        
        self.strategy_weights = self.parameters.get('strategy_weights', {
            'ma_crossover': 1.0,
            'mean_reversion': 1.0,
            'volatility_breakout': 1.0
        })
        
        self.signal_threshold = self.parameters.get('signal_threshold', 0.5)
        self.lookback_window = self.parameters.get('lookback_window', 50)
        
        # Data storage for regime detection
        self.data = {symbol: [] for symbol in self.symbols}
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
            
        logger.info(f"Composite Regime strategy initialized with {len(self.regime_map)} regime mappings")
    
    def add_sub_strategy(self, name: str, strategy: Strategy) -> None:
        """
        Add a sub-strategy to the composite.
        
        Args:
            name: Name of the strategy
            strategy: Strategy instance to add
        """
        self.sub_strategies[name] = strategy
        logger.info(f"Added sub-strategy: {name}")
        
    def set_regime_detector(self, detector: Any) -> None:
        """
        Set the regime detector.
        
        Args:
            detector: Regime detector instance
        """
        self.regime_detector = detector
        logger.info(f"Set regime detector: {detector.__class__.__name__}")
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        # Call parent configure first
        super().configure(config)
        
        # Update strategy-specific parameters
        self.regime_map = self.parameters.get('regime_map', self.regime_map)
        self.strategy_weights = self.parameters.get('strategy_weights', self.strategy_weights)
        self.signal_threshold = self.parameters.get('signal_threshold', self.signal_threshold)
        self.lookback_window = self.parameters.get('lookback_window', self.lookback_window)
        
        # Configure sub-strategies if available
        sub_strategy_configs = self.parameters.get('sub_strategies', {})
        for name, strategy_config in sub_strategy_configs.items():
            if name in self.sub_strategies:
                self.sub_strategies[name].configure(strategy_config)
                logger.info(f"Configured sub-strategy: {name}")
        
        # Configure regime detector if available
        regime_detector_config = self.parameters.get('regime_detector', {})
        if self.regime_detector and regime_detector_config:
            if hasattr(self.regime_detector, 'configure'):
                self.regime_detector.configure(regime_detector_config)
                logger.info(f"Configured regime detector")
        
        logger.info(f"Composite Regime strategy configured with {len(self.regime_map)} regime mappings")
    
    def detect_regime(self, symbol: str, data: List[Dict[str, Any]]) -> str:
        """
        Detect market regime using the attached regime detector.
        
        Args:
            symbol: Symbol to detect regime for
            data: Market data for the symbol
            
        Returns:
            str: Detected regime (e.g., 'trending', 'mean_reverting', 'volatile', 'neutral')
        """
        if not self.regime_detector:
            logger.warning("No regime detector available, defaulting to 'neutral'")
            return 'neutral'
        
        # Use the regime detector to identify current market regime
        regime = self.regime_detector.detect_regime(symbol, data)
        
        logger.debug(f"Detected regime for {symbol}: {regime}")
        return regime
    
    def get_active_strategies(self, regime: str) -> List[str]:
        """
        Get active strategies for the current regime.
        
        Args:
            regime: Current market regime
            
        Returns:
            List[str]: List of active strategy names
        """
        # Get strategies for the current regime, or all if not specified
        active_strategies = self.regime_map.get(regime, list(self.sub_strategies.keys()))
        
        # Filter to only include available strategies
        available_strategies = [name for name in active_strategies if name in self.sub_strategies]
        
        if not available_strategies:
            logger.warning(f"No active strategies for regime {regime}, using all available strategies")
            available_strategies = list(self.sub_strategies.keys())
        
        logger.debug(f"Active strategies for regime {regime}: {available_strategies}")
        return available_strategies
    
    def on_bar(self, bar_event):
        """
        Process a bar event and generate signals based on regime and active strategies.
        
        Args:
            bar_event: Market data bar event
            
        Returns:
            Optional signal event with directional value
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
            'open': bar_event.get_open(),
            'high': bar_event.get_high(),
            'low': bar_event.get_low(),
            'volume': bar_event.get_volume()
        })
        
        # Limit data to lookback window
        if len(self.data[symbol]) > self.lookback_window:
            self.data[symbol] = self.data[symbol][-self.lookback_window:]
        
        # Check if we have enough data
        if len(self.data[symbol]) < min(20, self.lookback_window):
            return None
        
        # Detect current regime
        self.current_regime = self.detect_regime(symbol, self.data[symbol])
        
        # Store regime history
        self.regime_history[symbol].append({
            'timestamp': timestamp,
            'regime': self.current_regime
        })
        
        # Get active strategies for current regime
        active_strategies = self.get_active_strategies(self.current_regime)
        
        # Collect signals from active strategies
        signals = []
        for strategy_name in active_strategies:
            strategy = self.sub_strategies.get(strategy_name)
            if not strategy:
                continue
            
            # Get signal from strategy
            # Note: We're bypassing the event system here to directly get the signal
            strategy_signal = strategy.on_bar(bar_event)
            
            if strategy_signal:
                weight = self.strategy_weights.get(strategy_name, 1.0)
                signal_value = strategy_signal.get_signal_value()
                
                signals.append({
                    'name': strategy_name,
                    'value': signal_value,
                    'weight': weight,
                    'weighted_value': signal_value * weight
                })
                
                logger.debug(f"Strategy {strategy_name} generated signal: {signal_value} with weight {weight}")
        
        # If no signals, return None
        if not signals:
            return None
        
        # Calculate weighted average signal
        total_weight = sum(s['weight'] for s in signals)
        if total_weight > 0:
            weighted_signal = sum(s['weighted_value'] for s in signals) / total_weight
        else:
            weighted_signal = 0
        
        # Apply threshold for signal generation
        # Convert to -1, 0, or 1 based on threshold
        if weighted_signal > self.signal_threshold:
            final_signal = 1
        elif weighted_signal < -self.signal_threshold:
            final_signal = -1
        else:
            final_signal = 0
        
        # If we have a signal, create a signal event
        if final_signal != 0:
            # Add a unique rule ID that includes regime information
            rule_id = f"composite_regime_{self.current_regime}_{symbol}_{timestamp}"
            
            # Create a signal event with rule_id
            signal = create_signal_event(
                signal_type=final_signal,
                symbol=symbol,
                timestamp=timestamp,
                strategy_id=rule_id
            , strength=abs(signal_value))
            
            # Add additional metadata about the signal
            if hasattr(signal, 'data') and isinstance(signal.data, dict):
                signal.data['regime'] = self.current_regime
                signal.data['active_strategies'] = active_strategies
                signal.data['component_signals'] = signals
            
            # Emit signal if we have an event bus
            if self.event_bus:
                self.event_bus.emit(signal)
                logger.info(f"Composite signal emitted for {symbol}: {final_signal}, regime={self.current_regime}")
            
            return signal
        
        return None
    
    def reset(self):
        """Reset the strategy state."""
        # Reset strategy-specific state
        self.data = {symbol: [] for symbol in self.symbols}
        self.regime_history = {symbol: [] for symbol in self.symbols}
        self.current_regime = None
        
        # Reset sub-strategies
        for strategy in self.sub_strategies.values():
            if hasattr(strategy, 'reset'):
                strategy.reset()
        
        # Reset regime detector
        if self.regime_detector and hasattr(self.regime_detector, 'reset'):
            self.regime_detector.reset()
        
        logger.info(f"Composite Regime strategy {self.name} reset")