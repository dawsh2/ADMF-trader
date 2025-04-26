"""
Component discovery utility for finding and registering components.
"""
import importlib
import inspect
import logging
import os
import pkgutil
from typing import Dict, Type, List, Optional, Any, Set

logger = logging.getLogger(__name__)

def discover_components(
    package_name: str,
    base_class: Type,
    registry=None,
    enabled_only: bool = True,
    config=None
):
    """
    Discover components in a package that inherit from a base class.
    
    Args:
        package_name: Package name to scan (e.g., 'strategies')
        base_class: Base class that components must inherit from
        registry: Optional registry to register components with
        enabled_only: Only return/register components that are enabled in config
        config: Configuration object to check for enabled components
        
    Returns:
        Dictionary of discovered component classes
    """
    discovered = {}
    
    try:
        # Import the package
        package = importlib.import_module(package_name)
    except ImportError as e:
        logger.error(f"Error importing package {package_name}: {e}")
        return discovered
    
    # Get the package path
    package_path = getattr(package, '__path__', [])
    prefix = package.__name__ + '.'
    
    # Scan for modules in the package
    for _, module_name, is_pkg in pkgutil.iter_modules(package_path, prefix):
        try:
            # Import the module
            module = importlib.import_module(module_name)
            
            # Find classes that inherit from base_class
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, base_class) and obj != base_class:
                    # Extract component name
                    if hasattr(obj, 'name') and isinstance(obj.name, str):
                        # Use class variable name attribute
                        component_name = obj.name
                    else:
                        # Convert CamelCase to snake_case
                        import re
                        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
                        component_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
                    
                    # Check if component is enabled in config
                    if enabled_only and config:
                        section_name = package_name.split('.')[-1]  # e.g., 'strategies'
                        section_path = f"{section_name}.{component_name}"
                        
                        # Navigate through config sections
                        current_section = config
                        for part in section_path.split('.'):
                            if hasattr(current_section, 'get_section'):
                                current_section = current_section.get_section(part)
                        
                        # Check enabled flag
                        enabled = getattr(current_section, 'get', lambda x, y: y)('enabled', True)
                        if not enabled:
                            logger.debug(f"Component {component_name} is disabled in config, skipping")
                            continue
                    
                    # Add to discovered components
                    discovered[component_name] = obj
                    
                    # Register if registry provided
                    if registry is not None and hasattr(registry, 'register'):
                        registry.register(component_name, obj)
                        logger.info(f"Registered component {component_name} in registry")
        except Exception as e:
            logger.warning(f"Error importing module {module_name}: {e}", exc_info=True)
    
    return discovered
