from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict
from src.core.events.event_types import EventType

@dataclass
class Event:
    """Event class to represent system events"""
    
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.now()

def create_event(event_type, data):
    """
    Create a new event
    
    Args:
        event_type: Type of event
        data: Event data
    
    Returns:
        Event: New event
    """
    return Event(type=event_type, data=data)