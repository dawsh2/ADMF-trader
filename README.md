# Quantitative Trading System

A modular, event-driven algorithmic trading system designed for research, backtesting, and deployment of trading strategies.

## Architecture

The system is built around a clear event flow that defines the responsibility of each module:

1. **Data Module**: Raw data → Bar events
   - Consumes market data from various sources
   - Produces standardized bar events

2. **Strategy Module**: Bar events → Signal events
   - Processes bar events using indicators and rules
   - Produces trading signal events

3. **Risk Module**: Signal events → Order events
   - Manages portfolio state and position sizing
   - Produces executable order events

4. **Execution Module**: Order events → Fill events
   - Handles order execution via brokers
   - Produces fill events and updates system state

## System Components

### Core Module

- **Event System**: Event types, bus, and utilities
- **Configuration**: YAML-based configuration with validation
- **DI Container**: Dependency injection for component creation
- **Utilities**: Component discovery, registries, etc.

### Data Module

- **Data Sources**: CSV, API, and database handlers
- **Data Transformers**: Normalization, resampling, etc.
- **Data Handlers**: Historical and real-time data handlers

### Strategy Module

- **Components**: Base components for strategy building
- **Indicators**: Technical indicators (MA, RSI, etc.)
- **Features**: Feature extraction from indicators
- **Rules**: Trading rules based on indicators and features
- **Strategies**: Composite and regime-adaptive strategies

### Risk Module

- **Portfolio**: Position tracking and portfolio management
- **Risk Managers**: Position sizing and risk controls
- **Risk Limits**: Trading limits and constraint checks

### Execution Module

- **Brokers**: Simulated and live broker interfaces
- **Order Management**: Order creation, tracking, and updates
- **Backtesting**: Historical simulation of strategies

### Analytics Module

- **Performance Metrics**: Return, risk, and trade metrics
- **Reporting**: Report generation and visualization

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/quantitative-trading.git
cd quantitative-trading

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```python
from core.config import Config
from core.di import Container
from execution.backtest import BacktestCoordinator

# Load configuration
config = Config()
config.load_file("config/backtest.yaml")

# Create container
container = Container()

# Register components
container.register("data_handler", HistoricalDataHandler)
container.register("portfolio", PortfolioManager)
container.register("risk_manager", StandardRiskManager)
container.register("strategy", MAStrategyFactory.create)

# Create and run backtest
backtest = BacktestCoordinator(container, config)
results = backtest.run(
    symbols=["AAPL", "MSFT"],
    start_date="2020-01-01",
    end_date="2020-12-31"
)

# Print results
print(results["summary_report"])
```

### Configuration

```yaml
# Example configuration file

# Data configuration
data:
  source: csv
  directory: data/historical
  file_pattern: "{symbol}_{timeframe}.csv"

# Strategy configuration
strategy:
  class: strategies.ma_crossover.MACrossoverStrategy
  parameters:
    fast_ma: 10
    slow_ma: 30
    symbols: ["AAPL", "MSFT"]

# Risk configuration
risk:
  position_sizing:
    method: percent_equity
    percent: 2.0
  limits:
    max_position_size: 1000
    max_exposure: 1.0

# Execution configuration
execution:
  broker:
    name: simulated
    slippage:
      model_type: percentage
      params:
        slippage_percent: 0.1
    commission:
      model_type: fixed
      params:
        commission: 5.0
```

## Architecture Principles

1. **Modularity**: Components are loosely coupled and can be replaced or extended
2. **Event-Driven**: Communication between components via events
3. **Configurability**: Components configurable via YAML
4. **Testability**: Components can be tested independently
5. **Dependency Injection**: Components receive dependencies via DI

## Risk Management

The Risk Management module handles:

- Position tracking for accurate P&L calculation
- Portfolio state management
- Position sizing with multiple strategies
- Risk limits and constraints
- Order validation

## Execution and Backtesting

The Execution module provides:

- Broker interfaces for order execution
- Order management for tracking orders
- Backtest coordination for historical simulation

## Analytics and Reporting

The Analytics module offers:

- Performance metric calculation
- Detailed reporting of results
- Trade analysis and visualization

## Future Development

- Optimization module for parameter tuning
- Machine learning integration
- Live trading support
- Web interface for monitoring

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
