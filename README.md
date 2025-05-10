# ADMF-Trader

ADMF-Trader is an algorithmic trading framework designed for systematic strategy development, testing, optimization, and execution. It provides a modular, event-driven architecture for building and evaluating trading strategies across multiple asset classes and timeframes.

## Key Features

- **Event-Driven Architecture**: Flexible, responsive system built on a pub/sub event model
- **Configurable Components**: Highly configurable trading components that adapt to different requirements
- **Strategy Framework**: Extensible framework for implementing diverse trading strategies
- **Risk Management**: Customizable risk management protocols with position sizing and risk limits
- **Backtesting Engine**: Fast, reliable backtesting with realistic market simulation
- **Optimization Framework**: Parameter optimization with train/test validation
- **Regime Detection**: Support for regime-aware trading strategies that adapt to market conditions
- **Performance Analytics**: Comprehensive performance metrics and reporting
- **Extensible Design**: Modular architecture to support additional components and functionality

## System Architecture

ADMF-Trader is organized into the following core modules:

- **Core**: System-level services including event bus, component lifecycle, and dependency injection
- **Data**: Data handling, market data processing, and data source management
- **Strategy**: Strategy definition, signal generation, and indicator frameworks
- **Risk**: Risk management, position sizing, and rule application
- **Execution**: Order management, broker simulation, and trade execution
- **Analytics**: Performance analysis, reporting, and visualization

## Usage Example

```python
# Configuration-based setup
from admf_trader.main import run_backtest

result = run_backtest(
    config_file="config/backtest.yaml",
    data_dir="data/",
    output_dir="results/"
)

# Programmatic setup
from admf_trader.core import System
from admf_trader.data import CSVDataHandler
from admf_trader.strategy import MACrossoverStrategy
from admf_trader.risk import StandardRiskManager
from admf_trader.execution import SimulatedBroker

# Configure system
system = System()
system.register(
    data_handler=CSVDataHandler(data_dir="data/", symbols=["AAPL", "MSFT"]),
    strategy=MACrossoverStrategy(fast_ma=10, slow_ma=30),
    risk_manager=StandardRiskManager(max_position_size=0.1),
    broker=SimulatedBroker(initial_capital=100000)
)

# Run backtest
system.run()

# Analyze results
from admf_trader.analytics import PerformanceAnalyzer

analyzer = PerformanceAnalyzer(system.get_equity_curve(), system.get_trades())
metrics = analyzer.analyze_performance()
print(f"Total Return: {metrics['total_return']:.2%}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
```

## Configuration

ADMF-Trader uses YAML configuration files to define system behavior:

```yaml
# config/backtest.yaml
name: MA Crossover Backtest
description: Simple moving average crossover strategy backtest

data:
  type: csv
  symbols: [AAPL, MSFT, GOOGL]
  timeframe: 1d
  start_date: 2020-01-01
  end_date: 2022-12-31

strategy:
  type: ma_crossover
  parameters:
    fast_ma: 10
    slow_ma: 30

risk:
  type: standard
  position_size: 0.1
  max_positions: 5
  stop_loss: 0.05

execution:
  type: simulated
  initial_capital: 100000
  commission: 0.001

analytics:
  metrics: [total_return, sharpe_ratio, max_drawdown]
  reports: [text, html]
  output_dir: results/
```

## Position Management

ADMF-Trader includes a robust position management system to handle:

- Limiting maximum positions per symbol
- Enforcing position sizing rules
- Ensuring proper state isolation between test runs
- Consistent tracking of active positions
- Prevention of duplicate signals

Configure position management via:

```yaml
risk:
  position_manager:
    max_positions: 1
    position_sizing_method: fixed  # or "percent_risk", "volatility", etc.
    fixed_quantity: 10  # for fixed sizing
    enforce_single_position: true
```

## Directory Structure

```
ADMF-trader/
├── config/                  # Configuration files
├── data/                    # Sample and test data
├── docs/                    # Documentation
├── results/                 # Backtest results
├── src/                     # Source code
│   ├── core/                # Core system components
│   ├── data/                # Data handling components
│   ├── strategy/            # Trading strategies
│   ├── risk/                # Risk management
│   ├── execution/           # Order and execution management
│   └── analytics/           # Performance analysis and reporting
├── tests/                   # Test suite
└── examples/                # Example scripts and notebooks
```

## Extending the Framework

ADMF-Trader is designed to be extended with custom components:

- **Custom Strategies**: Inherit from `Strategy` to implement your trading logic
- **Custom Indicators**: Create technical indicators by inheriting from `Indicator`
- **Custom Risk Managers**: Implement specialized risk management by extending `RiskManager`
- **Custom Data Handlers**: Support new data sources by implementing `DataHandler`
- **Custom Brokers**: Connect to real brokers by implementing the `Broker` interface

## Regime Ensemble Strategies

ADMF-Trader supports regime-aware trading strategies that can adapt to changing market conditions:

- Detect market regimes using various indicators
- Apply different trading rules based on the identified regime
- Combine multiple sub-strategies optimized for specific regimes
- Automatically switch between strategies as market conditions change

For detailed information, see the [REGIME_ENSEMBLE_README.md](REGIME_ENSEMBLE_README.md) and [REGIME_OPTIMIZATION_GUIDE.md](REGIME_OPTIMIZATION_GUIDE.md).

## Development Roadmap

Please see [IMPROVEMENTS.md](IMPROVEMENTS.md) for the system-wide improvement roadmap, as well as module-specific improvement files in each module directory.

## Quick Start

1. Install the package:
   ```bash
   pip install -e .
   ```

2. Run a simple backtest:
   ```bash
   python -m admf_trader.main --config config/backtest.yaml
   ```

3. Optimize a strategy:
   ```bash
   python -m admf_trader.optimizer --config config/optimization_test.yaml
   ```

4. Generate a performance report:
   ```bash
   python -m admf_trader.analytics.runner --config config/analytics_config.yaml
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.