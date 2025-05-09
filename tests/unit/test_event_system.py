"""
Unit tests for the Event system.
Tests the Event, EventBus, and related components individually.
"""

import sys
import os
import pytest
import uuid
import datetime
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import components to test - use canonical implementations
from src.core.event_system.event import Event, create_event
from src.core.event_system.event_types import EventType
from src.core.event_system.event_bus import EventBus  # Use canonical EventBus

class TestEventType:
    """Tests for the EventType enum."""
    
    def test_event_type_values(self):
        """Test that EventType has expected values."""
        # Check core event types
        assert hasattr(EventType, 'BAR')
        assert hasattr(EventType, 'SIGNAL')
        assert hasattr(EventType, 'ORDER')
        assert hasattr(EventType, 'FILL')
        
        # Check additional event types
        assert hasattr(EventType, 'PORTFOLIO')
        assert hasattr(EventType, 'STRATEGY')
        
        # Test enum behavior
        assert EventType.BAR != EventType.SIGNAL
        assert EventType.ORDER != EventType.FILL

class TestEvent:
    """Tests for the Event class."""
    
    def test_event_creation(self):
        """Test creating an Event with basic attributes."""
        # Create event
        data = {'test': 'data'}
        event = Event(EventType.BAR, data)
        
        # Test attributes
        assert event.event_type == EventType.BAR
        assert event.data == data
        assert isinstance(event.id, str)
        assert isinstance(event.timestamp, datetime.datetime)
        assert not event.consumed
    
    def test_event_methods(self):
        """Test Event class methods."""
        # Create event
        data = {'symbol': 'TEST', 'price': 100.0}
        event = Event(EventType.SIGNAL, data)
        
        # Test getter methods
        assert event.get_type() == EventType.SIGNAL
        assert event.get_id() == event.id
        assert event.get_timestamp() == event.timestamp
        
        # Test consumption tracking
        assert not event.is_consumed()
        event.consume()
        assert event.is_consumed()
    
    # Serialization is no longer part of the core Event class
    # def test_event_serialization(self):
    #     """Test event serialization and deserialization."""
    #     # Create event with fixed timestamp for deterministic testing
    #     timestamp = datetime.datetime(2024, 1, 1, 10, 0, 0)
    #     data = {'symbol': 'TEST', 'price': 100.0}
    #     event = Event(EventType.BAR, data, timestamp)
    #     
    #     # Add ID if needed
    #     event.id = "test-event-id"
    #     
    #     # Serialize
    #     serialized = event.serialize()
    #     
    #     # Check serialized data
    #     assert isinstance(serialized, str)
    #     assert "BAR" in serialized
    #     assert "TEST" in serialized
    #     assert "test-event-id" in serialized
    #     
    #     # Deserialize if method exists
    #     if hasattr(Event, 'deserialize'):
    #         deserialized = Event.deserialize(serialized)
    #         assert deserialized.event_type == event.event_type
    #         assert deserialized.data == event.data
    #         assert deserialized.id == event.id

