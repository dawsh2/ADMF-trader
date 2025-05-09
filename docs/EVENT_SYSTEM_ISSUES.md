# Event System Issues and Standardization

## Overview

During the implementation and testing of the modular rewrite, we identified several inconsistencies and issues with the Event system. This document outlines these issues and proposes standardization guidelines to ensure consistent usage across the codebase.

## Identified Issues

### 1. Inconsistent Event Constructor Usage

Different parts of the codebase create Event objects in different ways:

```python
# Pattern 1: Direct constructor with EventType and data dictionary
event = Event(EventType.BAR, {'symbol': 'SPY', 'price': 100})

# Pattern 2: Factory method from event_utils
event = create_bar_event('SPY', timestamp, open_price, high_price, low_price, close_price)

# Pattern 3: Specialized event classes
event = BarEvent(symbol='SPY', open_price=100, ...)
```

During testing, we encountered errors like:
```
AttributeError: property 'type_property' of 'Event' object has no setter
```

This suggests incompatible changes to the Event class constructor without updating all usage points.

### 2. Event Type Inconsistencies

Different modules use slightly different event types for similar events:

```python
# In some modules:
EventType.PORTFOLIO_UPDATE

# In other modules:
EventType.PORTFOLIO
```

### 3. Missing Documentation

There is limited documentation on:
- What events flow through the system
- Which components should listen to which events
- The expected structure of event data for each event type
- Best practices for event creation and handling

### 4. Incomplete Import Handling

Some modules attempt to import functions that don't exist:

```python
# Example error encountered:
ImportError: cannot import name 'create_trade_close_event' from 'src.core.events.event_utils'
```

## Standardization Guidelines

### Event Creation

All code should use a consistent pattern for event creation:

1. **For simple events**: Use direct Event constructor:

```python
event = Event(EventType.ORDER, {
    'symbol': 'SPY',
    'quantity': 100,
    'direction': 'BUY',
    'order_type': 'MARKET'
})
```

2. **For complex events**: Use factory methods from event_utils:

```python
from src.core.events.event_utils import create_order_event

event = create_order_event(
    symbol='SPY',
    order_type='MARKET',
    quantity=100,
    direction='BUY'
)
```

### Event Types

Standardize on a single set of event types:

```python
class EventType(enum.Enum):
    # Data events
    BAR = 1
    TICK = 2
    
    # Trading events
    SIGNAL = 3
    ORDER = 4
    FILL = 5
    
    # Portfolio events
    POSITION = 6
    PORTFOLIO = 7  # Use this everywhere instead of PORTFOLIO_UPDATE
    TRADE = 8
    
    # Lifecycle events
    START = 9
    STOP = 10
    ERROR = 11
    
    # Backtest events
    BACKTEST_START = 12
    BACKTEST_END = 13
    
    # Optimization events
    OPTIMIZATION_START = 14
    OPTIMIZATION_END = 15
    
    # Misc events
    METRIC = 16
    PERFORMANCE = 17
```

### Event Data Structure

Each event type should have a well-defined data structure:

1. **BAR Event**:
```python
{
    'symbol': 'SPY',             # Required: Instrument symbol
    'timestamp': datetime,       # Required: Bar timestamp
    'open': 100.0,               # Required: Open price
    'high': 101.0,               # Required: High price
    'low': 99.0,                 # Required: Low price
    'close': 100.5,              # Required: Close price
    'volume': 1000               # Optional: Volume
}
```

2. **SIGNAL Event**:
```python
{
    'symbol': 'SPY',             # Required: Instrument symbol
    'direction': 'LONG',         # Required: 'LONG' or 'SHORT'
    'strength': 1.0,             # Optional: Signal strength (0.0-1.0)
    'timestamp': datetime,       # Optional: Signal generation time
    'rule_id': 'rule_123'        # Optional: Identifier for the rule
}
```

3. **ORDER Event**:
```python
{
    'id': 'order_123',           # Required: Unique order ID
    'symbol': 'SPY',             # Required: Instrument symbol
    'order_type': 'MARKET',      # Required: 'MARKET', 'LIMIT', 'STOP', etc.
    'direction': 'BUY',          # Required: 'BUY' or 'SELL'
    'quantity': 100,             # Required: Order quantity
    'price': 100.5,              # Optional: Price for limit/stop orders
    'timestamp': datetime,       # Optional: Order creation time
    'status': 'CREATED',         # Optional: Order status
    'rule_id': 'rule_123'        # Optional: Identifier for the source rule
}
```

4. **FILL Event**:
```python
{
    'id': 'fill_123',            # Required: Unique fill ID
    'order_id': 'order_123',     # Required: Order ID this fill belongs to
    'symbol': 'SPY',             # Required: Instrument symbol
    'direction': 'BUY',          # Required: 'BUY' or 'SELL'
    'quantity': 100,             # Required: Fill quantity
    'price': 100.2,              # Required: Fill price
    'timestamp': datetime,       # Optional: Fill timestamp
    'commission': 1.0,           # Optional: Commission cost
    'rule_id': 'rule_123'        # Optional: Identifier for the source rule
}
```

5. **PORTFOLIO Event**:
```python
{
    'timestamp': datetime,       # Required: Update timestamp
    'capital': 10000.0,          # Required: Available capital (cash)
    'full_equity': 15000.0,      # Required: Total equity (cash + positions)
    'closed_only_equity': 12000.0, # Optional: Equity counting only closed trades
    'closed_pnl': 2000.0,        # Optional: Realized P&L
    'market_value': 5000.0,      # Optional: Value of open positions
    'positions': {...}           # Optional: Current positions
}
```

## Immediate Actions

1. **Audit Event Usage**:
   - Review all code that creates Event objects
   - Update to use consistent patterns
   - Fix any inconsistencies in event data structure

2. **Fix Event Class Issues**:
   - Review Event constructor implementation
   - Ensure backward compatibility or update all usage points
   - Add validation for required fields

3. **Add Factory Methods**:
   - Implement any missing factory methods in event_utils.py
   - Create comprehensive tests for all factory methods

4. **Create Mocks for Testing**:
   - Develop standardized mock classes for Event-related testing
   - Ensure mocks properly emulate real components' behavior

5. **Improve Error Handling**:
   - Add clear error messages when Event construction fails
   - Validate event data at creation time

## Long-term Recommendations

1. **Event System Documentation**:
   - Create comprehensive documentation on the event system architecture
   - Document event flow through different modules
   - Provide usage examples for all event types

2. **Event Type Consistency**:
   - Consider using string-based event types for better extensibility
   - Add namespacing for module-specific events

3. **Event Validation Middleware**:
   - Implement event validation middleware in the EventBus
   - Reject events with invalid structure

4. **Event Visualization Tools**:
   - Create tools to visualize event flow for debugging
   - Add event flow logging for tracing issues

By implementing these recommendations, we can ensure a more robust and consistent event system throughout the codebase.