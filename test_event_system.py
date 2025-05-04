#!/usr/bin/env python
"""
Test the event system to verify our fixes.
"""

import os
import sys
import logging
from datetime import datetime

# Set up path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the fixed event system
from src.core.events.event_bus import EventBus
from src.core.events.event_types import Event, EventType
from src.core.events.event_utils import create_signal_event, create_order_event

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_event_creation():
    """Test event creation and properties."""
    event = Event(EventType.BAR, {"test": "data"})
    assert event.event_type == EventType.BAR
    assert event.data["test"] == "data"
    assert event.id is not None
    logger.info("✅ Event creation test passed")

def test_event_equality():
    """Test event equality."""
    event1 = Event(EventType.BAR, {"test": "data"})
    event2 = Event(EventType.BAR, {"test": "data"}, event_id=event1.id)
    event3 = Event(EventType.BAR, {"test": "data"})
    
    assert event1 == event2
    assert event1 != event3
    logger.info("✅ Event equality test passed")

def test_event_serialization():
    """Test event serialization and deserialization."""
    event = Event(EventType.BAR, {"test": "data", "timestamp": datetime.now()})
    
    # Serialize
    serialized = event.serialize()
    assert isinstance(serialized, str)
    
    # Deserialize
    deserialized = Event.deserialize(serialized)
    assert deserialized.event_type == event.event_type
    assert deserialized.id == event.id
    logger.info("✅ Event serialization test passed")

def test_event_bus_registration():
    """Test event bus registration."""
    event_bus = EventBus()
    
    calls = []
    def handler(event):
        calls.append(event)
        return "handled"
    
    # Register
    event_bus.register(EventType.BAR, handler)
    
    # Verify registration
    assert event_bus.has_handlers(EventType.BAR)
    logger.info("✅ Event bus registration test passed")

def test_event_bus_emission():
    """Test event bus emission."""
    event_bus = EventBus()
    
    calls = []
    def handler(event):
        calls.append(event)
        return "handled"
    
    # Register
    event_bus.register(EventType.BAR, handler)
    
    # Emit
    event = Event(EventType.BAR, {"test": "data"})
    event_bus.emit(event)
    
    # Verify handler was called
    assert len(calls) == 1
    assert calls[0] == event
    logger.info("✅ Event bus emission test passed")

def test_create_order_event():
    """Test creating an order event."""
    order = create_order_event("BUY", 100, "TEST", "MARKET", 100.0)
    
    # Verify order properties
    assert order.get_type() == EventType.ORDER
    assert order.data.get("direction") == "BUY"
    assert order.data.get("quantity") == 100
    assert order.data.get("symbol") == "TEST"
    logger.info("✅ Create order event test passed")

def main():
    """Run event system tests."""
    logger.info("Running event system tests...")
    
    test_event_creation()
    test_event_equality()
    test_event_serialization()
    test_event_bus_registration()
    test_event_bus_emission()
    test_create_order_event()
    
    logger.info("All tests passed! ✅")
    return 0

if __name__ == "__main__":
    sys.exit(main())
