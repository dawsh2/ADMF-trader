from datetime import datetime

# Import from the canonical source to avoid circular imports
from src.core.event_system.event_types import EventType
from src.core.event_system.event import Event, create_event

# Note: This file is kept for backward compatibility
# It contains event creation utilities that use the canonical Event class

# Event creation functions
def create_bar_event(symbol, timestamp, open_price, high_price, low_price, close_price, volume=None):
    """Create a bar event"""
    # Create data structure for bar event
    data = {
        'symbol': symbol,
        'open': open_price,
        'high': high_price,
        'low': low_price,
        'close': close_price,
        'volume': volume or 0,
        'timeframe': 'default'  # Could be populated from context if needed
    }
    return Event(
        type=EventType.BAR,
        data=data,
        timestamp=timestamp
    )

def create_signal_event(symbol, signal_type, strategy_id=None, timestamp=None, strength=1.0):
    """Create a signal event"""
    # Create data structure for signal event
    data = {
        'symbol': symbol,
        'signal_type': signal_type,
        'strategy_id': strategy_id,
        'strength': strength
    }
    return Event(
        _type=EventType.SIGNAL,
        data=data,
        timestamp=timestamp
    )

def create_order_event(symbol, order_type, quantity, direction, price=None, order_id=None, timestamp=None):
    """Create an order event"""
    # Create data structure for order event
    data = {
        'symbol': symbol,
        'order_type': order_type,
        'quantity': quantity,
        'direction': direction,
        'price': price,
        'order_id': order_id
    }
    return Event(
        type=EventType.ORDER,
        data=data,
        timestamp=timestamp
    )

def create_fill_event(symbol, quantity, direction, fill_price, commission=0.0, order_id=None, timestamp=None):
    """Create a fill event"""
    # Create data structure for fill event
    data = {
        'symbol': symbol,
        'quantity': quantity,
        'direction': direction,
        'fill_price': fill_price,
        'commission': commission,
        'order_id': order_id
    }
    return Event(
        type=EventType.FILL,
        data=data,
        timestamp=timestamp
    )

def create_websocket_event(message, channel=None, timestamp=None):
    """Create a WebSocket event"""
    data = {
        'message': message,
        'channel': channel
    }
    return Event(
        type=EventType.TICK,  # WebSocket events are often tick data
        data=data,
        timestamp=timestamp
    )

def create_lifecycle_event(action, component=None, timestamp=None):
    """Create a lifecycle event"""
    if action == 'START':
        event_type = EventType.START
    elif action == 'STOP':
        event_type = EventType.STOP
    else:
        event_type = EventType.ERROR
    
    data = {
        'action': action,
        'component': component
    }
    return Event(
        type=event_type,
        data=data,
        timestamp=timestamp
    )

def create_error_event(error_type, message, component=None, timestamp=None):
    """Create an error event"""
    data = {
        'error_type': error_type,
        'message': message,
        'component': component
    }
    return Event(
        type=EventType.ERROR,
        data=data,
        timestamp=timestamp
    )

def create_backtest_event(action, backtest_id=None, statistics=None, timestamp=None):
    """Create a backtest event"""
    if action.upper() == 'START':
        event_type = EventType.BACKTEST_START
    else:  # 'END'
        event_type = EventType.BACKTEST_END
    
    data = {
        'action': action,
        'backtest_id': backtest_id,
        'statistics': statistics or {}
    }
    return Event(
        type=event_type,
        data=data,
        timestamp=timestamp
    )

def create_optimization_event(action, optimization_id=None, results=None, timestamp=None):
    """Create an optimization event"""
    if action.upper() == 'START':
        event_type = EventType.OPTIMIZATION_START
    else:  # 'END'
        event_type = EventType.OPTIMIZATION_END
    
    data = {
        'action': action,
        'optimization_id': optimization_id,
        'results': results or {}
    }
    return Event(
        type=event_type,
        data=data,
        timestamp=timestamp
    )

def create_portfolio_event(portfolio_id, holdings, cash, equity, timestamp=None):
    """Create a portfolio event"""
    data = {
        'portfolio_id': portfolio_id,
        'holdings': holdings,
        'cash': cash,
        'equity': equity
    }
    return Event(
        type=EventType.PORTFOLIO,
        data=data,
        timestamp=timestamp
    )

