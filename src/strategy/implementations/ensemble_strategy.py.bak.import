"""
Ensemble Strategy Implementation.

This strategy combines signals from multiple sub-strategies to produce a consolidated signal.
It demonstrates how to implement ensemble approaches while maintaining the separation between
signal generation and position management.
"""
import logging
from typing import Dict, Any, List, Optional

from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event
from src.strategy.strategy_base import Strategy

logger = logging.getLogger(__name__)

class EnsembleStrategy(Strategy):
    """
    Ensemble strategy that combines signals from multiple sub-strategies.
    
    This strategy demonstrates:
    1. How to combine multiple signal sources
    2. How to maintain the separation of concerns (no position tracking)
    3. How to implement ensemble aggregation methods (voting, weighted, etc.)
    """
    
    name = "ensemble_strategy"
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        """
        Initialize the Ensemble strategy.
        
        Args:
            event_bus: Event bus for communication
            data_handler: Data handler for market data
            name: Optional strategy name override
            parameters: Initial strategy parameters
        """
        # Call parent constructor with name from class or override
        super().__init__(event_bus, data_handler, name or self.name, parameters)
        
        # Sub-strategies collection
        self.sub_strategies = []
        
        # Extract parameters
        self.ensemble_method = self.parameters.get('ensemble_method', 'majority_vote')
        self.min_agreement = self.parameters.get('min_agreement', 0.5)  # For majority voting
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
            
        logger.info(f"Ensemble strategy initialized with method={self.ensemble_method}")
    
    def add_strategy(self, strategy):
        """
        Add a sub-strategy to the ensemble.
        
        Args:
            strategy: Strategy instance to add
        """
        self.sub_strategies.append(strategy)
        logger.info(f"Added sub-strategy: {strategy.name}")
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        # Call parent configure first
        super().configure(config)
        
        # Update strategy-specific parameters
        self.ensemble_method = self.parameters.get('ensemble_method', 'majority_vote')
        self.min_agreement = self.parameters.get('min_agreement', 0.5)
        
        # Configure sub-strategies if present
        if 'sub_strategies' in self.parameters:
            sub_configs = self.parameters['sub_strategies']
            for i, strategy in enumerate(self.sub_strategies):
                if i < len(sub_configs):
                    strategy.configure(sub_configs[i])
        
        logger.info(f"Ensemble strategy configured with method={self.ensemble_method}")
    
    def on_bar(self, bar_event):
        """
        Process a bar event by collecting signals from all sub-strategies and
        applying the ensemble method to produce a consolidated signal.
        
        Args:
            bar_event: Market data bar event
            
        Returns:
            Optional signal event with consolidated directional value
        """
        # Extract data from bar event
        symbol = bar_event.get_symbol()
        price = bar_event.get_close()
        timestamp = bar_event.get_timestamp()
        
        # Skip if not in our symbol list
        if symbol not in self.symbols:
            return None
        
        # Collect signals from all sub-strategies
        signals = []
        for strategy in self.sub_strategies:
            signal_event = strategy.on_bar(bar_event)
            if signal_event:
                signals.append(signal_event.get_signal_value())
                logger.debug(f"Sub-strategy {strategy.name} signal: {signal_event.get_signal_value()}")
        
        # If we have no signals, return None
        if not signals:
            return None
        
        # Apply ensemble method to get consolidated signal
        if self.ensemble_method == 'majority_vote':
            final_signal = self._majority_vote(signals)
        elif self.ensemble_method == 'unanimous':
            final_signal = self._unanimous_vote(signals)
        elif self.ensemble_method == 'average':
            final_signal = self._average_signal(signals)
        else:
            logger.warning(f"Unknown ensemble method: {self.ensemble_method}")
            return None
        
        # If no consensus reached (neutral), return None
        if final_signal == 0:
            return None
        
        # Create signal event with consolidated signal
        signal = create_signal_event(
            signal_value=final_signal,
            price=price,
            symbol=symbol,
            timestamp=timestamp
        )
        
        # Emit consolidated signal
        if self.event_bus:
            self.event_bus.emit(signal)
            logger.info(f"Ensemble signal emitted for {symbol}: {final_signal}")
        
        return signal
    
    def _majority_vote(self, signals):
        """Apply majority voting to signals."""
        if not signals:
            return 0
            
        bullish_count = sum(1 for s in signals if s > 0)
        bearish_count = sum(1 for s in signals if s < 0)
        total_count = len(signals)
        
        # Check if we have enough consensus
        bullish_ratio = bullish_count / total_count
        bearish_ratio = bearish_count / total_count
        
        if bullish_ratio >= self.min_agreement:
            return 1
        elif bearish_ratio >= self.min_agreement:
            return -1
        else:
            return 0  # No clear consensus
    
    def _unanimous_vote(self, signals):
        """Apply unanimous voting to signals."""
        if not signals:
            return 0
            
        # All signals must agree
        if all(s > 0 for s in signals):
            return 1
        elif all(s < 0 for s in signals):
            return -1
        else:
            return 0  # No unanimous consensus
    
    def _average_signal(self, signals):
        """Average all signals and threshold."""
        if not signals:
            return 0
            
        avg = sum(signals) / len(signals)
        
        # Threshold to get directional signal
        if avg > 0.5:
            return 1
        elif avg < -0.5:
            return -1
        else:
            return 0  # Neutral
    
    def reset(self):
        """Reset the strategy state."""
        # Reset strategy-specific state
        # Also reset all sub-strategies
        for strategy in self.sub_strategies:
            strategy.reset()
        
        logger.info(f"Ensemble strategy {self.name} reset")
