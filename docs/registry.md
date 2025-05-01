# Using Registry and Discovery in ADMF-Trader

## Component Registry and Discovery System

The Registry and Discovery utilities provide a powerful mechanism for managing components in your trading system. These features enable:

1. **Dynamic component loading** - discover components at runtime
2. **Reduced coupling** - code doesn't need to know about specific implementations 
3. **Configuration-driven behavior** - switch components via configuration
4. **Plugin architecture** - easily extend the system with new components

## The Registry Pattern

The Registry pattern provides a central place to store and retrieve components by name.

### Key Benefits

- **Late binding** - Components can be created when needed
- **Name-based lookup** - Get components by string names (from config)
- **Central management** - Single place to find all available components
- **Reduced imports** - No need to import all component classes everywhere

### Registry Implementation

The `Registry` class in `src/core/utils/registry.py` provides these key methods:

```python
# Register a component
registry.register(name, component)

# Get a component by name
component = registry.get(name)

# List all registered components
available_components = registry.list()

# Check if a component exists
if name in registry:
    # do something
```

### Registry Usage Examples

#### Strategy Registry

```python
from src.core.utils.registry import Registry
from src.strategy.strategy_base import Strategy

# Create a registry for strategies
strategy_registry = Registry()

# Register strategies manually
strategy_registry.register("ma_crossover", MACrossoverStrategy)
strategy_registry.register("rsi", RSIStrategy)
strategy_registry.register("momentum", MomentumStrategy)

# Use registry to create strategies from config
strategy_name = config.get_section("backtest").get("strategy")
strategy_class = strategy_registry.get(strategy_name)
if strategy_class:
    strategy = strategy_class(event_bus, data_handler)
```

#### Data Source Registry

```python
# Create a registry for data sources
data_source_registry = Registry()

# Register data sources
data_source_registry.register("csv", CSVDataSource)
data_source_registry.register("api", APIDataSource)
data_source_registry.register("database", DatabaseSource)

# Create data source from config
source_type = config.get_section("data").get("source")
source_class = data_source_registry.get(source_type)
data_source = source_class(**source_params)
```

## Component Discovery

The discovery mechanism builds on the registry by automatically finding and registering components.

### Key Benefits

- **Automatic registration** - No need to manually register components
- **Simplified architecture** - Just add a new file and it's discovered
- **Configuration control** - Enable/disable components via config
- **Reduced maintenance** - Don't need to update registration code

### Discovery Implementation

The `discover_components` function in `src/core/utils/discovery.py` scans packages for classes:

```python
discover_components(
    package_name,    # Package to scan
    base_class,      # Base class components must inherit from
    registry=None,   # Optional registry to register with
    enabled_only=True,  # Only discover enabled components
    config=None      # Config to check for enabled status
)
```

### Discovery Usage Examples

#### Discovering Strategies

```python
from src.core.utils.discovery import discover_components
from src.strategy.strategy_base import Strategy

# Create registry
strategy_registry = Registry()

# Discover all strategy implementations
strategies = discover_components(
    package_name="src.strategy.implementations", 
    base_class=Strategy,
    registry=strategy_registry,
    config=config
)

print(f"Discovered {len(strategies)} strategies:")
for name in strategy_registry.list():
    print(f"- {name}")
```

#### Discovering Indicators

```python
from src.core.utils.discovery import discover_components
from src.strategy.components.indicators.indicator_base import Indicator

# Create registry  
indicator_registry = Registry()

# Discover all indicators
indicators = discover_components(
    package_name="src.strategy.components.indicators",
    base_class=Indicator,
    registry=indicator_registry
)

# Now indicator_registry contains all indicators
```

## Integration with Configuration System

The registry and discovery mechanisms work well with the configuration system:

```yaml
# config.yaml
strategies:
  # Enable/disable specific strategies
  ma_crossover:
    enabled: true
    fast_window: 10
    slow_window: 30
  
  rsi_strategy:
    enabled: false
    
  momentum:
    enabled: true
    lookback: 20
```

```python
# Only enabled strategies will be discovered
discovered = discover_components(
    package_name="src.strategy.implementations",
    base_class=Strategy,
    registry=strategy_registry,
    enabled_only=True,
    config=config
)
```

## Integration with Dependency Injection

The registry and container work together seamlessly:

```python
# Discover components
strategy_registry = Registry()
discover_components("src.strategy.implementations", Strategy, strategy_registry)

# Register with container factory
def create_strategy(container):
    strategy_name = container.config.get_section("backtest").get("strategy")
    strategy_class = strategy_registry.get(strategy_name)
    strategy = strategy_class(
        container.get("event_bus"),
        container.get("data_handler")
    )
    return strategy

container.register_factory("strategy", create_strategy)
```

## Implementing a Pluggable Component System

With registry, discovery, and DI, you can create a fully pluggable system:

