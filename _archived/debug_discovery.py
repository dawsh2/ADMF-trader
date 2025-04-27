#!/usr/bin/env python
"""
Debug script for component discovery.

This script helps diagnose issues with the component discovery system
by tracing the discovery process and showing detailed information about
what's being found and registered.
"""
import logging
import sys
import inspect
import pkgutil
import importlib
from src.core.utils.registry import Registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Discovery-Debug")

def debug_discovery():
    """Debug the component discovery system."""
    logger.info("=== Starting Discovery Debugging ===")
    
    # First, check if we can import the strategy module
    logger.info("Attempting to import the strategy implementations module...")
    try:
        from src.strategy.strategy_base import Strategy
        logger.info("Successfully imported Strategy base class")
        
        module = importlib.import_module("src.strategy.implementations")
        logger.info(f"Module imported successfully! Path: {module.__path__}")
        
        # Check if we can get the MACrossoverStrategy class
        try:
            from src.strategy.implementations.ma_crossover import MACrossoverStrategy
            logger.info("Checking base class inheritance...")
            logger.info(f"MACrossoverStrategy is a subclass of Strategy: {issubclass(MACrossoverStrategy, Strategy)}")
            
            # Check class-level name
            if hasattr(MACrossoverStrategy, 'name') and isinstance(MACrossoverStrategy.name, str):
                logger.info(f"MACrossoverStrategy has class-level name: {MACrossoverStrategy.name}")
            else:
                logger.warning("MACrossoverStrategy is missing class-level name attribute")
        except ImportError:
            logger.error("Could not import MACrossoverStrategy class")
        
        # Now debug the discovery process
        logger.info("Debugging discovery process...")
        test_registry = Registry()
        
        # Import the discovery function
        from src.core.utils.discovery import discover_components
        
        # Add detailed logging to the discovery process
        logger.info(f"Looking for components in package: src.strategy.implementations")
        package = importlib.import_module("src.strategy.implementations")
        logger.info(f"Package imported: {package}")
        logger.info(f"Package path: {package.__path__}")
        prefix = package.__name__ + '.'
        logger.info(f"Prefix: {prefix}")
        
        # Manually iterate through modules
        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, prefix):
            logger.info(f"Found module: {module_name}, is_package: {is_pkg}")
            try:
                # Import the module
                module = importlib.import_module(module_name)
                logger.info(f"Successfully imported module: {module_name}")
                
                # Find classes
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    logger.info(f"Found class: {name}")
                    if issubclass(obj, Strategy) and obj != Strategy:
                        logger.info(f"Class {name} is a subclass of Strategy!")
                        
                        # Determine name
                        if hasattr(obj, 'name') and isinstance(obj.name, str):
                            component_name = obj.name
                            logger.info(f"Using class-level name attribute: {component_name}")
                        else:
                            import re
                            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
                            component_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
                            logger.info(f"Converted name from class name: {component_name}")
                        
                        # Register
                        test_registry.register(component_name, obj)
                        logger.info(f"Registered {component_name} in test registry")
                    else:
                        logger.info(f"Class {name} is NOT a subclass of Strategy or is Strategy itself")
            except Exception as e:
                logger.error(f"Error processing module {module_name}: {e}", exc_info=True)
        
        # Check what was registered
        logger.info("Components registered in the test registry:")
        try:
            for name, component in test_registry.items():
                logger.info(f"- {name}: {component}")
        except Exception as e:
            logger.error(f"Error iterating registry items: {e}", exc_info=True)
            # Fallback approach
            for name in test_registry.list():
                component = test_registry.get(name)
                logger.info(f"- {name}: {component}")
        
        # Verify MACrossoverStrategy was registered
        if 'ma_crossover' not in test_registry:
            logger.warning("FAILURE: MACrossoverStrategy was NOT registered")
        else:
            logger.info("SUCCESS: MACrossoverStrategy was properly registered")
        
        # Test running the discovery function directly
        logger.info("Testing discovery function directly...")
        discovered = discover_components(
            package_name="src.strategy.implementations",
            base_class=Strategy,
            registry=None
        )
        
        logger.info(f"Discovery results: {list(discovered.keys()) if discovered else 'No components found'}")
        
        # Check Python path
        logger.info("Python module search paths (sys.path):")
        for path in sys.path:
            logger.info(f"- {path}")
        
        # Check module structure
        logger.info("Checking module structure...")
        try:
            strategy_module = importlib.import_module("src.strategy")
            logger.info(f"Strategy module __init__.py exists and imports: {dir(strategy_module)}")
        except ImportError:
            logger.warning("Strategy module __init__.py missing or has errors")
        
        try:
            impl_module = importlib.import_module("src.strategy.implementations")
            logger.info(f"Implementations module __init__.py exists and imports: {dir(impl_module)}")
        except ImportError:
            logger.warning("Implementations module __init__.py missing or has errors")
        
        # Inspect Strategy class
        logger.info("Inspecting Strategy class...")
        logger.info(f"Strategy class: {Strategy}")
        logger.info(f"Strategy module: {Strategy.__module__}")
        logger.info(f"Strategy bases: {Strategy.__bases__}")
        logger.info(f"Strategy MRO: {Strategy.__mro__}")
    
    except Exception as e:
        logger.error(f"Error during discovery debugging: {e}", exc_info=True)
    
    logger.info("=== Discovery Debugging Complete ===")

if __name__ == "__main__":
    debug_discovery()
