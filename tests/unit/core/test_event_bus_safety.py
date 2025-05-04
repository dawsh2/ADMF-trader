"""
Tests for the enhanced event bus safety features.
"""
import pytest
import time
import threading
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from tests.adapters import EventBusAdapter, EventTimeoutWrapper
from tests.utils.event_tracker import EventMonitor

@pytest.fixture
def safe_event_bus():
    """Create a safe event bus with configurable limits."""
    event_bus = EventBus()
    # Configure with custom limits
    EventBusAdapter.apply(
        event_bus, 
        max_events=200,           # Limit to 200 events per type
        recursion_limit=8,        # Limit recursion depth to 8
        event_timeout=2.0         # Timeout handlers after 2 seconds
    )
    yield event_bus
    event_bus.reset()

@pytest.mark.unit
@pytest.mark.core
class TestEventBusSafety:
    
    def test_configurable_event_limits(self, safe_event_bus):
        """Test that configurable event limits are applied correctly."""
        # Verify the custom limits were applied
        assert safe_event_bus._max_events_per_cycle == 200
        assert safe_event_bus._max_recursion_depth == 8
        assert safe_event_bus._event_timeout == 2.0
    
    def test_event_flow_tracking(self, safe_event_bus):
        """Test tracking events through the system."""
        # Set up monitoring
        with EventMonitor(safe_event_bus) as monitor:
            # Create handlers for testing
            def signal_handler(event):
                # Signal handler creates order
                order_data = {
                    'symbol': event.get_data().get('symbol', 'TEST'),
                    'direction': 'BUY',
                    'quantity': 100
                }
                order_event = Event(EventType.ORDER, order_data)
                safe_event_bus.emit(order_event)
                return event
            
            def order_handler(event):
                # Order handler creates fill
                fill_data = {
                    'symbol': event.get_data().get('symbol', 'TEST'),
                    'direction': event.get_data().get('direction', 'BUY'),
                    'quantity': event.get_data().get('quantity', 0),
                    'price': 150.0
                }
                fill_event = Event(EventType.FILL, fill_data)
                safe_event_bus.emit(fill_event)
                return event
            
            # Register handlers
            safe_event_bus.register(EventType.SIGNAL, signal_handler)
            safe_event_bus.register(EventType.ORDER, order_handler)
            
            # Emit initial event
            signal_event = Event(EventType.SIGNAL, {'symbol': 'AAPL'})
            safe_event_bus.emit(signal_event)
            
            # Check event flow
            assert monitor.get_event_count(EventType.SIGNAL) == 1
            assert monitor.get_event_count(EventType.ORDER) == 1
            assert monitor.get_event_count(EventType.FILL) == 1
            
            # Verify stats are available
            stats = safe_event_bus.get_event_stats()
            assert stats['total_events'] >= 3  # At least our 3 events
            
            # Print summary for debugging
            monitor.print_summary()
    
    def test_recursive_event_protection(self, safe_event_bus):
        """Test protection against recursive events."""
        # Create a handler that would cause infinite recursion
        def recursive_handler(event):
            # This would cause an infinite loop without protection
            safe_event_bus.emit(event)
            return True
        
        # Register the handler
        safe_event_bus.register(EventType.BAR, recursive_handler)
        
        # Should not hang - will be caught by recursion detection
        event = Event(EventType.BAR, {'test': 'data'})
        result = safe_event_bus.emit(event)
        
        # Should return 0 because recursive event was detected and skipped
        assert result == 0
    
    def test_event_count_limiting(self, safe_event_bus):
        """Test that event count limits work."""
        # Create events collected during processing
        events_processed = []
        
        # Create a handler that spawns many events of the same type
        def chain_handler(event):
            events_processed.append(event)
            
            # Get event count
            count = event.get_data().get('count', 0)
            
            # Create a new event with incremented count
            if count < 300:  # Try to exceed our limit of 200
                next_event = Event(
                    EventType.BAR,
                    {'count': count + 1, 'parent': event.get_id()}
                )
                safe_event_bus.emit(next_event)
            
            return True
        
        # Register the handler
        safe_event_bus.register(EventType.BAR, chain_handler)
        
        # Emit the first event
        initial_event = Event(EventType.BAR, {'count': 0})
        safe_event_bus.emit(initial_event)
        
        # We should not process more than our limit of 200 events
        assert len(events_processed) <= 200
        
        # Verify the stats show we hit the limit
        stats = safe_event_bus.get_event_stats()
        assert stats['event_counts'].get(EventType.BAR, 0) <= 200
    
    def test_timeout_protection(self, safe_event_bus):
        """Test that slow handlers are protected by timeout."""
        # Track if the handler completed
        handler_completed = False
        
        # Create a very slow handler
        def slow_handler(event):
            nonlocal handler_completed
            # Sleep longer than our timeout of 2.0 seconds
            time.sleep(3.0)
            handler_completed = True
            return True
        
        # Register the handler
        safe_event_bus.register(EventType.BAR, slow_handler)
        
        # Start time
        start_time = time.time()
        
        # Emit an event
        event = Event(EventType.BAR, {'test': 'data'})
        
        # This should not hang for more than ~2 seconds
        safe_event_bus.emit(event)
        
        # Check duration
        duration = time.time() - start_time
        
        # Should be close to our 2 second timeout, not the full 3 seconds
        assert duration < 2.5
        
        # Handler should not have completed
        assert not handler_completed
