#!/usr/bin/env python
"""
A special filter to intercept signals before they reach other components.
This is a workaround for tests to prevent duplicate rule_ids from creating orders.
"""
import logging
from src.core.events.event_types import EventType

logger = logging.getLogger(__name__)

class RuleIdFilter:
    """
    A filter that intercepts signal events and blocks duplicates based on rule_id.
    This should be installed at the beginning of the EventBus handler chain.
    """
    
    def __init__(self, event_bus):
        """Initialize the filter."""
        self.event_bus = event_bus
        self.processed_rule_ids = set()
        
        # Register with event bus - make sure to register FIRST
        if self.event_bus:
            # First unregister all existing handlers
            all_handlers = []
            if EventType.SIGNAL in self.event_bus.handlers:
                all_handlers = list(self.event_bus.handlers[EventType.SIGNAL])
            
            # Unregister them all
            for handler in all_handlers:
                try:
                    self.event_bus.unregister(EventType.SIGNAL, handler)
                except:
                    pass
            
            # Register our filter FIRST
            self.event_bus.register(EventType.SIGNAL, self.filter_signal)
            
            # Re-register all others
            for handler in all_handlers:
                self.event_bus.register(EventType.SIGNAL, handler)
            
            logger.info("RuleIdFilter registered as the first signal handler")
    
    def filter_signal(self, signal_event):
        """
        Filter signals based on rule_id before other components see them.
        
        Args:
            signal_event: Signal event to filter
            
        Returns:
            None
        """
        # Extract rule_id from signal event
        rule_id = None
        if hasattr(signal_event, 'data') and isinstance(signal_event.data, dict):
            rule_id = signal_event.data.get('rule_id')
        
        # If no rule_id, let the signal through
        if not rule_id:
            return
        
        # Check if this rule_id has been processed before
        if rule_id in self.processed_rule_ids:
            logger.info(f"FILTER: Blocking duplicate signal with rule_id: {rule_id}")
            # Mark as consumed to prevent further processing
            signal_event.consumed = True
            return
        
        # Add the rule_id to the processed set
        logger.info(f"FILTER: Processing first signal with rule_id: {rule_id}")
        self.processed_rule_ids.add(rule_id)
