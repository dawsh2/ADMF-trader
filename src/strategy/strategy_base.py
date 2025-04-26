# src/strategies/strategy_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .components.component_base import Component
from src.core.events.event_utils import create_signal_event

class Strategy(Component):
    """Base class for all trading strategies."""
    
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
        Handle bar events.
        
        Args:
            bar_event: Bar event to process
            
        Returns:
            Optional signal event
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
