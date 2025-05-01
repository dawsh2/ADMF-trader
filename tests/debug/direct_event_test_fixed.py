"""
Direct test of the Event class with no adapters, pytest, or any other dependencies.
Use the correct attribute names based on inspection results.
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
        
        # Use the correct attribute name from inspection: event_type instead of type
        print(f"Event type: {event.event_type}")
        print(f"Event data: {event.data}")
        
        # Test event properties and methods
        print("\nTesting event properties and methods...")
        
        # Check for id attribute
        if hasattr(event, 'id'):
            print(f"Event has ID: {event.id}")
        
        # Check for timestamp attribute
        if hasattr(event, 'timestamp'):
            print(f"Event timestamp: {event.timestamp}")
        
        # Check for consumed attribute
        if hasattr(event, 'consumed'):
            print(f"Event consumed: {event.consumed}")
        
        # Check get methods if they exist
        if hasattr(event, 'get_type'):
            print(f"event.get_type() = {event.get_type()}")
        
        if hasattr(event, 'get_id'):
            print(f"event.get_id() = {event.get_id()}")
        
        # Check if mark_consumed works
        if hasattr(event, 'mark_consumed'):
            event.mark_consumed()
            print(f"After mark_consumed, event.consumed = {event.consumed}")
        
        # Create a second event
        print("\nCreating second event...")
        event2 = Event(EventType.BAR, data)
        
        # Compare events
        print("\nComparing events...")
        print(f"event.id = {event.id}")
        print(f"event2.id = {event2.id}")
        
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
