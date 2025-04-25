# src/core/utils/registry.py

from typing import Dict, Type, Any, List

class Registry:
    """Registry for components."""
    
    def __init__(self):
        """Initialize an empty registry."""
        self._components = {}
    
    def register(self, name: str, component: Any) -> None:
        """
        Register a component.
        
        Args:
            name: Component name
            component: Component class or instance
        """
        self._components[name] = component
    
    def get(self, name: str) -> Any:
        """
        Get a registered component.
        
        Args:
            name: Component name
            
        Returns:
            Component or None if not found
        """
        return self._components.get(name)
    
    def list(self) -> List[str]:
        """
        List all registered component names.
        
        Returns:
            List of component names
        """
        return list(self._components.keys())
    
    def items(self) -> Dict[str, Any]:
        """
        Get all components as dictionary.
        
        Returns:
            Dictionary of name -> component
        """
        return dict(self._components)
    
    def __contains__(self, name: str) -> bool:
        """
        Check if a component is registered.
        
        Args:
            name: Component name
            
        Returns:
            True if component is registered, False otherwise
        """
        return name in self._components
