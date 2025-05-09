# src/strategies/strategy_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .components.component_base import Component
from src.core.events.event_utils import create_signal_event
import logging

logger = logging.getLogger(__name__)

class Strategy(Component):
    """Base class for all trading strategies.
    
    Strategies are responsible for analyzing market data and generating directional signals.
    Strategies should NOT track position state or handle trading decisions.
    """
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        """
        Initialize strategy.
        
        Args:
            event_bus: Event bus for communication
            data_handler: Data handler for market data
            name: Strategy name
            parameters: Initial parameters
        """
        super().__init__(name, parameters)
        self.event_bus = event_bus
        self.data_handler = data_handler
        self.symbols = []
        self.components = {}  # Dict of component name -> component
        self.data = {}  # Initialize empty data dictionary
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        super().configure(config)
        # Extract symbols if present
        self.symbols = self.parameters.get('symbols', [])
    
    def add_component(self, component: Component, category: str = None):
        """
        Add a component to the strategy.
        
        Args:
            component: Component to add
            category: Optional category for organization
        """
        key = f"{category}.{component.name}" if category else component.name
        self.components[key] = component
    
    def get_component(self, name: str) -> Optional[Component]:
        """
        Get a component by name.
        
        Args:
            name: Component name or category.name
            
        Returns:
            Component or None if not found
        """
        return self.components.get(name)
    
    @abstractmethod
    def on_bar(self, bar_event):
        """
        Process a bar event and emit a directional signal based on market analysis.
        
        Strategies should focus purely on market analysis and signal generation.
        They should NOT track current positions or make trading decisions.
        
        Args:
            bar_event: Market data bar event
            
        Returns:
            Optional signal event with directional value (1, -1, 0)
            - 1 for bullish (buy)
            - -1 for bearish (sell)
            - 0 for neutral (no action)
        """
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameter values including all components."""
        params = super().get_parameters()
        
        # Include parameters of all components
        component_params = {}
        for name, component in self.components.items():
            component_params[name] = component.get_parameters()
            
        params['components'] = component_params
        return params
    
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Set parameters including all components."""
        # Update strategy parameters
        super().set_parameters({k: v for k, v in params.items() if k != 'components'})
        
        # Update component parameters if present
        if 'components' in params:
            component_params = params['components']
            for name, comp_params in component_params.items():
                if name in self.components:
                    self.components[name].set_parameters(comp_params)
    
    def get_parameter_space(self) -> Dict[str, Any]:
        """Get parameter space including all components."""
        space = super().get_parameter_space()
        
        # Include parameter spaces of all components
        component_spaces = {}
        for name, component in self.components.items():
            component_space = component.get_parameter_space()
            if component_space:
                component_spaces[name] = component_space
                
        if component_spaces:
            space['components'] = component_spaces
            
        return space

    def start(self):
        """Start the strategy."""
        logger.info(f"Strategy {self.name} started")
    
    def stop(self):
        """Stop the strategy."""
        logger.info(f"Strategy {self.name} stopped")

    def reset(self):
        """Reset strategy state."""
        # Default implementation - clear internal state
        self.data = {symbol: [] for symbol in self.symbols}
        # Child classes should override this
        logger.info(f"Strategy {self.name} reset")
