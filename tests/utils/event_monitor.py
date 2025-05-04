"""
Event monitoring utilities for testing.
"""
import logging
from src.core.events.event_types import EventType

logger = logging.getLogger(__name__)

class EventMonitor:
    """
    Monitor and track events for testing purposes.
    
    This class registers handlers for events and stores them
    for later inspection.
    """
    
    def __init__(self, event_bus):
        """
        Initialize the event monitor.
        
        Args:
            event_bus: Event bus to monitor
        """
        self.event_bus = event_bus
        self.events = {event_type: [] for event_type in EventType}
        self.handler_refs = {}
        self.active = False
        
    def start(self):
        """Start monitoring events."""
        if self.active:
            return
        
        # Register handlers for all event types
        for event_type in EventType:
            # Create a closure to capture the event type
            def create_handler(et):
                def handler(event):
                    self.events[et].append(event)
                    return True
                return handler
            
            handler = create_handler(event_type)
            # Store a reference to the handler to unregister later
            self.handler_refs[event_type] = handler
            self.event_bus.register(event_type, handler, priority=1000)  # High priority
        
        self.active = True
        logger.info("Event monitor started")
    
    def stop(self):
        """Stop monitoring events."""
        if not self.active:
            return
        
        # Unregister handlers
        for event_type, handler in self.handler_refs.items():
            self.event_bus.unregister(event_type, handler)
        
        self.handler_refs.clear()
        self.active = False
        logger.info("Event monitor stopped")
    
    def reset(self):
        """Reset the monitor by clearing all collected events."""
        for event_list in self.events.values():
            event_list.clear()
        logger.info("Event monitor reset")
    
    def get_events(self, event_type=None):
        """
        Get collected events.
        
        Args:
            event_type: Specific event type to retrieve, or None for all
            
        Returns:
            List of events or dict of events by type
        """
        if event_type is None:
            # Return all events
            return {et: events.copy() for et, events in self.events.items()}
        else:
            # Return events for specific type
            return self.events.get(event_type, []).copy()
    
    def get_event_count(self, event_type=None):
        """
        Get count of collected events.
        
        Args:
            event_type: Specific event type to count, or None for total
            
        Returns:
            Count of events
        """
        if event_type is None:
            # Return total count
            return sum(len(events) for events in self.events.values())
        else:
            # Return count for specific type
            return len(self.events.get(event_type, []))
    
    def print_summary(self):
        """Print a summary of collected events."""
        for event_type in EventType:
            count = len(self.events.get(event_type, []))
            if count > 0:
                logger.info(f"{event_type.name}: {count} events")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False  # Don't suppress exceptions
