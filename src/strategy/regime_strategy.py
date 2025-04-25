# src/strategies/regime_strategy.py
from .composite_strategy import CompositeStrategy
from typing import Dict, Any, List, Optional

class RegimeStrategy(CompositeStrategy):
    """
    Strategy that adapts to different market regimes.
    
    This can be:
    1. A strategy that filters signals based on regime
    2. A strategy that uses different parameter sets per regime
    3. A strategy that selects different sub-strategies per regime
    """
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        """Initialize regime strategy."""
        super().__init__(event_bus, data_handler, name, parameters)
        self.regime_detector = None
        self.regime_mappings = {}  # Regime -> strategy or parameter set
        self.current_regimes = {}  # Symbol -> current regime
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        super().configure(config)
        # Extract regime mappings
        self.regime_mappings = self.parameters.get('regime_mappings', {})
    
    def set_regime_detector(self, detector):
        """
        Set the regime detector.
        
        Args:
            detector: Regime detector component
        """
        self.regime_detector = detector
        self.add_component(detector, 'detector')
    
    def on_bar(self, bar_event):
        """
        Handle bar events with regime detection.
        
        Args:
            bar_event: Bar event to process
            
        Returns:
            Optional signal event
        """
        if not self.configured or not self.regime_detector:
            return super().on_bar(bar_event)
            
        symbol = bar_event.get_symbol()
        if symbol not in self.symbols:
            return None
        
        # Get data for regime detection
        lookback = self.regime_detector.parameters.get('lookback', 50)
        bars = self.data_handler.get_latest_bars(symbol, lookback)
        if len(bars) < lookback:
            # Not enough data for regime detection
            return super().on_bar(bar_event)
        
        # Create DataFrame from bars
        import pandas as pd
        df = pd.DataFrame([b.__dict__ for b in bars])
        
        # Detect current regime
        current_regime = self.regime_detector.detect_regime(df)
        self.current_regimes[symbol] = current_regime
        
        # Apply regime-specific behavior (multiple options demonstrated)
        if self.parameters.get('regime_strategy_type', 'filter') == 'filter':
            # Filter signals based on regime
            signal_event = super().on_bar(bar_event)
            if signal_event and current_regime in self.regime_mappings:
                allowed_signals = self.regime_mappings[current_regime]
                if signal_event.get_signal_value() not in allowed_signals:
                    return None  # Signal filtered out by regime
            return signal_event
        
        elif self.parameters.get('regime_strategy_type') == 'select':
            # Select regime-specific strategy
            if current_regime in self.regime_mappings:
                strategy_name = self.regime_mappings[current_regime]
                strategy = self.get_component(f"strategy.{strategy_name}")
                if strategy:
                    return strategy.on_bar(bar_event)
            # Fallback to default behavior
            return super().on_bar(bar_event)
        
        elif self.parameters.get('regime_strategy_type') == 'params':
            # Apply regime-specific parameters temporarily
            if current_regime in self.regime_mappings:
                # Save current parameters
                original_params = self.get_parameters()
                
                # Apply regime-specific parameters
                regime_params = self.regime_mappings[current_regime]
                self.set_parameters(regime_params)
                
                # Process with regime parameters
                signal_event = super().on_bar(bar_event)
                
                # Restore original parameters
                self.set_parameters(original_params)
                
                return signal_event
            
            # No regime match, use default
            return super().on_bar(bar_event)
        
        # Default behavior
        return super().on_bar(bar_event)
