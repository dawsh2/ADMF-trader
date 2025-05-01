# ADMF-Trader API Guide

This document provides a detailed overview of the ADMF-Trader API, focusing on key interfaces, common usage patterns, and examples for developers to extend and work with the system.

## Table of Contents

1. [Core System Components](#core-system-components)
2. [Event System](#event-system)
3. [Creating Strategies](#creating-strategies)
4. [Data Handling](#data-handling)
5. [Risk Management](#risk-management)
6. [Order Execution](#order-execution)
7. [Backtesting](#backtesting)
8. [Analytics and Reporting](#analytics-and-reporting)
9. [Common Patterns and Best Practices](#common-patterns-and-best-practices)

## Core System Components

### Bootstrapping the System

The `Bootstrap` class in `src/core/system_bootstrap.py` is the main entry point for initializing the system. It handles:

- Loading configuration
- Setting up the event system
- Discovering and registering components
- Initializing the dependency injection container

```python
from src.core.system_bootstrap import Bootstrap

# Initialize with configuration
bootstrap = Bootstrap(
    config_files=["config/your_config.yaml"],
    log_level="INFO",
    log_file="backtest.log"
)

# Setup the system
container, config = bootstrap.setup()

# Access components
backtest = container.get("backtest")
data_handler = container.get("data_handler")
strategy = container.get("strategy")
```

### Dependency Injection Container

The `Container` class in `src/core/di/container.py` provides dependency management:

```python
from src.core.di.container import Container

# Create a container
container = Container()

# Register a component
container.register_instance("component_name", component_instance)

# Get a component
component = container.get("component_name")

# Check if a component exists
if container.has("component_name"):
    # Use the component
    pass
```

### Configuration Management

The `Config` class in `src/core/config/config.py` handles configuration:

```python
from src.core.config.config import Config

# Create a config
config = Config()

# Load config from file
config.load_file("config/your_config.yaml")

# Load from environment variables
config.load_env(prefix="APP_")

# Access config sections and values
backtest_config = config.get_section("backtest")
symbols = backtest_config.get("symbols", [])
initial_capital = backtest_config.get_float("initial_capital", 100000.0)
```

## Event System

The event system is the backbone of ADMF-Trader, providing communication between components.

### Event Types

Event types are defined in `src/core/events/event_types.py`:

```python
from src.core.events.event_types import EventType, Event

# Available event types
# EventType.BAR - Market data bar updates
# EventType.SIGNAL - Trading signals from strategies
# EventType.ORDER - Order instructions
# EventType.FILL - Order fill notifications
# EventType.TRADE - Completed trade records

# Create an event
event = Event(
    type=EventType.SIGNAL,
    data={"symbol": "AAPL", "signal_value": 1},
    timestamp="2024-01-01 10:00:00"
)
```

### Event Bus

The `EventBus` class in `src/core/events/event_bus.py` handles event distribution:

```python
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event

# Create an event bus
event_bus = EventBus()

# Register a handler with priority
def handle_signal(signal_event):
    # Process the signal
    print(f"Received signal: {signal_event.get_signal_value()}")

event_bus.register(EventType.SIGNAL, handle_signal, priority=10)

# Emit an event
signal_event = Event(EventType.SIGNAL, {"symbol": "AAPL", "signal_value": 1})
event_bus.emit(signal_event)

# Unregister a handler
event_bus.unregister(EventType.SIGNAL, handle_signal)

# Reset the event bus
event_bus.reset()
```

### Event Manager

The `EventManager` class in `src/core/events/event_manager.py` provides component registration:

```python
from src.core.events.event_manager import EventManager
from src.core.events.event_types import EventType

# Create an event manager
event_manager = EventManager(event_bus)

# Register a component with event types
event_manager.register_component(
    "strategy", 
    strategy_instance, 
    [EventType.BAR]
)
```

### Event Utilities

The `event_utils.py` module provides helper functions for creating events:

```python
from src.core.events.event_utils import create_signal_event, create_order_event

# Create a signal event
signal = create_signal_event(
    signal_value=1,  # 1 for buy, -1 for sell
    price=100.50,
    symbol="AAPL",
    timestamp="2024-01-01 10:00:00"
)

# Create an order event
order = create_order_event(
    direction="BUY",
    quantity=100,
    symbol="AAPL",
    order_type="MARKET",
    price=100.50,
    timestamp="2024-01-01 10:00:00"
)
```

## Creating Strategies

### Strategy Base Class

All strategies inherit from the `Strategy` base class in `src/strategy/strategy_base.py`:

```python
from src.strategy.strategy_base import Strategy
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event

class MyCustomStrategy(Strategy):
    # Define name as a class variable for discovery
    name = "my_custom_strategy"
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        super().__init__(event_bus, data_handler, name or self.name, parameters)
        
        # Extract parameters with defaults
        self.my_param_1 = self.parameters.get('my_param_1', 10)
        self.my_param_2 = self.parameters.get('my_param_2', 20)
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        # Call parent configure first
        super().configure(config)
        
        # Update strategy-specific parameters
        self.my_param_1 = self.parameters.get('my_param_1', 10)
        self.my_param_2 = self.parameters.get('my_param_2', 20)
    
    def on_bar(self, bar_event):
        """Process a market data bar event."""
        # Extract data from bar event
        symbol = bar_event.get_symbol()
        
        # Skip if not in our symbol list
        if symbol not in self.symbols:
            return None
        
        # Extract price data
        price = bar_event.get_close()
        timestamp = bar_event.get_timestamp()
        
        # Implement your strategy logic here
        # ...
        
        # Generate a signal if conditions are met
        signal_value = 1  # Buy signal
        
        # Create and emit signal event
        signal = create_signal_event(
            signal_value=signal_value,
            price=price,
            symbol=symbol,
            timestamp=timestamp
        )
        
        if self.event_bus:
            self.event_bus.emit(signal)
        
        return signal
    
    def reset(self):
        """Reset the strategy state."""
        # Reset any strategy-specific state
        # Call parent reset
        super().reset()
```

### Example: Moving Average Crossover Strategy

Here's a simplified example of the moving average crossover strategy:

```python
from src.strategy.strategy_base import Strategy
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event

class MACrossoverStrategy(Strategy):
    name = "ma_crossover"
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        super().__init__(event_bus, data_handler, name or self.name, parameters)
        
        # Extract parameters
        self.fast_window = self.parameters.get('fast_window', 5)
        self.slow_window = self.parameters.get('slow_window', 15)
        self.price_key = self.parameters.get('price_key', 'close')
        
        # Internal state for data storage
        self.data = {symbol: [] for symbol in self.symbols}
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
    
    def on_bar(self, bar_event):
        # Implementation details...
        # See src/strategy/implementations/ma_crossover.py for full implementation
        pass
```

## Data Handling

### Data Handler

The data handling system loads and processes market data:

```python
from src.data.historical_data_handler import HistoricalDataHandler
from src.data.sources.csv_handler import CSVDataSource

# Create a data source
data_source = CSVDataSource("./data")

# Create a bar emitter (sends bar events to the event bus)
bar_emitter = BarEmitter("bar_emitter", event_bus)

# Create a data handler
data_handler = HistoricalDataHandler(data_source, bar_emitter)

# Load data
data_handler.load_data(
    symbols=["AAPL", "MSFT"], 
    start_date="2023-01-01",
    end_date="2023-12-31",
    timeframe="1d"
)

# Get the next bar for a symbol
bar = data_handler.get_next_bar("AAPL")
```

### Data Source Interface

Create custom data sources by implementing the `DataSourceBase` interface:

```python
from src.data.data_source_base import DataSourceBase

class MyCustomDataSource(DataSourceBase):
    def __init__(self, config_params):
        super().__init__()
        # Initialize with configuration
        
    def load_data(self, symbol, timeframe, start_date, end_date):
        # Load data for the given parameters
        # Return a DataFrame with the expected columns
        pass
```

## Risk Management

### Portfolio Management

The `PortfolioManager` class tracks positions and portfolio state:

```python
from src.risk.portfolio.portfolio import PortfolioManager

# Create a portfolio manager
portfolio = PortfolioManager(event_bus, initial_cash=100000.0)

# Get portfolio state
equity = portfolio.equity
cash = portfolio.cash
positions = portfolio.positions

# Get position for a symbol
position = portfolio.get_position("AAPL")
if position:
    quantity = position.quantity
    avg_cost = position.avg_cost
    
# Get equity curve as DataFrame
equity_curve = portfolio.get_equity_curve_df()

# Get recent trades
trades = portfolio.get_recent_trades()
```

### Risk Managers

Risk managers handle position sizing and risk controls:

```python
from src.risk.managers.simple import SimpleRiskManager

# Create a risk manager
risk_manager = SimpleRiskManager(event_bus, portfolio)

# Configure
risk_manager.position_size = 100
risk_manager.max_position_pct = 0.1

# Manual signal handling
signal_event = create_signal_event(1, 100.0, "AAPL")
risk_manager.on_signal(signal_event)  # Will create appropriate orders

# Reset state
risk_manager.reset()
```

## Order Execution

### Order Manager

The `OrderManager` processes orders and interacts with the broker:

```python
from src.execution.order_manager import OrderManager

# Create an order manager
order_manager = OrderManager(event_bus, broker)

# Create an order
order_id = order_manager.create_order(
    symbol="AAPL",
    order_type="MARKET",
    direction="BUY",
    quantity=100,
    price=150.0
)

# Get order status
order = order_manager.get_order(order_id)
status = order.get('status')  # 'PENDING', 'FILLED', etc.

# Cancel an order
order_manager.cancel_order(order_id)
```

### Broker Simulator

The `SimulatedBroker` simulates market execution:

```python
from src.execution.broker.broker_simulator import SimulatedBroker

# Create a simulated broker
broker = SimulatedBroker(event_bus)

# Configure 
broker.slippage = 0.001  # 0.1% slippage
broker.commission = 0.001  # 0.1% commission

# Process an order (normally called by the order manager)
order_event = create_order_event("BUY", 100, "AAPL", "MARKET", 150.0)
broker.on_order(order_event)  # Will emit a FILL event
```

## Backtesting

### Backtest Coordinator

The `BacktestCoordinator` orchestrates the entire backtest:

```python
from src.execution.backtest.backtest import BacktestCoordinator

# Create the coordinator
backtest = BacktestCoordinator(container, config)

# Run the backtest
results = backtest.run(
    symbols=["AAPL", "MSFT"],
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=100000.0,
    timeframe="1d"
)

# Access results
equity_curve = results['equity_curve']
trades = results['trades']
metrics = results['metrics']
summary_report = results['summary_report']
```

## Analytics and Reporting

### Performance Calculator

The `PerformanceCalculator` computes trading metrics:

```python
from src.analytics.performance.calculator import PerformanceCalculator

# Create calculator
calculator = PerformanceCalculator()

# Set data
calculator.set_equity_curve(equity_curve_df)
calculator.set_trades(trades_list)

# Calculate metrics
sharpe_ratio = calculator.calculate_sharpe_ratio()
drawdown = calculator.calculate_max_drawdown()

# Calculate all metrics
metrics = calculator.calculate_all_metrics()
```

### Report Generator

The `ReportGenerator` creates performance reports:

```python
from src.analytics.reporting.report_generator import ReportGenerator

# Create report generator
report_generator = ReportGenerator(calculator)

# Generate reports
summary = report_generator.generate_summary_report()
detailed = report_generator.generate_detailed_report()

# Save reports
saved_files = report_generator.save_reports(
    results,
    output_dir="./results",
    timestamp="20240501_120000"
)
```

## Common Patterns and Best Practices

### Event-Driven Component Communication

Components in ADMF-Trader communicate through events, not direct method calls:

```python
# GOOD: Event-driven communication
strategy.on_bar(bar_event)  # Processes the event and emits a signal event
risk_manager.on_signal(signal_event)  # Handles the signal and emits an order event
order_manager.on_order(order_event)  # Processes the order and sends to broker
broker.on_order(order_event)  # Executes the order and emits a fill event
portfolio.on_fill(fill_event)  # Updates portfolio state

# BAD: Direct method calls that bypass the event system
strategy.generate_signal(bar)  # Don't call methods directly
risk_manager.create_order(signal)  # Use events instead
```

### Component Configuration

All components should follow a consistent configuration pattern:

```python
def configure(self, config):
    """Configure the component with parameters."""
    # Handle both dictionary and Config object
    if hasattr(config, 'as_dict'):
        config_dict = config.as_dict()
    else:
        config_dict = dict(config)
        
    # Extract parameters with defaults
    self.parameter1 = config_dict.get('parameter1', default_value)
    self.parameter2 = config_dict.get('parameter2', default_value)
    
    # Log configuration
    logger.info(f"Component configured with parameters: {config_dict}")
```

### Idempotent Event Processing

Implement idempotent event processing using unique identifiers:

```python
def on_signal(self, signal_event):
    # Get unique ID for idempotent processing
    signal_id = signal_event.get_id()
    
    # Skip if already processed
    if signal_id in self.processed_signals:
        return None
        
    # Mark as processed immediately
    self.processed_signals.add(signal_id)
    
    # Process the signal
    # ...
```

### Proper Component Reset

All components should implement a proper reset method:

```python
def reset(self):
    """Reset component state."""
    # Clear collections
    self.data.clear()
    self.processed_ids.clear()
    
    # Reset counters and state
    self.counter = 0
    self.state = "INITIAL"
    
    # Log reset
    logger.info(f"Component {self.name} reset complete")
```

### Error Handling

Use consistent error handling patterns:

```python
def process_data(self, data):
    try:
        # Process data
        result = self._internal_processing(data)
        return result
    except ValueError as e:
        # Handle specific exceptions
        logger.error(f"Value error in data processing: {e}")
        return None
    except Exception as e:
        # Log unexpected errors
        logger.exception(f"Unexpected error: {e}")
        # Re-raise or return default
        return None
```

### Logging Best Practices

Follow consistent logging patterns:

```python
import logging
logger = logging.getLogger(__name__)

# In methods, use appropriate log levels
logger.debug("Detailed information for debugging")
logger.info("Confirmation of important events")
logger.warning("Potential issue or non-critical problem")
logger.error("Error that prevented operation from completing")
logger.critical("Critical error that may cause system failure")

# Include context in log messages
logger.info(f"Processing order {order_id} for {symbol} at {price:.2f}")

# Log method entry/exit for complex operations
logger.debug(f"Entering method process_data with {len(data)} items")
# ...
logger.debug(f"Exiting method process_data with result: {result}")
```

### Working with Event-Driven Architecture

Follow these principles when extending the system:

1. **Maintain Separation of Concerns**: 
   - Strategies only generate signals, they don't create orders
   - Risk managers handle position sizing and order creation
   - Order managers handle order execution

2. **Use Event Bus for Communication**:
   - Components should communicate via events, not direct method calls
   - Register for event types relevant to your component
   - Emit events when your component has something to share

3. **Handle Component Lifecycle**:
   - Implement proper initialization, configuration, and reset methods
   - Clean up resources when components are destroyed
   - Reset state between backtest runs

4. **Follow Registration Patterns**:
   - Register components with event manager in the correct order
   - Use standard naming conventions for component types
   - Set priorities for event handlers when order matters

These patterns ensure that your extensions integrate smoothly with the existing system and maintain the clean, event-driven architecture.