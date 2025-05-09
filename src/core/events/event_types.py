from enum import Enum, auto

class EventType(Enum):
    """Enum of all possible event types in the system"""
    
    # Market data events
    TICK = auto()
    BAR = auto()
    
    # Strategy events
    SIGNAL = auto()
    
    # Risk management events
    ORDER = auto()
    
    # Execution events
    FILL = auto()
    
    # System events
    START = auto()
    STOP = auto()
    ERROR = auto()