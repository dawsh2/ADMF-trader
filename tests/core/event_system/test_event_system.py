"""
Test cases for the event system.

This module contains unit tests for the core event system.
"""

import unittest
# Import directly from canonical sources to avoid warnings
from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType
from src.core.event_system.event_bus import EventBus

class EventTests(unittest.TestCase):
    """Test cases for the Event class."""
    
    def test_event_creation(self):
        """Test creating an event."""
        event = Event(EventType.BAR, {'symbol': 'AAPL', 'price': 150.0})
        
        self.assertEqual(event.get_type(), EventType.BAR)
        self.assertEqual(event.get_data(), {'symbol': 'AAPL', 'price': 150.0})
        self.assertFalse(event.is_consumed())
        
    def test_event_consumption(self):
        """Test consuming an event."""
        event = Event(EventType.BAR, {'symbol': 'AAPL', 'price': 150.0})
        
        self.assertFalse(event.is_consumed())
        event.consume()
        self.assertTrue(event.is_consumed())
        
    def test_dedup_key(self):
        """Test generating deduplication keys."""
        # Signal event with rule_id
        signal_event = Event(EventType.SIGNAL, {'symbol': 'AAPL', 'rule_id': 'rule1'})
        self.assertEqual(signal_event.get_dedup_key(), 'signal_rule1')
        
        # Order event with order_id
        order_event = Event(EventType.ORDER, {'symbol': 'AAPL', 'order_id': 'order1'})
        self.assertEqual(order_event.get_dedup_key(), 'order_order1')
        
        # Order event with rule_id
        order_event2 = Event(EventType.ORDER, {'symbol': 'AAPL', 'rule_id': 'rule1'})
        self.assertEqual(order_event2.get_dedup_key(), 'order_from_rule1')
        
        # Fill event with order_id
        fill_event = Event(EventType.FILL, {'symbol': 'AAPL', 'order_id': 'order1'})
        self.assertEqual(fill_event.get_dedup_key(), 'fill_order1')
        
class EventBusTests(unittest.TestCase):
    """Test cases for the EventBus class."""
    
    def setUp(self):
        """Set up the test case."""
        self.event_bus = EventBus()
        
    def test_subscribe_and_publish(self):
        """Test subscribing to and publishing events."""
        # Track received events
        received_events = []
        
        # Define handler
        def handler(event):
            received_events.append(event)
            
        # Subscribe to BAR events
        self.event_bus.subscribe(EventType.BAR, handler)
        
        # Publish a BAR event
        event = Event(EventType.BAR, {'symbol': 'AAPL', 'price': 150.0})
        self.event_bus.publish(event)
        
        # Verify handler was called
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].get_type(), EventType.BAR)
        self.assertEqual(received_events[0].get_data(), {'symbol': 'AAPL', 'price': 150.0})
        
    def test_deduplication(self):
        """Test event deduplication."""
        # Track received events
        received_events = []
        
        # Define handler
        def handler(event):
            received_events.append(event)
            
        # Subscribe to SIGNAL events
        self.event_bus.subscribe(EventType.SIGNAL, handler)
        
        # Publish two SIGNAL events with the same rule_id
        event1 = Event(EventType.SIGNAL, {'symbol': 'AAPL', 'rule_id': 'rule1'})
        event2 = Event(EventType.SIGNAL, {'symbol': 'AAPL', 'rule_id': 'rule1'})
        
        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        
        # Verify only first event was processed (deduplication)
        self.assertEqual(len(received_events), 1)
        
    def test_priority_order(self):
        """Test priority-based handler execution."""
        # Track call order
        call_order = []
        
        # Define handlers with different priorities
        def handler1(event):
            call_order.append('handler1')
            
        def handler2(event):
            call_order.append('handler2')
            
        def handler3(event):
            call_order.append('handler3')
            
        # Subscribe with different priorities (lower number = higher priority)
        self.event_bus.subscribe(EventType.BAR, handler2, priority=0)  # Default priority
        self.event_bus.subscribe(EventType.BAR, handler1, priority=-10)  # Higher priority
        self.event_bus.subscribe(EventType.BAR, handler3, priority=10)  # Lower priority
        
        # Publish an event
        event = Event(EventType.BAR, {'symbol': 'AAPL'})
        self.event_bus.publish(event)
        
        # Verify call order
        self.assertEqual(call_order, ['handler1', 'handler2', 'handler3'])
        
    def test_event_consumption(self):
        """Test event consumption stops further processing."""
        # Track call order
        call_order = []
        
        # Define handlers where one consumes the event
        def handler1(event):
            call_order.append('handler1')
            event.consume()  # Consume the event
            
        def handler2(event):
            call_order.append('handler2')
            
        # Subscribe both handlers
        self.event_bus.subscribe(EventType.BAR, handler1)
        self.event_bus.subscribe(EventType.BAR, handler2)
        
        # Publish an event
        event = Event(EventType.BAR, {'symbol': 'AAPL'})
        self.event_bus.publish(event)
        
        # Verify only first handler was called
        self.assertEqual(call_order, ['handler1'])
        
    def test_batching(self):
        """Test event batching."""
        # Track received events
        received_events = []
        
        # Define handler
        def handler(event):
            received_events.append(event)
            
        # Subscribe to BAR events
        self.event_bus.subscribe(EventType.BAR, handler)
        
        # Start batch
        self.event_bus.start_batch()
        
        # Publish events in batch
        event1 = Event(EventType.BAR, {'symbol': 'AAPL'})
        event2 = Event(EventType.BAR, {'symbol': 'MSFT'})
        
        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        
        # Verify no events processed yet
        self.assertEqual(len(received_events), 0)
        
        # End batch
        self.event_bus.end_batch()
        
        # Verify all events processed
        self.assertEqual(len(received_events), 2)
        self.assertEqual(received_events[0].get_data()['symbol'], 'AAPL')
        self.assertEqual(received_events[1].get_data()['symbol'], 'MSFT')
        
if __name__ == '__main__':
    unittest.main()