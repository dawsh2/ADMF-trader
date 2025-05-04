# ADMF-Trader Optimization Module

This module provides tools and implementations for strategy optimization, parameter tuning, and performance evaluation.

## Components Implemented

### Parameter Space

The `ParameterSpace` class defines the space of parameters for optimization, including:

- `IntegerParameter`: Integer parameters with min, max, and step
- `FloatParameter`: Float parameters with min, max, and optional step
- `CategoricalParameter`: Parameters with a set of discrete options
- `BooleanParameter`: Boolean parameters (True/False)

### Optimizers

- `GridSearch`: Exhaustive search over all combinations of parameters
- `RandomSearch`: Random sampling of parameter combinations, useful for high-dimensional spaces

## Usage Examples

### Creating a Parameter Space

```python
from src.strategy.optimization import ParameterSpace

# Create a parameter space
space = ParameterSpace("ma_crossover_space")

# Add parameters
space.add_integer("fast_window", 2, 20, 1)
space.add_integer("slow_window", 10, 50, 5)
space.add_float("threshold", 0.0, 1.0, 0.1)
space.add_categorical("price_key", ["open", "high", "low", "close"])
space.add_boolean("use_volatility")

# Calculate grid size
grid_size = space.get_grid_size()
print(f"Grid size: {grid_size} parameter combinations")

# Get a random point
point = space.get_random_point()
print(f"Random point: {point}")
```

### Grid Search Optimization

```python
from src.strategy.optimization import ParameterSpace, GridSearch

# Create parameter space
space = ParameterSpace("ma_crossover_space")
space.add_integer("fast_window", 2, 10, 1)
space.add_integer("slow_window", 10, 30, 5)

# Create grid search optimizer
optimizer = GridSearch(space)

# Define objective function
def objective_function(params):
    # Create and test strategy with parameters
    # Return performance metric (e.g., Sharpe ratio)
    return sharpe_ratio

# Run optimization
results = optimizer.search(
    objective_function=objective_function,
    maximize=True,
    max_evaluations=100,
    max_time=300  # 5 minutes
)

# Get best parameters
best_params = results['best_params']
best_score = results['best_score']
print(f"Best parameters: {best_params}")
print(f"Best score: {best_score}")
```

### Random Search Optimization

```python
from src.strategy.optimization import ParameterSpace, RandomSearch

# Create parameter space
space = ParameterSpace("ma_crossover_space")
space.add_integer("fast_window", 2, 50, 1)
space.add_integer("slow_window", 10, 200, 1)
space.add_float("threshold", 0.0, 1.0)

# Create random search optimizer
optimizer = RandomSearch(space, seed=42)  # for reproducibility

# Define objective function
def objective_function(params):
    # Create and test strategy with parameters
    # Return performance metric (e.g., Sharpe ratio)
    return sharpe_ratio

# Run optimization
results = optimizer.search(
    objective_function=objective_function,
    num_samples=100,
    maximize=True,
    max_time=300  # 5 minutes
)

# Get best parameters
best_params = results['best_params']
best_score = results['best_score']
print(f"Best parameters: {best_params}")
print(f"Best score: {best_score}")
```

## Future Enhancements

- Bayesian Optimization: Efficient optimization for expensive objective functions
- Genetic Algorithms: Evolution-inspired parameter optimization
- Walk-Forward Testing: Time-series cross-validation for strategies
- Feature Selection: Identify relevant features for strategy development
- Hyperparameter Tuning: Advanced methods for multi-level optimization
