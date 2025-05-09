# Modular Architecture Guide

## Overview

The ADMF-trader system has been rewritten with a modular architecture to improve maintainability, testability, and extensibility. This guide explains the architecture, key design principles, and how different modules interact.

## Core Design Principles

1. **Separation of Concerns**
   - Each module focuses on a specific domain
   - Components have well-defined responsibilities
   - Minimal dependencies between components

2. **Event-Driven Architecture**
   - Components communicate through events
   - Loose coupling between components
   - Asynchronous processing where appropriate

3. **Component Lifecycle Management**
   - Standard initialization, start, stop, reset patterns
   - Proper resource management
   - State isolation for testing

4. **Configuration-Driven**
   - Component behavior controlled through configuration
   - Validation of configuration parameters
   - Sensible defaults with clear overrides

5. **Testability**
   - Components designed for unit testing
   - Mock implementations for dependencies
   - Integration testing through well-defined interfaces

## System Architecture

The system is divided into the following primary modules:

```
ADMF-trader
├── Core
│   ├── Component Base
│   ├── Event System
│   ├── Configuration
│   └── Trade Repository
│
├── Data
│   ├── Data Handlers
│   ├── Data Transformers
│   └── Data Cache
│
├── Strategy
│   ├── Strategy Base
│   ├── Signal Generation
│   └── Strategy Registry
│
├── Risk
│   ├── Position Management
│   ├── Portfolio Management
│   └── Risk Limits
│
├── Execution
│   ├── Order Management
│   ├── Broker Interfaces
│   └── Backtest
│
├── Analytics
│   ├── Performance Metrics
│   ├── Reporting
│   └── Visualization
│
└── Optimization
    ├── Hyperparameter Optimization
    ├── Feature Selection
    └── Walk-Forward Testing
```

## Module Descriptions

### Core Module

The Core module provides foundational components used throughout the system.

**Components**:
- **Component Base**: Abstract base class for all components with lifecycle methods
- **Event System**: Event bus, event types, and event utilities
- **Configuration**: Configuration loading, validation, and handling
- **Trade Repository**: Centralized storage for trade records

### Data Module

The Data module handles data acquisition, transformation, and storage.

**Components**:
- **Data Handlers**: Interfaces for different data sources (CSV, API, database)
- **Data Transformers**: Tools for feature engineering and data preparation
- **Data Cache**: Efficient storage and retrieval of market data

### Strategy Module

The Strategy module implements trading strategies and signal generation.

**Components**:
- **Strategy Base**: Abstract base class for all strategies
- **Signal Generation**: Components that generate trading signals
- **Strategy Registry**: Dynamic registration and loading of strategies

### Risk Module

The Risk module manages positions, portfolios, and risk controls.

**Components**:
- **Position Management**: Tracking of individual positions and trades
- **Portfolio Management**: Portfolio-level tracking and accounting
- **Risk Limits**: Position sizing and risk control mechanisms

### Execution Module

The Execution module handles order management and execution.

**Components**:
- **Order Management**: Creation, validation, and tracking of orders
- **Broker Interfaces**: Communication with execution venues
- **Backtest**: Simulation of trading strategies on historical data

### Analytics Module

The Analytics module provides performance analysis and reporting.

**Components**:
- **Performance Metrics**: Calculation of trading performance metrics
- **Reporting**: Generation of backtest and trading reports
- **Visualization**: Charts and graphs for performance analysis

### Optimization Module

The Optimization module helps improve trading strategies.

**Components**:
- **Hyperparameter Optimization**: Finding optimal strategy parameters
- **Feature Selection**: Identifying the most important features
- **Walk-Forward Testing**: Validation of strategy robustness

## Component Lifecycle

All components follow a standardized lifecycle:

1. **Initialization**: Component receives its dependencies
   ```python
   def initialize(self, context):
       self.event_bus = context.get('event_bus')
       self.config = context.get('config')
   ```

2. **Start**: Component begins operation
   ```python
   def start(self):
       self.running = True
       # Subscribe to events, initialize resources
   ```

3. **Processing**: Component performs its function
   ```python
   def on_event(self, event):
       # Process events and perform actions
   ```

4. **Stop**: Component ceases operation
   ```python
   def stop(self):
       self.running = False
       # Unsubscribe from events, release resources
   ```

5. **Reset**: Component returns to initial state
   ```python
   def reset(self):
       # Clear internal state for reuse
       self.data = []
       self.processed_events = 0
   ```

## Event Flow

Events flow through the system in a specific pattern:

1. **Data Events** → **Strategy Components** → **Signal Events**
2. **Signal Events** → **Order Management** → **Order Events**
3. **Order Events** → **Broker** → **Fill Events**
4. **Fill Events** → **Position Management** → **Portfolio Events**
5. **Portfolio Events** → **Analytics** → **Performance Events**

Each component subscribes to relevant events and publishes new events based on its processing.

## Configuration System

Components are configured through a hierarchical configuration system:

```python
config = {
    'data': {
        'source': 'csv',
        'file_path': 'data/SPY_1min.csv',
        'timeframe': '1min'
    },
    'strategy': {
        'name': 'ma_crossover',
        'params': {
            'short_window': 10,
            'long_window': 30
        }
    },
    'risk': {
        'position_size': 0.02,
        'max_drawdown': 0.15
    },
    'backtest': {
        'initial_capital': 100000,
        'close_positions_eod': True
    }
}
```

## Development Guidelines

When developing new components or modifying existing ones:

1. **Follow the Component Pattern**
   - Inherit from the Component base class
   - Implement lifecycle methods properly
   - Document component purpose and interfaces

2. **Use the Event System Correctly**
   - Follow standard event creation patterns
   - Subscribe only to events your component needs
   - Publish events with standardized data structures

3. **Manage State Carefully**
   - Initialize state in the constructor or initialize method
   - Ensure proper state reset for reuse
   - Avoid shared mutable state between components

4. **Handle Errors Gracefully**
   - Log errors with appropriate severity
   - Fail early with clear error messages
   - Document error handling behavior

5. **Write Tests**
   - Unit tests for component behavior
   - Integration tests for component interactions
   - Use mock dependencies for isolation

## Common Patterns

### Factory Pattern

Creating components with proper configuration:

```python
def create_strategy(strategy_config):
    strategy_type = strategy_config.get('type')
    if strategy_type == 'ma_crossover':
        return MACrossoverStrategy('ma_strategy', strategy_config)
    elif strategy_type == 'mean_reversion':
        return MeanReversionStrategy('mr_strategy', strategy_config)
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
```

### Observer Pattern

Components observe events and react:

```python
def initialize(self, context):
    self.event_bus = context.get('event_bus')
    self.event_bus.subscribe(EventType.BAR, self.on_bar)

def on_bar(self, event):
    # Process bar event
    bar_data = event.get_data()
    # Do something with the data
```

### Strategy Pattern

Different algorithms with a common interface:

```python
class Strategy(Component):
    def generate_signals(self, data):
        raise NotImplementedError("Subclasses must implement generate_signals")

class MACrossoverStrategy(Strategy):
    def generate_signals(self, data):
        # Implement MA crossover logic
```

### Command Pattern

Encapsulating operations as objects:

```python
class Order:
    def __init__(self, symbol, direction, quantity):
        self.symbol = symbol
        self.direction = direction
        self.quantity = quantity

class OrderManager:
    def submit_order(self, order):
        # Process and submit the order
```

## Conclusion

By following these architecture principles and guidelines, we can maintain a clean, modular, and extensible trading system. The modular design allows for easy testing, extension, and maintenance, while the event-driven approach provides loose coupling between components.