"""
Direct test of the Event class with no adapters, pytest, or any other dependencies.
"""

import sys
import os
import time
import traceback

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_direct_event():
    """Test the Event class directly with no dependencies."""
    try:
        print("Importing Event and EventType classes...")
        # Directly import from module - no adapter layer
        from src.core.events.event_types import Event, EventType
        
        print("Creating basic event...")
        # Create a simple event
        start_time = time.time()
        data = {'symbol': 'TEST', 'price': 100.0}
        event = Event(EventType.BAR, data)
        creation_time = time.time() - start_time
        
        print(f"Event created in {creation_time:.6f} seconds")
        print(f"Event type: {event.type}")
        print(f"Event data: {event.data}")
        
        # Test event properties and methods
        print("\nTesting event properties and methods...")
        
        # Check if the event has an ID
        if hasattr(event, 'id'):
            print(f"Event has ID: {event.id}")
        else:
            print("Event has no ID attribute")
        
        # Check for other attributes
        for name in dir(event):
            if not name.startswith('__'):
                try:
                    value = getattr(event, name)
                    if not callable(value):
                        print(f"Attribute: {name} = {value}")
                except Exception as e:
                    print(f"Error accessing attribute {name}: {e}")
        
        # Check get methods if they exist
        if hasattr(event, 'get_type'):
            print(f"event.get_type() = {event.get_type()}")
        
        if hasattr(event, 'get_data'):
            print(f"event.get_data() = {event.get_data()}")
        
        # Create a second event
        print("\nCreating second event...")
        event2 = Event(EventType.BAR, data)
        
        # Test equality if __eq__ is implemented
        print("\nTesting equality...")
        print(f"event == event2: {event == event2}")
        print(f"event is event2: {event is event2}")
        
        print("\nTest completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error in test_direct_event: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting direct Event test...\n")
    success = test_direct_event()
    print(f"\nTest {'passed' if success else 'failed'}")
