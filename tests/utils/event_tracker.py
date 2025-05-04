"""
Event tracking utility for testing and debugging event flow.
"""
import time
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class EventTracker:
    """Track event statistics for better debugging."""
    
    def __init__(self):
        self.event_counts = defaultdict(int)
        self.event_sequence = []
        self.start_time = time.time()
        self.event_durations = defaultdict(list)
        self.errors = []
    
    def track_event(self, event_type, event_id, duration):
        """Track an event."""
        self.event_counts[event_type] += 1
        self.event_sequence.append((time.time() - self.start_time, event_type, event_id))
        self.event_durations[event_type].append(duration)
    
    def track_error(self, event_type, event_id, error):
        """Track an error that occurred during event processing."""
        self.errors.append({
            'time': time.time() - self.start_time,
            'event_type': event_type,
            'event_id': event_id,
            'error': str(error)
        })
    
    def get_stats(self):
        """Get event statistics."""
        stats = {
            "total_events": sum(self.event_counts.values()),
            "event_counts": dict(self.event_counts),
            "average_durations": {
                event_type: sum(durations) / len(durations) if durations else 0
                for event_type, durations in self.event_durations.items()
            },
            "error_count": len(self.errors)
        }
        return stats
    
    def print_summary(self):
        """Print a summary of tracked events."""
        stats = self.get_stats()
        print(f"Event Tracking Summary:")
        print(f"  Total events: {stats['total_events']}")
        print(f"  Event counts by type:")
        for event_type, count in sorted(stats['event_counts'].items(), key=lambda x: x[1], reverse=True):
            avg_duration = stats['average_durations'][event_type] * 1000  # Convert to ms
            print(f"    {event_type}: {count} events (avg {avg_duration:.2f}ms)")
        
        if self.errors:
            print(f"  Errors: {len(self.errors)}")
            for i, error in enumerate(self.errors[:5]):  # Show first 5 errors only
                print(f"    {i+1}. [{error['event_type']}]: {error['error']}")
            if len(self.errors) > 5:
                print(f"    ... and {len(self.errors) - 5} more errors")

class EventMonitor:
    """Monitor events flowing through an event bus."""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.tracker = EventTracker()
        self.handlers = {}
        self.active = False
    
    def __enter__(self):
        """Start monitoring when entering a context."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop monitoring when exiting a context."""
        self.stop()
        
        # Log exception if one occurred
        if exc_type is not None:
            logger.error(f"Error during event monitoring: {exc_val}")
            return False  # Don't suppress the exception
    
    def start(self):
        """Start monitoring events."""
        if self.active:
            logger.warning("Event monitor already active")
            return
        
        self.active = True
        self.tracker = EventTracker()  # Reset tracker
        
        # Register for all event types
        from src.core.events.event_types import EventType
        for event_type in EventType:
            # Create a handler for this event type
            def make_handler(et):
                def handler(event):
                    if not self.active:
                        return event
                    
                    start_time = time.time()
                    try:
                        # Just pass through the event
                        return event
                    finally:
                        duration = time.time() - start_time
                        self.tracker.track_event(et, event.get_id(), duration)
                return handler
            
            handler = make_handler(event_type)
            self.handlers[event_type] = handler
            
            # Register with low priority to ensure we see all events
            self.event_bus.register(event_type, handler, priority=999)
        
        logger.debug("Event monitoring started")
    
    def stop(self):
        """Stop monitoring events."""
        if not self.active:
            logger.warning("Event monitor not active")
            return
        
        self.active = False
        
        # Unregister all handlers
        from src.core.events.event_types import EventType
        for event_type in EventType:
            if event_type in self.handlers:
                try:
                    self.event_bus.unregister(event_type, self.handlers[event_type])
                except Exception as e:
                    logger.warning(f"Error unregistering handler for {event_type}: {e}")
        
        self.handlers = {}
        logger.debug("Event monitoring stopped")
    
    def get_stats(self):
        """Get event statistics."""
        return self.tracker.get_stats()
    
    def print_summary(self):
        """Print a summary of monitored events."""
        self.tracker.print_summary()
    
    def get_event_count(self, event_type=None):
        """Get the number of events, optionally filtered by type."""
        if event_type is None:
            return self.tracker.get_stats()["total_events"]
        return self.tracker.event_counts.get(event_type, 0)
    
    def get_event_sequence(self):
        """Get the sequence of events as a list of (time, type, id) tuples."""
        return self.tracker.event_sequence