1. **Define component interfaces** - Create base classes for all component types
2. **Organize by package** - Put implementations in well-structured packages
3. **Discover automatically** - Use discovery to find all implementations
4. **Configure at runtime** - Select components via configuration
5. **Create via container** - Let the DI container handle instantiation

### Component Organization Example

```
src/
├── strategy/
│   ├── components/
│   │   ├── indicators/
│   │   │   ├── __init__.py
│   │   │   ├── indicator_base.py    # Base interface
│   │   │   ├── moving_average.py    # Implementation
│   │   │   ├── rsi.py               # Implementation
│   │   │   └── macd.py              # Implementation
│   │   │
│   │   ├── features/
│   │   │   ├── feature_base.py      # Base interface
│   │   │   └── ...
│   │   │
│   │   └── rules/
│   │       ├── rule_base.py         # Base interface
│   │       └── ...
│   │
│   └── implementations/
│       ├── __init__.py
│       ├── strategy_base.py         # Base interface
│       ├── ma_crossover.py          # Implementation
│       └── ...
```

## Best Practices

1. **Consistent Base Classes** - Ensure all components inherit from a proper base class
2. **Clear Package Structure** - Organize code so discovery can find components
3. **Unique Names** - Components should have unique names in their registry
4. **Config Integration** - Use configuration to control which components are enabled
5. **Lazy Loading** - Only create components when needed
6. **Documentation** - Document available components for users
7. **Testing** - Test discovery to ensure all components are found

## Conclusion

The Registry and Discovery utilities provide powerful mechanisms for building a flexible, extensible trading system. By leveraging these patterns, you can create a system that's easily configurable and maintainable, while reducing coupling between components.



# Centralized Order Registry Architecture

## Core Concept

The centralized Order Registry pattern separates order tracking from order processing logic. It serves as the single source of truth for order state and provides a consistent view to all system components.

## Components Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌────────────────┐
│                 │     │                 │     │                │
│  Strategy       │     │  Risk Manager   │     │  Order Manager │
│                 │     │                 │     │                │
└────────┬────────┘     └────────┬────────┘     └────────┬───────┘
         │                       │                       │
         │ Signal Event          │ Order Event           │ Order Ops
         ▼                       ▼                       ▼
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│                           Event Bus                               │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│                      Order Registry (NEW)                         │
│                                                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────┐   │
│  │ Order Store   │  │ State Machine │  │ Validation Logic    │   │
│  └───────────────┘  └───────────────┘  └─────────────────────┘   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                │     │                 │     │                 │
│  Broker        │     │  Portfolio      │     │  Analytics      │
│                │     │                 │     │                 │
└────────────────┘     └─────────────────┘     └─────────────────┘
```

## Key Components

### 1. Order Registry (New Component)

The Order Registry is the core of the new design:

```python
class OrderRegistry:
    """Central registry for tracking all orders in the system."""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.orders = {}  # order_id -> Order
        self.state_changes = []  # Ordered history of state changes
        self._register_handlers()
    
    def _register_handlers(self):
        """Register event handlers for order-related events."""
        self.event_bus.register(EventType.ORDER, self.on_order)
        self.event_bus.register(EventType.FILL, self.on_fill)
        self.event_bus.register(EventType.ORDER_CANCEL, self.on_cancel)
    
    def register_order(self, order):
        """Register a new order in the system."""
        # Validate order
        if not self._validate_order(order):
            return False
            
        # Store order and emit state change event
        self.orders[order.order_id] = order
        self._emit_state_change(order, "REGISTERED")
        return True
    
    def update_order_status(self, order_id, new_status, **details):
        """Update an order's status with validation."""
        if order_id not in self.orders:
            return False
            
        order = self.orders[order_id]
        
        # Validate state transition
        if not self._valid_transition(order.status, new_status):
            return False
            
        # Update order status
        old_status = order.status
        order.status = new_status
        
        # Update additional details (e.g., fill information)
        for key, value in details.items():
            if hasattr(order, key):
                setattr(order, key, value)
                
        # Record and emit state change
        self._emit_state_change(order, f"{old_status} -> {new_status}")
        return True
    
    def get_order(self, order_id):
        """Get an order by ID with safe error handling."""
        return self.orders.get(order_id)
    
    def _valid_transition(self, current_status, new_status):
        """Validate state transitions using a state machine."""
        # State machine for order lifecycle
        valid_transitions = {
            OrderStatus.CREATED: [OrderStatus.PENDING, OrderStatus.CANCELED],
            OrderStatus.PENDING: [OrderStatus.PARTIAL, OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELED],
            OrderStatus.PARTIAL: [OrderStatus.FILLED, OrderStatus.CANCELED],
            OrderStatus.FILLED: [],  # Terminal state
            OrderStatus.CANCELED: [],  # Terminal state
            OrderStatus.REJECTED: [],  # Terminal state
        }
        
        return new_status in valid_transitions.get(current_status, [])
    
    def _emit_state_change(self, order, transition_description):
        """Emit an event for order state change."""
        event = Event(
            EventType.ORDER_STATE_CHANGE,
            {
                'order_id': order.order_id,
                'status': order.status.value,
                'transition': transition_description,
                'timestamp': datetime.datetime.now(),
                'order_snapshot': order.to_dict()
            }
        )
        
        # Record in history
        self.state_changes.append((order.order_id, transition_description, datetime.datetime.now()))
        
        # Emit event
        self.event_bus.emit(event)
    
    def _validate_order(self, order):
        """Validate order attributes."""
        # Simple validation logic
        if not order.symbol or not order.order_type or not order.direction:
            return False
            
        if order.quantity <= 0:
            return False
            
        if order.order_type in ['LIMIT', 'STOP'] and not order.price:
            return False
            
        return True
    
    # Event handlers
    def on_order(self, order_event):
        """Handle order events."""
        # Extract order details from event
        # Create and register order
        # Notify broker that order is ready for processing
    
    def on_fill(self, fill_event):
        """Handle fill events."""
        # Find order and validate fill
        # Update order with fill details
        # Emit state change event
    
    def on_cancel(self, cancel_event):
        """Handle cancel events."""
        # Find order and validate cancellation
        # Update order status
        # Emit state change event
