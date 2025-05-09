"""
Core event types for the ADMF-Trader system.

This module defines the standard event types used across the system.
The EventType enum combines all event types used in different parts
of the codebase to ensure consistency.
"""

from enum import Enum, auto

class EventType(Enum):
    """Unified enumeration of all event types used in the trading system."""
    
    # Market data events
    BAR = auto()           # Price bar event
    TICK = auto()          # Tick data event
    
    # Signal events (from strategy to risk manager)
    SIGNAL = auto()        # Trading signal event
    
    # Order events (from risk manager to execution)
    ORDER = auto()         # Order event
    ORDER_UPDATE = auto()  # Order status update event
    ORDER_CANCEL = auto()  # Order cancellation event
    
    # Execution events
    FILL = auto()          # Order fill event
    
    # Portfolio events
    PORTFOLIO = auto()         # Portfolio event (from events/event_types.py)
    PORTFOLIO_UPDATE = auto()  # Portfolio state update
    POSITION = auto()          # Position event (from events/event_types.py)
    TRADE = auto()             # Trade event (from events/event_types.py)
    TRADE_OPEN = auto()        # Trade opened
    TRADE_CLOSE = auto()       # Trade closed
    PERFORMANCE = auto()       # Performance metrics event
    
    # System events
    START = auto()             # System start event (from events/event_types.py)
    STOP = auto()              # System stop event (from events/event_types.py)
    BACKTEST_START = auto()    # Backtest started
    BACKTEST_END = auto()      # Backtest completed
    OPTIMIZATION_START = auto() # Optimization started (from events/event_types.py)
    OPTIMIZATION_END = auto()   # Optimization completed (from events/event_types.py)
    ERROR = auto()             # Error event
    LOG = auto()               # Logging event
    
    # Strategy events
    STRATEGY = auto()         # Strategy-related event
    
    # Data events (from events/event_types.py)
    DATA_READY = auto()        # Data is ready
    DATA_ERROR = auto()        # Data error occurred