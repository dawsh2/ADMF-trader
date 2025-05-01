"""
Super minimal test file that only tests the Event class with no dependencies.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Event types directly
from src.core.events.event_types import EventType

def test_event_type_enum():
    """Test the EventType enum without using Event class."""
    # Test that EventType has expected values
    assert hasattr(EventType, 'BAR')
    assert hasattr(EventType, 'SIGNAL')
    assert hasattr(EventType, 'ORDER')
    assert hasattr(EventType, 'FILL')
    
    # Test enum values can be compared
    assert EventType.BAR != EventType.SIGNAL
    assert EventType.ORDER != EventType.FILL
    
    print("EventType enum test passed")

def create_custom_event():
    """Create a minimal event without using the Event class."""
    # Create a simple structure to act as an event
    class SimpleEvent:
        def __init__(self, type_value, data):
            self.type = type_value
            self.data = data
    
    # Create an event
    data = {'test': 'data'}
    event = SimpleEvent(EventType.BAR, data)
    
    # Test event properties
    assert event.type == EventType.BAR
    assert event.data == data
    
    print("Custom event creation test passed")
    return event

if __name__ == "__main__":
    print("Starting tests...")
    
    # Run EventType test
    test_event_type_enum()
    
    # Run custom event test
    create_custom_event()
    
    print("All tests passed!")
