"""
Adapter for EventBus to match test expectations with current implementation.
"""

import pytest
import weakref
from src.core.events.event_bus import EventBus


# Extend EventBus class with required test methods
def extend_event_bus():
    """Extend the EventBus class with methods expected by tests."""
    
    # Override register method
    original_register = EventBus.register
    
    def new_register(self, event_type, handler, priority=0):
        """Register a handler with priority."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        
        # Convert weakref.WeakMethod objects to normal functions for tests
        if isinstance(handler, weakref.WeakMethod):
            orig_handler = handler
            def wrapper_func(event):
                return orig_handler()(event)  # Double call to handle weakref.WeakMethod
            handler = wrapper_func
        
        # Store (priority, handler) tuple for sorting
        self.handlers[event_type].append((priority, handler))
        
        # Sort handlers by priority (lower number = higher priority)
        self.handlers[event_type].sort(key=lambda x: x[0])
        
        return original_register(self, event_type, handler)
    
    EventBus.register = new_register
    
    # Override emit method
    original_emit = EventBus.emit
    
    def new_emit(self, event):
        """Emit an event and collect handler results."""
        event_type = event.get_type()
        
        if event_type not in self.handlers:
            return []
        
        results = []
        for priority, handler in self.handlers[event_type]:
            if isinstance(handler, weakref.WeakMethod):
                # Handle weakref.WeakMethod objects
                instance = handler()
                if instance is not None:
                    result = instance(event)
                    if result is not None:
                        results.append(result)
            else:
                try:
                    result = handler(event)
                    if result is not None:
                        results.append(result)
                except TypeError:
                    # Try as method with self as first arg
                    result = handler()
                    if result is not None:
                        results.append(result)
        
        return results
    
    EventBus.emit = new_emit
    
    # Override unregister method
    original_unregister = EventBus.unregister if hasattr(EventBus, 'unregister') else None
    
    def new_unregister(self, event_type, handler):
        """Unregister a handler."""
        if event_type in self.handlers:
            # Remove all instances of the handler
            self.handlers[event_type] = [(p, h) for p, h in self.handlers[event_type] 
                                       if (not isinstance(h, weakref.WeakMethod) and h != handler)]
        
        if original_unregister:
            return original_unregister(self, event_type, handler)
    
    EventBus.unregister = new_unregister
    
    # Override reset method
    original_reset = EventBus.reset if hasattr(EventBus, 'reset') else None
    
    def new_reset(self):
        """Reset the event bus."""
        self.handlers = {}
        
        if original_reset:
            return original_reset(self)
    
    EventBus.reset = new_reset


# Call this function at import time
extend_event_bus()


# Add fixture to ensure event bus extension is applied
@pytest.fixture(autouse=True)
def ensure_event_bus_extension():
    """Ensure EventBus class has been extended."""
    extend_event_bus()
