# Core Module

The `src/core` module provides the foundational infrastructure for the ADMF-Trader system. It contains the essential components and services that the entire application depends on.

## Overview

The Core module implements several critical services:

- **Event System**: A pub/sub messaging system that enables loose coupling between components
- **Dependency Injection**: A container system for managing component dependencies
- **System Bootstrap**: Initialization and configuration of the entire application
- **Component Model**: Base classes and interfaces for system components
- **Error Handling**: Centralized error management
- **Configuration**: Loading and management of application settings

## Key Components

### Event System (`events/`)

The event system provides a publish/subscribe mechanism for component communication. It allows various parts of the system to communicate without direct dependencies. See the [events README](./events/README.md) for more details.

### Dependency Injection (`di/`)

The dependency injection container handles the creation and lifecycle of components, automatically resolving dependencies:

```python
# Create a container
container = Container()

# Register components
container.register("data_source", CSVDataSource)
container.register("strategy", MACrossoverStrategy, 
                  {"data_source": "data_source"})

# Get components with dependencies resolved
strategy = container.get("strategy")  # Automatically gets a data_source
```

### System Bootstrap (`system_bootstrap.py`)

The Bootstrap class handles initialization of the entire system, including:

- Configuration loading
- Component discovery and registration
- Event system setup
- Dependency wiring

```python
# Create and initialize system
bootstrap = Bootstrap(config_files=["config.yaml"])
container, config = bootstrap.setup()

# Start operation
backtest = container.get("backtest")
backtest.run()
```

### Component Base (`component.py`)

The Component base class provides a standard lifecycle interface for all system components:

```python
class Component:
    def __init__(self, name)
    def initialize(self, context)  # Set up dependencies
    def start()                    # Begin operation
    def stop()                     # End operation
    def reset()                    # Clear internal state
```

### Configuration (`config/`)

The configuration system handles loading and accessing application settings from YAML files and environment variables.

## Module Structure

```
src/core/
├── __init__.py             # Package initialization
├── component.py            # Base Component class
├── data_model.py           # Core data structures
├── error_handler.py        # Error management
├── system_bootstrap.py     # System initialization
├── validation.py           # Input validation utilities
├── config/                 # Configuration management
├── di/                     # Dependency injection
├── events/                 # Event system (pub/sub)
├── logging/                # Logging infrastructure
└── utils/                  # Utility functions
```

## Dependencies

The Core module has minimal external dependencies and primarily relies on the Python standard library. It is designed to be self-contained and provides services to other modules rather than depending on them.

## Usage

The Core module is typically not used directly by application code. Instead, it provides infrastructure that the application builds upon. The main entry point for system startup is the Bootstrap class:

```python
from src.core.system_bootstrap import Bootstrap

# Initialize the system
bootstrap = Bootstrap(config_files=["trading_config.yaml"])
container, config = bootstrap.setup()

# Get core components
event_bus = container.get("event_bus")
data_handler = container.get("data_handler")
strategy = container.get("strategy")

# Start operation
strategy.start()
```

## Architecture

The Core module follows these architectural principles:

1. **Loose Coupling**: Components communicate through events, not direct references
2. **Dependency Inversion**: Higher-level modules do not depend on lower-level modules
3. **Single Responsibility**: Each class has a focused purpose
4. **Open/Closed**: The system is extensible without modifying existing code

For more information on ADMF-Trader's overall architecture, see the main project README.
