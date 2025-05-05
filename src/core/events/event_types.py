import uuid
import datetime
import json
from enum import Enum, auto
from typing import Dict, Any, Optional

class EventType(Enum):
    """Enum defining all event types in the system."""
    BAR = auto()            # Market data
    SIGNAL = auto()         # Trading signal
    ORDER = auto()          # Order request
    FILL = auto()           # Order fill
    POSITION = auto()       # Position update
    PORTFOLIO = auto()      # Portfolio state update
    STRATEGY = auto()       # Strategy state
    METRIC = auto()         # Performance metrics
    WEBSOCKET = auto()      # WebSocket events
    LIFECYCLE = auto()      # System lifecycle events
    ERROR = auto()          # Error events
    ORDER_STATE_CHANGE = auto()  # Order state changes
    ORDER_CANCEL = auto()   # Order cancellation events
    REJECT = auto()         # Order rejection events

    # New event types for improved architecture
    POSITION_OPEN = auto()  # Intent to open a position
    POSITION_CLOSE = auto() # Intent to close a position
    TRADE_OPEN = auto()     # Record of opened trade
    TRADE_CLOSE = auto()    # Record of closed trade

    OPTIMIZATION = auto()   # Optimization events
    FILTER = auto()         # Filter state events
    REGIME = auto()         # Market regime events    

