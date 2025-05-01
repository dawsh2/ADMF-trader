"""
Script to inspect the Event class and its methods to understand what might be causing issues.
"""

import sys
import os
import inspect
import traceback

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def inspect_event_class():
    """Inspect the Event class to understand its structure."""
    try:
        # Import event types
        print("Importing event_types module...")
        from src.core.events.event_types import EventType, Event
        
        # Print basic info about EventType
        print("\n=== EventType Info ===")
        print(f"Type: {type(EventType)}")
        print(f"Members: {list(EventType.__members__.keys())}")
        
        # Print basic info about Event class
        print("\n=== Event Class Info ===")
        print(f"Module: {Event.__module__}")
        print(f"MRO: {[c.__name__ for c in Event.__mro__]}")
        
        # Get __init__ method
        print("\n=== Event.__init__ ===")
        init_method = Event.__init__
        print(f"Signature: {inspect.signature(init_method)}")
        init_source = inspect.getsource(init_method)
        print(f"Source code:\n{init_source}")
        
        # Get all methods
        print("\n=== Event Methods ===")
        methods = inspect.getmembers(Event, predicate=inspect.isfunction)
        for name, method in methods:
            if name.startswith('__') and name != '__init__':
                continue  # Skip special methods except __init__
            print(f"Method: {name}{inspect.signature(method)}")
            try:
                source = inspect.getsource(method)
                print(f"Source (first 200 chars): {source[:200]}...")
            except Exception as e:
                print(f"Could not get source: {e}")
        
        # Get all attributes
        print("\n=== Event Attributes ===")
        attributes = inspect.getmembers(Event, lambda a: not inspect.isroutine(a))
        attributes = [a for a in attributes if not (a[0].startswith('__') and a[0].endswith('__'))]
        for name, attr in attributes:
            print(f"Attribute: {name} = {attr}")
        
        # Try to create a minimal instance
        print("\n=== Creating Event Instance ===")
        try:
            data = {'test': 'data'}
            event = Event(EventType.BAR, data)
            print(f"Event created with type: {event.type}")
            print(f"Event data: {event.data}")
            
            # Check for id attribute
            if hasattr(event, 'id'):
                print(f"Event ID: {event.id}")
            
            # Check for any unexpected attributes
            print("All instance attributes:")
            for attr_name, attr_value in event.__dict__.items():
                print(f"  - {attr_name}: {attr_value}")
                
        except Exception as e:
            print(f"Error creating event: {e}")
            traceback.print_exc()
    
    except Exception as e:
        print(f"Error importing or inspecting Event class: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting Event class inspection...")
    inspect_event_class()
    print("\nInspection complete.")
