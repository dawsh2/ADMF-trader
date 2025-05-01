#!/usr/bin/env python
"""
Enhanced version of RuleIdFilter to provide stronger deduplication.

This filter not only marks duplicate signals as consumed but also
completely blocks them from reaching other components by returning
early from the event bus emit method.
"""
import logging
import functools
from src.core.events.event_types import EventType

logger = logging.getLogger(__name__)

class EnhancedRuleIdFilter:
    """
    An enhanced filter that completely blocks duplicate signals based on rule_id.
    This should be installed at the beginning of the EventBus handler chain.
    """
    
    def __init__(self, event_bus):
        """Initialize the filter."""
        self.event_bus = event_bus
        self.processed_rule_ids = set()
        
        # Save the original emit method
        self.original_emit = event_bus.emit
        
        # Replace the emit method with our wrapped version
        event_bus.emit = self._wrap_emit(event_bus.emit)
        
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
                if handler != self.filter_signal:  # avoid duplicates
                    self.event_bus.register(EventType.SIGNAL, handler)
            
            logger.info("EnhancedRuleIdFilter registered as the first signal handler")
    
    def _wrap_emit(self, original_emit):
        """
        Wrap the event bus emit method to check signals before emitting.
        
        Args:
            original_emit: Original emit method to wrap
            
        Returns:
            Wrapped emit method
        """
        @functools.wraps(original_emit)
        def wrapped_emit(event, *args, **kwargs):
            # Only intercept signal events
            if hasattr(event, 'get_type') and event.get_type() == EventType.SIGNAL:
                # Extract rule_id from signal event
                rule_id = None
                if hasattr(event, 'data') and isinstance(event.data, dict):
                    rule_id = event.data.get('rule_id')
                
                # If this is a duplicate rule_id, completely block the event
                if rule_id and rule_id in self.processed_rule_ids:
                    logger.info(f"EMIT BLOCKED: Duplicate signal with rule_id: {rule_id}")
                    # Short-circuit and don't emit the event at all
                    return 0
            
            # For all other events, proceed with original emit
            return original_emit(event, *args, **kwargs)
        
        return wrapped_emit
    
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
    
    def reset(self):
        """Reset the filter state."""
        self.processed_rule_ids.clear()
        logger.info("EnhancedRuleIdFilter reset")
        
    def restore_emit(self):
        """Restore the original emit method."""
        if hasattr(self, 'original_emit') and self.original_emit:
            try:
                self.event_bus.emit = self.original_emit
                logger.info("Original emit method restored")
            except Exception as e:
                logger.error(f"Error restoring emit method: {e}")
        else:
            logger.warning("No original emit method to restore")
