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

# Import components to test
from src.core.events.event_types import Event, EventType
from src.core.events.event_bus import EventBus
from src.core.events.event_utils import create_signal_event, create_order_event

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
        event.mark_consumed()
        assert event.is_consumed()
    
    def test_event_serialization(self):
        """Test event serialization and deserialization."""
        # Create event with fixed timestamp for deterministic testing
        timestamp = datetime.datetime(2024, 1, 1, 10, 0, 0)
        data = {'symbol': 'TEST', 'price': 100.0}
        event = Event(EventType.BAR, data, timestamp)
        
        # Add ID if needed
        event.id = "test-event-id"
        
        # Serialize
        serialized = event.serialize()
        
        # Check serialized data
        assert isinstance(serialized, str)
        assert "BAR" in serialized
        assert "TEST" in serialized
        assert "test-event-id" in serialized
        
        # Deserialize if method exists
        if hasattr(Event, 'deserialize'):
            deserialized = Event.deserialize(serialized)
            assert deserialized.event_type == event.event_type
            assert deserialized.data == event.data
            assert deserialized.id == event.id

class TestEventBus:
    """Tests for the EventBus class."""
    
    def test_event_bus_creation(self):
        """Test creating an EventBus."""
        bus = EventBus()
        assert hasattr(bus, 'handlers')
        assert hasattr(bus, 'register')
        assert hasattr(bus, 'emit')
        assert hasattr(bus, 'unregister')
    
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
        
        # Register handlers
        bus.register(EventType.BAR, handler1)
        bus.register(EventType.SIGNAL, handler2)
        
        # Check registration
        assert bus.has_handlers(EventType.BAR)
        assert bus.has_handlers(EventType.SIGNAL)
        assert not bus.has_handlers(EventType.ORDER)
    
    def test_event_emission(self):
        """Test event emission and handler calling."""
        bus = EventBus()
        
        # Create tracking variables
        handler_calls = []
        
        # Define handler
        def handler(event):
            handler_calls.append(event)
        
        # Register handler
        bus.register(EventType.BAR, handler)
        
        # Create and emit event
        event = Event(EventType.BAR, {'test': 'data'})
        bus.emit(event)
        
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
        
        # Register handler
        bus.register(EventType.BAR, handler)
        
        # Unregister handler
        bus.unregister(EventType.BAR, handler)
        
        # Create and emit event
        event = Event(EventType.BAR, {'test': 'data'})
        bus.emit(event)
        
        # Check handler was not called
        assert len(handler_calls) == 0
    
    def test_event_bus_reset(self):
        """Test resetting the event bus."""
        bus = EventBus()
        
        # Register handlers
        def handler1(event): 
            pass
            
        def handler2(event): 
            pass
        
        bus.register(EventType.BAR, handler1)
        bus.register(EventType.SIGNAL, handler2)
        
        # Check registration
        assert bus.has_handlers(EventType.BAR)
        assert bus.has_handlers(EventType.SIGNAL)
        
        # Reset bus
        bus.reset()
        
        # Check handlers were cleared
        assert not bus.has_handlers(EventType.BAR)
        assert not bus.has_handlers(EventType.SIGNAL)
    
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
        
        # Register both handlers for same event type
        bus.register(EventType.BAR, handler1)
        bus.register(EventType.BAR, handler2)
        
        # Create and emit event
        event = Event(EventType.BAR, {'test': 'data'})
        bus.emit(event)
        
        # Check both handlers were called
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1
        assert handler1_calls[0] == event
        assert handler2_calls[0] == event

class TestEventUtils:
    """Tests for the event utilities."""
    
    def test_create_signal_event(self):
        """Test creating a signal event."""
        signal = create_signal_event(1, 100.0, 'TEST')
        
        # Check event properties
        assert signal.get_type() == EventType.SIGNAL
        assert signal.data.get('signal_value') == 1
        assert signal.data.get('price') == 100.0
        assert signal.data.get('symbol') == 'TEST'
    
    def test_create_order_event(self):
        """Test creating an order event."""
        order = create_order_event('BUY', 100, 'TEST', 'MARKET', 100.0)
        
        # Check event properties
        assert order.get_type() == EventType.ORDER
        assert order.data.get('direction') == 'BUY'
        assert order.data.get('quantity') == 100
        assert order.data.get('symbol') == 'TEST'
        assert order.data.get('order_type') == 'MARKET'
        assert order.data.get('price') == 100.0
