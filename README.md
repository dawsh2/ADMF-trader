# ADMF-Trader Framework

An algorithmic trading framework with modular, event-driven architecture.

## Directory Structure

```
ADMF-trader/
├── config/                 # Configuration files
│   └── backtest.yaml       # Backtest configuration
├── data/                   # Market data
├── results/                # Backtest results
├── src/                    # Source code
│   ├── analytics/          # Performance analysis
│   ├── core/               # Core components
│   │   ├── config/         # Configuration system
│   │   ├── di/             # Dependency injection
│   │   ├── events/         # Event system
│   │   └── utils/          # Utilities
│   ├── data/               # Data handling
│   ├── execution/          # Order execution
│   ├── risk/               # Risk management
│   └── strategy/           # Strategy components
│       ├── components/     # Strategy building blocks
│       └── implementations/ # Strategy implementations
├── debug_discovery.py      # Debug component discovery
├── generate_test_data.py   # Generate test data
└── run_backtest.py         # Run a backtest
```

## Quick Start

1. Generate test data:
   ```bash
   python generate_test_data.py --symbols AAPL,MSFT,GOOG --start-date 2023-01-01 --end-date 2023-12-31
   ```

2. Run a backtest:
   ```bash
   python run_backtest.py --config config/backtest.yaml
   ```

3. Debug component discovery (if needed):
   ```bash
   python debug_discovery.py
   ```

## Component Discovery System

The framework uses a discovery system to find and register components at runtime. This allows for a more modular and extensible architecture. The key components of this system are:

1. **Base Components**: All components (indicators, rules, strategies) inherit from the `Component` base class
2. **Component Registry**: The `Registry` class tracks available components
3. **Discovery Utility**: The `discover_components` function finds and registers components

To create a new strategy that will be automatically discovered:

1. Create a new Python module in `src/strategy/implementations/`
2. Define a strategy class that inherits from `Strategy`
3. Include a class-level `name` attribute for proper registration:

```python
class MyCustomStrategy(Strategy):
    # Class-level name for discovery
    name = "my_custom_strategy"
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        super().__init__(event_bus, data_handler, name or self.name, parameters)
        # Strategy implementation...
```

## Configuration System

The configuration system uses YAML files to provide flexible configuration:

```yaml
# Example strategy configuration
strategies:
  ma_crossover:
    enabled: true  # Enable/disable this strategy
    fast_window: 10  # Strategy parameters
    slow_window: 30
    symbols: ['AAPL', 'MSFT']
```

## Dependency Injection

The framework uses dependency injection to manage component dependencies. The core of this system is the `Container` class, which is responsible for creating and wiring components together.

## Event-Driven Architecture

The event system provides asynchronous communication between components:

1. **Events**: Various event types (Bar, Signal, Order, Fill)
2. **Event Bus**: Central communication hub
3. **Event Handlers**: Components that process events
4. **Event Emitters**: Components that emit events

## Adding New Components

To add new components to the system:

1. **New Indicator**: Create a class in `src/strategy/components/indicators/` that inherits from `Indicator`
2. **New Rule**: Create a class in `src/strategy/components/rules/` that inherits from `Rule`
3. **New Strategy**: Create a class in `src/strategy/implementations/` that inherits from `Strategy`

## Troubleshooting

If strategies are not being discovered properly:

1. Run the debug script: `python debug_discovery.py`
2. Check that you have a class-level `name` attribute in your strategy
3. Verify your strategy inherits correctly from the `Strategy` base class
4. Verify the package structure and imports in `__init__.py` files
