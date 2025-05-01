#!/usr/bin/env python
"""
Debug script to check how the event adapters are being applied.
This will help understand what might be causing the test to hang.
"""

import sys
import os
import time

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def check_event_class():
    """Check the Event class before any adapters are applied."""
    print("Checking Event class before adapters...")
    
    try:
        # Import the Event class
        from src.core.events.event_types import Event, EventType
        
        # Check for type property
        has_type = hasattr(Event, 'type')
        print(f"Event class has 'type' property: {has_type}")
        
        # Check original attributes and methods
        print(f"Event class methods: {[m for m in dir(Event) if callable(getattr(Event, m)) and not m.startswith('__')]}")
        print(f"Event class attributes: {[a for a in dir(Event) if not callable(getattr(Event, a)) and not a.startswith('__')]}")
        
        # Create an event and check its attributes
        print("\nCreating an event instance...")
        event = Event(EventType.BAR, {'test': 'data'})
        print(f"Event instance has the following attributes:")
        print(f"  - event_type: {getattr(event, 'event_type', 'Not found')}")
        print(f"  - data: {getattr(event, 'data', 'Not found')}")
        print(f"  - timestamp: {getattr(event, 'timestamp', 'Not found')}")
        print(f"  - id: {getattr(event, 'id', 'Not found')}")
        
        # Try to access type property (should fail if not added)
        try:
            print(f"  - type: {event.type}")
        except AttributeError:
            print("  - type: AttributeError - property doesn't exist")
            
        return True
    except Exception as e:
        print(f"Error checking Event class: {e}")
        import traceback
        traceback.print_exc()
        return False

def add_type_property():
    """Add the type property to the Event class."""
    print("\nAdding 'type' property to Event class...")
    
    try:
        from src.core.events.event_types import Event
        
        # Add type property if it doesn't exist
        if not hasattr(Event, 'type'):
            @property
            def type_property(self):
                """Bridge property to access event_type as type."""
                print(f"Accessing 'type' property, returning: {self.event_type}")
                return self.event_type
            
            # Add the property
            Event.type = type_property
            print("Successfully added 'type' property to Event class")
        else:
            print("Event class already has 'type' property")
            
        return True
    except Exception as e:
        print(f"Error adding type property: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_property():
    """Test accessing the property after it's been added."""
    print("\nTesting Event class with type property...")
    
    try:
        from src.core.events.event_types import Event, EventType
        
        # Create an event and check its attributes
        print("Creating a new event instance...")
        event = Event(EventType.BAR, {'test': 'data'})
        
        # Test event_type attribute
        print(f"event.event_type = {event.event_type}")
        
        # Test type property
        print(f"event.type = {event.type}")
        
        return True
    except Exception as e:
        print(f"Error testing with property: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    print("=== Event Adapter Debug ===")
    print(f"Python sys.path: {sys.path}")
    
    # Check Event class before adapters
    if not check_event_class():
        print("Failed to check Event class, exiting.")
        return 1
    
    # Add type property
    if not add_type_property():
        print("Failed to add type property, exiting.")
        return 1
    
    # Test with property
    if not test_with_property():
        print("Failed to test with property, exiting.")
        return 1
    
    print("\nDebug completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
