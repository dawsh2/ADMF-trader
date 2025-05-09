"""
Event bus with native deduplication for ADMF-Trader.

This implementation handles both signal deduplication and order tracking
as an integral part of the event bus, eliminating the need for separate
deduplication components.
"""
import logging
import weakref
import uuid
from typing import Dict, List, Set, Tuple, Callable, Any, Optional, Union

from src.core.events.event_types import EventType, Event

logger = logging.getLogger(__name__)

class EventBus:
    """
    Event bus with built-in deduplication and event tracking.
    
    Features:
    - Native deduplication of events by rule_id and order_id
    - Priority-based handler registration
    - Handler cleanup for dead references
    - Event consumption tracking
    - Detailed event statistics
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self.handlers: Dict[EventType, List[Tuple[int, Any]]] = {}
        self.processed_events: Dict[EventType, Dict[str, Any]] = {}
        self.event_counts: Dict[EventType, int] = {}
        self.event_registry: Dict[str, Any] = {}
        
    def emit(self, event: Event) -> int:
        """
        Emit an event to registered handlers with built-in deduplication.
        
        Args:
            event: Event to emit
            
        Returns:
            int: Number of handlers that processed the event
        """
        # Process event tracking and consumption handling
        event_id = event.get_id() 
        
        # Check if event is already consumed
        if event.is_consumed():
            logger.debug(f"Skipping already consumed event with ID: {event_id}")
            return 0
            
        try:
            event_type = event.get_type()
        except Exception as e:
            logger.error(f"Invalid event object, missing get_type() method: {e}")
            return 0
            
        # Get deduplication key if available
        dedup_key = self._get_dedup_key(event)
        
        # Check for duplicate if we have a key
        if dedup_key and self._is_duplicate(event_type, dedup_key):
            # Use lower log level to reduce noise
            logger.debug(f"BLOCKED: Duplicate event {event_type.name} with key: {dedup_key}")
            # Only print all dedup keys in DEBUG mode to reduce log verbosity
            if logger.getEffectiveLevel() <= logging.DEBUG and event_type in self.processed_events:
                keys = sorted(list(self.processed_events[event_type].keys()))
                logger.debug(f"All dedup keys for {event_type.name}: {keys}")
            return 0
            
        # Track the event
        self._track_event(event)
            
        # Process the event
        handlers_called = self._process_event(event)
        
        # Record as processed if we have a dedup key
        if dedup_key:
            self._record_processed(event_type, dedup_key, event)
            
        return handlers_called
        
    def register(self, event_type: EventType, handler: Callable, priority: int = 0) -> None:
        """
        Register a handler for an event type with priority.
        
        Args:
            event_type: Event type to handle
            handler: Handler function or method
            priority: Handler priority (lower number = higher priority, default=0)
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
            
        # Check if handler is already registered to prevent duplicates
        for _, existing_handler in self.handlers[event_type]:
            if existing_handler == handler:
                # Skip if already registered
                return
            
        # Use weak reference for method objects to prevent memory leaks
        if hasattr(handler, '__self__') and hasattr(handler, '__func__'):
            handler_ref = weakref.WeakMethod(handler)
        elif not hasattr(handler, '__call__'):
            logger.warning(f"Handler {handler} is not callable, ignoring")
            return
        else:
            handler_ref = handler
            
        # Add handler with priority
        self.handlers[event_type].append((priority, handler_ref))
        
        # Sort handlers by priority (lower number = higher priority)
        self.handlers[event_type].sort(key=lambda x: x[0])
        
    def unregister(self, event_type: EventType, handler: Callable) -> bool:
        """
        Unregister a handler for an event type.
        
        Args:
            event_type: Event type to unregister from
            handler: Handler to unregister
            
        Returns:
            bool: True if handler was unregistered, False otherwise
        """
        if event_type not in self.handlers:
            return False

        # Create a new list without the handler to avoid modifying during iteration
        original_handlers = self.handlers[event_type]
        filtered_handlers = []
        handler_removed = False
        
        for priority, h in original_handlers:
            # Check direct equality or resolve weak reference
            keep = True
            
            if h == handler:
                keep = False
                handler_removed = True
            elif hasattr(h, '__call__') and h() is not None:
                try:
                    if h() == handler:
                        keep = False
                        handler_removed = True
                except Exception:
                    # If we can't resolve the reference, keep it
                    pass
            
            if keep:
                filtered_handlers.append((priority, h))
        
        # Update handlers list
        self.handlers[event_type] = filtered_handlers
        
        # If all handlers are removed, delete the event type entry
        if not self.handlers[event_type]:
            del self.handlers[event_type]
                
        return handler_removed
        
    def reset(self) -> None:
        """Reset the event bus state for a new backtest."""
        self.processed_events.clear()
        self.event_counts.clear()
        self.event_registry.clear()
        
        # Clean up dead references in handlers
        self._clean_handlers()
        
        logger.info("Event bus reset complete")
        
    def get_event_counts(self) -> Dict[EventType, int]:
        """
        Get event counts by type.
        
        Returns:
            Dict: Event counts by event type
        """
        return self.event_counts.copy()
        
    def get_event_by_id(self, event_id: str) -> Optional[Any]:
        """
        Get an event by its ID.
        
        Args:
            event_id: Event ID to retrieve
            
        Returns:
            Optional[Any]: Event if found, None otherwise
        """
        return self.event_registry.get(event_id)
        
    def has_handlers(self, event_type: EventType) -> bool:
        """
        Check if there are handlers registered for an event type.
        
        Args:
            event_type: Event type to check
            
        Returns:
            bool: True if handlers exist, False otherwise
        """
        return event_type in self.handlers and len(self.handlers[event_type]) > 0
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics.
        
        Returns:
            Dict: Event bus statistics
        """
        stats = {
            'event_counts': {event_type.name: count for event_type, count in self.event_counts.items()},
            'handler_counts': {event_type.name: len(handlers) for event_type, handlers in self.handlers.items()},
            'processed_events': {event_type.name: len(events) for event_type, events in self.processed_events.items()},
            'registry_size': len(self.event_registry)
        }
        return stats
        
    def _get_dedup_key(self, event: Event) -> Optional[str]:
        """
        Extract deduplication key from event.
        
        Args:
            event: Event to extract key from
            
        Returns:
            Optional[str]: Deduplication key if available, None otherwise
        """
        # Extract data if available
        data = getattr(event, 'data', None)
        if not data or not isinstance(data, dict):
            return None
            
        event_type = event.get_type()
        
        # Handle specific event types
        if event_type == EventType.SIGNAL:
            # Use rule_id for signal deduplication
            rule_id = data.get('rule_id')
            if rule_id:
                logger.debug(f"Signal dedup key (rule_id): {rule_id}")
            return rule_id
        elif event_type == EventType.ORDER:
            # Use rule_id or order_id for order deduplication
            rule_id = data.get('rule_id')
            order_id = data.get('order_id')
            
            dedup_key = rule_id or order_id
            if dedup_key:
                logger.debug(f"Order dedup key: {dedup_key}")
            return dedup_key
        elif event_type == EventType.FILL:
            # Use order_id for fill deduplication
            order_id = data.get('order_id')
            if order_id:
                logger.debug(f"Fill dedup key (order_id): {order_id}")
            return order_id
            
        # Default case - use event ID if available
        event_id = getattr(event, 'id', None)
        if event_id:
            logger.debug(f"Default dedup key (event_id): {event_id}")
        return event_id
        
    def _is_duplicate(self, event_type: EventType, dedup_key: str) -> bool:
        """
        Check if an event is a duplicate.
        
        Args:
            event_type: Event type to check
            dedup_key: Deduplication key to check
            
        Returns:
            bool: True if event is a duplicate, False otherwise
        """
        if event_type not in self.processed_events:
            return False
            
        # Check if key exists in processed events
        return dedup_key in self.processed_events[event_type]
        
    def _record_processed(self, event_type: EventType, dedup_key: str, event: Event) -> None:
        """
        Record an event as processed.
        
        Args:
            event_type: Event type
            dedup_key: Deduplication key
            event: Event to record
        """
        if event_type not in self.processed_events:
            self.processed_events[event_type] = {}
            
        # Store the event with its key
        self.processed_events[event_type][dedup_key] = {
            'event_id': getattr(event, 'id', str(uuid.uuid4())),
            'timestamp': getattr(event, 'timestamp', None),
            'data': getattr(event, 'data', {}).copy() if hasattr(event, 'data') else {}
        }
        
    def _track_event(self, event: Event) -> None:
        """
        Track an event in the registry.
        
        Args:
            event: Event to track
        """
        # Get or create event ID
        event_id = getattr(event, 'id', None)
        if not event_id:
            event_id = str(uuid.uuid4())
            event.id = event_id
            
        # Store in registry with timestamp and consumption state
        self.event_registry[event_id] = {
            'type': event.get_type(),
            'timestamp': getattr(event, 'timestamp', None),
            'data': getattr(event, 'data', {}).copy() if hasattr(event, 'data') else {},
            'consumed': event.is_consumed()
        }
        
    def _process_event(self, event: Event) -> int:
        """
        Process an event with registered handlers.
        
        Args:
            event: Event to process
            
        Returns:
            int: Number of handlers called
        """
        event_type = event.get_type()
        handlers_called = 0
        
        # Track event count
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        # If we have no handlers, we're done
        if event_type not in self.handlers:
            return handlers_called
            
        # Make a copy to avoid modification during iteration
        handlers_copy = list(self.handlers[event_type])
        dead_refs = []
        
        logger.debug(f"Processing {event_type.name} event (ID: {getattr(event, 'id', 'unknown')})")
        
        # Process each handler
        for _, handler_ref in handlers_copy:
            # Check if event is consumed
            if event.is_consumed():
                logger.debug(f"Event {event_type.name} consumed, skipping remaining handlers")
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
                    
                # Call the handler and only count it once
                try:
                    handler(event)
                    handlers_called += 1
                except TypeError as te:
                    if "missing 1 required positional argument" in str(te):
                        # Log and skip handler with wrong signature
                        logger.error(f"Handler {handler.__name__ if hasattr(handler, '__name__') else handler} has incorrect signature: {te}")
                    else:
                        # Re-raise other TypeError exceptions
                        raise
                
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
        
    def _clean_handlers(self) -> None:
        """Clean up dead handler references."""
        for event_type in list(self.handlers.keys()):
            dead_refs = []
            
            # Check each handler
            for priority, handler_ref in self.handlers[event_type]:
                if isinstance(handler_ref, weakref.WeakMethod) or isinstance(handler_ref, weakref.ReferenceType):
                    # Try to resolve the reference
                    handler = handler_ref()
                    if handler is None:
                        dead_refs.append(handler_ref)
                        
            # Remove dead references
            if dead_refs:
                self.handlers[event_type] = [
                    h for h in self.handlers[event_type]
                    if h[1] not in dead_refs
                ]
                
            # Remove empty handler lists
            if not self.handlers[event_type]:
                del self.handlers[event_type]
