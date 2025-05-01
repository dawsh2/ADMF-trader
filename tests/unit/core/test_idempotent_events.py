"""
Unit tests for idempotent event processing.
Tests the implementation of idempotent event handling across system components.
"""

import pytest
import uuid
from src.core.events.event_types import EventType, Event


@pytest.mark.unit
@pytest.mark.core
class TestIdempotentEvents:
    
    def test_event_id_generation(self):
        """Test that events have unique IDs."""
        # Create multiple events and verify unique IDs
        events = []
        for i in range(10):
            event_data = {'symbol': 'TEST', 'price': 100.0 + i}
            event = Event(EventType.BAR, event_data)
            events.append(event)
        
        # Check that all event IDs are unique
        event_ids = [event.get_id() for event in events]
        assert len(event_ids) == len(set(event_ids))
        
        # Verify each ID is a valid UUID
        for event_id in event_ids:
            try:
                uuid.UUID(event_id)
                is_valid_uuid = True
            except ValueError:
                is_valid_uuid = False
            assert is_valid_uuid, f"Event ID {event_id} is not a valid UUID"
    
    def test_event_equality(self):
        """Test that events with the same ID are considered equal."""
        # Create an event
        event_data = {'symbol': 'TEST', 'price': 100.0}
        event1 = Event(EventType.BAR, event_data)
        
        # Create a copy of the event with the same ID
        event_id = event1.get_id()
        event2 = Event(EventType.BAR, event_data, event_id=event_id)
        
        # Create a different event
        event3 = Event(EventType.BAR, event_data)
        
        # Verify equality
        assert event1 == event2
        assert event1 != event3
        assert event2 != event3
    
    def test_idempotent_processing(self, event_bus):
        """Test that events are processed once even if emitted multiple times."""
        # Create a counter to track handler calls
        call_count = 0
        processed_ids = set()
        
        # Define an idempotent handler function
        def idempotent_handler(event):
            nonlocal call_count
            event_id = event.get_id()
            
            # Only process if not seen before
            if event_id not in processed_ids:
                processed_ids.add(event_id)
                call_count += 1
            return event
        
        # Register the handler
        event_bus.register(EventType.BAR, idempotent_handler)
        
        # Create an event
        event_data = {'symbol': 'TEST', 'price': 100.0}
        event = Event(EventType.BAR, event_data)
        
        # Emit the event multiple times
        for _ in range(5):
            event_bus.emit(event)
        
        # Verify handler was called only once
        assert call_count == 1
        assert len(processed_ids) == 1
    
    def test_idempotent_processing_different_events(self, event_bus):
        """Test that different events are processed independently."""
        # Create a counter to track handler calls
        call_count = 0
        processed_ids = set()
        
        # Define an idempotent handler function
        def idempotent_handler(event):
            nonlocal call_count
            event_id = event.get_id()
            
            # Only process if not seen before
            if event_id not in processed_ids:
                processed_ids.add(event_id)
                call_count += 1
            return event
        
        # Register the handler
        event_bus.register(EventType.BAR, idempotent_handler)
        
        # Create and emit multiple unique events
        for i in range(5):
            event_data = {'symbol': 'TEST', 'price': 100.0 + i}
            event = Event(EventType.BAR, event_data)
            event_bus.emit(event)
        
        # Verify each unique event was processed
        assert call_count == 5
        assert len(processed_ids) == 5
