"""
Unit tests for the EventBus class.
"""

import pytest
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event


@pytest.mark.unit
@pytest.mark.core
class TestEventBus:
    
    def test_initialization(self):
        """Test EventBus initialization."""
        event_bus = EventBus()
        assert event_bus is not None
        assert hasattr(event_bus, 'handlers')
        assert isinstance(event_bus.handlers, dict)
        assert len(event_bus.handlers) == 0  # No handlers registered initially
    
    def test_register_handler(self, event_bus):
        """Test registering an event handler."""
        # Define a simple handler function
        def test_handler(event):
            pass
        
        # Register the handler
        event_bus.register(EventType.BAR, test_handler)
        
        # Verify handler was registered
        assert EventType.BAR in event_bus.handlers
        assert test_handler in event_bus.handlers[EventType.BAR]
        assert len(event_bus.handlers[EventType.BAR]) == 1
    
    def test_register_handler_with_priority(self, event_bus):
        """Test registering an event handler with priority."""
        # Define a simple handler function
        def test_handler_1(event):
            pass
            
        def test_handler_2(event):
            pass
        
        # Register handlers with different priorities
        event_bus.register(EventType.BAR, test_handler_1, priority=10)
        event_bus.register(EventType.BAR, test_handler_2, priority=5)
        
        # Verify handlers were registered in priority order (lower number = higher priority)
        assert EventType.BAR in event_bus.handlers
        assert len(event_bus.handlers[EventType.BAR]) == 2
        
        handlers = event_bus.handlers[EventType.BAR]
        assert handlers[0] == test_handler_2  # Priority 5 should be first
        assert handlers[1] == test_handler_1  # Priority 10 should be second
    
    def test_unregister_handler(self, event_bus):
        """Test unregistering an event handler."""
        # Define a simple handler function
        def test_handler(event):
            pass
        
        # Register the handler
        event_bus.register(EventType.BAR, test_handler)
        
        # Verify handler was registered
        assert EventType.BAR in event_bus.handlers
        assert test_handler in event_bus.handlers[EventType.BAR]
        
        # Unregister the handler
        event_bus.unregister(EventType.BAR, test_handler)
        
        # Verify handler was unregistered
        assert len(event_bus.handlers[EventType.BAR]) == 0
    
    def test_emit_event(self, event_bus):
        """Test emitting an event."""
        # Create a list to track handler calls
        handler_calls = []
        
        # Define a handler function that appends to the list
        def test_handler(event):
            handler_calls.append(event)
            return event  # Return for testing
        
        # Register the handler
        event_bus.register(EventType.BAR, test_handler)
        
        # Create an event
        event_data = {'symbol': 'TEST', 'price': 100.0}
        event = Event(EventType.BAR, event_data)
        
        # Emit the event
        result = event_bus.emit(event)
        
        # Verify handler was called
        assert len(handler_calls) == 1
        assert handler_calls[0] == event
        assert result == [event]  # Should return handler results
    
    def test_emit_event_multiple_handlers(self, event_bus):
        """Test emitting an event with multiple handlers."""
        # Create lists to track handler calls
        handler1_calls = []
        handler2_calls = []
        
        # Define handler functions
        def test_handler1(event):
            handler1_calls.append(event)
            return "handler1_result"
        
        def test_handler2(event):
            handler2_calls.append(event)
            return "handler2_result"
        
        # Register the handlers
        event_bus.register(EventType.BAR, test_handler1)
        event_bus.register(EventType.BAR, test_handler2)
        
        # Create an event
        event_data = {'symbol': 'TEST', 'price': 100.0}
        event = Event(EventType.BAR, event_data)
        
        # Emit the event
        results = event_bus.emit(event)
        
        # Verify handlers were called
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1
        assert handler1_calls[0] == event
        assert handler2_calls[0] == event
        
        # Verify results
        assert len(results) == 2
        assert "handler1_result" in results
        assert "handler2_result" in results
    
    def test_emit_event_unknown_type(self, event_bus):
        """Test emitting an event with no registered handlers."""
        # Create an event
        event_data = {'symbol': 'TEST', 'price': 100.0}
        event = Event(EventType.BAR, event_data)
        
        # Emit the event (no handlers registered)
        results = event_bus.emit(event)
        
        # Should return empty list since no handlers
        assert results == []
    
    def test_reset(self, event_bus):
        """Test resetting the event bus."""
        # Define a simple handler function
        def test_handler(event):
            pass
        
        # Register handlers for different event types
        event_bus.register(EventType.BAR, test_handler)
        event_bus.register(EventType.SIGNAL, test_handler)
        
        # Verify handlers were registered
        assert EventType.BAR in event_bus.handlers
        assert EventType.SIGNAL in event_bus.handlers
        
        # Reset the event bus
        event_bus.reset()
        
        # Verify all handlers were removed
        assert len(event_bus.handlers) == 0
    
    def test_emission_order(self, event_bus):
        """Test that handlers are called in priority order."""
        # Create a list to record call order
        call_order = []
        
        # Define handler functions with different priorities
        def handler_low_priority(event):
            call_order.append("low")
            return "low"
        
        def handler_medium_priority(event):
            call_order.append("medium")
            return "medium"
        
        def handler_high_priority(event):
            call_order.append("high")
            return "high"
        
        # Register handlers with priorities
        event_bus.register(EventType.BAR, handler_low_priority, priority=30)
        event_bus.register(EventType.BAR, handler_medium_priority, priority=20)
        event_bus.register(EventType.BAR, handler_high_priority, priority=10)
        
        # Create and emit an event
        event = Event(EventType.BAR, {'test': 'data'})
        results = event_bus.emit(event)
        
        # Verify call order
        assert call_order == ["high", "medium", "low"]
        assert results == ["high", "medium", "low"]