def create_position_event(symbol, quantity, avg_price, current_price, realized_pnl=0.0, unrealized_pnl=0.0, timestamp=None):
    """Create a position event"""
    data = {
        'symbol': symbol,
        'quantity': quantity,
        'avg_price': avg_price,
        'current_price': current_price,
        'realized_pnl': realized_pnl,
        'unrealized_pnl': unrealized_pnl
    }
    return Event(
        type=EventType.POSITION,
        data=data,
        timestamp=timestamp
    )

def create_trade_event(symbol, quantity, price, direction, trade_id=None, order_id=None, commission=0.0, timestamp=None):
    """Create a trade event"""
    data = {
        'symbol': symbol,
        'quantity': quantity,
        'price': price,
        'direction': direction,
        'trade_id': trade_id,
        'order_id': order_id,
        'commission': commission
    }
    return Event(
        type=EventType.TRADE,
        data=data,
        timestamp=timestamp
    )

def create_performance_event(metrics, portfolio_id=None, period=None, timestamp=None):
    """Create a performance event"""
    data = {
        'metrics': metrics,
        'portfolio_id': portfolio_id,
        'period': period
    }
    return Event(
        type=EventType.PERFORMANCE,
        data=data,
        timestamp=timestamp
    )

# Placeholder for other functions mentioned in __init__.py
# These would need to be implemented based on your actual needs

# Serialization
def event_to_dict(event):
    """Convert an event to a dictionary"""
    return {
        'type': event.type.name,
        'data': event.data,
        'timestamp': event.timestamp.isoformat() if event.timestamp else None
    }

def dict_to_event(event_dict):
    """Convert a dictionary to an event"""
    event_type = EventType[event_dict['type']]
    data = event_dict['data']
    timestamp = datetime.fromisoformat(event_dict['timestamp']) if event_dict.get('timestamp') else None
    return Event(type=event_type, data=data, timestamp=timestamp)

def serialize_event(event):
    """Serialize an event to a JSON string"""
    import json
    return json.dumps(event_to_dict(event))

def deserialize_event(serialized_event):
    """Deserialize a JSON string to an event"""
    import json
    return dict_to_event(json.loads(serialized_event))

# Filtering
def filter_events_by_type(events, event_type):
    """Filter events by type"""
    return [event for event in events if event.type == event_type]

def filter_events_by_symbol(events, symbol):
    """Filter events by symbol"""
    return [event for event in events if event.data.get('symbol') == symbol]

def filter_events_by_time(events, start_time, end_time):
    """Filter events by time range"""
    return [event for event in events 
            if event.timestamp and start_time <= event.timestamp <= end_time]

# Async helpers
async def emit_event_async(event_bus, event):
    """Emit an event asynchronously"""
    # This would need to be implemented based on your event bus
    pass

async def emit_events_async(event_bus, events):
    """Emit multiple events asynchronously"""
    # This would need to be implemented based on your event bus
    pass

def is_async_handler(handler):
    """Check if a handler is asynchronous"""
    import inspect
    return inspect.iscoroutinefunction(handler)

def wrap_sync_handler(handler):
    """Wrap a synchronous handler to be used asynchronously"""
    async def wrapper(event):
        return handler(event)
    return wrapper

def wrap_async_handler(handler):
    """Wrap an asynchronous handler to be used synchronously"""
    import asyncio
    def wrapper(event):
        return asyncio.run(handler(event))
    return wrapper

# Transformation
def transform_events(events, transform_func):
    """Transform events using a function"""
    return [transform_func(event) for event in events]

async def transform_events_async(events, transform_func):
    """Transform events asynchronously"""
    results = []
    for event in events:
        if is_async_handler(transform_func):
            result = await transform_func(event)
        else:
            result = transform_func(event)
        results.append(result)
    return results

# Processing
def process_events(events, process_func):
    """Process events using a function"""
    for event in events:
        process_func(event)

async def process_events_async(events, process_func):
    """Process events asynchronously"""
    for event in events:
        if is_async_handler(process_func):
            await process_func(event)
        else:
            process_func(event)

# Event tracking
class EventTracker:
    """Track events for analysis"""
    
    def __init__(self):
        self.events = []
    
    def track(self, event):
        """Track an event"""
        self.events.append(event)
    
    def get_events(self, event_type=None, symbol=None, start_time=None, end_time=None):
        """Get tracked events with optional filtering"""
        filtered_events = self.events
        
        if event_type is not None:
            filtered_events = filter_events_by_type(filtered_events, event_type)
        
        if symbol is not None:
            filtered_events = filter_events_by_symbol(filtered_events, symbol)
        
        if start_time is not None and end_time is not None:
            filtered_events = filter_events_by_time(filtered_events, start_time, end_time)
        
        return filtered_events
