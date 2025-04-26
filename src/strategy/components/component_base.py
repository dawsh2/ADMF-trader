"""
Base component class for all strategy components.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

class Component(ABC):
    """Base class for all strategy components with optimization support."""
    
    # Default class component name - override in subclasses
    name = None
    
    def __init__(self, name=None, parameters=None):
        """
        Initialize component.
        
        Args:
            name: Component name (overrides class name)
            parameters: Initial parameters
        """
        # Use name from args, class attribute, or class name
        class_name = self.__class__.name if hasattr(self.__class__, 'name') and self.__class__.name else self.__class__.__name__
        self._name = name or class_name
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
    
    @classmethod
    def get_class_name(cls):
        """
        Get component name from class.
        
        Returns:
            str: Component name defined at class level or converted class name
        """
        if hasattr(cls, 'name') and cls.name:
            return cls.name
            
        # Convert CamelCase to snake_case
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
