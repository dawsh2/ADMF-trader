# Configuration and Dependency Injection Specification

## Overview

The Configuration and Dependency Injection (DI) systems form the backbone of the trading framework, enabling modular, testable, and configurable components. This specification outlines the design and implementation of these critical systems to ensure consistency and simplicity throughout the framework.

## Module Structure

```
core/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── schema.py                # Configuration schema validation
│   ├── loaders/                 # Configuration loaders
│   │   ├── __init__.py
│   │   ├── yaml_loader.py       # YAML configuration loader
│   │   ├── json_loader.py       # JSON configuration loader
│   │   └── env_loader.py        # Environment variable loader
│   ├── defaults/                # Default configurations
│   │   ├── __init__.py
│   │   ├── core_defaults.py     # Core system defaults
│   │   ├── strategy_defaults.py # Strategy defaults
│   │   └── risk_defaults.py     # Risk management defaults
│   └── utils/                   # Configuration utilities
│       ├── __init__.py
│       ├── converter.py         # Type conversion utilities
│       └── validator.py         # Validation utilities
└── di/
    ├── __init__.py
    ├── container.py             # DI container
    ├── provider.py              # Component provider
    ├── factory.py               # Component factory
    ├── registry.py              # Component registry
    └── decorators.py            # DI decorators
```

## 1. Configuration System

### 1.1 Configuration Manager

The `Config` class manages configuration loading, access, and validation.

**Key Functionality:**
- Loading configuration from multiple sources (YAML, JSON, environment variables)
- Accessing configuration values with type conversion
- Validating configuration against schemas
- Providing default values
- Configuration overrides
- Section-based organization

**Interface:**
```python
class Config:
    def __init__(self, defaults: Dict[str, Any] = None):
        """Initialize configuration with optional defaults."""
        
    def load_file(self, filepath: str) -> None:
        """Load configuration from a file (YAML, JSON)."""
        
    def load_env(self, prefix: str = "APP_", separator: str = "_") -> None:
        """Load configuration from environment variables."""
        
    def load_dict(self, config_dict: Dict[str, Any]) -> None:
        """Load configuration from a dictionary."""
        
    def get_section(self, section: str) -> 'ConfigSection':
        """Get a configuration section."""
        
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default."""
        
    def get_int(self, key: str, default: int = 0) -> int:
        """Get a configuration value as an integer."""
        
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a configuration value as a float."""
        
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a configuration value as a boolean."""
        
    def get_list(self, key: str, default: List = None) -> List:
        """Get a configuration value as a list."""
        
    def get_dict(self, key: str, default: Dict = None) -> Dict:
        """Get a configuration value as a dictionary."""
        
    def validate(self, schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration against a schema."""
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary."""
        
    def save(self, filepath: str) -> None:
        """Save configuration to a file."""
```

### 1.2 Configuration Section

The `ConfigSection` class provides access to a specific section of the configuration.

**Key Functionality:**
- Access to a specific configuration section
- Type-converted value access
- Nested section access
- Default value handling

**Interface:**
```python
class ConfigSection:
    def __init__(self, name: str, config: Dict[str, Any], parent: 'Config' = None):
        """Initialize a configuration section."""
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default."""
        
    def get_int(self, key: str, default: int = 0) -> int:
        """Get a configuration value as an integer."""
        
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a configuration value as a float."""
        
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a configuration value as a boolean."""
        
    def get_list(self, key: str, default: List = None) -> List:
        """Get a configuration value as a list."""
        
    def get_dict(self, key: str, default: Dict = None) -> Dict:
        """Get a configuration value as a dictionary."""
        
    def get_section(self, name: str) -> 'ConfigSection':
        """Get a nested configuration section."""
        
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        
    def update(self, values: Dict[str, Any]) -> None:
        """Update multiple configuration values."""
        
    def as_dict(self) -> Dict[str, Any]:
        """Convert section to a dictionary."""
```

### 1.3 Configuration Schema

The `ConfigSchema` class validates configuration against a schema.

**Key Functionality:**
- Schema definition
- Type validation
- Required field validation
- Value constraints
- Default values
- Nested schema validation

