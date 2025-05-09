"""
Enhanced pub/sub event bus with native deduplication for ADMF-Trader.

This implementation provides a full-featured pub/sub event system with:
1. Clear publish/subscribe terminology
2. Native deduplication with configurable strategies
3. Priority-based subscriber processing
4. Event batching for improved performance
5. Comprehensive metrics for monitoring and debugging
6. Event replay capabilities for debugging
7. Backward compatibility with previous API
"""
import logging
import time
import uuid
import weakref
import statistics
from typing import Dict, List, Set, Tuple, Callable, Any, Optional, Union
from datetime import datetime
from collections import defaultdict, deque

from src.core.events.event_types import EventType, Event
from src.core.events.event_adapter import patch_event_methods

logger = logging.getLogger(__name__)

class EventBus:
    """
    Enhanced event bus implementing the pub/sub pattern with advanced features.
    
    Features:
    - Clear publish/subscribe terminology
    - Native deduplication with configurable strategies
    - Priority-based subscriber processing
    - Event batching for improved performance
    - Comprehensive metrics for monitoring and debugging
    - Event replay capabilities for debugging
    - Backward compatibility with previous API
    """
    
    # Deduplication strategies
    DEDUP_NONE = "none"         # No deduplication
    DEDUP_ID = "id"             # Deduplicate by event ID only
    DEDUP_RULE = "rule"         # Deduplicate by rule_id for signals, order_id for orders/fills
    DEDUP_FULL = "full"         # Full deduplication based on event type rules
    
    # Default priorities
    DEFAULT_PRIORITY = 0
    HIGH_PRIORITY = -100        # Lower number = higher priority
    CRITICAL_PRIORITY = -1000
    
    def __init__(self, 
                 deduplication_strategy=DEDUP_FULL,
                 enable_metrics=False, 
                 enable_replay=False,
                 metrics_window_size=100,
                 max_event_history=1000):
        """
        Initialize the event bus.
        
        Args:
            deduplication_strategy: Strategy for deduplication (DEDUP_*)
            enable_metrics: Whether to collect performance metrics
            enable_replay: Whether to enable event replay
            metrics_window_size: Number of events to keep metrics for
            max_event_history: Maximum number of events to keep for replay
        """
        # Apply event method patches for compatibility
        patch_event_methods()
        
        # Core subscriber registry - event_type -> [(priority, subscriber)]
        self.subscribers = {}
        
        # Backward compatibility - handlers is an alias for subscribers
        self.handlers = self.subscribers
        
        # Deduplication tracking
        self.deduplication_strategy = deduplication_strategy
        self.processed_events = {}  # event_type -> {dedup_key: event_info}
        
        # Event tracking
        self.event_counts = defaultdict(int)
        self.event_registry = {}  # event_id -> event_info
        
        # Metrics
        self.enable_metrics = enable_metrics
        self.metrics_window_size = metrics_window_size
        self.metrics = {
            'processing_times': defaultdict(lambda: deque(maxlen=metrics_window_size)),
            'handler_times': defaultdict(lambda: deque(maxlen=metrics_window_size)),
            'events_per_second': defaultdict(float),
            'last_metrics_time': time.time(),
            'events_since_last': defaultdict(int),
        }
        
        # Replay support
        self.enable_replay = enable_replay
        self.max_event_history = max_event_history
        self.event_history = deque(maxlen=max_event_history) if enable_replay else None
        
        # Batching support
        self.batch_mode = False
        self.batched_events = []
        
        logger.info(f"EventBus initialized with deduplication_strategy={deduplication_strategy}, "
                   f"enable_metrics={enable_metrics}, enable_replay={enable_replay}")
    
    #-----------------------------------------------------------------------
    # Core Pub/Sub Methods
    #-----------------------------------------------------------------------
    
    def subscribe(self, event_type: EventType, handler: Callable, priority: int = DEFAULT_PRIORITY) -> None:
        """
        Subscribe a handler to an event type with priority.
        
        Args:
            event_type: Event type to subscribe to
            handler: Handler function or method
            priority: Handler priority (lower number = higher priority)
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
            
        # Check if handler is already registered to prevent duplicates
        for _, existing_handler in self.subscribers[event_type]:
            if existing_handler == handler:
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
        self.subscribers[event_type].append((priority, handler_ref))
        
        # Sort handlers by priority (lower number = higher priority)
        self.subscribers[event_type].sort(key=lambda x: x[0])
        
        handler_name = getattr(handler, '__name__', str(handler))
        logger.debug(f"Subscribed {handler_name} to {event_type.name} with priority {priority}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable) -> bool:
        """
        Unsubscribe a handler from an event type.
        
        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to unsubscribe
            
        Returns:
            bool: True if handler was unsubscribed, False otherwise
        """
        if event_type not in self.subscribers:
            return False

        # Create a new list without the handler to avoid modifying during iteration
        original_handlers = self.subscribers[event_type]
        filtered_handlers = []
        handler_removed = False
        
        for priority, h in original_handlers:
            # Check direct equality or resolve weak reference
            keep = True
            
            if h == handler:
                keep = False
                handler_removed = True
            elif hasattr(h, '__call__') and isinstance(h, weakref.ReferenceType):
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
        self.subscribers[event_type] = filtered_handlers
        
        # If all handlers are removed, delete the event type entry
        if not self.subscribers[event_type]:
            del self.subscribers[event_type]
                
        return handler_removed
    
    def publish(self, event: Event) -> int:
        """
        Publish an event to subscribers with built-in deduplication.
        
        Args:
            event: Event to publish
            
        Returns:
            int: Number of handlers that processed the event
        """
        # Handle batching
        if self.batch_mode:
            self.batched_events.append(event)
            return 0
            
        # Record event for replay if enabled
        if self.enable_replay and self.event_history is not None:
            self.event_history.append(event)
            
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
            
        # Metrics: Record event start time
        start_time = time.time() if self.enable_metrics else None
            
        # Get deduplication key if available and enabled
        dedup_key = None
        if self.deduplication_strategy != self.DEDUP_NONE:
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
        handlers_called = self._process_event(event, start_time)
        
        # Record as processed if we have a dedup key
        if dedup_key:
            self._record_processed(event_type, dedup_key, event)
            
        # Update metrics
        if self.enable_metrics:
            self._update_metrics(event_type, time.time() - start_time)
            
        return handlers_called
        
    #-----------------------------------------------------------------------
    # Batching Methods
    #-----------------------------------------------------------------------
    
    def start_batch(self) -> None:
        """Start batching events for later processing."""
        self.batch_mode = True
        self.batched_events = []
        logger.debug("Event batching started")
    
    def end_batch(self) -> int:
        """
        Process all batched events and return to normal mode.
        
        Returns:
            int: Number of events processed
        """
        self.batch_mode = False
        events = self.batched_events
        self.batched_events = []
        
        logger.debug(f"Processing {len(events)} batched events")
        
        # Process all batched events
        total_handled = 0
        for event in events:
            total_handled += self.publish(event)
        
        return total_handled
    
    def discard_batch(self) -> int:
        """
        Discard all batched events without processing.
        
        Returns:
            int: Number of events discarded
        """
        self.batch_mode = False
        count = len(self.batched_events)
        self.batched_events = []
        
        logger.debug(f"Discarded {count} batched events")
        return count
    
    #-----------------------------------------------------------------------
    # Replay Methods
    #-----------------------------------------------------------------------
    
    def enable_replay_recording(self, max_events=None) -> None:
        """
        Start recording events for replay.
        
        Args:
            max_events: Maximum number of events to store (None for default)
        """
        self.enable_replay = True
        if max_events is not None:
            self.max_event_history = max_events
            
        self.event_history = deque(maxlen=self.max_event_history)
        logger.info(f"Event replay recording enabled (max {self.max_event_history} events)")
    
    def disable_replay_recording(self) -> None:
        """Stop recording events for replay."""
        self.enable_replay = False
        logger.info("Event replay recording disabled")
    
    def clear_replay_history(self) -> int:
        """
        Clear the replay event history.
        
        Returns:
            int: Number of events cleared
        """
        count = len(self.event_history) if self.event_history else 0
        self.event_history = deque(maxlen=self.max_event_history) if self.enable_replay else None
        logger.debug(f"Cleared replay history ({count} events)")
        return count
    
    def replay_events(self, start_index=0, end_index=None) -> int:
        """
        Replay recorded events from start to end index.
        
        Args:
            start_index: Starting event index
            end_index: Ending event index (None for all remaining)
            
        Returns:
            int: Number of events replayed
        """
        if not self.event_history:
            logger.warning("No events to replay")
            return 0
            
        end = end_index or len(self.event_history)
        replay_count = 0
        
        # Temporarily disable recording during replay
        original_recording = self.enable_replay
        self.enable_replay = False
        
        # Temporary flag for replay
        self._in_replay_mode = True
        
        logger.info(f"Replaying events from {start_index} to {end}")
        
        # Process each event in the range
        for i in range(start_index, min(end, len(self.event_history))):
            event = self.event_history[i]
            self.publish(event)
            replay_count += 1
            
        # Restore original settings
        self.enable_replay = original_recording
        self._in_replay_mode = False
        
        logger.info(f"Replayed {replay_count} events")
        return replay_count
    
    def get_replay_history_info(self) -> Dict[str, Any]:
        """
        Get information about the replay history.
        
        Returns:
            Dict: Information about recorded events
        """
        if not self.event_history:
            return {"enabled": self.enable_replay, "count": 0}
            
        # Count event types
        type_counts = defaultdict(int)
        for event in self.event_history:
            type_counts[event.get_type().name] += 1
            
        # Get time range if available
        start_time = None
        end_time = None
        
        for event in self.event_history:
            timestamp = getattr(event, 'timestamp', None)
            if timestamp:
                if start_time is None or timestamp < start_time:
                    start_time = timestamp
                if end_time is None or timestamp > end_time:
                    end_time = timestamp
        
        return {
            "enabled": self.enable_replay,
            "count": len(self.event_history),
            "max_size": self.max_event_history,
            "type_counts": dict(type_counts),
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            }
        }
    
    #-----------------------------------------------------------------------
    # Metrics Methods
    #-----------------------------------------------------------------------
    
    def enable_metrics_collection(self, window_size=None) -> None:
        """
        Enable metrics collection.
        
        Args:
            window_size: Size of the sliding window for metrics
        """
        self.enable_metrics = True
        if window_size is not None:
            self.metrics_window_size = window_size
            
        # Initialize/reset metrics
        self.metrics = {
            'processing_times': defaultdict(lambda: deque(maxlen=self.metrics_window_size)),
            'handler_times': defaultdict(lambda: deque(maxlen=self.metrics_window_size)),
            'events_per_second': defaultdict(float),
            'last_metrics_time': time.time(),
            'events_since_last': defaultdict(int),
        }
        
        logger.info(f"Metrics collection enabled (window size: {self.metrics_window_size})")
    
    def disable_metrics_collection(self) -> None:
        """Disable metrics collection."""
        self.enable_metrics = False
        logger.info("Metrics collection disabled")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get collected performance metrics.
        
        Returns:
            Dict: Performance metrics
        """
        if not self.enable_metrics:
            return {"metrics_disabled": True}
            
        # Calculate averages
        avg_processing_times = {}
        for event_type, times in self.metrics['processing_times'].items():
            if times:
                avg_processing_times[event_type.name] = {
                    'mean': statistics.mean(times),
                    'median': statistics.median(times) if len(times) > 0 else 0,
                    'min': min(times) if times else 0,
                    'max': max(times) if times else 0,
                    'count': len(times)
                }
        
        # Calculate rates
        now = time.time()
        time_diff = now - self.metrics['last_metrics_time']
        
        if time_diff > 0.1:  # Only recalculate if enough time has passed
            for event_type, count in self.metrics['events_since_last'].items():
                if count > 0:
                    self.metrics['events_per_second'][event_type] = count / time_diff
                    
            # Reset counters
            self.metrics['last_metrics_time'] = now
            self.metrics['events_since_last'] = defaultdict(int)
        
        # Build result
        return {
            'event_counts': {event_type.name: count for event_type, count in self.event_counts.items()},
            'processing_times_ms': {k: {m: v * 1000 for m, v in metrics.items()}  # Convert to ms
                              for k, metrics in avg_processing_times.items()},
            'events_per_second': {event_type.name: rate 
                               for event_type, rate in self.metrics['events_per_second'].items()},
            'total_events': sum(self.event_counts.values()),
            'window_size': self.metrics_window_size
        }
    
    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        if self.enable_metrics:
            self.enable_metrics_collection(self.metrics_window_size)
            
        logger.debug("Metrics reset")
    
    #-----------------------------------------------------------------------
    # System Methods
    #-----------------------------------------------------------------------
    
    def reset(self) -> None:
        """Reset the event bus state for a new session."""
        # Keep subscribers but clear all other state
        self.processed_events.clear()
        self.event_counts.clear()
        self.event_registry.clear()
        
        # Reset metrics
        if self.enable_metrics:
            self.reset_metrics()
            
        # Reset replay history
        if self.enable_replay:
            self.clear_replay_history()
        
        # Clean up dead references in subscribers
        self._clean_subscribers()
        
        logger.info("Event bus reset complete")
    
    def has_subscribers(self, event_type: EventType) -> bool:
        """
        Check if there are subscribers for an event type.
        
        Args:
            event_type: Event type to check
            
        Returns:
            bool: True if subscribers exist, False otherwise
        """
        return event_type in self.subscribers and len(self.subscribers[event_type]) > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics.
        
        Returns:
            Dict: Event bus statistics
        """
        # Get live subscriber counts (resolving weak references)
        live_subscribers = {}
        
        for event_type, subscribers in self.subscribers.items():
            live_count = 0
            for _, sub_ref in subscribers:
                if isinstance(sub_ref, weakref.ReferenceType):
                    if sub_ref() is not None:
                        live_count += 1
                else:
                    live_count += 1
                    
            live_subscribers[event_type.name] = live_count
        
        # Build stats
        stats = {
            'event_counts': {event_type.name: count for event_type, count in self.event_counts.items()},
            'subscriber_counts': live_subscribers,
            'processed_events': {event_type.name: len(events) for event_type, events in self.processed_events.items()},
            'registry_size': len(self.event_registry),
            'deduplication_strategy': self.deduplication_strategy,
            'metrics_enabled': self.enable_metrics,
            'replay_enabled': self.enable_replay,
            'replay_history_size': len(self.event_history) if self.event_history else 0,
            'batch_mode': self.batch_mode,
            'batched_events': len(self.batched_events) if self.batch_mode else 0
        }
        
        # Include metrics if enabled
        if self.enable_metrics:
            stats['metrics'] = self.get_metrics()
            
        return stats
    
    #-----------------------------------------------------------------------
    # Backward Compatibility Methods
    #-----------------------------------------------------------------------
    
    def emit(self, event: Event) -> int:
        """
        Backward-compatible wrapper for publish().
        
        Args:
            event: Event to emit
            
        Returns:
            int: Number of handlers that processed the event
        """
        return self.publish(event)
    
    def register(self, event_type: EventType, handler: Callable, priority: int = 0) -> None:
        """
        Backward-compatible wrapper for subscribe().
        
        Args:
            event_type: Event type to handle
            handler: Handler function or method
            priority: Handler priority (lower number = higher priority, default=0)
        """
        return self.subscribe(event_type, handler, priority)
    
    def unregister(self, event_type: EventType, handler: Callable) -> bool:
        """
        Backward-compatible wrapper for unsubscribe().
        
        Args:
            event_type: Event type to unregister from
            handler: Handler to unregister
            
        Returns:
            bool: True if handler was unregistered, False otherwise
        """
        return self.unsubscribe(event_type, handler)
    
    def has_handlers(self, event_type: EventType) -> bool:
        """
        Backward-compatible wrapper for has_subscribers().
        
        Args:
            event_type: Event type to check
            
        Returns:
            bool: True if handlers exist, False otherwise
        """
        return self.has_subscribers(event_type)
    
    def get_event_counts(self) -> Dict[EventType, int]:
        """
        Get event counts by type.
        
        Returns:
            Dict: Event counts by event type
        """
        return dict(self.event_counts)
    
    def get_event_by_id(self, event_id: str) -> Optional[Any]:
        """
        Get an event by its ID.
        
        Args:
            event_id: Event ID to retrieve
            
        Returns:
            Optional[Any]: Event if found, None otherwise
        """
        return self.event_registry.get(event_id)
        
    #-----------------------------------------------------------------------
    # Internal Helper Methods
    #-----------------------------------------------------------------------
    
    def _get_dedup_key(self, event: Event) -> Optional[str]:
        """
        Extract deduplication key based on strategy.
        
        Args:
            event: Event to extract key from
            
        Returns:
            Optional[str]: Deduplication key if available, None otherwise
        """
        # Handle different deduplication strategies
        if self.deduplication_strategy == self.DEDUP_NONE:
            return None
            
        # ID-based deduplication (simplest)
        if self.deduplication_strategy == self.DEDUP_ID:
            return event.get_id()
            
        # Extract data if available for rule-based deduplication
        data = getattr(event, 'data', None)
        if not data or not isinstance(data, dict):
            return event.get_id()  # Fall back to ID
            
        event_type = event.get_type()
        
        # Rule-based or full deduplication strategies
        if self.deduplication_strategy in (self.DEDUP_RULE, self.DEDUP_FULL):
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
        
        # Default: use event ID
        return event.get_id()
        
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
            'event_id': event.get_id(),
            'timestamp': getattr(event, 'timestamp', datetime.now()),
            'data': getattr(event, 'data', {}).copy() if hasattr(event, 'data') else {}
        }
        
    def _track_event(self, event: Event) -> None:
        """
        Track an event in the registry.
        
        Args:
            event: Event to track
        """
        # Get or create event ID
        event_id = event.get_id()
            
        # Store in registry with timestamp and consumption state
        self.event_registry[event_id] = {
            'type': event.get_type(),
            'timestamp': getattr(event, 'timestamp', datetime.now()),
            'data': getattr(event, 'data', {}).copy() if hasattr(event, 'data') else {},
            'consumed': event.is_consumed()
        }
        
    def _process_event(self, event: Event, start_time=None) -> int:
        """
        Process an event with registered subscribers.
        
        Args:
            event: Event to process
            start_time: Start time for metrics (if enabled)
            
        Returns:
            int: Number of handlers called
        """
        event_type = event.get_type()
        handlers_called = 0
        
        # Track event count
        self.event_counts[event_type] += 1
        
        # If we have metrics enabled, track this event
        if self.enable_metrics:
            self.metrics['events_since_last'][event_type] += 1
        
        # If we have no subscribers, we're done
        if event_type not in self.subscribers:
            return handlers_called
            
        # Make a copy to avoid modification during iteration
        subscribers_copy = list(self.subscribers[event_type])
        dead_refs = []
        
        logger.debug(f"Processing {event_type.name} event (ID: {event.get_id()})")
        
        # Process each subscriber
        for priority, subscriber_ref in subscribers_copy:
            # Check if event is consumed
            if event.is_consumed():
                logger.debug(f"Event {event_type.name} consumed, skipping remaining subscribers")
                break
                
            try:
                # Resolve weak reference if needed
                subscriber = None
                handler_id = id(subscriber_ref)
                handler_start = time.time() if self.enable_metrics else None
                
                if isinstance(subscriber_ref, weakref.WeakMethod):
                    subscriber = subscriber_ref()
                    if subscriber is None:
                        dead_refs.append(subscriber_ref)
                        continue
                elif isinstance(subscriber_ref, weakref.ReferenceType):
                    subscriber = subscriber_ref()
                    if subscriber is None:
                        dead_refs.append(subscriber_ref)
                        continue
                else:
                    subscriber = subscriber_ref
                    
                # Call the subscriber and count it
                try:
                    subscriber(event)
                    handlers_called += 1
                    
                    # Track handler metrics if enabled
                    if self.enable_metrics and handler_start:
                        handler_time = time.time() - handler_start
                        key = (event_type, handler_id)
                        self.metrics['handler_times'][key].append(handler_time)
                        
                except TypeError as te:
                    if "missing 1 required positional argument" in str(te):
                        # Log and skip handler with wrong signature
                        handler_name = getattr(subscriber, '__name__', str(subscriber))
                        logger.error(f"Handler {handler_name} has incorrect signature: {te}")
                    else:
                        # Re-raise other TypeError exceptions
                        raise
                
            except Exception as e:
                handler_name = getattr(subscriber, '__name__', str(subscriber))
                logger.error(f"Error in handler {handler_name}: {e}", exc_info=True)
                
        # Clean up dead references
        if dead_refs and event_type in self.subscribers:
            self.subscribers[event_type] = [
                s for s in self.subscribers[event_type]
                if s[1] not in dead_refs
            ]
            
        return handlers_called
        
    def _update_metrics(self, event_type, processing_time):
        """
        Update metrics for event processing.
        
        Args:
            event_type: Type of event processed
            processing_time: Time taken to process
        """
        if not self.enable_metrics:
            return
            
        # Add to processing times deque (limited by window size)
        self.metrics['processing_times'][event_type].append(processing_time)
    
    def _clean_subscribers(self) -> None:
        """Clean up dead subscriber references."""
        for event_type in list(self.subscribers.keys()):
            dead_refs = []
            
            # Check each subscriber
            for priority, sub_ref in self.subscribers[event_type]:
                if isinstance(sub_ref, weakref.ReferenceType):
                    # Try to resolve the reference
                    subscriber = sub_ref()
                    if subscriber is None:
                        dead_refs.append(sub_ref)
                        
            # Remove dead references
            if dead_refs:
                self.subscribers[event_type] = [
                    s for s in self.subscribers[event_type]
                    if s[1] not in dead_refs
                ]
                
            # Remove empty subscriber lists
            if not self.subscribers[event_type]:
                del self.subscribers[event_type]
