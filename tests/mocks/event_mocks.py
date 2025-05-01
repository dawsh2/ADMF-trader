"""
Mock implementations of Event and EventType for testing purposes.
"""

import enum
import uuid
import datetime
import json

class MockEventType(enum.Enum):
    """Mock of the EventType enum."""
    BAR = 1
    SIGNAL = 2
    ORDER = 3
    FILL = 4
    POSITION = 5
    PORTFOLIO = 6
    STRATEGY = 7
    METRIC = 8
    WEBSOCKET = 9
    LIFECYCLE = 10
    ERROR = 11
    ORDER_STATE_CHANGE = 12
    ORDER_CANCEL = 13
    REJECT = 14
    OPTIMIZATION = 15
    FILTER = 16
    REGIME = 17

class MockEvent:
    """Mock implementation of the Event class for testing purposes."""
    
    def __init__(self, event_type, data=None, timestamp=None):
        self.event_type = event_type
        self.type = event_type  # Add both attributes to avoid issues
        self.data = data or {}
        self.timestamp = timestamp or datetime.datetime.now()
        self.id = str(uuid.uuid4())
        self.consumed = False
    
    def get_type(self):
        """Get the event type."""
        return self.event_type
    
    def get_timestamp(self):
        """Get the event timestamp."""
        return self.timestamp
    
    def get_id(self):
        """Get the unique event ID."""
        return self.id
    
    def get_data(self):
        """Get event data."""
        return self.data
    
    def mark_consumed(self):
        """Mark this event as consumed to prevent duplicate processing."""
        self.consumed = True
    
    def is_consumed(self):
        """Check if this event has been consumed."""
        return self.consumed
    
    def __eq__(self, other):
        """Compare events based on ID."""
        if not isinstance(other, MockEvent):
            return False
        return self.id == other.id
    
    # Helper methods commonly used in tests
    def get_symbol(self):
        """Get symbol from event data."""
        return self.data.get('symbol')
    
    def get_close(self):
        """Get close price from event data."""
        return self.data.get('close')
    
    def get_signal_value(self):
        """Get signal value from event data."""
        return self.data.get('signal_value')
    
    def serialize(self):
        """Serialize event to JSON string."""
        serialized_data = {
            'id': self.id,
            'event_type': self.event_type.name,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data
        }
        return json.dumps(serialized_data)
    
    @classmethod
    def deserialize(cls, json_str):
        """Deserialize JSON string back to Event object."""
        data = json.loads(json_str)
        
        # Reconstruct event
        event_type = MockEventType[data['event_type']]
        timestamp = datetime.datetime.fromisoformat(data['timestamp'])
        event_data = data['data']
        
        event = cls(event_type, event_data, timestamp)
        event.id = data['id']
        
        return event

# Create mock functions to mirror event_utils functionality
def create_mock_signal_event(signal_value, price, symbol, timestamp=None):
    """Create a mock signal event."""
    data = {
        'signal_value': signal_value,
        'price': price,
        'symbol': symbol,
        'timestamp': timestamp or datetime.datetime.now().isoformat()
    }
    return MockEvent(MockEventType.SIGNAL, data)

def create_mock_order_event(direction, quantity, symbol, order_type, price, timestamp=None):
    """Create a mock order event."""
    data = {
        'direction': direction,
        'quantity': quantity,
        'symbol': symbol,
        'order_type': order_type,
        'price': price,
        'timestamp': timestamp or datetime.datetime.now().isoformat()
    }
    return MockEvent(MockEventType.ORDER, data)

def create_mock_bar_event(symbol, open_price, high, low, close, volume, timestamp=None):
    """Create a mock bar event."""
    data = {
        'symbol': symbol,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'timestamp': timestamp or datetime.datetime.now().isoformat()
    }
    return MockEvent(MockEventType.BAR, data)
