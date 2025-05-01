"""
Fixed version of the adapter test that works with the Event class.
"""

import sys
import os

# Add project root to path so 'src' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Event and EventType classes
from src.core.events.event_types import Event, EventType

# Define the fixed adapter function
def apply_adapter_fix():
    """Apply the fix to the Event class."""
    # Add type property to bridge event_type to type if not already present
    if not hasattr(Event, 'type'):
        @property
        def type_property(self):
            """Bridge property to access event_type as type."""
            return self.event_type
        
        Event.type = type_property
        print("Added 'type' property to Event class")
    else:
        print("Event class already has 'type' property")

# Apply the fix
apply_adapter_fix()

# Test that it works
def test_adapter_fix():
    """Test that the adapter fix works."""
    # Create an event
    data = {'symbol': 'TEST', 'price': 100.0}
    event = Event(EventType.BAR, data)
    
    # Access attributes
    print(f"event.event_type = {event.event_type}")  # Original attribute
    print(f"event.type = {event.type}")  # Property added by adapter
    print(f"event.data = {event.data}")
    
    # Verify they match
    assert event.event_type == event.type
    assert event.event_type == EventType.BAR
    assert event.data == data
    
    print("Adapter fix works correctly!")
    return True

# Run the test if this file is executed directly
if __name__ == "__main__":
    print("Testing fixed adapter...")
    test_adapter_fix()
