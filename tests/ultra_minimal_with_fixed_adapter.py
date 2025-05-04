"""
Ultra minimal test file that explicitly imports and uses the fixed adapter.
"""

import sys
import os

# Add project root to path so 'src' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Event and EventType classes
from src.core.events.event_types import Event, EventType

# Add type property to bridge event_type to type
def fix_event_class():
    """Add the 'type' property to the Event class."""
    if not hasattr(Event, 'type'):
        @property
        def type_property(self):
            """Bridge property to access event_type as type."""
            return self.event_type
        
        # Add the type property
        Event.type = type_property
        # Property added successfully
    else:
        # Property already exists
        pass

# Simple direct test
def test_event_with_fixed_adapter():
    """Test Event class with the fixed adapter."""
    # Create event
    data = {'symbol': 'TEST', 'price': 100.0}
    event = Event(EventType.BAR, data)
    
    # Test accessing type via the property added by the adapter
    assert event.event_type == EventType.BAR
    assert hasattr(event, 'type'), "Event should have 'type' property after adapter is applied"
    assert event.type == EventType.BAR
    assert event.data == data
    
    print("Event created with correct type!")
    
    # Test the standard methods
    assert event.get_type() == EventType.BAR
    assert event.get_id() == event.id
    
    print("All event methods working correctly!")
    
    return True

# Run test
if __name__ == "__main__":
    print("Testing Event with fixed adapter...")
    # Apply the fix
    fix_event_class()
    # Run the test
    success = test_event_with_fixed_adapter()
    print(f"Test {'passed' if success else 'failed'}!")
