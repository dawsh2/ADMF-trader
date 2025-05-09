# Broker Integration and EOD Position Closing Guide

This document explains how to use the enhanced broker integration and end-of-day position closing features in the ADMF-trader backtest system.

## Overview

The backtesting system has been enhanced with:

1. Proper broker integration with realistic market simulation
2. Configurable slippage and commission models
3. End-of-day position closing for overnight risk management
4. State isolation for optimization support

These features make the backtests more realistic and allow for better risk management simulation.

## Configuration

### End-of-Day Position Closing

To enable the end-of-day position closing feature, add the following to your backtest configuration:

```yaml
backtest:
  close_positions_eod: true  # Enable end-of-day position closing
```

When enabled, all open positions will be closed at the end of each trading day, simulating a strategy that doesn't hold positions overnight.

### Broker Configuration

The broker component can be configured with custom slippage and commission models:

```yaml
backtest:
  broker:
    # Slippage model configuration
    slippage:
      model: "variable"  # Options: "fixed" or "variable"
      base_slippage_percent: 0.05  # 0.05% base slippage
      
    # Commission model configuration
    commission:
      commission_type: "percentage"  # Options: "percentage", "fixed", "per_share", "tiered"
      rate: 0.1  # 0.1% commission rate
      min_commission: 1.0  # $1 minimum commission
```

See the `eod_position_closing_example.yaml` file for a complete example configuration.

## Slippage Models

### Fixed Slippage Model

Applies a fixed percentage slippage to all orders:

```yaml
slippage:
  model: "fixed"
  slippage_percent: 0.1  # 0.1% slippage
```

### Variable Slippage Model

Calculates slippage based on order size, market volatility, and random factors:

```yaml
slippage:
  model: "variable"
  base_slippage_percent: 0.05  # Base slippage
  size_impact: 0.01  # Impact of order size
  volatility_impact: 0.5  # Impact of market volatility
  random_factor: 0.2  # Random component
```

## Commission Models

The system supports several commission models:

### Percentage Commission

```yaml
commission:
  commission_type: "percentage"
  rate: 0.1  # 0.1% of trade value
```

### Fixed Commission

```yaml
commission:
  commission_type: "fixed"
  rate: 5.0  # $5 per trade
```

### Per-Share Commission

```yaml
commission:
  commission_type: "per_share"
  rate: 0.01  # $0.01 per share
```

### Tiered Commission

Tiered commissions can be configured in the code by calling `commission_model.add_tier(min_value, max_value, rate)`.

## Market Simulator

The market simulator provides more realistic market behavior:

```yaml
market_simulator:
  max_price_impact: 0.01  # Maximum price impact
  liquidity_factor: 1.0  # Market liquidity
  enable_gaps: true  # Enable price gaps
  randomize_fills: true  # Add randomness to fills
```

## How EOD Position Closing Works

1. The system tracks the current trading day based on bar timestamps
2. When a new day is detected, all positions from the previous day are closed
3. Closing is done by creating market orders in the opposite direction of each position
4. All closing orders are marked with reason "EOD_POSITION_CLOSE"

## Implementation Details

- The `BacktestCoordinator` class handles the setup of broker components
- The `on_bar_eod_check` method monitors for day changes
- The `_close_all_positions` method handles the actual position closing
- Position closing is implemented by creating offsetting orders through the event system

## Best Practices

1. Always enable EOD position closing when backtesting strategies that shouldn't hold overnight risk
2. Configure realistic slippage and commission models to avoid overly optimistic results
3. Use the variable slippage model for more realistic simulations of large orders
4. Monitor the logs for information about positions being closed at end of day

## Examples

Run a backtest with EOD position closing:

```python
from src.execution.backtest import BacktestCoordinator
from src.core.config import load_config

# Load config with EOD position closing enabled
config = load_config('config/eod_position_closing_example.yaml')

# Create backtest coordinator
backtest = BacktestCoordinator('backtest', config['backtest'])

# Run the backtest
results = backtest.run()
```