**Interface:**
```python
class ConfigSchema:
    def __init__(self, schema: Dict[str, Any]):
        """Initialize with a schema definition."""
        
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration against the schema."""
        
    @staticmethod
    def create_schema_from_template(template: Dict[str, Any]) -> Dict[str, Any]:
        """Create a schema from a template configuration."""
        
    @staticmethod
    def create_schema_from_class(cls: Type) -> Dict[str, Any]:
        """Create a schema from a class with type annotations."""
        
    def apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply schema defaults to configuration."""
```

### 1.4 Configuration File Examples

**YAML Configuration Example:**
```yaml
# config.yaml
core:
  log_level: INFO
  event_buffer_size: 1000
  
data:
  source: csv
  data_dir: ./data
  default_timeframe: 1d
  
strategy:
  ma_crossover:
    fast_window: 10
    slow_window: 20
    price_key: close
    
  mean_reversion:
    lookback: 20
    z_threshold: 1.5
    price_key: close
    
risk:
  position_sizing:
    method: percent_risk
    params:
      risk_percent: 0.01
      max_position_size: 100000
  
  limits:
    max_exposure: 1.0
    max_position_size: 0.1
    max_concentration: 0.25
    max_drawdown: 0.2
  
execution:
  broker: simulated
  slippage_model: default
  commission_model: default
  
analytics:
  metrics:
    - total_return
    - sharpe_ratio
    - max_drawdown
    - win_rate
  benchmark: SPY
```

**Environment Variables Example:**
```
APP_CORE_LOG_LEVEL=DEBUG
APP_DATA_SOURCE=csv
APP_DATA_DATA_DIR=/path/to/data
APP_STRATEGY_MA_CROSSOVER_FAST_WINDOW=12
APP_RISK_POSITION_SIZING_PARAMS_RISK_PERCENT=0.02
```

## 2. Dependency Injection System

### 2.1 DI Container

The `Container` class manages component registration, resolution, and lifecycle.

**Key Functionality:**
- Component registration
- Dependency resolution
- Singleton vs. transient instances
- Factory methods
- Lazy initialization
- Lifecycle management

**Interface:**
```python
class Container:
    def __init__(self):
        """Initialize the container."""
        
    def register(self, name: str, component_class: Type[T], 
                dependencies: Dict[str, str] = None, singleton: bool = True) -> 'Container':
        """Register a component class."""
        
    def register_instance(self, name: str, instance: Any) -> 'Container':
        """Register a pre-created instance."""
        
    def register_factory(self, name: str, factory: Callable[['Container'], T]) -> 'Container':
        """Register a factory function for complex initialization."""
        
    def get(self, name: str) -> Any:
        """Get a component instance by name."""
        
    def inject(self, instance: Any) -> Any:
        """Inject dependencies into an existing instance."""
        
    def create(self, component_class: Type[T], **kwargs) -> T:
        """Create a new instance of a class with dependencies."""
        
    def reset(self) -> None:
        """Reset all singleton instances."""
        
    def has(self, name: str) -> bool:
        """Check if a component is registered."""
        
    def remove(self, name: str) -> None:
        """Remove a component registration."""
        
    def get_all(self, base_type: Type[T]) -> List[T]:
        """Get all registered components of a specific base type."""
```

### 2.2 Component Provider

The `Provider` class provides dependency resolution utilities.

**Key Functionality:**
- Constructor injection
- Property injection
- Method injection
- Autowiring
- Dependency resolution

**Interface:**
```python
class Provider:
    def __init__(self, container: Container):
        """Initialize with a container."""
        
    def get_instance(self, component_class: Type[T], **kwargs) -> T:
        """Create a new instance with dependencies."""
        
    def inject_properties(self, instance: Any) -> Any:
        """Inject properties into an instance."""
        
    def inject_methods(self, instance: Any) -> Any:
        """Inject dependencies into methods."""
        
    def resolve_dependencies(self, component_class: Type[T]) -> Dict[str, Any]:
        """Resolve dependencies for a class."""
        
    def resolve_dependency(self, dependency_type: Type[T]) -> T:
        """Resolve a single dependency by type."""
```

### 2.3 Component Factory

The `ComponentFactory` creates components with dependencies.

**Key Functionality:**
- Creating components from registry
- Configuring components from configuration
- Component discovery
- Component caching

