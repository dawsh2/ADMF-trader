# Events Module

The `src/core/events` module implements a powerful event system based on the publish/subscribe (pub/sub) pattern. It enables loosely coupled communication between components throughout the ADMF-Trader system.

## Overview

The event system allows components to communicate without direct dependencies. Publishers send events to the event bus, and subscribers receive only the events they're interested in. This design creates a flexible, maintainable architecture where components can be added, removed, or modified without affecting others.

## Key Components

### EventBus

The `EventBus` class is the central message broker that connects publishers and subscribers:

```python
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event

# Create event bus
event_bus = EventBus()

# Subscribe to events
event_bus.subscribe(EventType.BAR, strategy.on_bar)

# Publish an event
bar_event = BarEvent("AAPL", timestamp, open_price, high, low, close, volume)
event_bus.publish(bar_event)
```

#### Features

The EventBus provides several advanced features:

1. **Priority-based Processing**: Subscribers can be registered with priority levels to ensure proper event handling order:
   ```python
   event_bus.subscribe(EventType.FILL, portfolio.on_fill, priority=EventBus.HIGH_PRIORITY)
   ```

2. **Deduplication**: Prevents duplicate processing of signals and orders with configurable strategies:
   ```python
   event_bus = EventBus(deduplication_strategy=EventBus.DEDUP_RULE)
   ```

3. **Event Batching**: Improves performance by processing events in batches:
   ```python
   event_bus.start_batch()
   # Publish multiple events...
   event_bus.end_batch()  # Process all at once
   ```

4. **Performance Metrics**: Provides detailed metrics on event processing:
   ```python
   event_bus.enable_metrics_collection()
   metrics = event_bus.get_metrics()
   ```

5. **Event Replay**: Records and replays events for debugging:
   ```python
   event_bus.enable_replay_recording()
   # System runs...
   event_bus.replay_events()  # Replay all events
   ```

6. **Memory Management**: Uses weak references to prevent memory leaks

### Event Types and Classes

The module defines standard event types and specialized event classes:

```python
# Event Types Enum
class EventType(Enum):
    BAR = auto()           # Market data
    SIGNAL = auto()        # Trading signals
    ORDER = auto()         # Order requests
    FILL = auto()          # Order fills
    # ... and more
```

Specialized event classes provide type-safe interfaces:

```python
# Bar event with market data
bar_event = BarEvent(
    symbol="AAPL",
    timestamp=datetime.now(),
    open_price=150.25,
    high_price=151.80,
    low_price=149.90,
    close_price=151.50,
    volume=1000000
)

# Signal event for trading
signal = SignalEvent(
    signal_value=SignalEvent.BUY,
    price=151.50,
    symbol="AAPL",
    rule_id="ma_crossover_5_20"
)
```

### EventManager

The `EventManager` coordinates event flow between components, ensuring proper initialization and shutdown:

```python
# Create manager with event bus
manager = EventManager(event_bus)

# Register components with event types they handle
manager.register_component("strategy", strategy, [EventType.BAR])
manager.register_component("risk_manager", risk_manager, [EventType.SIGNAL])
```

## Event Flow

A typical event flow in the system:

1. **Data Handler** emits `BAR` events with market data
2. **Strategy** receives `BAR` events and emits `SIGNAL` events
3. **Risk Manager** receives `SIGNAL` events and emits `ORDER` events
4. **Order Manager** receives `ORDER` events and sends to broker
5. **Broker** processes orders and emits `FILL` events
6. **Portfolio** receives `FILL` events and updates positions

## Best Practices

When working with the event system:

1. **Event Design**: Keep events simple and focused on a single purpose
2. **Handler Complexity**: Keep event handlers concise and efficient
3. **Error Handling**: Handle exceptions in event handlers to prevent disrupting the event flow
4. **Priorities**: Use priorities sparingly and only when necessary
5. **Consumption**: Mark events as consumed when appropriate to stop further processing

## Backward Compatibility

For backward compatibility, the following method aliases are provided:

- `emit()` → `publish()`
- `register()` → `subscribe()`
- `unregister()` → `unsubscribe()`

We recommend using the standard pub/sub terminology in new code.

## Example Usage

### Creating and Publishing Events

```python
from src.core.events.event_types import EventType, BarEvent
from datetime import datetime

# Create a bar event
bar = BarEvent(
    symbol="AAPL",
    timestamp=datetime.now(),
    open_price=150.25,
    high_price=151.80,
    low_price=149.90,
    close_price=151.50,
    volume=1000000
)

# Publish the event
event_bus.publish(bar)
```

### Subscribing to Events

```python
class Strategy:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        
        # Subscribe to events
        event_bus.subscribe(EventType.BAR, self.on_bar)
        
    def on_bar(self, event):
        # Process the bar event
        symbol = event.get_symbol()
        close = event.get_close()
        
        # Generate signals based on data
        if self.should_buy(symbol, close):
            signal = SignalEvent(
                SignalEvent.BUY, 
                close, 
                symbol, 
                rule_id="strategy_rule_1"
            )
            self.event_bus.publish(signal)
```

### Component Integration

```python
# In system_bootstrap.py
def _setup_event_system(self, container, config):
    """Set up the event system components."""
    event_bus = EventBus()
    event_manager = EventManager(event_bus)
    
    container.register_instance("event_bus", event_bus)
    container.register_instance("event_manager", event_manager)
    
    # Register components in order
    data_handler = container.get("data_handler")
    event_manager.register_component("data_handler", data_handler, [EventType.BAR])
    
    strategy = container.get("strategy")
    event_manager.register_component("strategy", strategy, [EventType.BAR])
    
    # More components...
```

## Advanced Features

### Event Batching

```python
# Start batching mode
event_bus.start_batch()

# Publish multiple events
for symbol in symbols:
    for i in range(len(data[symbol])):
        bar = create_bar_event(symbol, data[symbol][i])
        event_bus.publish(bar)  # Events are queued, not processed yet

# Process all events at once
event_bus.end_batch()
```

### Performance Metrics

```python
# Enable metrics collection
event_bus.enable_metrics_collection(window_size=1000)

# Run system...

# Get detailed metrics
metrics = event_bus.get_metrics()
print(f"Total events: {metrics['total_events']}")
print(f"Events per second: {metrics['events_per_second']}")
print(f"Average processing time: {metrics['processing_times_ms']}")
```

### Event Replay

```python
# Enable recording for debugging
event_bus.enable_replay_recording()

# Run system...

# Check what was recorded
history_info = event_bus.get_replay_history_info()
print(f"Recorded {history_info['count']} events")

# Replay events for debugging
event_bus.replay_events(start_index=0, end_index=100)
```