class Event:
    """Base class for all events in the system."""
    
    def __init__(self, event_type, data=None, timestamp=None, event_id=None):
        self.event_type = event_type
        self.data = data or {}
        self.timestamp = timestamp or datetime.datetime.now()
        self.id = event_id or str(uuid.uuid4())
        self.consumed = False  # Track if event has been consumed
    
    def get_type(self):
        """Get the event type."""
        return self.event_type
    
    def get_timestamp(self):
        """Get the event timestamp."""
        return self.timestamp
        
    def get_id(self):
        """Get the unique event ID."""
        return self.id
        
    def mark_consumed(self):
        """Mark this event as consumed to prevent duplicate processing."""
        self.consumed = True
        
    def is_consumed(self):
        """Check if this event has been consumed."""
        return self.consumed
        
    def __eq__(self, other):
        """Compare events based on their ID."""
        if not isinstance(other, Event):
            return False
        return self.id == other.id

    def serialize(self):
        """
        Serialize event to JSON string with type preservation.
        
        Returns:
            JSON string representation
        """
        serialized_data = {
            'id': self.id,
            'event_type': self.event_type.name,  # Convert enum to string
            'timestamp': self.timestamp.isoformat(),  # ISO format for datetime
            'data': self._prepare_data_for_serialization(self.data)
        }
        
        return json.dumps(serialized_data)
    
    def _prepare_data_for_serialization(self, data):
        """
        Prepare data for serialization, handling special types.
        
        Args:
            data: Data to prepare
            
        Returns:
            Serialization-ready data
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result[key] = self._prepare_data_for_serialization(value)
            return result
        elif isinstance(data, list):
            return [self._prepare_data_for_serialization(item) for item in data]
        elif isinstance(data, datetime.datetime):
            return {"__datetime__": data.isoformat()}
        elif isinstance(data, Enum):
            return {"__enum__": {"class": data.__class__.__name__, "name": data.name}}
        elif hasattr(data, "to_dict") and callable(data.to_dict):
            # Handle custom objects with to_dict method
            dict_data = data.to_dict()
            dict_data["__type__"] = data.__class__.__name__
            return dict_data
        else:
            return data
    
    @classmethod
    def deserialize(cls, json_str):
        """
        Deserialize JSON string back to Event object.
        
        Args:
            json_str: JSON string from serialize()
            
        Returns:
            Event object
        """
        data = json.loads(json_str)
        
        # Reconstruct event
        event_type = EventType[data['event_type']]
        timestamp = datetime.datetime.fromisoformat(data['timestamp'])
        event_data = cls._process_serialized_data(data['data'])
        
        event = cls(event_type, event_data, timestamp)
        event.id = data['id']
        
        return event
    
    @classmethod
    def _process_serialized_data(cls, data):
        """
        Process serialized data back to original types.
        
        Args:
            data: Serialized data
            
        Returns:
            Reconstructed data
        """
        if isinstance(data, dict):
            # Handle special type markers
            if "__datetime__" in data:
                return datetime.datetime.fromisoformat(data["__datetime__"])
            elif "__enum__" in data:
                enum_data = data["__enum__"]
                enum_class = globals()[enum_data["class"]]  # Get enum class by name
                return enum_class[enum_data["name"]]  # Get enum value by name
            elif "__type__" in data:
                return ObjectRegistry.from_dict(data)
            
            # Regular dict
            result = {}
            for key, value in data.items():
                result[key] = cls._process_serialized_data(value)
            return result
        elif isinstance(data, list):
            return [cls._process_serialized_data(item) for item in data]
        else:
            return data


class BarEvent(Event):
    """Market data bar event."""
    
    def __init__(self, symbol, timestamp, open_price, high_price, 
                 low_price, close_price, volume):
        data = {
            'symbol': symbol,
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        }
        super().__init__(EventType.BAR, data, timestamp)
    
    # Accessor methods
    def get_symbol(self):
        return self.data['symbol']
        
    def get_open(self):
        return self.data['open']
        
    def get_high(self):
        return self.data['high']
        
    def get_low(self):
        return self.data['low']
        
    def get_close(self):
        return self.data['close']
        
    def get_volume(self):
        return self.data['volume']


class SignalEvent(Event):
    """Trading signal event."""
    
    # Signal constants
    BUY = 1
    SELL = -1
    NEUTRAL = 0
    
    def __init__(self, signal_value, price, symbol, rule_id=None, 
                 confidence=1.0, metadata=None, timestamp=None):
        # Validate signal value
        if signal_value not in (self.BUY, self.SELL, self.NEUTRAL):
            raise ValueError(f"Invalid signal value: {signal_value}")
            
        data = {
            'signal_value': signal_value,
            'price': price,
            'symbol': symbol,
            'rule_id': rule_id,
            'confidence': confidence,
            'metadata': metadata or {},
        }
        super().__init__(EventType.SIGNAL, data, timestamp)
    
    # Accessor methods
    def get_signal_value(self):
        return self.data['signal_value']
        
    def get_symbol(self):
        return self.data['symbol']
        
    def get_price(self):
        return self.data['price']
        
    def is_buy(self):
        return self.data['signal_value'] == self.BUY
        
    def is_sell(self):
        return self.data['signal_value'] == self.SELL


class OrderEvent(Event):
    """Order request event."""
    
    # Order types
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    STOP = 'STOP'
    
    # Order directions
    BUY = 'BUY'
    SELL = 'SELL'
    
    def __init__(self, symbol, order_type, direction, quantity, 
                 price=None, timestamp=None):
        data = {
            'symbol': symbol,
            'order_type': order_type,
            'direction': direction,
            'quantity': quantity,
            'price': price,
        }
        super().__init__(EventType.ORDER, data, timestamp)
    
    # Accessor methods
    def get_symbol(self):
        return self.data['symbol']
        
    def get_order_type(self):
        return self.data['order_type']
        
    def get_direction(self):
        return self.data['direction']
        
    def get_quantity(self):
        return self.data['quantity']
        
    def get_price(self):
        return self.data['price']


class OrderCancelEvent(Event):
    """Order cancellation event."""
    
    def __init__(self, order_id, reason=None, timestamp=None):
        data = {
            'order_id': order_id,
            'reason': reason or "User requested cancellation",
        }
        super().__init__(EventType.ORDER_CANCEL, data, timestamp)
    
    # Accessor methods
    def get_order_id(self):
        return self.data['order_id']
        
    def get_reason(self):
        return self.data['reason']


class FillEvent(Event):
    """Order fill event."""
    
    def __init__(self, symbol, direction, quantity, price, 
                 commission=0.0, timestamp=None):
        data = {
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'commission': commission,
        }
        super().__init__(EventType.FILL, data, timestamp)
    
    # Accessor methods
    def get_symbol(self):
        return self.data['symbol']
        
    def get_direction(self):
        return self.data['direction']
        
    def get_quantity(self):
        return self.data['quantity']
        
    def get_price(self):
        return self.data['price']
        
    def get_commission(self):
        return self.data['commission']


class WebSocketEvent(Event):
    """WebSocket connection event."""
    
    # Connection states
    CONNECTING = 'CONNECTING'
    CONNECTED = 'CONNECTED'
    DISCONNECTED = 'DISCONNECTED'
    MESSAGE = 'MESSAGE'
    ERROR = 'ERROR'
    
    def __init__(self, connection_id, state, data=None, timestamp=None):
        event_data = {
            'connection_id': connection_id,
            'state': state,
            'data': data or {},
        }
        super().__init__(EventType.WEBSOCKET, event_data, timestamp)
    
    # Accessor methods
    def get_connection_id(self):
        return self.data['connection_id']
        
    def get_state(self):
        return self.data['state']
        
    def get_data(self):
        return self.data['data']


class LifecycleEvent(Event):
    """System lifecycle event."""
    
    # Lifecycle states
    INITIALIZING = 'INITIALIZING'
    INITIALIZED = 'INITIALIZED'
    STARTING = 'STARTING'
    RUNNING = 'RUNNING'
    STOPPING = 'STOPPING'
    STOPPED = 'STOPPED'
    ERROR = 'ERROR'
    
    def __init__(self, state, component=None, data=None, timestamp=None):
        event_data = {
            'state': state,
            'component': component,
            'data': data or {},
        }
        super().__init__(EventType.LIFECYCLE, event_data, timestamp)
    
    # Accessor methods
    def get_state(self):
        return self.data['state']
        
    def get_component(self):
        return self.data['component']
        
    def get_data(self):
        return self.data['data']


class ErrorEvent(Event):
    """Error event."""
    
    def __init__(self, error_type, message, source=None, exception=None, timestamp=None):
        data = {
            'error_type': error_type,
            'message': message,
            'source': source,
            'exception': str(exception) if exception else None,
        }
        super().__init__(EventType.ERROR, data, timestamp)
    
    # Accessor methods
    def get_error_type(self):
        return self.data['error_type']
        
    def get_message(self):
        return self.data['message']
        
    def get_source(self):
        return self.data['source']
        
    def get_exception(self):
        return self.data['exception']


# Updates to src/core/events/event_types.py
class OptimizationEvent(Event):
    """Optimization result event."""
    
    def __init__(self, strategy, parameters, metrics, timestamp=None):
        data = {
            'strategy': strategy,
            'parameters': parameters,
            'metrics': metrics
        }
        super().__init__(EventType.OPTIMIZATION, data, timestamp)
    
    def get_strategy(self):
        return self.data['strategy']
        
    def get_parameters(self):
        return self.data['parameters']
        
    def get_metrics(self):
        return self.data['metrics']


class FilterEvent(Event):
    """Filter state change event."""
    
    def __init__(self, filter_name, symbol, state, reason=None, timestamp=None):
        data = {
            'filter_name': filter_name,
            'symbol': symbol,
            'state': state,  # True/False for active/inactive
            'reason': reason
        }
        super().__init__(EventType.FILTER, data, timestamp)
    
    def get_filter_name(self):
        return self.data['filter_name']
        
    def get_symbol(self):
        return self.data['symbol']
        
    def get_state(self):
        return self.data['state']
        
    def get_reason(self):
        return self.data['reason']


class RegimeEvent(Event):
    """Market regime change event."""
    
    def __init__(self, symbol, regime, confidence=1.0, timestamp=None):
        data = {
            'symbol': symbol,
            'regime': regime,
            'confidence': confidence
        }
        super().__init__(EventType.REGIME, data, timestamp)
    
    def get_symbol(self):
        return self.data['symbol']
        
    def get_regime(self):
        return self.data['regime']
        
    def get_confidence(self):
        return self.data['confidence']    


class PositionOpenEvent(Event):
    """Intent to open a new position."""
    
    def __init__(self, symbol, direction, quantity, price, rule_id=None,
                 timestamp=None, order_id=None, metadata=None):
        data = {
            'symbol': symbol,
            'direction': direction,  # "BUY" or "SELL"
            'quantity': quantity,
            'price': price,
            'rule_id': rule_id,
            'order_id': order_id,
            'metadata': metadata or {}
        }
        super().__init__(EventType.POSITION_OPEN, data, timestamp)
    
    # Accessor methods
    def get_symbol(self):
        return self.data['symbol']
        
    def get_direction(self):
        return self.data['direction']
        
    def get_quantity(self):
        return self.data['quantity']
        
    def get_price(self):
        return self.data['price']
        
    def get_rule_id(self):
        return self.data['rule_id']
        
    def get_order_id(self):
        return self.data['order_id']
        
    def get_metadata(self):
        return self.data['metadata']


class PositionCloseEvent(Event):
    """Intent to close an existing position."""
    
    def __init__(self, symbol, direction, quantity, price, rule_id=None,
                 timestamp=None, order_id=None, metadata=None):
        data = {
            'symbol': symbol,
            'direction': direction,  # "BUY" or "SELL"
            'quantity': quantity,
            'price': price,
            'rule_id': rule_id,
            'order_id': order_id,
            'metadata': metadata or {}
        }
        super().__init__(EventType.POSITION_CLOSE, data, timestamp)
    
    # Accessor methods
    def get_symbol(self):
        return self.data['symbol']
        
    def get_direction(self):
        return self.data['direction']
        
    def get_quantity(self):
        return self.data['quantity']
        
    def get_price(self):
        return self.data['price']
        
    def get_rule_id(self):
        return self.data['rule_id']
        
    def get_order_id(self):
        return self.data['order_id']
        
    def get_metadata(self):
        return self.data['metadata']


class TradeOpenEvent(Event):
    """Record of an opened trade."""
    
    def __init__(self, symbol, direction, quantity, price, commission=0.0,
                 timestamp=None, rule_id=None, order_id=None, transaction_id=None):
        data = {
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'rule_id': rule_id,
            'order_id': order_id,
            'transaction_id': transaction_id or str(uuid.uuid4())
        }
        super().__init__(EventType.TRADE_OPEN, data, timestamp)
    
    # Accessor methods
    def get_symbol(self):
        return self.data['symbol']
        
    def get_direction(self):
        return self.data['direction']
        
    def get_quantity(self):
        return self.data['quantity']
        
    def get_price(self):
        return self.data['price']
        
    def get_commission(self):
        return self.data['commission']
        
    def get_rule_id(self):
        return self.data['rule_id']
        
    def get_order_id(self):
        return self.data['order_id']
        
    def get_transaction_id(self):
        return self.data['transaction_id']


class TradeCloseEvent(Event):
    """Record of a closed trade."""
    
    def __init__(self, symbol, direction, quantity, entry_price, exit_price, 
                 entry_time, exit_time, pnl, commission=0.0, rule_id=None, 
                 order_id=None, transaction_id=None):
        data = {
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'pnl': pnl,
            'commission': commission,
            'rule_id': rule_id,
            'order_id': order_id,
            'transaction_id': transaction_id
        }
        super().__init__(EventType.TRADE_CLOSE, data, exit_time)
    
    # Accessor methods
    def get_symbol(self):
        return self.data['symbol']
        
    def get_direction(self):
        return self.data['direction']
        
    def get_quantity(self):
        return self.data['quantity']
        
    def get_entry_price(self):
        return self.data['entry_price']
        
    def get_exit_price(self):
        return self.data['exit_price']
        
    def get_entry_time(self):
        return self.data['entry_time']
        
    def get_exit_time(self):
        return self.data['exit_time']
        
    def get_pnl(self):
        return self.data['pnl']
        
    def get_commission(self):
        return self.data['commission']
        
    def get_rule_id(self):
        return self.data['rule_id']
        
    def get_order_id(self):
        return self.data['order_id']
        
    def get_transaction_id(self):
        return self.data['transaction_id']
