"""
Simple event bus implementation that replaces the complex event system.

This implementation provides a straightforward pub/sub event system without
the over-engineered deduplication and event tracking mechanisms that were
causing fragility and potential event loss.
"""

from collections import defaultdict
from enum import Enum, auto

class EventType(Enum):
    """Standard event types for the system."""
    BAR = auto()
    SIGNAL = auto()
    ORDER = auto()
    FILL = auto()
    TRADE_OPEN = auto()
    TRADE_CLOSE = auto()
    PORTFOLIO_UPDATE = auto()
    BACKTEST_START = auto()
    BACKTEST_END = auto()
    # Add other event types as needed

class Event:
    """Base class for all events in the system."""
    
    def __init__(self, event_type, data=None):
        """
        Initialize a new event.
        
        Args:
            event_type (EventType): Type of this event
            data (dict, optional): Event data payload
        """
        self.event_type = event_type
        self.data = data or {}
        
    def get_type(self):
        """Get the event type."""
        return self.event_type
        
    def get_data(self):
        """Get the event data."""
        return self.data
        
    def __str__(self):
        """String representation of the event."""
        return f"Event({self.event_type}, {self.data})"

class SimpleEventBus:
    """
    Simple pub/sub event system without complex deduplication.
    
    This implementation focuses on simplicity and reliability over
    complex event tracking mechanisms.
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self.subscribers = defaultdict(list)
        self.event_log = []  # Optional: simple event log for debugging
        self.log_events = False  # Flag to control event logging
        
    def subscribe(self, event_type, handler):
        """
        Subscribe a handler to a specific event type.
        
        Args:
            event_type (EventType): Event type to subscribe to
            handler (callable): Function to call when event occurs
        """
        self.subscribers[event_type].append(handler)
        
    def unsubscribe(self, event_type, handler):
        """
        Unsubscribe a handler from a specific event type.
        
        Args:
            event_type (EventType): Event type to unsubscribe from
            handler (callable): Handler to remove
        """
        if event_type in self.subscribers:
            self.subscribers[event_type] = [
                h for h in self.subscribers[event_type] if h != handler
            ]
        
    def publish(self, event):
        """
        Publish an event to all subscribers.
        
        Args:
            event (Event): Event to publish
        """
        event_type = event.get_type()
        
        # Optional event logging for debugging
        if self.log_events:
            self.event_log.append(event)
        
        # Simply distribute the event without complex deduplication
        for handler in self.subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                # Simple error logging - a real implementation would use proper logging
                print(f"Error in event handler {handler.__name__}: {e}")
                
    def clear(self):
        """Clear all event subscriptions and logs."""
        self.subscribers.clear()
        self.event_log.clear()
        
    def enable_logging(self, enabled=True):
        """
        Enable or disable event logging.
        
        Args:
            enabled (bool): Whether logging should be enabled
        """
        self.log_events = enabled
