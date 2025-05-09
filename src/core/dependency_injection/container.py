"""
Dependency Injection Container for ADMF-Trader.

This module provides a simple dependency injection container
that supports singleton and factory registrations.
"""

import logging
from typing import Dict, Any, Callable, Optional, Type, Union, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

class Container:
    """
    Dependency injection container for managing components.
    
    Features:
    - Component registration and resolution
    - Singleton and factory registration
    - Component lifecycle management
    - Circular dependency detection
    """
    
    def __init__(self):
        """Initialize the container."""
        self.components: Dict[str, Dict[str, Any]] = {}
        self.resolving: set = set()  # For detecting circular dependencies
        
    def register(self, name: str, component: Union[Any, Callable[..., Any]], 
                singleton: bool = True) -> 'Container':
        """
        Register a component with the container.
        
        Args:
            name: Name for the component
            component: Component instance or factory function
            singleton: Whether to treat as singleton (True) or factory (False)
            
        Returns:
            Container: Self for method chaining
        """
        self.components[name] = {
            'instance': component if singleton and not callable(component) else None,
            'factory': component if callable(component) or not singleton else lambda: component,
            'singleton': singleton
        }
        
        logger.debug(f"Registered component '{name}' as {'singleton' if singleton else 'factory'}")
        return self
        
    def register_instance(self, name: str, instance: Any) -> 'Container':
        """
        Register an existing instance as a singleton.
        
        Args:
            name: Name for the component
            instance: Component instance
            
        Returns:
            Container: Self for method chaining
        """
        return self.register(name, instance, singleton=True)
        
    def register_factory(self, name: str, factory: Callable[..., Any]) -> 'Container':
        """
        Register a factory function.
        
        Args:
            name: Name for the component
            factory: Factory function that creates component instances
            
        Returns:
            Container: Self for method chaining
        """
        return self.register(name, factory, singleton=False)
        
    def register_class(self, name: str, cls: Type[T], singleton: bool = True,
                       **kwargs) -> 'Container':
        """
        Register a class.
        
        Args:
            name: Name for the component
            cls: Class to register
            singleton: Whether instances should be singletons
            **kwargs: Arguments to pass to the constructor
            
        Returns:
            Container: Self for method chaining
        """
        factory = lambda: cls(**kwargs)
        return self.register(name, factory, singleton)
        
    def get(self, name: str) -> Any:
        """
        Resolve a component by name.
        
        Args:
            name: Name of the component to resolve
            
        Returns:
            Any: Resolved component
            
        Raises:
            ValueError: If component is not registered
            RuntimeError: If circular dependency detected
        """
        if name not in self.components:
            raise ValueError(f"Component '{name}' not registered")
            
        # Check for circular dependencies
        if name in self.resolving:
            raise RuntimeError(f"Circular dependency detected when resolving '{name}'")
            
        component = self.components[name]
        
        # Return instance if it's a singleton and already instantiated
        if component['singleton'] and component['instance'] is not None:
            return component['instance']
            
        # Add to resolving set to detect circular dependencies
        self.resolving.add(name)
        
        try:
            # Create instance from factory
            instance = component['factory']()
            
            # Store instance if it's a singleton
            if component['singleton']:
                component['instance'] = instance
                
            return instance
        finally:
            # Remove from resolving set
            self.resolving.discard(name)
            
    def has(self, name: str) -> bool:
        """
        Check if a component is registered.
        
        Args:
            name: Name of the component to check
            
        Returns:
            bool: True if registered, False otherwise
        """
        return name in self.components
        
    def remove(self, name: str) -> bool:
        """
        Remove a registered component.
        
        Args:
            name: Name of the component to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        if name in self.components:
            del self.components[name]
            logger.debug(f"Removed component '{name}'")
            return True
        return False
        
    def reset(self) -> None:
        """Reset the container, clearing all registrations."""
        self.components.clear()
        self.resolving.clear()
        logger.info("Container reset")
        
    def get_all_registrations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all component registrations.
        
        Returns:
            Dict: All component registrations
        """
        return {name: {'singleton': info['singleton']} for name, info in self.components.items()}