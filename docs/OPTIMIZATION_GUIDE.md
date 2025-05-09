# ADMF-Trader Optimization Guide

This guide provides a comprehensive overview of the optimization capabilities in ADMF-Trader, including parameter optimization with train/test splitting to prevent overfitting and robustness testing.

## Table of Contents

1. [Overview](#overview)
2. [Train/Test Splitting](#traintest-splitting)
3. [Optimization Methods](#optimization-methods)
4. [Robustness Testing](#robustness-testing)
5. [Command-Line Interface](#command-line-interface)
6. [Configuration](#configuration)
7. [Advanced Usage](#advanced-usage)

## Overview

The ADMF-Trader optimization framework provides tools to:

- Find optimal strategy parameters through various search methods
- Prevent overfitting with proper train/test validation
- Test strategy robustness across market regimes and through Monte Carlo simulation
- Analyze strategy performance in different market conditions

## Train/Test Splitting

Train/test splitting is essential to prevent overfitting during strategy optimization. The system supports several splitting methods:

### Ratio-based splitting

Divides the data chronologically based on a ratio (e.g., 70% training, 30% testing):

```
Training Data                     Testing Data
|---------------------------|     |----------|
```

### Date-based splitting

Splits data based on specific dates:

```
Training Data                     Testing Data
|---------------------------|     |----------|
2020-01-01      2022-12-31  2023-01-01  2023-12-31
```

### Fixed-length splitting

Uses fixed time periods for training and testing:

```
Training Data                     Testing Data
|---------------------------|     |----------|
   252 trading days            63 trading days
```

## Optimization Methods

### Grid Search

Exhaustively searches through all combinations of parameters within a defined grid:

- Advantages: Guaranteed to find the global optimum within the grid
- Disadvantages: Exponential complexity with parameter count
- Best for: Small parameter spaces with few parameters

Example:
```bash
python optimize_strategy.py --config config/backtest.yaml --strategy ma_crossover --method grid --param-file config/parameter_spaces/ma_crossover_params.yaml
```

### Random Search

Randomly samples points from the parameter space:

- Advantages: More efficient exploration of large parameter spaces
- Disadvantages: May miss optimal combinations
- Best for: Large parameter spaces with many parameters

Example:
```bash
python optimize_strategy.py --config config/backtest.yaml --strategy ma_crossover --method random --num-samples 200 --param-file config/parameter_spaces/ma_crossover_params.yaml
```

### Walk-Forward Optimization

Tests parameters across rolling windows of data:

- Advantages: Most robust to changing market conditions
- Disadvantages: More complex, requires sufficient data
- Best for: Real-world trading strategies

Walk-forward optimization uses multiple rolling windows for training and testing:

```
Window 1: |--Training--|--Testing--|
Window 2:        |--Training--|--Testing--|
Window 3:               |--Training--|--Testing--|
```

Example:
```bash
python optimize_strategy.py --config config/backtest.yaml --strategy ma_crossover --method walk_forward --window-size 252 --step-size 63 --param-file config/parameter_spaces/ma_crossover_params.yaml
```

## Robustness Testing

Robustness testing ensures that strategy performance is consistent and reliable.

### Monte Carlo Simulation

Monte Carlo simulation resamples historical trades to generate a distribution of potential outcomes:

- Bootstrap sampling: Resamples trades with replacement
- Block bootstrap: Preserves trade sequences for more realistic sampling
- Random returns: Generates synthetic trades based on statistical properties

Example:
```bash
python optimize_strategy.py --config config/backtest.yaml --strategy ma_crossover --enable-monte-carlo --num-simulations 1000 --monte-carlo-method bootstrap
```

### Market Regime Analysis

Analyzes strategy performance across different market conditions:

- Trend-based regimes: Bullish, bearish, sideways
- Volatility-based regimes: High volatility, low volatility
- Mean-reversion regimes: Trending vs. mean-reverting

Example:
```bash
python optimize_strategy.py --config config/backtest.yaml --strategy ma_crossover --enable-regime-analysis --regime-method trend
```

## Command-Line Interface

The `optimize_strategy.py` script provides a comprehensive command-line interface:

```bash
python optimize_strategy.py --help
```

Basic usage:
```bash
python optimize_strategy.py --config config/backtest.yaml --strategy ma_crossover --param-file config/parameter_spaces/ma_crossover_params.yaml --output-dir ./results
```

## Configuration

### Parameter Space Definition

Parameter spaces are defined in YAML or JSON files:

```yaml
# Parameter space for MA Crossover strategy
fast_window:
  type: integer
  min: 2
  max: 50
  step: 1

slow_window:
  type: integer
  min: 10
  max: 200
  step: 5
  log_scale: true  # logarithmic scale for better exploration

price_key:
  type: categorical
  categories:
    - open
    - high
    - low
    - close

use_volatility_adjustment:
  type: boolean
```

### Objective Functions

The optimization process uses objective functions to evaluate strategy performance. Default objective functions include:

- **Sharpe Ratio**: Risk-adjusted return (returns / volatility)
- **Sortino Ratio**: Penalizes only downside volatility
- **Calmar Ratio**: Returns / maximum drawdown
- **Composite Objective**: Weighted combination of metrics with penalties

Custom objective functions can be created by extending the `CompositeObjectiveFunction` class.

## Advanced Usage

### Cross-Validation

For more robust parameter selection, use cross-validation with multiple time periods:

```bash
python optimize_strategy.py --config config/backtest.yaml --strategy ma_crossover --method walk_forward --window-size 252 --step-size 63 --window-type expanding
```

### Combining Optimization with Robustness Testing

For a complete workflow, combine optimization with robustness testing:

```bash
python optimize_strategy.py --config config/backtest.yaml --strategy ma_crossover --method grid --train-test-split 0.7 --enable-monte-carlo --enable-regime-analysis
```

### Parameter Dependencies

Advanced parameter spaces can include dependencies between parameters:

```python
param_space.add_dependency(
    'strategy_type',
    'max_holding_period',
    lambda strategy_type: 
        {'min': 1, 'max': 5} if strategy_type == 'day_trading' 
        else {'min': 5, 'max': 30}
)
```

## Common Anti-Patterns and Pitfalls

### Overfitting

Signs of overfitting include:

- Large performance gap between in-sample and out-of-sample results
- Complex strategies with many parameters
- Excessive sensitivity to small parameter changes
- Perfect in-sample performance

### Insufficient Data

Ensure you have enough data for robust optimization:

- At least 2-3 years of data for daily strategies
- Multiple market regimes (bull, bear, sideways)
- Statistically significant number of trades

### Parameter Instability

Watch for parameter instability in walk-forward optimization:

- Highly variable optimal parameters across windows
- Low consistency score
- Poor out-of-sample performance

## Conclusion

Proper optimization with train/test splitting and robustness testing is essential for developing reliable trading strategies. Use the tools and methods provided by ADMF-Trader to create strategies that generalize well to unseen market conditions and avoid the pitfalls of overfitting.
