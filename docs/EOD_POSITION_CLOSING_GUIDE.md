# End-of-Day Position Closing Guide

## Overview

The End-of-Day (EOD) Position Closing feature allows strategies to automatically close all open positions at the end of each trading day. This feature is particularly useful for:

- Day trading strategies that shouldn't hold overnight risk
- Backtesting strategies with daily risk management constraints
- Simulating trading strategies with specific operational constraints

## How It Works

When enabled, the BacktestCoordinator:

1. Monitors bar events and detects when the trading day changes
2. When a new day is detected, automatically closes all positions from the previous day
3. Creates market orders in the opposite direction of each position
4. Marks closing orders with the reason "EOD_POSITION_CLOSE" for reporting and analysis

## Configuration

To enable EOD position closing, add the `close_positions_eod` flag to your backtest configuration:

```python
config = {
    'close_positions_eod': True,
    # Other configuration parameters...
}
```

You can also configure this in a YAML configuration file:

```yaml
backtest:
  close_positions_eod: true
  initial_capital: 100000.0
  # Other parameters...
```

## Example Usage

Here's a complete example of setting up a backtest with EOD position closing:

```python
from src.core.event_system.event_bus import EventBus
from src.core.trade_repository import TradeRepository
from src.execution.backtest.backtest_coordinator import BacktestCoordinator
from src.data.data_handler import CSVDataHandler
from src.strategy.ma_crossover import MACrossoverStrategy
from src.risk.portfolio.portfolio import Portfolio
from src.risk.position_manager import PositionManager
from src.execution.broker.simulated_broker import SimulatedBroker
from src.execution.broker.market_simulator import MarketSimulator

# Create event bus and trade repository
event_bus = EventBus()
trade_repository = TradeRepository()

# Create context
context = {
    'event_bus': event_bus,
    'trade_repository': trade_repository
}

# Create backtest configuration with EOD position closing
config = {
    'close_positions_eod': True,
    'broker': {
        'slippage': {
            'model': 'fixed',
            'slippage_percent': 0.1
        },
        'commission': {
            'commission_type': 'percentage',
            'rate': 0.1,
            'min_commission': 1.0
        }
    }
}

# Create components
data_handler = CSVDataHandler('data_handler', {'file_path': 'data/SPY_1min.csv'})
strategy = MACrossoverStrategy('ma_strategy', {'short_window': 10, 'long_window': 30})
position_manager = PositionManager('position_manager')
portfolio = Portfolio('portfolio', {'initial_capital': 100000.0})
market_simulator = MarketSimulator('market_simulator')
broker = SimulatedBroker('broker', config['broker'])

# Create backtest coordinator
backtest = BacktestCoordinator('backtest', config)

# Add components to backtest
backtest.add_component('data_handler', data_handler)
backtest.add_component('strategy', strategy)
backtest.add_component('position_manager', position_manager)
backtest.add_component('portfolio', portfolio)
backtest.add_component('market_simulator', market_simulator)
backtest.add_component('broker', broker)

# Initialize backtest
backtest.initialize(context)

# Setup backtest
backtest.setup()

# Run backtest
results = backtest.run()

# Analyze results
total_trades = len(results['trades'])
eod_closing_trades = len([t for t in results['trades'] if t.get('reason') == 'EOD_POSITION_CLOSE'])

print(f"Total trades: {total_trades}")
print(f"EOD closing trades: {eod_closing_trades}")
print(f"Final capital: {results['final_capital']}")
```

## Implementation Details

The EOD position closing is implemented in the `BacktestCoordinator` class through two main methods:

1. `on_bar_eod_check(self, event)` - Monitors bar events and detects day changes
2. `_close_all_positions(self, trading_day)` - Closes all positions when a day change is detected

Here's a simplified view of the implementation:

```python
def on_bar_eod_check(self, event):
    """Check for end-of-day position closing."""
    bar_data = event.get_data()
    timestamp = bar_data.get('timestamp')
    
    # Get current date (ignoring time)
    current_date = timestamp.date()
    
    # First bar of the backtest - initialize the day tracking
    if self.current_day is None:
        self.current_day = current_date
        return
        
    # Check if day has changed
    if current_date != self.current_day:
        # Day has changed - close positions from previous day
        logger.info(f"Day changed from {self.current_day} to {current_date}, closing positions")
        
        # Close positions
        self._close_all_positions(self.current_day)
        
        # Update current day
        self.current_day = current_date
```

## Performance Impact

Enabling EOD position closing may impact backtest performance in several ways:

1. **Additional Trades**: Creates more trades, which may increase commission costs
2. **Reduced Overnight Exposure**: Eliminates overnight market risk
3. **Missed Overnight Moves**: May miss profitable gaps and overnight movements
4. **More Realistic Day Trading**: Better simulates actual day trading constraints

## Best Practices

1. **Use with Intraday Data**: This feature is most useful with intraday data (minutes or hours)
2. **Consider Commission Costs**: Factor in the additional commission costs from more trades
3. **Compare Results**: Run tests both with and without EOD closing to understand the impact
4. **Analyze EOD Trades**: Review the EOD closing trades separately in your analysis
5. **Timezone Awareness**: Ensure your data timestamps use a consistent timezone

## Limitations

1. **Timestamp Requirements**: All bar data must have valid timestamps with date information
2. **Market Close Detection**: The system detects day changes, not actual market closes
3. **Fill Assumptions**: Assumes all closing orders can be filled at the last available price
4. **After-Hours Trading**: Doesn't account for after-hours or pre-market trading

## Troubleshooting

If you encounter issues with EOD position closing:

1. **Check Timestamps**: Ensure all bar data has valid timestamps with date information
2. **Verify Event Flow**: Ensure bar events are being properly published and received
3. **Check Position Manager**: Verify the position manager is tracking positions correctly
4. **Log Verification**: Enable debug logging to see detailed EOD closing information

## Advanced Configuration

For more control over the EOD closing behavior, you can implement a custom position manager that defines a `close_all_positions` method with specific logic:

```python
class CustomPositionManager(PositionManager):
    def close_all_positions(self, reason=None):
        """Custom implementation of position closing."""
        # Implement custom logic for position closing
        # For example, close only certain symbols, use limit orders, etc.
```

Then use this custom position manager in your backtest:

```python
position_manager = CustomPositionManager('position_manager')
backtest.add_component('position_manager', position_manager)
```

## Conclusion

The EOD position closing feature is a powerful tool for simulating day trading strategies and managing overnight risk in backtests. By automatically closing positions at the end of each trading day, it provides a more realistic simulation of day trading constraints and helps assess strategy performance without overnight exposure.