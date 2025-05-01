# ADMF-Trader (Adaptive Decision Making Framework Trader)

A modular, event-driven algorithmic trading system with a component-based architecture designed for strategy development, backtesting, and optimization.

## System Overview

ADMF-Trader is built around a hierarchical component architecture that allows for:

- Compositional strategy design (build complex strategies from simple components)
- Parameter optimization across all levels
- Regime-adaptive trading approaches
- Clean separation of concerns through an event-driven architecture

```
Market Data --> Signal Generators --> Strategy --> Risk --> Order Execution
```

## Core Architecture Principles

- **Component-Based Design**: All trading elements inherit from a common Component base class
- **Hierarchical Structure**: Clear progression from low-level to high-level components
- **Compositional Approach**: Complex strategies built by combining simpler components
- **Parameter Management**: Unified interface for parameter getting/setting
- **Optimization Support**: Design that facilitates parameter and weight optimization
- **Event-Driven**: Clean event flow between system components with idempotent event processing
- **Dependency Injection**: Container-based approach for managing component dependencies

## System Architecture

```
src/
├── core/
│   ├── events/               # Event system with idempotent event processing
│   ├── config/               # Configuration management
│   ├── di/                   # Dependency injection container
│   └── utils/                # Discovery and registry utilities
├── data/
│   ├── sources/              # Data sources (CSV, API, DB)
│   ├── transformers/         # Data transformations
│   └── generators/           # Synthetic data generation
├── strategy/
│   ├── components/           # Strategy components
│   │   ├── indicators/       # Technical indicators
│   │   ├── features/         # Feature extraction
│   │   └── rules/            # Trading rules
│   ├── implementations/      # Concrete strategies (MA Crossover, Regime Ensemble)
│   └── optimization/         # Strategy optimization
├── risk/
│   ├── portfolio/            # Portfolio state
│   │   ├── portfolio.py      # Portfolio management
│   │   └── position.py       # Position tracking
│   └── managers/             # Risk managers (simple and enhanced)
├── execution/
│   ├── broker/               # Broker interfaces and simulation
│   ├── backtest/             # Backtesting engine
│   ├── order_registry.py     # Centralized order tracking
│   └── order_manager.py      # Order management
└── analytics/
    ├── metrics/              # Performance metrics calculation
    ├── performance/          # Performance analysis
    └── reporting/            # Report generation
```

## Key Features

- **Event-driven Architecture**: Clean event flow with idempotent event processing
- **Modular Design**: Build complex strategies from simpler components
- **Multiple Strategy Support**: MA crossover, regime-based ensembles, and more
- **Risk Management**: Position sizing and risk controls with clear separation from strategy logic
- **Backtest Analysis**: Comprehensive performance metrics and reporting
- **Data Generation**: Support for generating synthetic market data with different regimes
- **Component Discovery**: Automatic discovery and registration of strategy components
- **Regime Detection**: Support for adaptive strategies based on market regimes

## Getting Started

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/admf-trader.git
cd admf-trader
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make scripts executable (Unix/Linux/Mac):
```bash
chmod +x setup.sh
./setup.sh
```

### Running the System

The main entry point is `main.py` which provides a clean interface to the system:

```bash
# Basic usage
python main.py --config config/head_test.yaml

# With data generation
python main.py --config config/regime_ensemble.yaml --generate-data --data-type multi_regime --plot-data

# Custom output directory
python main.py --config config/head_test.yaml --output-dir ./custom_results
```

### Configuration

The system is configured using YAML files in the `config/` directory:

- `head_test.yaml`: Moving average crossover for test data
- `mini_test.yaml`: Minimal test configuration
- `regime_ensemble.yaml`: Regime-based ensemble strategy

Example configuration:

```yaml
# Configuration for MA Crossover with HEAD_1min data
backtest:
  initial_capital: 100000.0
  symbols: ['HEAD']
  data_dir: "./data"
  timeframe: "1min"
  data_source: "csv"
  start_date: "2024-01-01"
  end_date: "2024-12-31"

strategies:  
  ma_crossover:
    enabled: true
    fast_window: 5
    slow_window: 15
    price_key: "close"

risk_manager:
  position_size: 100
  max_position_pct: 0.1
```

## Adding a New Strategy

To implement a new strategy:

1. Create a new strategy class in `src/strategy/implementations/`
2. Inherit from the `Strategy` base class
3. Implement the `on_bar` method to analyze market data and emit signals
4. Add configuration in a YAML file
5. Run the backtest with your new strategy

Example:

```python
from src.strategy.strategy_base import Strategy
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event

class MyCustomStrategy(Strategy):
    # Define name as a class variable for discovery
    name = "my_custom_strategy"
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        super().__init__(event_bus, data_handler, name or self.name, parameters)
        
        # Extract parameters
        self.my_param = self.parameters.get('my_param', 10)
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
    
    def configure(self, config):
        super().configure(config)
        self.my_param = self.parameters.get('my_param', 10)
    
    def on_bar(self, bar_event):
        # Your strategy logic here
        # When you want to emit a signal:
        signal = create_signal_event(
            signal_value=1,  # 1 for buy, -1 for sell
            price=bar_event.get_close(),
            symbol=bar_event.get_symbol(),
            timestamp=bar_event.get_timestamp()
        )
        
        if self.event_bus:
            self.event_bus.emit(signal)
            
        return signal
```

## Future Directions

1. **Enhanced Optimization Framework**: Advanced parameter and weight optimization
2. **Options Spread Trading**: Support for options trading strategies
3. **Reinforcement Learning**: Integration with RL for policy-based strategies
4. **Live Trading**: Real-time data feeds and broker interfaces
5. **Visualization**: Interactive performance dashboards
6. **Alternative Data**: Integration with sentiment and alternative data sources

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.