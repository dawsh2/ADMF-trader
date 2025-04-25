# src/strategies/composite_strategy.py
from .strategy_base import Strategy
from typing import Dict, Any, List, Optional

class CompositeStrategy(Strategy):
    """
    Strategy that composes multiple sub-strategies.
    
    This can be used for:
    1. Multi-rule strategies
    2. Strategy ensembles
    3. Regime-filtered strategies
    4. Any other strategy composition
    """
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        """Initialize composite strategy."""
        super().__init__(event_bus, data_handler, name, parameters)
        self.strategies = []  # List of sub-strategies
        self.combination_method = 'majority'  # How to combine signals
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        super().configure(config)
        # Extract strategy-specific parameters
        self.combination_method = self.parameters.get('combination_method', 'majority')
    
    def add_strategy(self, strategy):
        """
        Add a sub-strategy.
        
        Args:
            strategy: Strategy to add
        """
        self.strategies.append(strategy)
        # Also add as a component for parameter handling
        self.add_component(strategy, 'strategy')
    
    def on_bar(self, bar_event):
        """
        Handle bar events by delegating to sub-strategies and combining signals.
        
        Args:
            bar_event: Bar event to process
            
        Returns:
            Optional signal event
        """
        if not self.configured or not self.strategies:
            return None
            
        symbol = bar_event.get_symbol()
        if symbol not in self.symbols:
            return None
        
        # Collect signals from all sub-strategies
        signals = []
        for strategy in self.strategies:
            signal_event = strategy.on_bar(bar_event)
            if signal_event:
                signals.append((signal_event.get_signal_value(), strategy.parameters.get('weight', 1.0)))
        
        # Combine signals based on method
        combined_signal = self._combine_signals(signals)
        
        # Generate signal event if non-zero
        if combined_signal != 0:
            current_price = bar_event.get_close()
            return create_signal_event(combined_signal, current_price, symbol, self.name)
        
        return None
    
    def _combine_signals(self, signals):
        """
        Combine signals from multiple strategies.
        
        Args:
            signals: List of (signal_value, weight) tuples
            
        Returns:
            Combined signal value (-1, 0, or 1)
        """
        # Implementation similar to the original MultiRuleStrategy
        if not signals:
            return 0
            
        if self.combination_method == 'majority':
            weighted_sum = sum(signal * weight for signal, weight in signals)
            if weighted_sum > 0:
                return 1
            elif weighted_sum < 0:
                return -1
            else:
                return 0
        # Other combination methods...
        return 0
