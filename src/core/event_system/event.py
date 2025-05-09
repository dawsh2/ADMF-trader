"""
Event class for the ADMF-Trader system.

This module provides the core Event class used for all event-based communication.
This implementation uses dataclasses for cleaner code, type safety, and automatic
method generation, while maintaining compatibility with different usage patterns.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, ClassVar

from src.core.event_system.event_types import EventType

@dataclass
class Event:
    """
    Dataclass for all events in the system.
    
    Events are used to communicate between components, providing a 
    loosely coupled architecture. This implementation uses dataclasses
    for cleaner code, type safety, and automatic method generation.
    
    For backward compatibility, both property and method-based access
    patterns are supported (e.g., both event.type and event.get_type()).
    """
    
    # Internal fields
    _type: EventType  # Use an underscore to avoid conflicts with property
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    consumed: bool = False
    
    # Class constants for specialized event types
    SIGNAL: ClassVar[str] = "SIGNAL"
    ORDER: ClassVar[str] = "ORDER"
    FILL: ClassVar[str] = "FILL"
    
    # Ensure the constructor accepts 'type' as the first parameter for backward compatibility
    def __post_init__(self):
        """Run after initialization to handle any compatibility issues."""
        # Nothing needed here as long as field names match initializer
        pass
        
    # Backward compatibility properties and methods
    
    @property
    def type(self) -> EventType:
        """Event type property - primary access pattern."""
        return self._type
    
    @property
    def event_type(self) -> EventType:
        """Event type property for backward compatibility."""
        return self._type
    
    def get_type(self) -> EventType:
        """Get the event type (for backward compatibility)."""
        return self.type
    
    def get_data(self) -> Dict[str, Any]:
        """Get the event data (for backward compatibility)."""
        return self.data
    
    def get_id(self) -> str:
        """Get the unique event ID (for backward compatibility)."""
        return self.id
    
    def get_symbol(self) -> Optional[str]:
        """Get symbol from event data for convenience."""
        return self.data.get('symbol')
        
    def get_direction(self) -> Optional[str]:
        """Get direction from event data for convenience."""
        return self.data.get('direction')
        
    def get_quantity(self) -> Optional[float]:
        """Get quantity from event data for convenience."""
        return self.data.get('quantity')
        
    def get_price(self) -> Optional[float]:
        """Get price from event data for convenience."""
        return self.data.get('price')
    
    def get_timestamp(self) -> datetime:
        """Get timestamp, either from event data or the event itself."""
        if 'timestamp' in self.data:
            return self.data.get('timestamp')
        return self.timestamp
    
    def is_consumed(self) -> bool:
        """Check if the event has been consumed."""
        return self.consumed
    
    def consume(self) -> None:
        """Mark the event as consumed, preventing further processing."""
        self.consumed = True
    
    def reset_consumed(self) -> None:
        """Reset consumed state."""
        self.consumed = False
    
    def get_dedup_key(self) -> str:
        """
        Get a key for deduplication based on event type and data.
        
        Different event types may have different deduplication rules.
        """
        # Signal events deduplicate by rule_id
        if self.type == EventType.SIGNAL and 'rule_id' in self.data:
            return f"signal_{self.data['rule_id']}"
        
        # Order events deduplicate by order_id or rule_id
        elif self.type == EventType.ORDER:
            order_id = self.data.get('order_id')
            rule_id = self.data.get('rule_id')
            
            if order_id:
                return f"order_{order_id}"
            elif rule_id:
                return f"order_from_{rule_id}"
        
        # Fill events deduplicate by order_id
        elif self.type == EventType.FILL and 'order_id' in self.data:
            return f"fill_{self.data['order_id']}"
        
        # Default to using the event ID
        return self.id


# Factory function for creating events - for compatibility with event_utils
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
    return Event(
        _type=event_type,
        data=data or {},
        timestamp=timestamp or datetime.now(),
        id=event_id or str(uuid.uuid4())
    )