class TestEventBus:
    """Tests for the EventBus class."""
    
    def test_event_bus_creation(self):
        """Test creating an EventBus."""
        bus = EventBus()
        # Check for methods in canonical EventBus
        assert hasattr(bus, 'subscribers')
        assert hasattr(bus, 'subscribe')
        assert hasattr(bus, 'publish')
        assert hasattr(bus, 'unsubscribe')
    
    def test_event_handler_registration(self):
        """Test registering event handlers."""
        bus = EventBus()
        
        # Create tracking variables
        handler1_calls = []
        handler2_calls = []
        
        # Define handlers
        def handler1(event):
            handler1_calls.append(event)
        
        def handler2(event):
            handler2_calls.append(event)
        
        # Register handlers - use subscribe method
        bus.subscribe(EventType.BAR, handler1)
        bus.subscribe(EventType.SIGNAL, handler2)
        
        # Check registration - use has_subscribers method
        assert bus.has_subscribers(EventType.BAR)
        assert bus.has_subscribers(EventType.SIGNAL)
        assert not bus.has_subscribers(EventType.ORDER)
    
    def test_event_emission(self):
        """Test event emission and handler calling."""
        bus = EventBus()
        
        # Create tracking variables
        handler_calls = []
        
        # Define handler
        def handler(event):
            handler_calls.append(event)
        
        # Register handler - use subscribe method
        bus.subscribe(EventType.BAR, handler)
        
        # Create and emit event - use publish method
        event = Event(_type=EventType.BAR, data={'test': 'data'})
        bus.publish(event)
        
        # Check handler was called
        assert len(handler_calls) == 1
        assert handler_calls[0] == event
    
    def test_event_unregistration(self):
        """Test unregistering event handlers."""
        bus = EventBus()
        
        # Create tracking variables
        handler_calls = []
        
        # Define handler
        def handler(event):
            handler_calls.append(event)
        
        # Register handler - use subscribe method
        bus.subscribe(EventType.BAR, handler)
        
        # Unregister handler - use unsubscribe method
        bus.unsubscribe(EventType.BAR, handler)
        
        # Create and emit event - use publish method
        event = Event(_type=EventType.BAR, data={'test': 'data'})
        bus.publish(event)
        
        # Check handler was not called
        assert len(handler_calls) == 0
    
    def test_event_bus_reset(self):
        """Test resetting the event bus."""
        bus = EventBus()
        
        # Note: In the canonical implementation, reset() does not clear subscribers
        # but rather clears processed_keys, event_counts, etc.
        # We'll test the bus's ability to continue processing events after reset()
        
        # Create a test event
        event = Event(_type=EventType.BAR, data={'test': 'data'})
        
        # Create tracking variables
        handler_calls = []
        
        # Define handler
        def handler(event):
            handler_calls.append(event)
            
        # Register handler
        bus.subscribe(EventType.BAR, handler)
        
        # Reset the bus
        bus.reset()
        
        # Publish an event after reset - this should still work
        bus.publish(event)
        
        # Check that the handler was still called
        assert len(handler_calls) == 1
    
    def test_multiple_handlers(self):
        """Test multiple handlers for same event type."""
        bus = EventBus()
        
        # Create tracking variables
        handler1_calls = []
        handler2_calls = []
        
        # Define handlers
        def handler1(event):
            handler1_calls.append(event)
        
        def handler2(event):
            handler2_calls.append(event)
        
        # Register both handlers for same event type - use subscribe method
        bus.subscribe(EventType.BAR, handler1)
        bus.subscribe(EventType.BAR, handler2)
        
        # Create and emit event - use publish method
        event = Event(_type=EventType.BAR, data={'test': 'data'})
        bus.publish(event)
        
        # Check both handlers were called
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1
        assert handler1_calls[0] == event
        assert handler2_calls[0] == event

class TestEventUtils:
    """Tests for the event utilities."""
    
    def test_create_signal_event(self):
        """Test creating a signal event."""
        # Use canonical Event constructor directly
        signal_data = {
            'symbol': 'TEST',
            'signal_type': 'BUY',
            'strategy_id': 'strategy_1',
            'strength': 1.0
        }
        signal = Event(_type=EventType.SIGNAL, data=signal_data)
        
        # Check event properties
        assert signal.get_type() == EventType.SIGNAL
        assert signal.data.get('symbol') == 'TEST'
        assert signal.data.get('signal_type') == 'BUY'
        assert signal.data.get('strategy_id') == 'strategy_1'
    
    def test_create_order_event(self):
        """Test creating an order event."""
        # Use canonical Event constructor directly
        order_data = {
            'symbol': 'TEST',
            'order_type': 'MARKET',
            'quantity': 100,
            'direction': 'BUY',
            'price': 100.0
        }
        order = Event(_type=EventType.ORDER, data=order_data)
        
        # Check event properties
        assert order.get_type() == EventType.ORDER
        assert order.data.get('symbol') == 'TEST'
        assert order.data.get('order_type') == 'MARKET'
        assert order.data.get('quantity') == 100
        assert order.data.get('direction') == 'BUY'
        assert order.data.get('price') == 100.0
