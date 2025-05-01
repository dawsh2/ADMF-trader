"""
Debug tools to help diagnose test failures.
"""

import importlib
import inspect
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def inspect_class(module_name, class_name):
    """
    Print detailed information about a class to help debug tests.
    
    Args:
        module_name: Name of the module containing the class
        class_name: Name of the class to inspect
    """
    print(f"\n--- INSPECTING CLASS: {class_name} from {module_name} ---")
    
    try:
        # Import the module
        module = importlib.import_module(module_name)
        
        # Get the class
        cls = getattr(module, class_name)
        
        # Print basic info
        print(f"Class: {cls.__name__}")
        print(f"Module: {cls.__module__}")
        print(f"MRO: {[c.__name__ for c in cls.__mro__]}")
        
        # Get methods
        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        print(f"\nMethods ({len(methods)}):")
        for name, method in methods:
            print(f"  - {name}{inspect.signature(method)}")
        
        # Get attributes
        attrs = inspect.getmembers(cls, lambda a: not(inspect.isroutine(a)))
        attrs = [a for a in attrs if not(a[0].startswith('__') and a[0].endswith('__'))]
        print(f"\nAttributes ({len(attrs)}):")
        for name, attr in attrs:
            print(f"  - {name} = {attr}")
        
        # Get instance methods
        instance = None
        try:
            instance = cls()
            instance_methods = inspect.getmembers(instance, predicate=inspect.ismethod)
            print(f"\nInstance Methods ({len(instance_methods)}):")
            for name, method in instance_methods:
                print(f"  - {name}{inspect.signature(method)}")
        except Exception as e:
            print(f"\nCould not create instance: {e}")
        
        print("\n--- END INSPECTION ---")
        
    except Exception as e:
        print(f"Error inspecting class: {e}")


def inspect_module(module_name):
    """
    Print detailed information about a module to help debug tests.
    
    Args:
        module_name: Name of the module to inspect
    """
    print(f"\n--- INSPECTING MODULE: {module_name} ---")
    
    try:
        # Import the module
        module = importlib.import_module(module_name)
        
        # Print basic info
        print(f"Module: {module.__name__}")
        print(f"File: {module.__file__}")
        
        # Get classes
        classes = inspect.getmembers(module, inspect.isclass)
        print(f"\nClasses ({len(classes)}):")
        for name, cls in classes:
            if cls.__module__ == module.__name__:
                print(f"  - {name}")
        
        # Get functions
        functions = inspect.getmembers(module, inspect.isfunction)
        print(f"\nFunctions ({len(functions)}):")
        for name, func in functions:
            if func.__module__ == module.__name__:
                print(f"  - {name}{inspect.signature(func)}")
        
        print("\n--- END INSPECTION ---")
        
    except Exception as e:
        print(f"Error inspecting module: {e}")


def run_event_bus_diagnostics():
    """
    Run diagnostics for the event bus to help debug test failures.
    """
    print("\n--- EVENT BUS DIAGNOSTICS ---")
    
    try:
        # Import the event bus module
        from src.core.events.event_bus import EventBus
        from src.core.events.event_types import Event, EventType
        
        # Create test objects
        bus = EventBus()
        event = Event(EventType.BAR, {'test': 'data'})
        
        # Test basic operations
        print("\nTesting basic operations:")
        print(f"EventBus created: {bus}")
        print(f"Event created: {event}")
        
        # Record handler calls
        calls = []
        
        # Define test handler
        def test_handler(evt):
            calls.append(evt)
            return "test_result"
        
        # Register handler
        print("\nRegistering handler...")
        bus.register(EventType.BAR, test_handler)
        
        # Check handlers
        print(f"Handlers: {bus.handlers}")
        
        # Emit event
        print("\nEmitting event...")
        results = bus.emit(event)
        
        # Check results
        print(f"Handler called: {len(calls) > 0}")
        print(f"Results: {results}")
        
        print("\n--- END EVENT BUS DIAGNOSTICS ---")
    
    except Exception as e:
        print(f"Error in event bus diagnostics: {e}")


def run_strategy_diagnostics():
    """
    Run diagnostics for strategies to help debug test failures.
    """
    print("\n--- STRATEGY DIAGNOSTICS ---")
    
    try:
        # Import strategy classes
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy
        from src.core.events.event_bus import EventBus
        from src.core.events.event_types import Event, EventType
        
        # Create test objects
        event_bus = EventBus()
        strategy = MACrossoverStrategy(event_bus, None, parameters={
            'fast_window': 5,
            'slow_window': 15,
            'price_key': 'close',
            'symbols': ['TEST']
        })
        
        # Print strategy attributes
        print("\nStrategy attributes:")
        print(f"Name: {strategy.name}")
        print(f"Fast window: {strategy.fast_window}")
        print(f"Slow window: {strategy.slow_window}")
        print(f"Price key: {strategy.price_key}")
        print(f"Symbols: {strategy.symbols}")
        
        # Check data structures
        print("\nData structures:")
        print(f"Data: {strategy.data}")
        print(f"Fast MA: {strategy.fast_ma}")
        print(f"Slow MA: {strategy.slow_ma}")
        
        # Create test event
        event = Event(EventType.BAR, {
            'symbol': 'TEST',
            'timestamp': '2024-01-01 09:30:00',
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000
        })
        
        # Test on_bar method
        print("\nTesting on_bar method...")
        signal = strategy.on_bar(event)
        print(f"Signal: {signal}")
        
        # Check updated data structures
        print("\nUpdated data structures:")
        print(f"Data: {strategy.data}")
        print(f"Fast MA: {strategy.fast_ma}")
        print(f"Slow MA: {strategy.slow_ma}")
        
        print("\n--- END STRATEGY DIAGNOSTICS ---")
    
    except Exception as e:
        print(f"Error in strategy diagnostics: {e}")


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug tools for tests")
    parser.add_argument('--class', dest='class_name', help='Class name to inspect')
    parser.add_argument('--module', dest='module_name', help='Module name to inspect')
    parser.add_argument('--event-bus', action='store_true', help='Run event bus diagnostics')
    parser.add_argument('--strategy', action='store_true', help='Run strategy diagnostics')
    
    args = parser.parse_args()
    
    if args.class_name and args.module_name:
        inspect_class(args.module_name, args.class_name)
    elif args.module_name:
        inspect_module(args.module_name)
    elif args.event_bus:
        run_event_bus_diagnostics()
    elif args.strategy:
        run_strategy_diagnostics()
    else:
        print("No action specified. Use --help for options.")
