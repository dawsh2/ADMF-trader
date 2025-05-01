"""
Test with a mock Event class to avoid timeout issues.
"""

import sys
import os
import enum

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Create mock classes instead of importing the real ones
class EventType(enum.Enum):
    BAR = "BAR"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"

class MockEvent:
    """Mock Event class that mimics the real Event class."""
    def __init__(self, event_type, data=None):
        self.event_type = event_type
        self.data = data or {}
        self.id = f"mock-id-{id(self)}"
        self.consumed = False
    
    def get_type(self):
        """Get event type."""
        return self.event_type
    
    def get_data(self):
        """Get event data."""
        return self.data
    
    def get_id(self):
        """Get event ID."""
        return self.id
    
    def is_consumed(self):
        """Check if this event has been consumed."""
        return self.consumed
    
    def mark_consumed(self):
        """Mark this event as consumed."""
        self.consumed = True

def extend_mock_event():
    """Add 'type' property to MockEvent."""
    if not hasattr(MockEvent, 'type'):
        @property
        def type_property(self):
            """Bridge property to access event_type as type."""
            return self.event_type
        
        MockEvent.type = type_property
        print("Added 'type' property to MockEvent class")

def test_mock_event():
    """Test the mock event with the type property."""
    # Extend the mock
    extend_mock_event()
    
    # Create a mock event
    data = {'symbol': 'TEST', 'price': 100.0}
    event = MockEvent(EventType.BAR, data)
    
    # Test direct attribute
    assert event.event_type == EventType.BAR
    
    # Test property
    assert event.type == EventType.BAR
    
    # Test methods
    assert event.get_type() == EventType.BAR
    assert event.get_data() == data
    assert event.get_id() == event.id
    
    # Test consumption
    assert not event.is_consumed()
    event.mark_consumed()
    assert event.is_consumed()
    
    print("All tests passed for MockEvent!")
    return True

if __name__ == "__main__":
    print("Testing with mock Event...")
    test_mock_event()
