"""
Adaptive risk manager that adjusts to market regimes.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple, Union

from core.events.event_types import EventType
from .standard_risk_manager import StandardRiskManager
from .sizing import PositionSizerFactory
from .limits import LimitManagerFactory

logger = logging.getLogger(__name__)

class AdaptiveRiskManager(StandardRiskManager):
    """
    Risk manager that adapts to different market regimes.
    
    This manager extends the standard risk manager with:
    - Regime-specific parameter sets
    - Automatic parameter switching between regimes
    - Smooth transition between parameter sets
    - Optimization support for regime-specific parameters
    """
    
    def __init__(self, event_bus, portfolio_manager, 
                position_sizer=None, limit_manager=None, 
                regime_detector=None, name=None):
        """
        Initialize adaptive risk manager.
        
        Args:
            event_bus: Event bus for communication
            portfolio_manager: Portfolio for position information
            position_sizer: Optional position sizer
            limit_manager: Optional limit manager
            regime_detector: Optional regime detector component
            name: Optional risk manager name
        """
        super().__init__(
            event_bus=event_bus,
            portfolio_manager=portfolio_manager,
            position_sizer=position_sizer,
            limit_manager=limit_manager,
            name=name or "adaptive_risk_manager"
        )
        
        # Regime management
        self.regime_detector = regime_detector
        self.current_regime = "normal"  # Default regime
        self.regime_parameters = {
            "normal": {},  # Will be populated with defaults
        }
        self.transition_factor = 1.0  # For smooth transitions
        
        # Register for regime events
        if self.event_bus:
            self.event_bus.register(EventType.REGIME, self.on_regime)
        
        # Update stats
        self.stats.update({
            'regime_changes': 0,
            'current_regime': self.current_regime
        })
        
        # Configuration defaults - extend StandardRiskManager config
        self.config.update({
            'regime_adaptation': {
                'enabled': True,
                'smooth_transition': True,
                'transition_period': 5,  # Number of bars to transition
            },
            'regimes': {
                'normal': {
                    'position_sizing': {
                        'method': 'fixed',
                        'quantity': 100
                    },
                    'drawdown_control': {
                        'enabled': False,
                        'threshold': 0.05,
                        'reduction': 0.5,
                        'cutoff': 0.20
                    }
                },
                'bullish': {
                    'position_sizing': {
                        'method': 'percent_equity',
                        'percent': 10.0
                    },
                    'drawdown_control': {
                        'enabled': True,
                        'threshold': 0.10,
                        'reduction': 0.5,
                        'cutoff': 0.20
                    }
                },
                'bearish': {
                    'position_sizing': {
                        'method': 'percent_risk',
                        'risk_percent': 1.0,
                        'stop_percent': 3.0
                    },
                    'drawdown_control': {
                        'enabled': True,
                        'threshold': 0.03,
                        'reduction': 0.3,
                        'cutoff': 0.10
                    }
                },
                'volatile': {
                    'position_sizing': {
                        'method': 'volatility',
                        'atr_multiple': 1.0,
                        'risk_percent': 1.5
                    },
                    'drawdown_control': {
                        'enabled': True,
                        'threshold': 0.05,
                        'reduction': 0.3,
                        'cutoff': 0.15
                    }
                }
            }
        })
    
    def configure(self, config):
        """
        Configure the adaptive risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        # Use standard configuration first
        super().configure(config)
        
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        # Extract regime-specific configurations
        if 'regimes' in config_dict:
            regimes_config = config_dict['regimes']
            
            # Store regime-specific parameters
            for regime, regime_config in regimes_config.items():
                self.regime_parameters[regime] = regime_config
                
                # Create position sizer for this regime if required
                if 'position_sizing' in regime_config:
                    if regime not in self.regime_parameters:
                        self.regime_parameters[regime] = {}
                    
                    # Create and configure position sizer
                    regime_sizer = PositionSizerFactory.create(config=regime_config['position_sizing'])
                    self.regime_parameters[regime]['position_sizer'] = regime_sizer
        
        # Initialize with default regime
        self._apply_regime_parameters(self.current_regime)
        
        logger.info(f"Configured adaptive risk manager: {self.name}")
    
    def set_regime_detector(self, detector):
        """
        Set the regime detector component.
        
        Args:
            detector: Regime detector component
        """
        self.regime_detector = detector
    
    def on_regime(self, regime_event):
        """
        Handle regime change events.
        
        Args:
            regime_event: Regime event to process
        """
        # Track the event
        self.event_tracker.track_event(regime_event)
        
        # Extract regime information
        symbol = regime_event.data.get('symbol', '*')  # '*' for market-wide regime
        regime = regime_event.data.get('regime')
        confidence = regime_event.data.get('confidence', 1.0)
        
        if not regime:
            return  # Invalid regime event
        
        # Skip if no change or low confidence
        if regime == self.current_regime or confidence < 0.5:
            return
        
        # Update regime and apply parameters
        self._change_regime(regime)
    
    def on_bar(self, bar_event):
        """
        Handle bar events for regime detection.
        
        Args:
            bar_event: Bar event to process
        """
        # Track the event
        self.event_tracker.track_event(bar_event)
        
        # Skip if no regime detector
        if not self.regime_detector:
            return
        
        # Get current timestamp for transition handling
        self.current_timestamp = bar_event.get_timestamp()
        
        # Update transition factor if in transition
        if self.transition_factor < 1.0:
            self._update_transition()
    
    def _change_regime(self, new_regime):
        """
        Change to a new market regime.
        
        Args:
            new_regime: New regime name
        """
        # Skip if regime not defined
        if new_regime not in self.regime_parameters:
            logger.warning(f"Unknown regime: {new_regime}, staying in {self.current_regime}")
            return
        
        old_regime = self.current_regime
        self.current_regime = new_regime
        
        # Update stats
        self.stats['regime_changes'] += 1
        self.stats['current_regime'] = new_regime
        
        # Log regime change
        logger.info(f"Market regime changed: {old_regime} to {new_regime}")
        
        # Apply regime parameters
        if self.config['regime_adaptation']['smooth_transition']:
            self.transition_factor = 0.0  # Start transition
            self._update_transition()
        else:
            self._apply_regime_parameters(new_regime)
    
    def _update_transition(self):
        """Update transition factor and apply blended parameters."""
        if self.transition_factor < 1.0:
            # Increment transition factor
            transition_period = self.config['regime_adaptation']['transition_period']
            self.transition_factor += 1.0 / transition_period
            
            # Cap at 1.0
            self.transition_factor = min(1.0, self.transition_factor)
            
            # Apply blended parameters
            self._apply_blended_parameters()
    
    def _apply_regime_parameters(self, regime):
        """
        Apply parameters for a specific regime.
        
        Args:
            regime: Regime name
        """
        if regime not in self.regime_parameters:
            logger.warning(f"Unknown regime: {regime}, using default parameters")
            regime = "normal"  # Fall back to default
        
        regime_params = self.regime_parameters[regime]
        
        # Apply position sizing parameters
        if 'position_sizer' in regime_params:
            # Use pre-configured sizer
            self.position_sizer = regime_params['position_sizer']
        elif 'position_sizing' in regime_params:
            # Configure existing sizer
            self.position_sizer.configure(regime_params['position_sizing'])
        
        # Apply drawdown control parameters
        if 'drawdown_control' in regime_params:
            self.config['drawdown_control'] = regime_params['drawdown_control']
        
        # Apply other config parameters
        for section, section_config in regime_params.items():
            if section not in ['position_sizer', 'position_sizing', 'drawdown_control'] and section in self.config:
                if isinstance(section_config, dict):
                    self.config[section].update(section_config)
                else:
                    self.config[section] = section_config
    
    def _apply_blended_parameters(self):
        """Apply blended parameters during regime transition."""
        # Get parameters for both regimes
        from_regime = "normal"  # Default if not found
        for regime in self.regime_parameters:
            if regime != self.current_regime:
                from_regime = regime
                break
        
        from_params = self.regime_parameters.get(from_regime, {})
        to_params = self.regime_parameters.get(self.current_regime, {})
        
        # Blend position sizing parameters
        if 'position_sizing' in from_params and 'position_sizing' in to_params:
            from_sizing = from_params['position_sizing']
            to_sizing = to_params['position_sizing']
            
            # Check if methods are compatible for blending
            if from_sizing.get('method') == to_sizing.get('method'):
                blended_sizing = dict(to_sizing)  # Start with target values
                
                # Blend numeric parameters
                for param, value in to_sizing.items():
                    if param != 'method' and param in from_sizing and isinstance(value, (int, float)):
                        from_value = from_sizing[param]
                        blended_value = from_value + (value - from_value) * self.transition_factor
                        blended_sizing[param] = blended_value
                
                # Apply blended parameters
                self.position_sizer.configure(blended_sizing)
            else:
                # Can't blend different methods, use weighted random selection
                if self.transition_factor > 0.5:
                    # More than halfway through transition, use target method
                    self.position_sizer.configure(to_sizing)
                else:
                    # Less than halfway, keep using source method
                    self.position_sizer.configure(from_sizing)
        
        # Blend drawdown control parameters
        if 'drawdown_control' in from_params and 'drawdown_control' in to_params:
            from_dd = from_params['drawdown_control']
            to_dd = to_params['drawdown_control']
            
            blended_dd = dict(to_dd)  # Start with target values
            
            # Blend numeric parameters
            for param, value in to_dd.items():
                if param != 'enabled' and param in from_dd and isinstance(value, (int, float)):
                    from_value = from_dd[param]
                    blended_value = from_value + (value - from_value) * self.transition_factor
                    blended_dd[param] = blended_value
            
            # Apply blended parameters
            self.config['drawdown_control'] = blended_dd
    
    def detect_regime(self, bar_event):
        """
        Detect market regime from a bar event.
        
        Args:
            bar_event: Bar event to analyze
            
        Returns:
            str: Detected regime
        """
        if not self.regime_detector:
            return self.current_regime  # No detector, use current regime
        
        # Use regime detector component to identify regime
        symbol = bar_event.get_symbol()
        timestamp = bar_event.get_timestamp()
        
        # Get indicator values needed for regime detection
        # (This implementation depends on the specific detector)
        try:
            if hasattr(self.regime_detector, 'detect_regime'):
                regime = self.regime_detector.detect_regime(bar_event)
                return regime
                
            return self.current_regime  # Default
        except Exception as e:
            logger.error(f"Error detecting regime: {e}")
            return self.current_regime
    
    def set_regime_parameters(self, regime, parameters):
        """
        Set parameters for a specific regime.
        
        Args:
            regime: Regime name
            parameters: Parameter dictionary
        """
        self.regime_parameters[regime] = parameters
        
        # If this is the current regime, apply parameters immediately
        if regime == self.current_regime:
            self._apply_regime_parameters(regime)
    
    def get_regime_parameters(self, regime=None):
        """
        Get parameters for a specific regime.
        
        Args:
            regime: Regime name (None for all regimes)
            
        Returns:
            Dict: Regime parameters
        """
        if regime:
            return self.regime_parameters.get(regime, {})
        else:
            return dict(self.regime_parameters)
    
    def get_current_regime(self):
        """
        Get current market regime.
        
        Returns:
            str: Current regime
        """
        return self.current_regime
    
    def override_regime(self, regime):
        """
        Manually override the current regime.
        
        Args:
            regime: New regime to set
        """
        if regime in self.regime_parameters:
            self._change_regime(regime)
            return True
        else:
            logger.warning(f"Unknown regime: {regime}, override failed")
            return False
    
    def on_signal(self, signal_event):
        """
        Handle signal events and create orders using regime-specific parameters.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            Order event or None
        """
        # Using standard signal processing with regime-specific parameters
        return super().on_signal(signal_event)
    
    def get_parameters(self):
        """
        Get current parameter values.
        
        Returns:
            Dict: Parameter values
        """
        params = super().get_parameters()
        params.update({
            'current_regime': self.current_regime,
            'regime_parameters': self.get_regime_parameters(),
            'transition_factor': self.transition_factor
        })
        return params
    
    def set_parameters(self, params):
        """
        Set parameters.
        
        Args:
            params: Parameter dictionary
        """
        super().set_parameters(params)
        
        if 'regime_parameters' in params:
            for regime, regime_params in params['regime_parameters'].items():
                self.set_regime_parameters(regime, regime_params)
        
        if 'current_regime' in params:
            new_regime = params['current_regime']
            if new_regime != self.current_regime:
                self.override_regime(new_regime)
    
    def reset(self):
        """Reset risk manager state."""
        super().reset()
        
        # Reset regime state
        self.current_regime = "normal"
        self.transition_factor = 1.0
        
        # Apply default parameters
        self._apply_regime_parameters(self.current_regime)
        
        # Update stats
        self.stats.update({
            'regime_changes': 0,
            'current_regime': self.current_regime
        })
        
        logger.info(f"Reset adaptive risk manager: {self.name}")
    
    def to_dict(self):
        """
        Convert to dictionary.
        
        Returns:
            Dict: Dictionary representation
        """
        result = super().to_dict()
        result.update({
            'current_regime': self.current_regime,
            'transition_factor': self.transition_factor,
            'regimes': list(self.regime_parameters.keys())
        })
        return result


