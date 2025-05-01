#!/usr/bin/env python3
"""
Check the import statements in system_bootstrap.py to see which strategy implementation is being loaded.
"""
import os
import sys
import importlib
import inspect
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_imports():
    """Check which implementation of MACrossoverStrategy is being loaded."""
    
    # Import discovery module
    from src.core.utils.discovery import discover_components
    
    # Find all available strategy implementations
    from src.strategy.strategy_base import Strategy
    
    # Create a simple registry
    class SimpleRegistry:
        def __init__(self):
            self.components = {}
        def register(self, name, component):
            self.components[name] = component
            print(f"Registering {name}: {component.__module__}.{component.__name__}")
    
    # Create registry and discover components
    print("DISCOVERING STRATEGY IMPLEMENTATIONS:")
    print("-" * 60)
    registry = SimpleRegistry()
    discover_components("src.strategy.implementations", Strategy, registry)
    print("-" * 60)
    
    # Print info about all registered components
    print("\nREGISTERED COMPONENTS:")
    print("-" * 60)
    for name, component in registry.components.items():
        # Print detailed information about component
        print(f"Name: {name}")
        print(f"Module: {component.__module__}")
        print(f"Class: {component.__name__}")
        
        # Get the file where the class is defined
        file = inspect.getfile(component)
        print(f"File: {file}")
        
        # Try to extract the 'name' class variable
        if hasattr(component, 'name'):
            print(f"name class variable: {component.name}")
        
        print("-" * 60)
    
    print("\nSYS.MODULES ENTRIES:")
    print("-" * 60)
    for module_name in sorted(sys.modules.keys()):
        if "ma_crossover" in module_name:
            module = sys.modules[module_name]
            print(f"Module: {module_name}")
            print(f"Path: {getattr(module, '__file__', 'N/A')}")
            print()
    
    # Check if ma_crossover_original is loaded
    print("\nCHECKING MODULE LOADING:")
    print("-" * 60)
    
    try:
        from src.strategy.implementations.ma_crossover_original import MACrossoverStrategy as OriginalStrategy
        print("✓ ma_crossover_original can be imported")
    except ImportError:
        print("✗ ma_crossover_original cannot be imported")
    
    try:
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy as CurrentStrategy
        print("✓ ma_crossover can be imported")
    except ImportError:
        print("✗ ma_crossover cannot be imported")
    
    try:
        from src.strategy.implementations.ma_crossover_fixed import MACrossoverStrategy as FixedStrategy
        print("✓ ma_crossover_fixed can be imported")
    except ImportError:
        print("✗ ma_crossover_fixed cannot be imported")
    
    # Compare implementation details
    print("\nCOMPARING IMPLEMENTATIONS:")
    print("-" * 60)
    
    try:
        # Import all implementations
        try:
            from src.strategy.implementations.ma_crossover_original import MACrossoverStrategy as OriginalStrategy
            print("Original implementation imported")
            
            # Check rule_id generation
            source = inspect.getsource(OriginalStrategy.on_bar)
            if 'rule_id=f"{self.name}_{self.signal_count}"' in source:
                print("✗ Original implementation uses incorrect rule_id format")
            else:
                print("✓ Original implementation uses correct rule_id format")
        except ImportError:
            print("Original implementation not available")
        
        try:
            from src.strategy.implementations.ma_crossover import MACrossoverStrategy as CurrentStrategy
            print("\nCurrent implementation imported")
            
            # Check rule_id generation
            source = inspect.getsource(CurrentStrategy.on_bar)
            if 'rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"' in source:
                print("✓ Current implementation uses correct rule_id format")
            else:
                print("✗ Current implementation uses incorrect rule_id format")
                
            # Check signal direction tracking
            if 'self.signal_directions' in source:
                print("✓ Current implementation tracks signal directions")
            else:
                print("✗ Current implementation does not track signal directions")
        except ImportError:
            print("Current implementation not available")
        
        try:
            from src.strategy.implementations.ma_crossover_fixed import MACrossoverStrategy as FixedStrategy
            print("\nFixed implementation imported")
            
            # Check rule_id generation
            source = inspect.getsource(FixedStrategy.on_bar)
            if 'rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"' in source:
                print("✓ Fixed implementation uses correct rule_id format")
            else:
                print("✗ Fixed implementation uses incorrect rule_id format")
        except ImportError:
            print("Fixed implementation not available")
            
    except Exception as e:
        logger.error(f"Error comparing implementations: {e}", exc_info=True)

def main():
    """Main function."""
    print("=" * 60)
    print("CHECKING STRATEGY IMPLEMENTATIONS")
    print("=" * 60)
    check_imports()
    return 0

if __name__ == "__main__":
    sys.exit(main())
