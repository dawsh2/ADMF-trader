#!/usr/bin/env python
"""
Fix for the event bus to correctly handle weakref method calls.

This script patches the event bus's emit method to properly handle
calling weakref methods.
"""
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('event_bus_fix.log', mode='w')
    ]
)
logger = logging.getLogger("EventBusFix")

def patch_event_bus_emit():
    """
    Patch the event bus emit method to correctly handle weakref method calls.
    """
    try:
        # Import the event bus module
        from src.core.events.event_bus import EventBus
        import weakref
        import types
        
        # Store the original emit method
        original_emit = EventBus.emit
        
        # Define our fixed emit method
        def fixed_emit(self, event):
            """
            Fixed emit method that correctly handles weakref method calls.
            """
            # Add consumed property if needed
            if not hasattr(event, 'consumed'):
                event.consumed = False

            try:
                event_type = event.get_type()
            except Exception as e:
                logger.error(f"Invalid event object, missing get_type() method: {e}")
                return 0

            handlers_called = 0
            
            # Track event count
            if event_type in self.event_counts:
                self.event_counts[event_type] += 1
            else:
                self.event_counts[event_type] = 1

            logger.debug(f"Emitting {event_type.name} event (ID: {event.get_id()})")
            
            # Process handlers
            if event_type in self.handlers:
                # Make a copy to avoid modification during iteration
                handlers_copy = list(self.handlers[event_type])
                dead_refs = []

                for handler_ref in handlers_copy:
                    # Check if event is consumed
                    if hasattr(event, 'consumed') and event.consumed:
                        logger.debug(f"Skipping handler for {event_type.name}: Event marked as consumed")
                        break
                        
                    try:
                        # Get actual handler from weakref if needed
                        handler = None
                        if isinstance(handler_ref, weakref.WeakMethod):
                            # FIXED: Correctly resolve WeakMethod reference
                            handler = handler_ref()
                            if handler is None:
                                dead_refs.append(handler_ref)
                                continue
                        elif isinstance(handler_ref, weakref.ReferenceType):
                            # Handle regular weakref
                            handler = handler_ref()
                            if handler is None:
                                dead_refs.append(handler_ref)
                                continue
                        else:
                            # Regular strong reference
                            handler = handler_ref

                        # Call the handler with exception handling
                        try:
                            # Call the handler
                            handler(event)
                            handlers_called += 1
                            
                            # Check if event is consumed after handler execution
                            if hasattr(event, 'consumed') and event.consumed:
                                logger.debug(f"Event {event_type.name} consumed by handler")
                                break
                        except Exception as handler_error:
                            logger.error(f"Error in handler {getattr(handler, '__name__', str(handler))}: {handler_error}", 
                                        exc_info=True)
                    except Exception as ref_error:
                        logger.error(f"Error resolving handler reference: {ref_error}")

                # Clean up any dead references
                if dead_refs and event_type in self.handlers:
                    self.handlers[event_type] = [
                        h for h in self.handlers[event_type] 
                        if h not in dead_refs
                    ]
                    logger.debug(f"Cleaned up {len(dead_refs)} dead handler references")

            return handlers_called
        
        # Replace the emit method on the EventBus class
        EventBus.emit = fixed_emit
        
        logger.info("Successfully patched EventBus.emit method")
        return True
    except Exception as e:
        logger.error(f"Failed to patch EventBus.emit method: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = patch_event_bus_emit()
    print(f"Patch {'succeeded' if success else 'failed'}")
