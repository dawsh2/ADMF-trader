"""
Event bus implementation for the ADMF-Trader system.

This module provides the core event bus used for all event-based communication,
with features like deduplication, priority-based processing, and event batching.
"""

import time
import logging
import weakref
from typing import Dict, List, Callable, Set, Tuple, Optional, Any
from collections import defaultdict, deque

from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType

logger = logging.getLogger(__name__)

class EventBus:
    """
    Central event bus for publishing and subscribing to events.
    
    Features:
    - Event publication and subscription
    - Deduplication of events
    - Priority-based event handling
    - Event batching for performance
    - Metrics collection
    - Event replay for debugging
    """
    
    def __init__(self, deduplication: bool = True, enable_metrics: bool = False,
                enable_replay: bool = False, metrics_window_size: int = 100):
        """
        Initialize the event bus.
        
        Args:
            deduplication: Whether to enable event deduplication
            enable_metrics: Whether to collect performance metrics
            enable_replay: Whether to enable event replay
            metrics_window_size: Window size for metrics collection
        """
        # Subscriber registry: event_type -> [(priority, handler)]
        self.subscribers: Dict[EventType, List[Tuple[int, Callable]]] = defaultdict(list)
        
        # Deduplication registry: set of processed event keys
        self.processed_keys: Set[str] = set()
        self.deduplication = deduplication
        
        # Event tracking
        self.event_counts: Dict[EventType, int] = defaultdict(int)
        
        # Metrics
        self.enable_metrics = enable_metrics
        self.metrics_window_size = metrics_window_size
        self.metrics: Dict[str, Any] = {}
        if enable_metrics:
            self.metrics = {
                'processing_times': defaultdict(lambda: deque(maxlen=metrics_window_size)),
                'handler_times': defaultdict(lambda: deque(maxlen=metrics_window_size)),
                'events_per_second': defaultdict(float),
                'last_metrics_time': time.time(),
                'events_since_last': defaultdict(int),
            }
        
        # Replay support
        self.enable_replay = enable_replay
        self.event_history = deque(maxlen=1000) if enable_replay else None
        
        # Batch mode support
        self.batch_mode = False
        self.batched_events = []
        
        logger.info(f"EventBus initialized with deduplication={deduplication}, "
                  f"enable_metrics={enable_metrics}, enable_replay={enable_replay}")
                  
    def subscribe(self, event_type: EventType, handler: Callable[[Event], None], 
                 priority: int = 0) -> None:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of events to subscribe to
            handler: Function to call when event occurs
            priority: Priority for this handler (lower number = higher priority)
        """
        # Check if handler is already registered
        for _, existing_handler in self.subscribers[event_type]:
            if existing_handler == handler:
                return
        
        # Use weak references for method objects to prevent memory leaks
        if hasattr(handler, '__self__') and hasattr(handler, '__func__'):
            handler_ref = weakref.WeakMethod(handler)
        else:
            handler_ref = handler
            
        # Add handler with priority
        self.subscribers[event_type].append((priority, handler_ref))
        
        # Sort handlers by priority (lower number = higher priority)
        self.subscribers[event_type].sort(key=lambda x: x[0])
        
        handler_name = getattr(handler, '__name__', str(handler))
        logger.debug(f"Subscribed {handler_name} to {event_type.name} with priority {priority}")
                
    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> bool:
        """
        Unsubscribe from events of a specific type.
        
        Args:
            event_type: Type of events to unsubscribe from
            handler: Handler to unsubscribe
            
        Returns:
            bool: True if handler was unsubscribed, False otherwise
        """
        if event_type not in self.subscribers:
            return False
            
        # Create a new list without the handler
        original_handlers = self.subscribers[event_type]
        filtered_handlers = []
        handler_removed = False
        
        for priority, h in original_handlers:
            # Check if this is the handler to remove
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
        
        # Remove empty subscriber lists
        if not self.subscribers[event_type]:
            del self.subscribers[event_type]
            
        return handler_removed
        
    def publish(self, event: Event) -> int:
        """
        Publish an event to subscribers.
        
        Args:
            event: Event to publish
            
        Returns:
            int: Number of handlers that processed the event
        """
        # Handle batching
        if self.batch_mode:
            self.batched_events.append(event)
            return 0
            
        # Track event for replay if enabled
        if self.enable_replay and self.event_history is not None:
            self.event_history.append(event)
            
        # Perform deduplication if enabled
        if self.deduplication:
            dedup_key = event.get_dedup_key()
            if dedup_key in self.processed_keys:
                logger.debug(f"Skipping duplicate event: {event}")
                return 0
            self.processed_keys.add(dedup_key)
            
        # Start timing if metrics are enabled
        start_time = time.time() if self.enable_metrics else None
        
        # Track the event count
        event_type = event.get_type()
        self.event_counts[event_type] += 1
        
        # If metrics are enabled, track this event
        if self.enable_metrics:
            self.metrics['events_since_last'][event_type] += 1
            
        # If no subscribers, we're done
        if event_type not in self.subscribers:
            return 0
            
        # Process the event
        handlers_called = self._process_event(event, start_time)
        
        # Update metrics
        if self.enable_metrics and start_time is not None:
            self._update_metrics(event_type, time.time() - start_time)
            
        return handlers_called
        
    def _process_event(self, event: Event, start_time: Optional[float] = None) -> int:
        """
        Process an event by calling subscribed handlers.
        
        Args:
            event: Event to process
            start_time: Start time for metrics
            
        Returns:
            int: Number of handlers called
        """
        event_type = event.get_type()
        handlers_called = 0
        
        # Make a copy to avoid modification during iteration
        subscribers_copy = list(self.subscribers[event_type])
        dead_refs = []
        
        logger.debug(f"Processing {event_type.name} event (ID: {event.get_id()})")
        
        # Process each subscriber in priority order
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
                subscriber(event)
                handlers_called += 1
                
                # Track handler metrics if enabled
                if self.enable_metrics and handler_start:
                    handler_time = time.time() - handler_start
                    key = (event_type, handler_id)
                    self.metrics['handler_times'][key].append(handler_time)
                    
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
        
    def _update_metrics(self, event_type: EventType, processing_time: float) -> None:
        """
        Update metrics for event processing.
        
        Args:
            event_type: Type of event processed
            processing_time: Time taken to process the event
        """
        if not self.enable_metrics:
            return
            
        self.metrics['processing_times'][event_type].append(processing_time)
        
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
        
    def reset(self) -> None:
        """Reset the event bus state for a new session."""
        # Keep subscribers but clear all other state
        self.processed_keys.clear()
        self.event_counts.clear()
        
        # Reset metrics
        if self.enable_metrics:
            self.metrics = {
                'processing_times': defaultdict(lambda: deque(maxlen=self.metrics_window_size)),
                'handler_times': defaultdict(lambda: deque(maxlen=self.metrics_window_size)),
                'events_per_second': defaultdict(float),
                'last_metrics_time': time.time(),
                'events_since_last': defaultdict(int),
            }
            
        # Reset replay history
        if self.enable_replay:
            self.event_history = deque(maxlen=1000)
            
        # Reset batch mode
        self.batch_mode = False
        self.batched_events = []
        
        # Clean up dead references in subscribers
        self._clean_subscribers()
        
        logger.info("Event bus reset complete")
        
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
            'processed_keys': len(self.processed_keys),
            'deduplication': self.deduplication,
            'metrics_enabled': self.enable_metrics,
            'replay_enabled': self.enable_replay,
            'batch_mode': self.batch_mode,
            'batched_events': len(self.batched_events) if self.batch_mode else 0
        }
        
        return stats