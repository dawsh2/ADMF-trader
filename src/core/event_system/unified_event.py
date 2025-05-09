"""
Unified Event class for the ADMF-Trader system.

This module provides a single, consistent Event class implementation
that works across the entire codebase, replacing the multiple
inconsistent implementations that existed previously.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum, auto

# Re-export EventType to maintain imports
from src.core.event_system.event_types import EventType


class Event:
    """
    Base class for all events in the system.
    
    This implementation is backward compatible with both the class-based
    implementation in event_system/event.py and the dataclass-based
    implementation in events/event_types.py.
    """
    
    def __init__(self, event_type: EventType, data: Optional[Dict[str, Any]] = None,
                 timestamp: Optional[datetime] = None, event_id: Optional[str] = None):
        """
        Initialize an event.
        
        Args:
            event_type: Type of the event
            data: Dictionary containing event data
            timestamp: Event timestamp (defaults to now)
            event_id: Unique event ID (defaults to generated UUID)
        """
        self._type = event_type
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()
        self.id = event_id or str(uuid.uuid4())
        self.consumed = False
        
    @property
    def type(self) -> EventType:
        """Event type property for compatibility with dataclass implementation."""
        return self._type
        
    @property
    def event_type(self) -> EventType:
        """Event type property for compatibility with class implementation."""
        return self._type
        
    @property
    def event_id(self) -> str:
        """Event ID property for compatibility with dataclass implementation."""
        return self.id
        
    def get_type(self) -> EventType:
        """Get the event type."""
        return self._type
        
    def get_data(self) -> Dict[str, Any]:
        """Get the event data."""
        return self.data
        
    def get_id(self) -> str:
        """Get the unique event ID."""
        return self.id
        
    def is_consumed(self) -> bool:
        """Check if the event has been consumed."""
        return self.consumed
        
    def consume(self) -> None:
        """Mark the event as consumed, preventing further processing."""
        self.consumed = True
        
    def reset_consumed(self) -> None:
        """Reset consumed state (for compatibility with dataclass implementation)."""
        self.consumed = False
        
    def get_dedup_key(self) -> str:
        """
        Get a key for deduplication based on event type and data.
        
        Different event types may have different deduplication rules.
        """
        # Signal events deduplicate by rule_id
        if self._type == EventType.SIGNAL and 'rule_id' in self.data:
            return f"signal_{self.data['rule_id']}"
            
        # Order events deduplicate by order_id or rule_id
        elif self._type == EventType.ORDER:
            order_id = self.data.get('order_id')
            rule_id = self.data.get('rule_id')
            
            if order_id:
                return f"order_{order_id}"
            elif rule_id:
                return f"order_from_{rule_id}"
                
        # Fill events deduplicate by order_id
        elif self._type == EventType.FILL and 'order_id' in self.data:
            return f"fill_{self.data['order_id']}"
            
        # Default to using the event ID
        return self.id
        
    def __str__(self) -> str:
        """String representation of the event."""
        return f"Event(type={self._type.name}, id={self.id}, timestamp={self.timestamp})"
        
    def __repr__(self) -> str:
        """Detailed string representation of the event."""
        return f"Event(type={self._type.name}, id={self.id}, timestamp={self.timestamp}, data={self.data})"


# Factory function for creating events
def create_event(event_type: EventType, data: Optional[Dict[str, Any]] = None, 
                timestamp: Optional[datetime] = None, event_id: Optional[str] = None) -> Event:
    """
    Create a new event.
    
    Args:
        event_type: Type of event
        data: Event data dictionary
        timestamp: Optional timestamp (defaults to now)
        event_id: Optional event ID (defaults to generated UUID)
        
    Returns:
        Event: New event instance
    """
    return Event(event_type, data, timestamp, event_id)