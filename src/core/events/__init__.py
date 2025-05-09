"""
Event system module for the algorithmic trading framework.

This package provides an event-driven architecture for the trading system,
serving as the central nervous system for communication between components.
The event system supports both synchronous and asynchronous operations,
allowing for efficient handling of real-time data streams and WebSocket
connections.
"""

# Import canonical Event and EventType from event_system
from src.core.event_system.event_types import EventType
from src.core.event_system.event import Event, create_event

from .event_bus import EventBus

from .event_manager import EventManager

from .event_utils import EventTracker

from .event_utils import (
    # Event creation
    create_bar_event, create_signal_event, create_order_event, create_fill_event,
    create_websocket_event, create_lifecycle_event, create_error_event,
    create_backtest_event, create_optimization_event,
    create_portfolio_event, create_position_event, create_trade_event, create_performance_event,
    
    # Serialization
    event_to_dict, dict_to_event, serialize_event, deserialize_event,
    
    # Filtering
    filter_events_by_type, filter_events_by_symbol, filter_events_by_time,
    
    # Async helpers
    emit_event_async, emit_events_async, is_async_handler,
    wrap_sync_handler, wrap_async_handler,
    
    # Transformation
    transform_events, transform_events_async,
    
    # Processing
    process_events, process_events_async

    
)

from .event_schema import SchemaValidator

from .event_handlers import (
    # Base handlers
    EventHandler, AsyncEventHandler,
    
    # Implementations
    LoggingHandler, AsyncLoggingHandler,
    FilterHandler, AsyncFilterHandler,
    ChainHandler, AsyncChainHandler,
    BufferedHandler, AsyncBufferedHandler,
    WebSocketHandler
)

from .event_emitters import (
    # Base emitters
    EventEmitter, AsyncEventEmitter,
    
    # Implementations
    HistoricalDataEmitter, EventGeneratorEmitter, WebSocketEmitter
)

__all__ = [
    # Event types
    'EventType', 'Event', 'create_event',
    
    # Event bus
    'EventBus',
    
    # Event manager
    'EventManager',
    
    # Event utilities
    'create_bar_event', 'create_signal_event', 'create_order_event', 'create_fill_event',
    'create_websocket_event', 'create_lifecycle_event', 'create_error_event',
    'create_backtest_event', 'create_optimization_event',
    'create_portfolio_event', 'create_position_event', 'create_trade_event', 'create_performance_event',
    'event_to_dict', 'dict_to_event', 'serialize_event', 'deserialize_event',
    'filter_events_by_type', 'filter_events_by_symbol', 'filter_events_by_time',
    'emit_event_async', 'emit_events_async', 'is_async_handler',
    'wrap_sync_handler', 'wrap_async_handler',
    'transform_events', 'transform_events_async',
    'process_events', 'process_events_async', 'EventTracker',
    
    # Event schema
    'SchemaValidator',
    
    # Event handlers
    'EventHandler', 'AsyncEventHandler',
    'LoggingHandler', 'AsyncLoggingHandler',
    'FilterHandler', 'AsyncFilterHandler',
    'ChainHandler', 'AsyncChainHandler',
    'BufferedHandler', 'AsyncBufferedHandler',
    'WebSocketHandler',
    
    # Event emitters
    'EventEmitter', 'AsyncEventEmitter',
    'HistoricalDataEmitter', 'EventGeneratorEmitter', 'WebSocketEmitter'
]