**Interface:**
```python
class ComponentFactory:
    def __init__(self, container: Container, registry: 'ComponentRegistry', config: Config = None):
        """Initialize with container, registry, and optional config."""
        
    def create(self, name: str, **kwargs) -> Any:
        """Create a component by name with optional overrides."""
        
    def create_from_config(self, config_section: str) -> Any:
        """Create a component from configuration."""
        
    def create_all(self, base_type: Type[T]) -> List[T]:
        """Create all registered components of a specific base type."""
        
    def register_component_type(self, type_name: str, component_class: Type[T]) -> None:
        """Register a component type for creation."""
```

### 2.4 Component Registry

The `ComponentRegistry` manages component registration.

**Key Functionality:**
- Component type registration
- Component discovery
- Component validation
- Metadata handling

**Interface:**
```python
class ComponentRegistry:
    def __init__(self):
        """Initialize the registry."""
        
    def register(self, name: str, component_class: Type[T]) -> None:
        """Register a component class."""
        
    def register_from_module(self, module) -> None:
        """Register components from a module."""
        
    def discover_components(self, package_name: str) -> None:
        """Automatically discover and register components."""
        
    def get_component_class(self, name: str) -> Type:
        """Get a component class by name."""
        
    def get_all_component_classes(self) -> Dict[str, Type]:
        """Get all registered component classes."""
        
    def get_components_by_base(self, base_class: Type[T]) -> Dict[str, Type[T]]:
        """Get components that inherit from a base class."""
```

### 2.5 Decorators

Decorators for simplifying dependency injection.

**Key Functionality:**
- Component registration
- Dependency specification
- Configuration binding
- Lifecycle hooks

**Examples:**
```python
@component("ma_crossover_strategy")
class MovingAverageCrossoverStrategy(StrategyBase):
    """Moving average crossover strategy."""
    
@inject
def __init__(self, event_bus=Inject(EventBus), data_handler=Inject(DataHandler)):
    """Initialize with injected dependencies."""
    
@config_section("strategy.ma_crossover")
class MAConfig:
    """Configuration for MA strategy."""
    fast_window: int = 10
    slow_window: int = 20
    price_key: str = "close"
    
@initializer
def setup(self):
    """Called after initialization."""
    
@disposer
def cleanup(self):
    """Called before disposal."""
```

## 3. Integration Between Configuration and DI

### 3.1 Configuration-Aware Container

The `ConfigurableContainer` extends the DI container with configuration integration.

**Key Functionality:**
- Component configuration from config
- Configuration-based component selection
- Configuration validation against component requirements
- Dynamic reconfiguration

**Interface:**
```python
class ConfigurableContainer(Container):
    def __init__(self, config: Config = None):
        """Initialize with optional configuration."""
        
    def set_config(self, config: Config) -> None:
        """Set the configuration."""
        
    def register_from_config(self, config_section: str, base_type: Type[T] = None) -> 'ConfigurableContainer':
        """Register components from a configuration section."""
        
    def get_configured(self, name: str, config_section: str = None) -> Any:
        """Get a configured component instance."""
        
    def create_configured(self, component_class: Type[T], config_section: str = None, **kwargs) -> T:
        """Create a configured instance of a class."""
```

### 3.2 Components with Configuration Support

Components that want configuration support can implement the `Configurable` interface.

**Interface:**
```python
class Configurable(ABC):
    @abstractmethod
    def configure(self, config: ConfigSection) -> None:
        """Configure the component."""
        
    @classmethod
    @abstractmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """Get the default configuration."""
        
    @classmethod
    @abstractmethod
    def validate_config(cls, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration for this component."""
```

### 3.3 Configuration-Based Factory

The `ConfigFactory` creates components based on configuration.

**Key Functionality:**
- Creating components from configuration
- Component type selection from configuration
- Parameter configuration
- Configuration validation

**Interface:**
```python
class ConfigFactory:
    def __init__(self, container: Container, config: Config):
        """Initialize with container and configuration."""
        
    def create_from_config(self, config_section: str, instance_name: str = None) -> Any:
        """Create a component from configuration."""
        
    def create_many_from_config(self, config_section: str) -> Dict[str, Any]:
        """Create multiple components from configuration."""
        
    def create_by_type(self, type_name: str, config_section: str = None) -> Any:
        """Create a component by type name with configuration."""
```

