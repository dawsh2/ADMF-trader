# ADMF-Trader Optimization Framework

This module provides a standardized framework for optimizing trading strategies while preventing overfitting through train/test validation.

## Overview

The optimization framework leverages the analytics module for consistent performance calculations and can be run directly from the main.py entry point using configuration files.

Key features:
- Consistent metrics calculation using the analytics module
- Multiple optimization methods (grid search, random search, walk-forward)
- Proper train/test validation to prevent overfitting
- Standardized reporting and visualization
- Fully configurable through YAML files

## Usage

The optimization framework can be used in two ways:

### 1. Command Line Interface

Run optimization directly from the command line:

```bash
python main.py optimize --config config/optimization/my_strategy.yaml
```

#### Command Line Arguments

When not using a configuration file, you can specify options directly:

```bash
python main.py optimize --strategy simple_ma_crossover --param-file config/parameter_spaces/ma_crossover_params.yaml --method grid --objective sharpe_ratio --train-ratio 0.7 --test-ratio 0.3
```

### 2. Programmatic API

```python
from src.strategy.optimization.optimizer import StrategyOptimizer

# Create configuration
config = {
    'strategy': {
        'name': 'simple_ma_crossover'
    },
    'parameter_file': 'config/parameter_spaces/ma_crossover_params.yaml',
    'optimization': {
        'method': 'grid',
        'objective': 'sharpe_ratio'
    },
    'data': {
        'train_test_split': {
            'method': 'ratio',
            'train_ratio': 0.7,
            'test_ratio': 0.3
        }
    }
}

# Create optimizer
optimizer = StrategyOptimizer(config)

# Run optimization
results = optimizer.optimize()
```

## Configuration

The optimization framework is configured through YAML files. A template is provided at `config/optimization/template.yaml`.

### Key Configuration Sections

#### Strategy

Defines the strategy to optimize and any fixed parameters:

```yaml
strategy:
  name: "simple_ma_crossover"
  fixed_params:
    position_size: 1.0
    use_trailing_stop: false
```

#### Parameter Space

Defines the parameters to optimize:

```yaml
parameter_space:
  - name: fast_period
    type: integer
    min: 5
    max: 30
    step: 5
  - name: slow_period
    type: integer
    min: 20
    max: 100
    step: 20
```

Or reference a separate parameter file:

```yaml
parameter_file: "config/parameter_spaces/ma_crossover_params.yaml"
```

#### Optimization Settings

Defines the optimization method and objective function:

```yaml
optimization:
  method: "grid"  # grid, random, walk_forward
  objective: "sharpe_ratio"  # sharpe_ratio, profit_factor, max_drawdown, etc.
  
  # For random search
  num_trials: 100
  
  # For walk-forward optimization
  window_size: 60  # trading days
  step_size: 20
  window_type: "rolling"  # rolling, expanding
```

#### Train/Test Split

Configures how data is split for validation:

```yaml
data:
  train_test_split:
    enabled: true
    method: "ratio"  # ratio, date, or fixed
    train_ratio: 0.7
    test_ratio: 0.3
```

## Available Objective Functions

The framework provides several objective functions:

- `total_return`: Maximize total return
- `sharpe_ratio`: Maximize Sharpe ratio (risk-adjusted return)
- `profit_factor`: Maximize profit factor (gross profit / gross loss)
- `max_drawdown`: Minimize maximum drawdown
- `win_rate`: Maximize win rate
- `expectancy`: Maximize expectancy (win rate * avg win - loss rate * avg loss)
- `risk_adjusted_return`: Maximize return / max drawdown
- `combined_score`: Weighted combination of multiple metrics
- `stability_score`: Maximize equity curve stability

## Optimization Methods

### Grid Search

Exhaustively tries all combinations of parameters within the defined grid.

```yaml
optimization:
  method: "grid"
```

### Random Search

Randomly samples parameter combinations from the defined space.

```yaml
optimization:
  method: "random"
  num_trials: 100
```

### Walk-Forward Optimization

Optimizes parameters across rolling windows of data to ensure robustness.

```yaml
optimization:
  method: "walk_forward"
  window_size: 60  # trading days
  step_size: 20
  window_type: "rolling"  # rolling, expanding
```

## Preventing Overfitting

The framework uses several techniques to prevent overfitting:

1. **Train/Test Validation**: Optimizes on training data and validates on unseen test data
2. **Walk-Forward Analysis**: Tests parameters across different market regimes
3. **Overfitting Metrics**: Calculates performance differences between train and test to detect overfitting
4. **Multiple Objectives**: Uses risk-adjusted metrics rather than just maximizing returns

## Reporting

The framework generates comprehensive reports in multiple formats:

- **Text**: Human-readable summary of optimization results
- **CSV**: Detailed results for all parameter combinations
- **HTML**: Interactive report with visualizations
- **Visualizations**: Parameter heatmaps, equity curves, and more

Reports are saved to the specified output directory (default: `./optimization_results`).

## Example

To optimize a simple moving average crossover strategy:

1. Create a configuration file:

```yaml
# config/optimization/ma_crossover.yaml
strategy:
  name: "simple_ma_crossover"
  
parameter_space:
  - name: fast_period
    type: integer
    min: 5
    max: 30
    step: 5
  - name: slow_period
    type: integer
    min: 20
    max: 100
    step: 20
    
optimization:
  method: "grid"
  objective: "sharpe_ratio"
  
data:
  symbols: ["AAPL"]
  sources:
    - symbol: "AAPL"
      file: "data/AAPL_1day.csv"
      
  train_test_split:
    enabled: true
    method: "ratio"
    train_ratio: 0.7
    test_ratio: 0.3
```

2. Run the optimization:

```bash
python main.py optimize --config config/optimization/ma_crossover.yaml
```

3. Review the results in the output directory.