# Factory for creating adaptive risk managers
class AdaptiveRiskManagerFactory:
    """Factory for creating adaptive risk managers."""
    
    @staticmethod
    def create(event_bus, portfolio_manager, regime_detector=None, config=None):
        """
        Create an adaptive risk manager.
        
        Args:
            event_bus: Event bus
            portfolio_manager: Portfolio manager
            regime_detector: Optional regime detector
            config: Optional configuration
            
        Returns:
            AdaptiveRiskManager: Risk manager instance
        """
        # Create position sizer
        position_sizer = None
        if config and 'position_sizing' in config:
            position_sizer = PositionSizerFactory.create(config=config['position_sizing'])
        else:
            position_sizer = PositionSizerFactory.create('fixed')
        
        # Create limit manager
        limit_manager = None
        if config and 'limits' in config:
            limit_manager = LimitManagerFactory.create_from_config(config['limits'])
        else:
            limit_manager = LimitManagerFactory.create_default_manager()
        
        # Create risk manager
        risk_manager = AdaptiveRiskManager(
            event_bus=event_bus,
            portfolio_manager=portfolio_manager,
            position_sizer=position_sizer,
            limit_manager=limit_manager,
            regime_detector=regime_detector
        )
        
        # Configure if config provided
        if config:
            risk_manager.configure(config)
            
        return risk_manager