## 4. System Bootstrapping

### 4.1 Bootstrap Process

The `Bootstrap` class initializes the entire system.

**Key Functionality:**
- Configuration loading
- Container initialization
- Component registration
- System startup

**Interface:**
```python
class Bootstrap:
    def __init__(self, config_files: List[str] = None, env_prefix: str = "APP_"):
        """Initialize with configuration files and environment prefix."""
        
    def setup(self) -> Tuple[Container, Config]:
        """Set up the system and return container and config."""
        
    def register_core_components(self, container: Container, config: Config) -> None:
        """Register core components."""
        
    def register_data_components(self, container: Container, config: Config) -> None:
        """Register data components."""
        
    def register_strategy_components(self, container: Container, config: Config) -> None:
        """Register strategy components."""
        
    def register_risk_components(self, container: Container, config: Config) -> None:
        """Register risk management components."""
        
    def register_execution_components(self, container: Container, config: Config) -> None:
        """Register execution components."""
        
    def register_analytics_components(self, container: Container, config: Config) -> None:
        """Register analytics components."""
```

### 4.2 Bootstrap Usage Example

```python
# Initialize the system
bootstrap = Bootstrap(
    config_files=["config.yaml", "strategies.yaml"],
    env_prefix="TRADING_"
)
container, config = bootstrap.setup()

# Get components
event_bus = container.get("event_bus")
data_handler = container.get("data_handler")
strategy = container.get("strategy")
risk_manager = container.get("risk_manager")
broker = container.get("broker")

# Start the system
event_bus.start()
```

## 5. Configuration and DI Use Cases

### 5.1 Strategy Configuration

```yaml
# strategies.yaml
strategies:
  ma_crossover:
    class: trading.strategies.MovingAverageCrossoverStrategy
    enabled: true
    parameters:
      fast_window: 10
      slow_window: 30
      price_key: close
      trade_sizing: percent_equity
      percent_equity: 0.1
      
  mean_reversion:
    class: trading.strategies.MeanReversionStrategy
    enabled: true
    parameters:
      lookback: 20
      z_threshold: 1.5
      price_key: close
      trade_sizing: fixed
      fixed_size: 100
```

```python
# Strategy creation from configuration
strategy_factory = ConfigFactory(container, config)
strategies = strategy_factory.create_many_from_config("strategies")

# Access individual strategies
ma_strategy = strategies["ma_crossover"]
mr_strategy = strategies["mean_reversion"]

# Or create a specific strategy
ma_strategy = strategy_factory.create_from_config("strategies.ma_crossover")
```

### 5.2 Data Source Configuration

```yaml
# data_sources.yaml
data:
  default_source: csv
  
  sources:
    csv:
      class: trading.data.CSVDataSource
      parameters:
        data_dir: ./data
        filename_pattern: "{symbol}_{timeframe}.csv"
        date_column: timestamp
        date_format: "%Y-%m-%d"
        
    yahoo:
      class: trading.data.YahooDataSource
      parameters:
        cache_dir: ./cache
        proxy: null
        
    alpha_vantage:
      class: trading.data.AlphaVantageDataSource
      parameters:
        api_key: ${ALPHA_VANTAGE_API_KEY}
        cache_dir: ./cache
```

```python
# Data source creation from configuration
data_factory = ConfigFactory(container, config)
data_sources = data_factory.create_many_from_config("data.sources")

# Get default data source
default_source_name = config.get("data.default_source")
default_source = data_sources[default_source_name]

# Or create a specific data source
yahoo_source = data_factory.create_from_config("data.sources.yahoo")
```

### 5.3 Risk Management Configuration

```yaml
# risk.yaml
risk:
  manager:
    class: trading.risk.StandardRiskManager
    parameters:
      position_sizing:
        method: percent_risk
        risk_percent: 0.01
        max_position_size: 1000
      
      limits:
        max_exposure: 1.0
        max_position_size: 0.1
        max_concentration: 0.25
        max_drawdown: 0.2
      
      drawdown_control:
        enabled: true
        threshold: 0.1
        action: reduce_size
        reduction_factor: 0.5
```