```

### 2. Modified Broker Component

The broker now only handles order execution after confirmation from the registry:

```python
class BrokerWithRegistry:
    """Broker that works with the centralized Order Registry."""
    
    def __init__(self, event_bus, order_registry):
        self.event_bus = event_bus
        self.order_registry = order_registry
        self._register_handlers()
    
    def _register_handlers(self):
        """Register handlers for broker-related events."""
        # Process orders only AFTER they've been registered
        self.event_bus.register(EventType.ORDER_STATE_CHANGE, self.on_order_state_change)
    
    def on_order_state_change(self, event):
        """Process orders only when they're properly registered."""
        # Only process orders that have just been registered
        if event.data['transition'] == "REGISTERED":
            order_id = event.data['order_id']
            order = self.order_registry.get_order(order_id)
            
            if order:
                # Now it's safe to process the order
                self.process_order(order)
    
    def process_order(self, order):
        """Process an order and generate a fill."""
        # Standard order processing logic
        # Generate fill event with the order_id reference
        fill_event = create_fill_event(
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.quantity,
            price=calculate_fill_price(order),
            order_id=order.order_id  # Explicit reference
        )
        
        # Emit fill event
        self.event_bus.emit(fill_event)
```

### 3. Modified Order Manager

The Order Manager now delegates state tracking to the registry:

```python
class OrderManagerWithRegistry:
    """Order manager that works with the centralized Order Registry."""
    
    def __init__(self, event_bus, order_registry):
        self.event_bus = event_bus
        self.order_registry = order_registry
        self._register_handlers()
    
    def _register_handlers(self):
        """Register event handlers."""
        self.event_bus.register(EventType.SIGNAL, self.on_signal)
    
    def on_signal(self, signal_event):
        """Create orders from signals."""
        # Extract signal details
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        
        # Create order
        order_id = str(uuid.uuid4())
        order = Order(
            symbol=symbol,
            order_type='MARKET',
            direction='BUY' if signal_value > 0 else 'SELL',
            quantity=calculate_position_size(symbol, price),
            price=price,
            order_id=order_id
        )
        
        # Create order event
        order_event = create_order_event(
            symbol=symbol,
            order_type=order.order_type,
            direction=order.direction,
            quantity=order.quantity,
            price=order.price,
            order_id=order_id
        )
        
        # Emit order event (will be handled by registry)
        self.event_bus.emit(order_event)
    
    def cancel_order(self, order_id):
        """Request order cancellation."""
        # Create and emit cancel event
        cancel_event = Event(
            EventType.ORDER_CANCEL,
            {'order_id': order_id}
        )
        
        self.event_bus.emit(cancel_event)
```

## Benefits of This Architecture

1. **Single Source of Truth**: The Order Registry is the only authoritative source for order state
2. **Explicit Sequencing**: Orders must be registered before they can be processed
3. **Validation**: State transitions are explicitly validated
4. **Event History**: Complete audit trail of order state changes
5. **Thread Safety**: Atomic operations with proper validation
6. **No Timing Hacks**: No reliance on delays or retries
7. **Clear Responsibility**: Each component has a well-defined role

## Implementation Steps

1. Create the `OrderRegistry` class
2. Update the EventType enum to include `ORDER_STATE_CHANGE`
3. Modify Broker to work with OrderRegistry
4. Update OrderManager to delegate to registry
5. Update EventManager component registration
6. Integrate with existing code

## Testing Strategy

1. **Unit Tests**:
   - Test OrderRegistry state transitions
   - Test validation logic
   - Test event emissions

2. **Integration Tests**:
   - Test complete order→fill flow
   - Test cancel flow
   - Test error cases and recovery

3. **Load Tests**:
   - Test with high volume of concurrent orders
   - Test with various order timing patterns