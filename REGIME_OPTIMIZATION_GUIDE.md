# Regime-Based Ensemble Optimization Guide

This guide explains how to implement and use the regime-based ensemble optimization in the ADMF-trader system. It covers the key concepts, configuration options, and usage instructions.

## Overview

Regime-based ensemble optimization is a sophisticated approach that:

1. Identifies distinct market regimes (trending, mean-reverting, volatile, etc.)
2. Optimizes strategy parameters separately for each regime
3. Creates an ensemble strategy that adapts its behavior based on the detected regime
4. Uses train/test validation to prevent overfitting

This approach can significantly improve trading strategy robustness by adapting to changing market conditions.

## Implementation

The implementation consists of several key components:

1. **Regime Detection**: Uses market metrics to identify different market regimes
2. **Ensemble Strategy**: Combines multiple sub-strategies with regime-dependent weights
3. **Parameter Optimization**: Optimizes parameters for each regime or for the overall strategy
4. **Validation Framework**: Tests performance across different market regimes and prevents overfitting

## Configuration Options

The optimization is configured through YAML files with the following key sections:

### Basic Settings

```yaml
backtest:
  strategy: regime_ensemble
  initial_capital: 100000.0
  symbols: ['SPY']
  timeframe: "1min"

data:
  source_type: csv
  sources:
    - symbol: SPY
      file: data/SPY_1min.csv
      date_column: timestamp
      date_format: "%Y-%m-%d %H:%M:%S"
  
  # Train/test split configuration
  train_test_split:
    method: ratio
    train_ratio: 0.7
    test_ratio: 0.3
```

### Optimization Settings

```yaml
optimization:
  method: grid  # grid, random or walk_forward
  objective: train_test_combined  # Special objective that combines train and test performance
  train_weight: 0.4  # Weight for training performance
  test_weight: 0.6   # Weight for test performance (higher to prevent overfitting)
  sub_objective: sharpe_ratio  # Metric used for both train and test evaluation
```

### Parameter Space

```yaml
parameter_space:
  # Regime detection parameters
  - name: volatility_window
    type: integer
    min: 30
    max: 120
    step: 30
    
  # Strategy parameters
  - name: fast_ma_window
    type: integer
    min: 10
    max: 40
    step: 10
    
  # Regime weights
  - name: trend_weight_trend_following
    type: float
    min: 0.5
    max: 1.0
    step: 0.25
```

## Running Optimization

To run the optimization, use the main entry point with the `--optimize` flag:

```bash
python main.py --config config/regime_ensemble_optimization.yaml --optimize
```

Command line options:

- `--config`: Path to the configuration file (required)
- `--optimize`: Flag to enable optimization mode
- `--method`: Override the optimization method (grid, random, walk_forward)
- `--param-file`: Optional path to a separate parameter space file
- `--output-dir`: Directory for results output
- `--verbose` or `--debug`: Enable more detailed logging

## Interpreting Results

The optimization generates several outputs:

1. **JSON Results**: Detailed optimization results including best parameters
2. **HTML Report**: Human-readable report with performance metrics and charts
3. **Overfitting Analysis**: Plot showing training vs. testing performance
4. **Equity Curves**: Comparison of equity curves on training and testing data

### Overfitting Analysis

The overfitting analysis plot shows training vs. testing performance for all parameter combinations. A high correlation between training and testing scores indicates a robust strategy that generalizes well.

### Best Parameters

The best parameters section shows the optimal configuration for each component. For a balanced approach that performs well across all regimes, choose parameters that have:

1. Good performance on both training and testing data
2. Reasonable performance across all detected regimes
3. A good balance between returns, risk, and stability

## Advanced Usage

### Regime-Specific Optimization

To optimize parameters separately for each regime, you can:

1. Run the standard optimization first to identify market regimes
2. Filter your data into regime-specific datasets
3. Run separate optimizations for each regime
4. Combine the regime-specific strategies into a final ensemble

### Walk-Forward Optimization

For even more robust results, use walk-forward optimization:

```yaml
optimization:
  method: walk_forward
  window_size: 60   # Days for each window
  step_size: 20     # Days to advance each window
  window_type: rolling  # rolling or expanding
```

## Troubleshooting

Common issues:

1. **No trades generated**: Check your data quality and regime detection parameters
2. **Poor test performance**: Likely overfitting; reduce parameter space or increase regularization
3. **Inconsistent regime detection**: Adjust regime thresholds or use alternative detection methods
4. **Memory errors**: Reduce parameter space size or use random search instead of grid search

## Next Steps

After optimization, implement the results by:

1. Creating a regime_ensemble instance with optimized parameters
2. Running backtests across different market conditions to validate
3. Implementing forward testing or paper trading
4. Setting up monitoring to evaluate regime detection accuracy

## Conclusion

Regime-based ensemble optimization provides a powerful framework for building adaptive trading strategies. By identifying market regimes and optimizing parameters for each, you can create strategies that perform well across a wide range of market conditions.