```python
# Risk manager creation from configuration
risk_factory = ConfigFactory(container, config)
risk_manager = risk_factory.create_from_config("risk.manager")

# Update risk parameters
risk_section = config.get_section("risk.manager.parameters")
risk_manager.configure(risk_section)
```

## 6. Testing and Validation

### 6.1 Unit Testing

Components and configuration should be thoroughly unit tested:

```python
def test_config_loading():
    # Test loading from file
    config = Config()
    config.load_file("test_config.yaml")
    assert config.get("core.log_level") == "INFO"
    
    # Test loading from dict
    config = Config()
    config.load_dict({"core": {"log_level": "DEBUG"}})
    assert config.get("core.log_level") == "DEBUG"
    
    # Test loading from environment
    os.environ["APP_CORE_LOG_LEVEL"] = "WARNING"
    config = Config()
    config.load_env(prefix="APP_")
    assert config.get("core.log_level") == "WARNING"

def test_di_container():
    # Test component registration and resolution
    container = Container()
    container.register("logger", Logger)
    logger = container.get("logger")
    assert isinstance(logger, Logger)
    
    # Test dependency injection
    container.register("event_bus", EventBus)
    container.register("strategy", Strategy, {"event_bus": "event_bus"})
    strategy = container.get("strategy")
    assert strategy.event_bus is container.get("event_bus")
```

### 6.2 Integration Testing

Integration between configuration and DI should be tested:

```python
def test_configured_component():
    # Set up container with configuration
    config = Config()
    config.load_dict({
        "strategy": {
            "ma_crossover": {
                "fast_window": 10,
                "slow_window": 30
            }
        }
    })
    
    container = ConfigurableContainer(config)
    container.register("strategy", MovingAverageCrossoverStrategy)
    
    # Get configured component
    strategy = container.get_configured("strategy", "strategy.ma_crossover")
    
    # Verify configuration was applied
    assert strategy.fast_window == 10
    assert strategy.slow_window == 30
```

### 6.3 System Testing

The bootstrap process should be tested:

```python
def test_bootstrap():
    # Set up test configuration
    with open("test_config.yaml", "w") as f:
        f.write("""
        core:
          log_level: INFO
        
        data:
          source: csv
          data_dir: ./test_data
        
        strategy:
          ma_crossover:
            fast_window: 15
            slow_window: 35
        """)
    
    # Bootstrap the system
    bootstrap = Bootstrap(config_files=["test_config.yaml"])
    container, config = bootstrap.setup()
    
    # Verify components were created and configured
    event_bus = container.get("event_bus")
    assert event_bus is not None
    
    strategy = container.get("strategy")
    assert strategy is not None
    assert strategy.fast_window == 15
    assert strategy.slow_window == 35
```

## 7. Implementation Plan

### Phase 1: Core Configuration System (1 week)

1. Implement Config class
2. Implement ConfigSection class
3. Implement config loaders
4. Add configuration validation
5. Create unit tests

### Phase 2: Core DI System (1 week)

1. Implement Container class
2. Implement Provider class
3. Implement ComponentRegistry
4. Add dependency resolution
5. Create unit tests

### Phase 3: Integration (1 week)

1. Implement ConfigurableContainer
2. Implement ConfigFactory
3. Create integration between Config and DI
4. Add integration tests

### Phase 4: Bootstrapping (1 week)

1. Implement Bootstrap class
2. Create component registration logic
3. Add system initialization
4. Create system tests

### Phase 5: Refinement (1 week)

1. Add decorators for easier DI usage
2. Improve error handling and diagnostics
3. Optimize performance
4. Add documentation and examples

## 8. Dependencies

- PyYAML (for YAML configuration)
- jsonschema (for schema validation)
- typing_inspect (for type inspection)
- python-dotenv (for environment variable handling)

## 9. Success Criteria

1. All configuration and DI components function correctly and pass tests
2. Components can be configured via YAML, JSON, and environment variables
3. Dependencies are correctly resolved and injected
4. System bootstrapping initializes all components correctly
5. Configuration validation prevents invalid configurations
6. Integration between systems is seamless
7. The system is easy to use and well-documented
