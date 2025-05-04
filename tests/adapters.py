"""
Adapters for enhancing components with safety features for testing.
"""
import logging
import functools
import threading
import time
import uuid
import weakref
from types import MethodType

logger = logging.getLogger(__name__)

class EventBusAdapter:
    """
    Adapter to enhance the EventBus with safety features.
    
    This adapter adds safety checks to prevent common issues:
    - Recursion detection to avoid infinite loops
    - Event count limiting to prevent resource exhaustion
    - Idempotency protection
    - Better weak reference handling
    """
    
    @staticmethod
    def apply(event_bus, max_events=1000, recursion_limit=10, event_timeout=None):
        """
        Apply safety enhancements to an event bus instance.
        
        Args:
            event_bus: The event bus to enhance
            
        Returns:
            The enhanced event bus
        """
        # Add safety attributes with configurable limits
        event_bus._max_events_per_cycle = max_events
        event_bus._current_processing_stack = set()
        event_bus._emission_depth = 0
        event_bus._max_recursion_depth = recursion_limit
        event_bus._cycle_event_counter = {}
        event_bus._event_timeout = event_timeout
        event_bus._event_tracker = None
        
        # Create event tracker if not present
        try:
            from tests.utils.event_tracker import EventTracker
            event_bus._event_tracker = EventTracker()
        except ImportError:
            logger.debug("EventTracker not available - detailed event tracking disabled")
            
        # Store original emit method
        if not hasattr(event_bus, '_original_emit'):
            event_bus._original_emit = event_bus.emit
        
        # Enhance emit method with safety checks
        @functools.wraps(event_bus._original_emit)
        def safe_emit(self, event):
            """Enhanced emit method with safety checks."""
            # Get event ID for tracking
            event_id = event.get_id()
            logger.debug(f"Processing event ID: {event_id}, type: {event.get_type()}")
            
            # Check recursion depth
            self._emission_depth += 1
            if self._emission_depth > self._max_recursion_depth:
                self._emission_depth -= 1
                logger.warning(f"Maximum recursion depth ({self._max_recursion_depth}) exceeded for event: {event_id}")
                return 0
            
            # Check for cyclic processing
            if event_id in self._current_processing_stack:
                self._emission_depth -= 1
                logger.warning(f"Cyclic event processing detected for event ID: {event_id}")
                return 0
            
            # Check event count per type
            event_type = event.get_type()
            self._cycle_event_counter[event_type] = self._cycle_event_counter.get(event_type, 0) + 1
            if self._cycle_event_counter[event_type] > self._max_events_per_cycle:
                self._emission_depth -= 1
                logger.warning(f"Too many events of type {event_type} in one cycle: {self._cycle_event_counter[event_type]}")
                return 0
            
            # Track this event as being processed
            self._current_processing_stack.add(event_id)
            
            # Track timing
            start_time = time.time()
            
            try:
                # Call the original method with timeout if configured
                if self._event_timeout and self._event_timeout > 0:
                    from tests.adapters import EventTimeoutWrapper
                    result = EventTimeoutWrapper.run_with_timeout(
                        lambda: self._original_emit(event),
                        timeout=self._event_timeout
                    )
                else:
                    result = self._original_emit(event)
                    
                # Track success if we have a tracker
                if hasattr(self, '_event_tracker') and self._event_tracker:
                    duration = time.time() - start_time
                    self._event_tracker.track_event(event_type, event_id, duration)
                    
                return result
            except Exception as e:
                logger.error(f"Error in event processing: {e}", exc_info=True)
                
                # Track error if we have a tracker
                if hasattr(self, '_event_tracker') and self._event_tracker:
                    self._event_tracker.track_error(event_type, event_id, e)
                    
                return 0
            finally:
                # Always clean up tracking state
                self._current_processing_stack.remove(event_id)
                self._emission_depth -= 1
        
        # Apply the enhanced method
        event_bus.emit = MethodType(safe_emit, event_bus)
        
        # Also enhance the _process_event method for better handler error handling
        if hasattr(event_bus, '_process_event'):
            original_process = event_bus._process_event
            
            @functools.wraps(original_process)
            def safe_process_event(self, event):
                """Enhanced event processing with better error handling."""
                event_type = event.get_type()
                handlers_called = 0
                
                # If we have no handlers, we're done
                if event_type not in self.handlers:
                    return handlers_called
                
                # Make a copy to avoid modification during iteration
                handlers_copy = list(self.handlers[event_type])
                dead_refs = []
                
                # Process each handler with error protection
                for _, handler_ref in handlers_copy:
                    # Skip if event is consumed
                    if event.is_consumed():
                        break
                    
                    try:
                        # Resolve weak reference if needed
                        handler = None
                        if isinstance(handler_ref, weakref.WeakMethod):
                            handler = handler_ref()
                            if handler is None:
                                dead_refs.append(handler_ref)
                                continue
                        elif isinstance(handler_ref, weakref.ReferenceType):
                            handler = handler_ref()
                            if handler is None:
                                dead_refs.append(handler_ref)
                                continue
                        else:
                            handler = handler_ref
                        
                        # Call the handler with timeout protection if handler is a method
                        if handler is not None:
                            # Handle non-callable objects as a special case
                            if not callable(handler):
                                logger.warning(f"Handler {handler} is not callable")
                                dead_refs.append(handler_ref)
                                continue
                                
                            # Call the handler
                            handler(event)
                            handlers_called += 1
                        
                    except Exception as e:
                        handler_name = getattr(handler, '__name__', str(handler))
                        logger.error(f"Error in handler {handler_name}: {e}", exc_info=True)
                
                # Clean up dead references
                if dead_refs and event_type in self.handlers:
                    self.handlers[event_type] = [
                        h for h in self.handlers[event_type]
                        if h[1] not in dead_refs
                    ]
                
                return handlers_called
            
            # Apply the enhanced method
            event_bus._process_event = MethodType(safe_process_event, event_bus)
        
        # Enhance the reset method to clear safety state too
        original_reset = event_bus.reset
        
        @functools.wraps(original_reset)
        def safe_reset(self):
            """Enhanced reset method that also clears safety state."""
            # Call original reset
            original_reset()
            
            # Reset safety state
            self._emission_depth = 0
            self._current_processing_stack.clear()
            self._cycle_event_counter.clear()
            
            logger.info("EventBus reset complete (with safety state)")
        
        # Apply the enhanced reset method
        event_bus.reset = MethodType(safe_reset, event_bus)
        
        # Add method to get event statistics
        def get_event_stats(self):
            """Get statistics about processed events."""
            if hasattr(self, '_event_tracker') and self._event_tracker:
                return self._event_tracker.get_stats()
            else:
                return {
                    "total_events": sum(self._cycle_event_counter.values()) if hasattr(self, '_cycle_event_counter') else 0,
                    "event_counts": dict(self._cycle_event_counter) if hasattr(self, '_cycle_event_counter') else {},
                    "max_recursion_depth": self._max_recursion_depth if hasattr(self, '_max_recursion_depth') else 10,
                    "max_events_per_cycle": self._max_events_per_cycle if hasattr(self, '_max_events_per_cycle') else 1000
                }
        
        event_bus.get_event_stats = MethodType(get_event_stats, event_bus)
        
        # Silently apply enhancements - no need to log every time
        logger.debug("Applied safety enhancements to EventBus")
        return event_bus

class EventTimeoutWrapper:
    """
    Wrapper to add timeout protection to events.
    """
    
    @staticmethod
    def run_with_timeout(func, timeout=5, *args, **kwargs):
        """
        Run a function with timeout protection.
        
        Args:
            func: Function to run
            timeout: Timeout in seconds
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The function result or raises TimeoutError
        """
        result = {"completed": False, "result": None, "error": None}
        completed = threading.Event()
        
        def run_func():
            try:
                result["result"] = func(*args, **kwargs)
                result["completed"] = True
            except Exception as e:
                result["error"] = e
            finally:
                completed.set()
        
        thread = threading.Thread(target=run_func)
        thread.daemon = True
        thread.start()
        
        if not completed.wait(timeout):
            raise TimeoutError(f"Function timed out after {timeout} seconds")
        
        if result["error"]:
            raise result["error"]
        
        return result["result"]
