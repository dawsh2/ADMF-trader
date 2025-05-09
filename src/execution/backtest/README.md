# Backtest Module

## Overview

The Backtest module provides components for simulating trading strategies using historical data. It coordinates data flow between components, handles event processing, and collects performance metrics.

## Key Components

### BacktestCoordinator

The `BacktestCoordinator` is the central component that manages the backtest process. It:

- Coordinates component initialization and lifecycle
- Processes data from the data handler
- Manages event flow between components
- Collects and processes results
- Provides features like end-of-day position closing

## Usage

### Basic Usage

```python
from src.core.event_system.event_bus import EventBus
from src.execution.backtest.backtest_coordinator import BacktestCoordinator
from src.data.data_handler import CSVDataHandler
from src.strategy.ma_crossover import MACrossoverStrategy
from src.risk.portfolio.portfolio import Portfolio
from src.execution.broker.simulated_broker import SimulatedBroker

# Create event bus
event_bus = EventBus()

# Create components
data_handler = CSVDataHandler('data_handler', {'file_path': 'data/SPY_1min.csv'})
strategy = MACrossoverStrategy('ma_strategy', {'short_window': 10, 'long_window': 30})
portfolio = Portfolio('portfolio', {'initial_capital': 100000.0})
broker = SimulatedBroker('broker')

# Create backtest configuration
config = {
    'close_positions_eod': True,  # Enable end-of-day position closing
    'broker': {
        'slippage': {
            'model': 'variable',
            'base_slippage_percent': 0.05
        },
        'commission': {
            'commission_type': 'percentage',
            'rate': 0.1
        }
    }
}

# Create backtest coordinator
backtest = BacktestCoordinator('backtest', config)

# Add components to backtest
backtest.add_component('data_handler', data_handler)
backtest.add_component('strategy', strategy)
backtest.add_component('portfolio', portfolio)
backtest.add_component('broker', broker)

# Create context
context = {
    'event_bus': event_bus,
    'trade_repository': trade_repository
}

# Initialize and run backtest
backtest.initialize(context)
backtest.setup()
results = backtest.run()

# Process results
print(f"Final capital: {results['final_capital']}")
print(f"Total trades: {results['statistics']['trades_executed']}")
```

## End-of-Day Position Closing

The BacktestCoordinator includes support for end-of-day position closing, which is useful for strategies that shouldn't hold positions overnight.

### How It Works

1. The coordinator monitors bar events and detects when the trading day changes
2. When a new day is detected, all positions from the previous day are closed
3. Closing is done by creating market orders in the opposite direction of each position
4. All closing orders are marked with reason "EOD_POSITION_CLOSE"

### Enabling EOD Position Closing

To enable end-of-day position closing, add the following to your backtest configuration:

```python
config = {
    'close_positions_eod': True
}
```

## Broker Integration

The BacktestCoordinator integrates with the enhanced broker module to provide more realistic market simulation.

### Broker Configuration

```python
config = {
    'broker': {
        # Slippage model configuration
        'slippage': {
            'model': 'variable',  # Options: 'fixed' or 'variable'
            'base_slippage_percent': 0.05,  # 0.05% base slippage
            'size_impact': 0.01,  # Impact of order size
            'volatility_impact': 0.5,  # Impact of volatility
            'random_factor': 0.2  # Random component
        },
        
        # Commission model configuration
        'commission': {
            'commission_type': 'percentage',  # Options: 'percentage', 'fixed', 'per_share', 'tiered'
            'rate': 0.1,  # 0.1% commission rate
            'min_commission': 1.0,  # $1 minimum commission
            'max_commission': 50.0  # $50 maximum commission
        },
        
        # Market simulator configuration
        'market_simulator': {
            'max_price_impact': 0.01,  # Maximum price impact
            'liquidity_factor': 1.0,  # Market liquidity
            'enable_gaps': True,  # Enable price gaps
            'randomize_fills': True  # Add randomness to fills
        }
    }
}
```

## Component Lifecycle

The BacktestCoordinator manages component lifecycle as follows:

1. **Initialization**: Components are initialized with a shared context
2. **Setup**: Components are set up before the backtest begins
3. **Execution**: The backtest runs, processing data and events
4. **Closing**: All positions are closed at the end of the backtest
5. **Cleanup**: Components are stopped and resources released

## Results Processing

After a backtest completes, the coordinator processes the results to:

1. Calculate performance metrics
2. Collect trade information
3. Process equity curve data
4. Verify consistency between trades and equity

Results are returned as a dictionary containing:

```python
{
    'final_capital': 110000.0,  # Final portfolio value
    'positions': {...},         # Final positions
    'trades': [...],            # List of all trades
    'statistics': {             # Performance statistics
        'return_pct': 10.0,
        'sharpe_ratio': 1.5,
        'max_drawdown': 5.0,
        'win_rate': 60.0,
        'profit_factor': 1.8,
        ...
    },
    'equity_curve': [...],      # Equity curve data
    'trades_equity_consistent': True  # Consistency check flag
}
```

## Error Handling

The BacktestCoordinator includes error handling for common issues:

- Missing components
- Data inconsistency
- Event processing failures
- Position closing errors

Errors are logged with detailed information to help diagnose issues.

## Best Practices

1. **Component Separation**: Keep components focused on their specific responsibilities
2. **State Isolation**: Ensure components can be reset for multiple backtest runs
3. **Error Handling**: Implement proper error handling in all components
4. **Resource Management**: Release resources properly in the stop/cleanup methods
5. **Event Usage**: Use the standardized event structures defined in the event system

## Known Issues

1. **Event System Inconsistencies**: Some event-related issues have been identified (see `/docs/EVENT_SYSTEM_ISSUES.md`)
2. **Testing Complexity**: Testing components in isolation can be challenging due to dependencies

## Future Enhancements

1. **Multi-threading Support**: Parallel processing for faster backtests
2. **Live Trading Integration**: Seamless transition from backtest to live trading
3. **Advanced Market Impact Models**: More sophisticated market simulation
4. **Scenario Analysis**: Support for testing strategies under different market scenarios