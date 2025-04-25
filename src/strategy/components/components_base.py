# src/strategies/components/component_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

class Component(ABC):
    """Base class for all strategy components with optimization support."""
    
    def __init__(self, name=None, parameters=None):
        """
        Initialize component.
        
        Args:
            name: Component name
            parameters: Initial parameters
        """
        self._name = name or self.__class__.__name__
        self.parameters = parameters or {}
        self.configured = False
    
    def configure(self, config):
        """
        Configure the component with parameters.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        # Extract parameters from config
        if hasattr(config, 'as_dict'):
            self.parameters = config.as_dict()
        else:
            self.parameters = dict(config)
            
        self.configured = True
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get current parameter values for optimization.
        
        Returns:
            Dict of parameter name -> value
        """
        return dict(self.parameters)
    
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """
        Set parameters for optimization.
        
        Args:
            params: Dict of parameter name -> value
        """
        self.parameters.update(params)
    
    def get_parameter_space(self) -> Dict[str, List[Any]]:
        """
        Get parameter space for optimization.
        
        Returns:
            Dict of parameter name -> list of possible values
        """
        # Override in concrete components to define parameter space
        return {}
    
    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate parameters for optimization.
        
        Args:
            params: Dict of parameter name -> value
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Override in concrete components for custom validation
        return True, ""
    
    @property
    def name(self):
        """Get component name."""
        return self._name
    
    @name.setter
    def name(self, value):
        """Set component name."""
        self._name = value
