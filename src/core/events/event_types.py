"""
DEPRECATED: This module is deprecated in favor of src.core.event_system modules.

This module is kept for backward compatibility but will be removed in a future version.
Please use the canonical implementations:
- Import EventType from src.core.event_system.event_types
- Import Event from src.core.event_system.event

The canonical implementation now uses dataclasses for cleaner code and better type safety.
"""

import warnings
import enum

# Emit deprecation warning
warnings.warn(
    "The event_types module in src.core.events is deprecated and will be removed. "
    "Please import EventType from src.core.event_system.event_types and "
    "Event from src.core.event_system.event instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import and re-export the canonical EventType from event_system
from src.core.event_system.event_types import EventType

# For backward compatibility with code that uses Enum.auto
auto = enum.auto

# Import and re-export the canonical Event class from event_system
from src.core.event_system.event import Event, create_event

# The canonical event system now uses dataclasses with backward compatibility

# Note: For backward compatibility, we define classes for specialized event types
# but they just wrap our Event dataclass implementation for tests that expect them

class BarEvent(Event):
    """Backward compatibility wrapper for bar events."""
    pass
    
class SignalEvent(Event):
    """Backward compatibility wrapper for signal events."""
    pass
    
class OrderEvent(Event):
    """Backward compatibility wrapper for order events."""
    pass
    
class FillEvent(Event):
    """Backward compatibility wrapper for fill events."""
    pass
    
class WebSocketEvent(Event):
    """Backward compatibility wrapper for websocket events."""
    pass
    
class LifecycleEvent(Event):
    """Backward compatibility wrapper for lifecycle events."""
    pass
    
class ErrorEvent(Event):
    """Backward compatibility wrapper for error events."""
    pass
    
class BacktestEvent(Event):
    """Backward compatibility wrapper for backtest events."""
    pass
    
class OptimizationEvent(Event):
    """Backward compatibility wrapper for optimization events."""
    pass
    
class PortfolioEvent(Event):
    """Backward compatibility wrapper for portfolio events."""
    pass
    
class PositionEvent(Event):
    """Backward compatibility wrapper for position events."""
    pass
    
class TradeEvent(Event):
    """Backward compatibility wrapper for trade events."""
    pass
    
class PerformanceEvent(Event):
    """Backward compatibility wrapper for performance events."""
    pass

# Import the specialized event factory functions for backward compatibility
from src.core.events.event_utils import (
    create_bar_event,
    create_signal_event, 
    create_order_event,
    create_fill_event,
    create_websocket_event,
    create_lifecycle_event,
    create_error_event,
    create_backtest_event,
    create_optimization_event,
    create_portfolio_event,
    create_position_event,
    create_trade_event,
    create_performance_event
)