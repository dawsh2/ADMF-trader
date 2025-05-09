"""
Robust event bus with improved error handling and traceability.

This implementation ensures events are properly handled even when errors
occur in event handlers, and provides traceability for debugging.
"""

import logging
import traceback
from collections import defaultdict
from src.core.event_bus import EventType

logger = logging.getLogger(__name__)

class RobustEventBus:
    """Event bus with improved error handling and traceability"""
    
    def __init__(self):
        """Initialize the robust event bus."""
        self.subscribers = defaultdict(list)
        self.event_log = []
        logger.info("RobustEventBus initialized")
        
    def register(self, event_type, handler):
        """
        Register a handler for an event type.
        
        Args:
            event_type (EventType): Event type to subscribe to
            handler (callable): Handler function
        """
        self.subscribers[event_type].append(handler)
        handler_name = getattr(handler, '__name__', str(handler))
        logger.info(f"Handler {handler_name} registered for event type {event_type}")
        
    def emit(self, event_type, event_data=None):
        """
        Emit an event with data.
        
        Args:
            event_type (EventType): Type of event
            event_data (dict, optional): Event data
        """
        # Create an Event object from type and data
        from src.core.events.event_types import Event
        event = Event(event_type, event_data)
        self.publish(event)
        
    def publish(self, event):
        """
        Publish an event with error handling.
        
        Args:
            event (Event): Event to publish
        """
        event_type = event.get_type()
        self.event_log.append(event)  # Log for traceability
        
        if event_type not in self.subscribers:
            logger.debug(f"No subscribers for event type {event_type}")
            return
            
        for handler in self.subscribers[event_type]:
            try:
                handler(event)
            except Exception as e:
                # Log error but continue processing other handlers
                handler_name = getattr(handler, '__name__', str(handler))
                logger.error(f"Error in event handler {handler_name}: {e}")
                logger.error(traceback.format_exc())
                # Continue with other handlers, don't let one failure stop processing
    
    def get_event_log(self):
        """
        Return the event log for debugging.
        
        Returns:
            list: List of events
        """
        return self.event_log
    
    def clear_event_log(self):
        """Clear the event log."""
        self.event_log = []
        
    def reset(self):
        """Reset the event bus state."""
        self.subscribers = defaultdict(list)
        self.event_log = []
        logger.info("RobustEventBus reset")
