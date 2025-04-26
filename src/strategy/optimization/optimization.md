# Advanced Optimization Framework for ADMF-Trader

This document outlines the design for a flexible, powerful optimization system for algorithmic trading strategies. The framework supports granular control over optimization processes, multiple objective functions, various optimization techniques, and complex optimization workflows.

## Implementation Philosophy

The design philosophy behind this optimization framework centers around:

1. **Flexible Component Integration**: Optimizers should work seamlessly with any component in the trading system 

2. **Minimal Boilerplate**: Avoid repetitive code when creating optimization workflows

3. **Configuration-Driven**: Enable complex optimization processes to be defined declaratively 

4. **Granular Control**: Provide fine-grained control over what parameters are optimized and how

5. **Sequential Optimization**: Support multi-stage optimization where results from one stage inform the next

6. **Joint Optimization**: Allow multiple components to be optimized simultaneously when needed

7. **Regime-Specific Optimization**: Enable parameters to be optimized separately for different market regimes

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Framework Architecture](#framework-architecture)
3. [Optimization Workflows](#optimization-workflows)
4. [Configuration System](#configuration-system)
5. [Extending the Framework](#extending-the-framework)
6. [Implementation Guidelines](#implementation-guidelines)
7. [Example Use Cases](#example-use-cases)

## Core Concepts

### Optimization Components

The framework is built around several key components:

- **Parameter Spaces**: Defines the search space for optimization
- **Objective Functions**: Metrics to optimize for (e.g., Sharpe ratio, win rate)
- **Optimizers**: Algorithms that search through the parameter space
- **Constraints**: Rules that limit parameter combinations
- **Workflows**: Sequences of optimization steps

### Flexibility First

The framework prioritizes flexibility over rigid structure:

- Any component can be optimized independently
- Multiple optimization methods can be used in sequence
- Different metrics can be used at different stages
- Complex workflows can be defined declaratively

## Framework Architecture

### Class Hierarchy

```
OptimizationBase
├── ParameterSpace
│   ├── DiscreteParameterSpace
│   ├── ContinuousParameterSpace
│   └── MixedParameterSpace
├── Objective
│   ├── ReturnObjective
│   ├── RiskObjective
│   ├── CompositeObjective
│   └── CustomObjective
├── Optimizer
│   ├── GridOptimizer
│   ├── RandomOptimizer
│   ├── BayesianOptimizer
│   ├── GeneticOptimizer
│   └── CustomOptimizer
├── ComponentOptimizer      # Component-specific optimization
├── OptimizerManager        # Orchestrates optimization process
├── Constraint
│   ├── RangeConstraint
│   ├── RelationalConstraint
│   └── CustomConstraint
└── Workflow
    ├── SingleStageWorkflow 
    ├── SequentialWorkflow
    ├── ParallelWorkflow
    └── CustomWorkflow
```

### Core Components

#### 1. OptimizerManager

Central manager for orchestrating the optimization process:

```python
class OptimizerManager:
    """Manager for orchestrating optimization processes."""
    
    def __init__(self, config=None, backtest_runner=None):
        """Initialize optimizer manager."""
        self.config = config or {}
        self.backtest_runner = backtest_runner
        self.optimizers = {}
        self.workflows = {}
        self.results = {}
        
    def register_optimizer(self, name, optimizer):
        """Register an optimizer."""
        self.optimizers[name] = optimizer
        
    def register_workflow(self, name, workflow):
        """Register a workflow."""
        self.workflows[name] = workflow
        
    def create_workflow(self, workflow_type, config):
        """Create a workflow from configuration."""
        # Factory method for creating workflows
        if workflow_type == 'sequential':
            return SequentialWorkflow.from_config(config, self.backtest_runner)
        elif workflow_type == 'regime_based':
            return RegimeBasedWorkflow.from_config(config, self.backtest_runner)
        # Add more workflow types as needed
        
    def run_workflow(self, workflow_name, **kwargs):
        """Run a registered workflow."""
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow {workflow_name} not found")
            
        results = workflow.run(**kwargs)
        self.results[workflow_name] = results
        return results
        
    def run_from_config(self, config):
        """Run optimization from configuration."""
        # Parse config
        workflow_type = config.get('type', 'sequential')
        workflow_config = config.get('stages', [])
        
        # Create workflow
        workflow = self.create_workflow(workflow_type, workflow_config)
        
        # Run workflow
        results = workflow.run()
        
        return results
        
    def save_results(self, filename):
        """Save optimization results to file."""
        # Save results
        
    def load_results(self, filename):
        """Load optimization results from file."""
        # Load results
```

#### 2. ComponentOptimizer

Specialized optimizer for trading components with mixins for different component types:

```python
class ComponentOptimizer:
    """Optimizer for specific component types."""
    
    def __init__(self, component, optimizer, objective, backtest_runner=None):
        """Initialize component optimizer."""
        self.component = component
        self.optimizer = optimizer
        self.objective = objective
        self.backtest_runner = backtest_runner
        
    def optimize(self, **kwargs):
        """Run optimization for the component."""
        # Extract parameter space from component
        parameter_space = ParameterSpace.from_component(self.component)
        
        # Configure optimizer
        self.optimizer.set_parameter_space(parameter_space)
        
        # Define evaluation function
        def evaluate(params):
            # Set parameters on component
            self.component.set_parameters(params)
            
            # Run backtest
            results = self.backtest_runner()
            
            # Calculate objective
            return self.objective.calculate(results)
            
        # Run optimization
        return self.optimizer.optimize(evaluate, **kwargs)
        
    @classmethod
    def from_config(cls, component, config, backtest_runner=None):
        """Create component optimizer from configuration."""
        # Parse config
        optimizer_config = config.get('optimizer', {})
        objective_config = config.get('objective', {})
        
        # Create optimizer
        optimizer = create_optimizer_from_config(optimizer_config)
        
        # Create objective
        objective = create_objective_from_config(objective_config)
        
        # Create component optimizer
        return cls(component, optimizer, objective, backtest_runner)
```

#### 3. Component Optimizer Mixins

Specialized mixins for different component types:

```python
class IndicatorOptimizerMixin:
    """Mixin for optimizing indicators."""
    
    def optimize_indicator_parameters(self, indicator, **kwargs):
        """Optimize indicator parameters."""
        parameter_space = ParameterSpace.from_component(indicator)
        
        def evaluate(params):
            indicator.set_parameters(params)
            # Update indicator values
            indicator.calculate(self.backtest_runner.get_data())
            # Run backtest
            results = self.backtest_runner()
            return self.objective.calculate(results)
            
        return self.optimizer.optimize(evaluate, **kwargs)

class RuleOptimizerMixin:
    """Mixin for optimizing rules."""
    
    def optimize_rule_parameters(self, rule, **kwargs):
        """Optimize rule parameters."""
        parameter_space = ParameterSpace.from_component(rule)
        
        def evaluate(params):
            rule.set_parameters(params)
            # Run backtest
            results = self.backtest_runner()
            return self.objective.calculate(results)
            
        return self.optimizer.optimize(evaluate, **kwargs)

class StrategyOptimizerMixin:
    """Mixin for optimizing strategies."""
    
    def optimize_strategy_parameters(self, strategy, **kwargs):
        """Optimize strategy parameters."""
        parameter_space = ParameterSpace.from_component(strategy)
        
        def evaluate(params):
            strategy.set_parameters(params)
            # Run backtest
            results = self.backtest_runner()
            return self.objective.calculate(results)
            
        return self.optimizer.optimize(evaluate, **kwargs)
        
    def optimize_rule_weights(self, strategy, **kwargs):
        """Optimize rule weights within a strategy."""
        # Extract rules
        rules = strategy.get_components(type='rule')
        
        # Create weight parameter space
        weight_space = {}
        for rule_name, rule in rules.items():
            weight_space[f"weights.{rule_name}"] = [0.1, 0.5, 1.0, 1.5, 2.0]
            
        parameter_space = ParameterSpace(weight_space)
        
        def evaluate(params):
            for rule_name, weight in params.items():
                rule_name = rule_name.replace('weights.', '')
                if rule_name in rules:
                    rules[rule_name].weight = weight
                    
            # Run backtest
            results = self.backtest_runner()
            return self.objective.calculate(results)
            
        return self.optimizer.optimize(evaluate, **kwargs)
```

#### 4. JointOptimizer

Optimizer for joint optimization of multiple components:

```python
class JointOptimizer:
    """Optimize multiple components simultaneously."""
    
    def __init__(self, components, optimizer, objective, backtest_runner=None):
        """Initialize joint optimizer."""
        self.components = components  # List of (component, param_prefix) tuples
        self.optimizer = optimizer
        self.objective = objective
        self.backtest_runner = backtest_runner
        
    def optimize(self, **kwargs):
        """Run joint optimization."""
        # Build combined parameter space
        combined_space = {}
        
        for component, prefix in self.components:
            # Get component parameter space
            component_space = component.get_parameter_space()
            
            # Add prefix to parameter names if provided
            if prefix:
                component_space = {f"{prefix}.{k}": v for k, v in component_space.items()}
                
            # Add to combined space
            combined_space.update(component_space)
            
        parameter_space = ParameterSpace(combined_space)
        
        # Configure optimizer
        self.optimizer.set_parameter_space(parameter_space)
        
        # Define evaluation function
        def evaluate(params):
            # Set parameters on components
            for component, prefix in self.components:
                # Extract component-specific parameters
                if prefix:
                    component_params = {}
                    prefix_len = len(prefix) + 1  # +1 for the dot
                    for k, v in params.items():
                        if k.startswith(f"{prefix}."):
                            component_params[k[prefix_len:]] = v
                else:
                    # No prefix, use all parameters directly
                    component_params = params
                    
                # Set parameters on component
                component.set_parameters(component_params)
                
            # Run backtest
            results = self.backtest_runner()
            
            # Calculate objective
            return self.objective.calculate(results)
            
        # Run optimization
        return self.optimizer.optimize(evaluate, **kwargs)
```

#### 5. Parameter Space

Defines the searchable parameters for optimization:

```python
class ParameterSpace:
    """Define the parameter space for optimization."""
    
    def __init__(self, parameters: Dict[str, Any]):
        """Initialize parameter space."""
        self.parameters = parameters
        self.validate()
    
    def validate(self):
        """Validate parameter space configuration."""
        
    def sample(self, method='grid', n_samples=None):
        """Sample from parameter space using specified method."""
        
    def get_bounds(self):
        """Get parameter bounds as dict."""
        
    @classmethod
    def from_component(cls, component):
        """Create parameter space from a component's get_parameter_space()."""
        
    def combine(self, other_space):
        """Combine with another parameter space for joint optimization."""
        combined_params = {**self.parameters, **other_space.parameters}
        return ParameterSpace(combined_params)
```

#### 2. Objective Functions

Metrics to optimize for:

```python
class Objective(ABC):
    """Base class for optimization objectives."""
    
    def __init__(self, name=None, weight=1.0, direction='maximize'):
        """Initialize objective function."""
        self.name = name or self.__class__.__name__
        self.weight = weight
        self.direction = direction  # 'maximize' or 'minimize'
    
    @abstractmethod
    def calculate(self, results: Dict[str, Any]) -> float:
        """Calculate objective value from backtest results."""
        
    def normalize(self, value: float) -> float:
        """Normalize objective value to [0, 1] range."""
```

Example implementations:

```python
class SharpeObjective(Objective):
    """Sharpe ratio objective function."""
    
    def calculate(self, results: Dict[str, Any]) -> float:
        """Calculate Sharpe ratio from backtest results."""
        metrics = results.get('metrics', {})
        return metrics.get('sharpe_ratio', 0.0)

class WinRateObjective(Objective):
    """Win rate objective function."""
    
    def calculate(self, results: Dict[str, Any]) -> float:
        """Calculate win rate from backtest results."""
        metrics = results.get('metrics', {})
        return metrics.get('win_rate', 0.0)
```

#### 3. Optimizers

Algorithms that search through parameter spaces:

```python
class Optimizer(ABC):
    """Base class for parameter optimization."""
    
    def __init__(self, parameter_space, objectives=None, constraints=None):
        """Initialize optimizer."""
        self.parameter_space = parameter_space
        self.objectives = objectives or []
        self.constraints = constraints or []
        self.results = []
    
    @abstractmethod
    def optimize(self, evaluate_func, n_trials=None, **kwargs):
        """Run optimization process."""
        
    def add_objective(self, objective):
        """Add an objective function."""
        
    def add_constraint(self, constraint):
        """Add a constraint."""
        
    def get_best_parameters(self):
        """Get best parameters based on objectives."""
```

#### 4. Constraints

Rules that limit parameter combinations:

```python
class Constraint(ABC):
    """Base class for optimization constraints."""
    
    @abstractmethod
    def is_satisfied(self, parameters: Dict[str, Any]) -> bool:
        """Check if parameters satisfy constraint."""
        
    def validate_and_adjust(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and adjust parameters to meet constraint."""
```

Example implementations:

```python
class RangeConstraint(Constraint):
    """Constraint that limits parameter to specific range."""
    
    def __init__(self, param_name, min_value=None, max_value=None):
        """Initialize range constraint."""
        self.param_name = param_name
        self.min_value = min_value
        self.max_value = max_value
    
    def is_satisfied(self, parameters: Dict[str, Any]) -> bool:
        """Check if parameter is within range."""
        value = parameters.get(self.param_name)
        if value is None:
            return True
            
        if self.min_value is not None and value < self.min_value:
            return False
            
        if self.max_value is not None and value > self.max_value:
            return False
            
        return True

class RelationalConstraint(Constraint):
    """Constraint between two parameters (e.g., param1 < param2)."""
    
    def __init__(self, param1, param2, relation='<'):
        """Initialize relational constraint."""
        self.param1 = param1
        self.param2 = param2
        self.relation = relation
    
    def is_satisfied(self, parameters: Dict[str, Any]) -> bool:
        """Check if relation between parameters is satisfied."""
        value1 = parameters.get(self.param1)
        value2 = parameters.get(self.param2)
        
        if value1 is None or value2 is None:
            return True
            
        if self.relation == '<':
            return value1 < value2
        elif self.relation == '<=':
            return value1 <= value2
        elif self.relation == '>':
            return value1 > value2
        elif self.relation == '>=':
            return value1 >= value2
        elif self.relation == '==':
            return value1 == value2
        else:
            raise ValueError(f"Unknown relation: {self.relation}")
```

## Optimization Workflows

Workflows are sequences of optimization steps that can be combined to create complex optimization strategies.

### 1. Single-Stage Workflow

```python
class SingleStageWorkflow:
    """Simple workflow with one optimization stage."""
    
    def __init__(self, component, optimizer, objective, backtest_func):
        """Initialize single-stage workflow."""
        self.component = component
        self.optimizer = optimizer
        self.objective = objective
        self.backtest_func = backtest_func
    
    def run(self):
        """Run optimization workflow."""
        # Setup evaluation function
        def evaluate(params):
            self.component.set_parameters(params)
            results = self.backtest_func()
            return self.objective.calculate(results)
            
        # Run optimization
        return self.optimizer.optimize(evaluate)
```

### 2. Sequential Workflow

```python
class SequentialWorkflow:
    """Sequential optimization of multiple components/parameters."""
    
    def __init__(self, stages, backtest_func):
        """Initialize sequential workflow."""
        self.stages = stages  # List of (component, optimizer, objective) tuples
        self.backtest_func = backtest_func
        self.results = []
    
    def run(self):
        """Run sequential optimization workflow."""
        for stage_num, (component, optimizer, objective) in enumerate(self.stages):
            logger.info(f"Running optimization stage {stage_num+1}/{len(self.stages)}")
            
            # Setup evaluation function for this stage
            def evaluate(params):
                component.set_parameters(params)
                results = self.backtest_func()
                return objective.calculate(results)
                
            # Run optimization for this stage
            stage_result = optimizer.optimize(evaluate)
            self.results.append(stage_result)
            
            # Apply best parameters before moving to next stage
            best_params = stage_result.get_best_parameters()
            component.set_parameters(best_params)
            
        return self.results
```

### 3. Regime-Based Workflow

```python
class RegimeBasedWorkflow:
    """Optimize different parameters for different regimes."""
    
    def __init__(self, strategy, regime_detector, regimes, backtest_func):
        """Initialize regime-based workflow."""
        self.strategy = strategy
        self.regime_detector = regime_detector
        self.regimes = regimes  # Dict of regime_name -> (optimizer, objective)
        self.backtest_func = backtest_func
        self.results = {}
    
    def run(self):
        """Run regime-based optimization workflow."""
        for regime_name, (optimizer, objective) in self.regimes.items():
            logger.info(f"Optimizing for regime: {regime_name}")
            
            # Setup regime-specific evaluation
            def evaluate(params):
                # Configure strategy for this regime
                self.strategy.set_regime_parameters(regime_name, params)
                
                # Create regime-specific backtest
                def regime_filter(bar):
                    return self.regime_detector.detect_regime(bar) == regime_name
                    
                # Run backtest with regime filter
                results = self.backtest_func(filter_func=regime_filter)
                return objective.calculate(results)
                
            # Run optimization for this regime
            regime_result = optimizer.optimize(evaluate)
            self.results[regime_name] = regime_result
            
            # Apply best parameters for this regime
            best_params = regime_result.get_best_parameters()
            self.strategy.set_regime_parameters(regime_name, best_params)
            
        return self.results
```

### 4. Walk-Forward Workflow

```python
class WalkForwardWorkflow:
    """Walk-forward optimization to test parameter stability."""
    
    def __init__(self, component, optimizer, objective, backtest_func, 
                 training_periods, validation_periods, steps):
        """Initialize walk-forward workflow."""
        self.component = component
        self.optimizer = optimizer
        self.objective = objective
        self.backtest_func = backtest_func
        self.training_periods = training_periods
        self.validation_periods = validation_periods
        self.steps = steps
        self.results = []
    
    def run(self):
        """Run walk-forward optimization workflow."""
        for step in range(self.steps):
            # Calculate time windows
            train_start = step * self.validation_periods
            train_end = train_start + self.training_periods
            valid_start = train_end
            valid_end = valid_start + self.validation_periods
            
            logger.info(f"Step {step+1}/{self.steps}: "
                        f"Training {train_start}-{train_end}, "
                        f"Validation {valid_start}-{valid_end}")
            
            # Setup training function
            def evaluate(params):
                self.component.set_parameters(params)
                results = self.backtest_func(start=train_start, end=train_end)
                return self.objective.calculate(results)
                
            # Run optimization on training period
            opt_result = self.optimizer.optimize(evaluate)
            best_params = opt_result.get_best_parameters()
            
            # Apply best parameters
            self.component.set_parameters(best_params)
            
            # Validate on out-of-sample period
            valid_results = self.backtest_func(start=valid_start, end=valid_end)
            valid_score = self.objective.calculate(valid_results)
            
            # Save results
            self.results.append({
                'step': step,
                'train_window': (train_start, train_end),
                'valid_window': (valid_start, valid_end),
                'best_params': best_params,
                'train_score': opt_result.get_best_score(),
                'valid_score': valid_score
            })
            
        return self.results
```

## Configuration System

The optimization framework is fully configurable via YAML:

```yaml
optimization:
  # General settings
  output_dir: ./results/optimization
  save_results: true
  parallel: true
  n_jobs: 4
  
  # Components to optimize
  components:
    regime_detector:
      type: regime_detector
      class: src.strategy.components.regime.trend_detector.TrendRegimeDetector
      parameter_space:
        volatility_window: [15, 20, 25]
        volatility_threshold: [0.01, 0.015, 0.02]
        trend_ma_window: [40, 50, 60]
        trend_threshold: [0.03, 0.05, 0.07]
    
    trend_rule:
      type: rule
      class: src.strategy.components.rules.ma_crossover.MACrossoverRule
      parameter_space:
        fast_ma_window: [5, 10, 15]
        slow_ma_window: [20, 30, 40]
    
    mean_reversion_rule:
      type: rule
      class: src.strategy.components.rules.rsi.RSIRule
      parameter_space:
        rsi_window: [10, 14, 18]
        rsi_overbought: [65, 70, 75]
        rsi_oversold: [25, 30, 35]
    
  # Optimization objectives
  objectives:
    sharpe:
      class: src.optimization.objectives.sharpe_objective.SharpeObjective
      weight: 1.0
      direction: maximize
    
    win_rate:
      class: src.optimization.objectives.win_rate_objective.WinRateObjective
      weight: 1.0
      direction: maximize
    
    drawdown:
      class: src.optimization.objectives.drawdown_objective.DrawdownObjective
      weight: 0.5
      direction: minimize
    
  # Optimizers
  optimizers:
    grid:
      class: src.optimization.optimizers.grid_optimizer.GridOptimizer
      
    genetic:
      class: src.optimization.optimizers.genetic_optimizer.GeneticOptimizer
      population_size: 50
      n_generations: 20
      mutation_rate: 0.1
    
  # Constraints
  constraints:
    ma_relation:
      class: src.optimization.constraints.relational_constraint.RelationalConstraint
      param1: fast_ma_window
      param2: slow_ma_window
      relation: <
  
  # Workflow definition
  workflow:
    type: sequential
    stages:
      # Stage 1: Optimize regime detection for win rate
      - component: regime_detector
        optimizer: grid
        objective: win_rate
      
      # Stage 2: Optimize trend rule parameters per regime
      - component: trend_rule
        optimizer: grid
        objective: sharpe
        regime: trend
      
      # Stage 3: Optimize mean reversion rule parameters per regime
      - component: mean_reversion_rule
        optimizer: grid
        objective: sharpe
        regime: mean_reversion
      
      # Stage 4: Optimize ensemble weights for all regimes
      - component: strategy
        optimizer: genetic
        objective: 
          class: src.optimization.objectives.composite_objective.CompositeObjective
          objectives:
            - sharpe
            - drawdown
```

## Extending the Framework

### 1. Custom Objectives

Create custom objective functions by subclassing `Objective`:

```python
class ProfitFactorObjective(Objective):
    """Objective that optimizes for profit factor."""
    
    def calculate(self, results: Dict[str, Any]) -> float:
        """Calculate profit factor from backtest results."""
        metrics = results.get('metrics', {})
        return metrics.get('profit_factor', 1.0)
```

### 2. Custom Optimizers

Create custom optimizers for specialized optimization techniques:

```python
class SimulatedAnnealingOptimizer(Optimizer):
    """Simulated annealing optimizer for parameter tuning."""
    
    def __init__(self, parameter_space, objectives=None, constraints=None,
                 init_temp=100, cooling_rate=0.95, n_iters=100):
        """Initialize simulated annealing optimizer."""
        super().__init__(parameter_space, objectives, constraints)
        self.init_temp = init_temp
        self.cooling_rate = cooling_rate
        self.n_iters = n_iters
    
    def optimize(self, evaluate_func, **kwargs):
        """Run simulated annealing optimization."""
        # Simulated annealing implementation
        ...
```

### 3. Custom Workflows

Create custom optimization workflows for specialized needs:

```python
class AdaptiveWorkflow:
    """Adaptive workflow that changes optimization approach based on results."""
    
    def __init__(self, component, optimizers, objective, backtest_func):
        """Initialize adaptive workflow."""
        self.component = component
        self.optimizers = optimizers  # List of optimizer instances
        self.objective = objective
        self.backtest_func = backtest_func
    
    def run(self):
        """Run adaptive optimization workflow."""
        # Start with simple optimizer
        current_optimizer = self.optimizers[0]
        best_score = -float('inf')
        
        for i, optimizer in enumerate(self.optimizers):
            logger.info(f"Running optimizer {i+1}/{len(self.optimizers)}: {optimizer.__class__.__name__}")
            
            # Setup evaluation function
            def evaluate(params):
                self.component.set_parameters(params)
                results = self.backtest_func()
                return self.objective.calculate(results)
            
            # Run optimization
            result = optimizer.optimize(evaluate)
            current_score = result.get_best_score()
            
            # Check if we improved
            if current_score > best_score * 1.05:  # 5% improvement threshold
                best_score = current_score
                best_params = result.get_best_parameters()
                self.component.set_parameters(best_params)
            else:
                # Not enough improvement, stop
                break
                
        return best_score, best_params
```

## Optimization Results Management

### Parameter Storage and Retrieval

A critical feature of the optimization framework is the ability to save optimized parameters and load them for out-of-sample testing.

#### 1. Strategy-Specific Parameter Storage

Optimization results are stored in a strategy-specific manner to support multiple strategies and versions:

```
optimized_params/
├── ma_crossover/
│   ├── v1.0_2025-04-25.yaml
│   ├── v1.1_2025-04-26.yaml
│   └── v1.0_aggressive_2025-04-25.yaml
├── regime_ensemble/
│   ├── v1.0_2025-04-25.yaml
│   ├── v1.0_trend_only_2025-04-26.yaml
│   └── v2.0_with_volatility_2025-04-27.yaml
└── mean_reversion/
    ├── v1.0_2025-04-25.yaml
    └── v1.1_with_filter_2025-04-26.yaml
```

The filename convention includes:
- Strategy name (as directory)
- Version number
- Optional variant description
- Date of optimization

#### 2. Parameter File Format

Each parameter file follows a standardized YAML format:

```yaml
# regime_ensemble/v1.0_2025-04-25.yaml
strategy:
  name: "regime_ensemble"    # Strategy identifier (must match directory)
  version: "1.0"             # Version number
  variant: ""                # Optional variant description
  optimization_date: "2025-04-25"
  in_sample_period: ["2020-01-01", "2023-01-01"]
  metrics:
    sharpe_ratio: 1.82
    win_rate: 0.56
    max_drawdown: -0.12
  parameters:
    regime_detector:
      volatility_window: 20
      volatility_threshold: 0.015
      trend_ma_window: 50
      trend_threshold: 0.05
    regimes:
      trend:
        trend_rule:
          fast_ma_window: 10
          slow_ma_window: 30
        weights:
          trend_rule: 1.0
          mean_reversion_rule: 0.2
          volatility_rule: 0.5
      mean_reversion:
        mean_reversion_rule:
          rsi_window: 14
          rsi_overbought: 70
          rsi_oversold: 30
        weights:
          trend_rule: 0.2
          mean_reversion_rule: 1.0
          volatility_rule: 0.3
```

#### 3. Enhanced OptimizerManager Methods

The OptimizerManager includes strategy-aware methods for saving and loading parameters:

```python
class OptimizerManager:
    """Manager for orchestrating optimization processes."""
    
    # ...existing implementation...
    
    def save_optimization_results(self, strategy_name, version="1.0", variant="", 
                                 base_dir="optimized_params", metadata=None):
        """
        Save optimization results for a specific strategy.
        
        Args:
            strategy_name: Name of the strategy
            version: Version number (default: "1.0")
            variant: Optional variant description
            base_dir: Base directory for parameter storage
            metadata: Additional metadata to include
        
        Returns:
            Path to saved parameter file
        """
        # Create strategy directory if it doesn't exist
        strategy_dir = os.path.join(base_dir, strategy_name)
        os.makedirs(strategy_dir, exist_ok=True)
        
        # Build filename with version, variant, and date
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        filename_parts = [f"v{version}"]
        if variant:
            filename_parts.append(variant.replace(" ", "_"))
        filename_parts.append(date_str)
        filename = "_".join(filename_parts) + ".yaml"
        filepath = os.path.join(strategy_dir, filename)
        
        # Build results dictionary
        results = {
            'strategy': {
                'name': strategy_name,
                'version': version,
                'variant': variant,
                'optimization_date': date_str,
                'in_sample_period': metadata.get('in_sample_period') if metadata else None,
                'metrics': metadata.get('metrics', {}) if metadata else {},
                'parameters': {}
            }
        }
        
        # Collect optimized parameters for each component
        for component_name, component in self.components.items():
            results['strategy']['parameters'][component_name] = component.get_parameters()
        
        # Save to file
        with open(filepath, 'w') as f:
            yaml.dump(results, f, default_flow_style=False)
        
        logger.info(f"Saved optimization results to {filepath}")
        return filepath
    
    def load_optimization_results(self, strategy_name, version=None, variant=None, 
                                 date=None, filename=None, base_dir="optimized_params"):
        """
        Load optimization results for a specific strategy.
        
        Args:
            strategy_name: Name of the strategy
            version: Optional version filter (e.g., "1.0")
            variant: Optional variant filter
            date: Optional date filter (e.g., "2025-04-25")
            filename: Optional exact filename to load
            base_dir: Base directory for parameter storage
            
        Returns:
            Dictionary of loaded results
        """
        strategy_dir = os.path.join(base_dir, strategy_name)
        
        # If exact filename provided, use it
        if filename:
            filepath = os.path.join(strategy_dir, filename)
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Parameter file not found: {filepath}")
        else:
            # Find matching parameter files
            files = os.listdir(strategy_dir)
            
            # Apply filters
            if version:
                files = [f for f in files if f.startswith(f"v{version}")]
            if variant:
                variant_slug = variant.replace(" ", "_")
                files = [f for f in files if variant_slug in f]
            if date:
                files = [f for f in files if date in f]
            
            if not files:
                raise FileNotFoundError(
                    f"No parameter files found for strategy '{strategy_name}' "
                    f"with filters: version={version}, variant={variant}, date={date}"
                )
            
            # Use most recent file if multiple matches
            files.sort(reverse=True)  # Sort by filename, which includes date
            filepath = os.path.join(strategy_dir, files[0])
        
        # Load parameter file
        with open(filepath, 'r') as f:
            results = yaml.safe_load(f)
        
        # Validate strategy name
        stored_strategy = results.get('strategy', {}).get('name')
        if stored_strategy != strategy_name:
            logger.warning(
                f"Strategy name mismatch: expected '{strategy_name}', found '{stored_strategy}'"
            )
        
        # Apply parameters to components
        strategy_params = results.get('strategy', {}).get('parameters', {})
        for component_name, params in strategy_params.items():
            if component_name in self.components:
                self.components[component_name].set_parameters(params)
                logger.info(f"Applied optimized parameters to {component_name}")
        
        return results
    
    def list_available_parameters(self, strategy_name=None, base_dir="optimized_params"):
        """
        List available parameter files.
        
        Args:
            strategy_name: Optional strategy name filter
            base_dir: Base directory for parameter storage
            
        Returns:
            Dictionary of available parameter files
        """
        results = {}
        
        # If strategy_name provided, only list that strategy
        if strategy_name:
            strategy_dir = os.path.join(base_dir, strategy_name)
            if not os.path.exists(strategy_dir):
                return {}
            
            strategies = [strategy_name]
        else:
            # List all strategies
            if not os.path.exists(base_dir):
                return {}
                
            strategies = [d for d in os.listdir(base_dir) 
                         if os.path.isdir(os.path.join(base_dir, d))]
        
        # Build results dictionary
        for strategy in strategies:
            strategy_dir = os.path.join(base_dir, strategy)
            files = os.listdir(strategy_dir)
            
            # Parse file information
            strategy_files = []
            for filename in files:
                if not filename.endswith('.yaml'):
                    continue
                
                # Extract metadata from filename
                parts = filename.replace('.yaml', '').split('_')
                version = parts[0]
                date = parts[-1]
                
                # Extract variant if present
                variant = '_'.join(parts[1:-1]) if len(parts) > 2 else ""
                
                strategy_files.append({
                    'filename': filename,
                    'version': version,
                    'variant': variant,
                    'date': date,
                    'path': os.path.join(strategy_dir, filename)
                })
            
            results[strategy] = strategy_files
        
        return results
```

### Integration with Backtest Framework

The BacktestCoordinator is extended to support strategy-specific parameters:

```python
class BacktestCoordinator:
    """Coordinator for backtest execution."""
    
    # ...existing implementation...
    
    def load_optimized_parameters(self, strategy_name, version=None, variant=None, 
                                 date=None, filename=None, base_dir="optimized_params"):
        """
        Load optimized parameters for a specific strategy.
        
        Args:
            strategy_name: Name of the strategy
            version: Optional version filter
            variant: Optional variant filter
            date: Optional date filter
            filename: Optional exact filename to load
            base_dir: Base directory for parameter storage
        """
        # Construct file path if filename provided
        if filename:
            filepath = os.path.join(base_dir, strategy_name, filename)
        else:
            # Find matching parameter file
            strategy_dir = os.path.join(base_dir, strategy_name)
            
            # Find all YAML files
            files = [f for f in os.listdir(strategy_dir) if f.endswith('.yaml')]
            
            # Apply filters
            if version:
                files = [f for f in files if f.startswith(f"v{version}")]
            if variant:
                variant_slug = variant.replace(" ", "_")
                files = [f for f in files if variant_slug in f]
            if date:
                files = [f for f in files if date in f]
            
            if not files:
                raise FileNotFoundError(
                    f"No parameter files found for strategy '{strategy_name}' "
                    f"with filters: version={version}, variant={variant}, date={date}"
                )
            
            # Use most recent file if multiple matches
            files.sort(reverse=True)
            filepath = os.path.join(strategy_dir, files[0])
        
        # Load and apply parameters
        with open(filepath, 'r') as f:
            params = yaml.safe_load(f)
        
        # Extract strategy parameters
        strategy_params = params.get('strategy', {}).get('parameters', {})
        
        # Apply parameters to components
        for component_name, component_params in strategy_params.items():
            component = self.get_component(component_name)
            if component:
                component.set_parameters(component_params)
                logger.info(f"Applied optimized parameters to {component_name}")
        
        self.using_optimized_params = True
        self.optimized_params_source = filepath
        
        return params
    
    def run(self, strategy_name, in_sample=False, 
           load_parameters=None, save_parameters=None, **kwargs):
        """
        Run backtest with optional optimized parameters.
        
        Args:
            strategy_name: Name of the strategy to run
            in_sample: Whether this is an in-sample backtest
            load_parameters: Dict of parameters to load (version, variant, date, filename)
            save_parameters: Dict of parameters for saving results (version, variant)
            **kwargs: Additional backtest parameters
            
        Returns:
            Backtest results
        """
        # Load optimized parameters if requested
        if not in_sample and load_parameters:
            self.load_optimized_parameters(
                strategy_name=strategy_name,
                **load_parameters
            )
        
        # Run backtest
        results = self._run_backtest(**kwargs)
        
        # Save optimized parameters if requested (typically for in-sample tests)
        if in_sample and save_parameters:
            # Get optimizer manager
            optimizer_manager = self.container.get("optimizer_manager")
            
            # Save parameters
            param_file = optimizer_manager.save_optimization_results(
                strategy_name=strategy_name,
                version=save_parameters.get('version', '1.0'),
                variant=save_parameters.get('variant', ''),
                metadata={
                    'in_sample_period': [kwargs.get('start_date'), kwargs.get('end_date')],
                    'metrics': results.get('metrics', {})
                }
            )
            
            # Add file path to results
            results['optimized_params_file'] = param_file
        
        # Add information about parameter source to results
        if hasattr(self, 'using_optimized_params'):
            results['optimized_params_used'] = self.optimized_params_source
        
        return results
```

### Walk-Forward Analysis with Strategy Support

The walk-forward optimizer supports strategy-specific parameters:

```python
class WalkForwardOptimizer:
    """Walk-forward optimization with out-of-sample testing."""
    
    def __init__(self, strategy_name, config, backtest_factory):
        """
        Initialize walk-forward optimizer.
        
        Args:
            strategy_name: Name of the strategy
            config: Optimization configuration
            backtest_factory: Factory function to create backtest runners
        """
        self.strategy_name = strategy_name
        self.config = config
        self.backtest_factory = backtest_factory
        self.n_windows = config.get('n_windows', 5)
        self.train_size = config.get('train_size', 252)  # Default to 1 year
        self.test_size = config.get('test_size', 63)    # Default to 3 months
        self.results_dir = config.get('results_dir', 
                                     f'./results/walkforward/{strategy_name}')
        self.version = config.get('version', '1.0')
        self.variant = config.get('variant', '')
        
    def run(self):
        """
        Run walk-forward optimization.
        
        Returns:
            Dictionary of results for each window
        """
        os.makedirs(self.results_dir, exist_ok=True)
        results = []
        
        for window in range(self.n_windows):
            window_variant = f"{self.variant}_window_{window}" if self.variant else f"window_{window}"
            
            logger.info(f"Processing walk-forward window {window+1}/{self.n_windows}")
            
            # Calculate in-sample and out-of-sample periods
            train_start, train_end = self._get_train_period(window)
            test_start, test_end = self._get_test_period(window)
            
            logger.info(f"Training period: {train_start} to {train_end}")
            logger.info(f"Testing period: {test_start} to {test_end}")
            
            # Run in-sample optimization
            train_config = self._create_config(train_start, train_end)
            optimizer = OptimizerManager(
                backtest_runner=self.backtest_factory(train_start, train_end, True)
            )
            train_results = optimizer.run_from_config(train_config)
            
            # Save optimized parameters with window-specific variant
            param_file = optimizer.save_optimization_results(
                strategy_name=self.strategy_name,
                version=self.version,
                variant=window_variant,
                base_dir=self.results_dir,
                metadata={
                    'window': window,
                    'train_period': (train_start, train_end),
                    'test_period': (test_start, test_end),
                    'metrics': train_results.get('metrics', {})
                }
            )
            
            # Run out-of-sample test with optimized parameters
            test_runner = self.backtest_factory(test_start, test_end, False)
            test_results = test_runner.run(
                strategy_name=self.strategy_name,
                in_sample=False, 
                load_parameters={'filename': os.path.basename(param_file), 
                                'base_dir': self.results_dir}
            )
            
            # Store results for this window
            window_results = {
                'window': window,
                'train_period': (train_start, train_end),
                'test_period': (test_start, test_end),
                'train_metrics': train_results.get('metrics', {}),
                'test_metrics': test_results.get('metrics', {}),
                'optimized_params': param_file
            }
            
            results.append(window_results)
            
            # Save summary for this window
            with open(os.path.join(self.results_dir, f"window_{window}_summary.json"), 'w') as f:
                json.dump(window_results, f, indent=2, default=str)
        
        # Save overall results
        with open(os.path.join(self.results_dir, "walkforward_results.json"), 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return results
```

### Configuration Integration with Strategy Support

The configuration system supports strategy-specific optimization:

```yaml
backtest:
  # Standard backtest config
  strategy: "regime_ensemble"  # Strategy identifier
  symbols: ["AAPL", "MSFT", "GOOGL"]
  start_date: "2020-01-01"
  end_date: "2023-12-31"
  
  # Optimization parameters (for in-sample backtest)
  optimization:
    enabled: true
    save_parameters:
      version: "1.0"
      variant: "standard"
    workflow: "sequential"
    stages:
      # ...optimization stages as defined earlier...
    
  # Parameter loading (for out-of-sample backtest)
  load_parameters:
    version: "1.0"
    variant: "standard"
    date: "2025-04-25"
  
  # Walk-forward analysis
  walk_forward:
    enabled: false
    n_windows: 5
    train_size: 252  # 1 year
    test_size: 63    # 3 months
    version: "1.0"
    variant: "walkforward"
```

## Example Use Cases

### 1. Regime-Based MA Strategy Optimization Using OptimizerManager

```python
# Create optimizer manager
optimizer_manager = OptimizerManager(backtest_runner=backtest_func)

# Create configuration for optimization
optimization_config = {
    'type': 'sequential',
    'stages': [
        # Stage 1: Optimize regime detection parameters for win rate
        {
            'component': 'regime_detector',
            'parameters': {
                'volatility_window': [15, 20, 25],
                'volatility_threshold': [0.01, 0.015, 0.02],
                'trend_ma_window': [40, 50, 60],
                'trend_threshold': [0.03, 0.05, 0.07]
            },
            'optimizer': {
                'type': 'grid',
                'exhaustive': True
            },
            'objective': {
                'type': 'win_rate',
                'direction': 'maximize' 
            }
        },
        
        # Stage 2: Optimize rules for trend regime
        {
            'component': 'trend_rule',
            'regime': 'trend',
            'parameters': {
                'fast_window': [5, 10, 15],
                'slow_window': [20, 30, 40]
            },
            'optimizer': {
                'type': 'grid',
                'exhaustive': True
            },
            'objective': {
                'type': 'return',
                'direction': 'maximize'
            }
        },
        
        # Stage 3: Optimize rules for mean-reversion regime
        {
            'component': 'mean_rev_rule',
            'regime': 'mean_reversion',
            'parameters': {
                'rsi_window': [10, 14, 18],
                'rsi_overbought': [65, 70, 75],
                'rsi_oversold': [25, 30, 35]
            },
            'optimizer': {
                'type': 'grid',
                'exhaustive': True
            },
            'objective': {
                'type': 'win_rate',
                'direction': 'maximize'
            }
        },
        
        # Stage 4: Optimize rule weights across all regimes
        {
            'component': 'strategy',
            'parameters': {
                'weights.trend_rule': [0.1, 0.5, 1.0, 1.5, 2.0],
                'weights.mean_rev_rule': [0.1, 0.5, 1.0, 1.5, 2.0],
                'weights.vol_breakout_rule': [0.1, 0.5, 1.0, 1.5, 2.0]
            },
            'optimizer': {
                'type': 'genetic',
                'population_size': 50,
                'n_generations': 20,
                'mutation_rate': 0.1
            },
            'objective': {
                'type': 'sharpe',
                'direction': 'maximize'
            }
        }
    ]
}

# Run optimization workflow
results = optimizer_manager.run_from_config(optimization_config)

# Alternative manual approach:
regime_detector = TrendRegimeDetector()
strategy = RegimeStrategy()
trend_rule = strategy.get_component('trend_rule')
mean_rev_rule = strategy.get_component('mean_rev_rule')

# 1. Create component optimizers
regime_optimizer = ComponentOptimizer(
    regime_detector,
    GridOptimizer(),
    WinRateObjective(),
    backtest_func
)

trend_rule_optimizer = ComponentOptimizer(
    trend_rule,
    GridOptimizer(),
    ReturnObjective(),
    backtest_func
)

mean_rev_optimizer = ComponentOptimizer(
    mean_rev_rule,
    GridOptimizer(),
    WinRateObjective(),
    backtest_func
)

weight_optimizer = StrategyOptimizerMixin()
weight_optimizer.component = strategy
weight_optimizer.optimizer = GeneticOptimizer()
weight_optimizer.objective = SharpeObjective()
weight_optimizer.backtest_runner = backtest_func

# 2. Run sequentially
regime_results = regime_optimizer.optimize()
trend_results = trend_rule_optimizer.optimize()
mean_rev_results = mean_rev_optimizer.optimize()
weight_results = weight_optimizer.optimize_rule_weights()
```

### 2. Joint Optimization of Multiple Components

```python
# Create a JointOptimizer for optimizing multiple components together
trend_rule = strategy.get_component('trend_rule')
mean_rev_rule = strategy.get_component('mean_rev_rule')

# Create components list with prefixes for namespaces
components = [
    (trend_rule, 'trend'),
    (mean_rev_rule, 'mean_rev')
]

# Create joint optimizer
joint_optimizer = JointOptimizer(
    components=components,
    optimizer=GeneticOptimizer(),
    objective=SharpeObjective(),
    backtest_runner=backtest_func
)

# Run joint optimization
joint_results = joint_optimizer.optimize(
    population_size=50,
    n_generations=30
)

# Apply best parameters to components
best_params = joint_results.get_best_parameters()
trend_params = {k.replace('trend.', ''): v for k, v in best_params.items() if k.startswith('trend.')}
mean_rev_params = {k.replace('mean_rev.', ''): v for k, v in best_params.items() if k.startswith('mean_rev.')}

trend_rule.set_parameters(trend_params)
mean_rev_rule.set_parameters(mean_rev_params)

# Alternative configuration-based approach:
optimization_config = {
    'type': 'joint',
    'components': [
        {
            'name': 'trend_rule',
            'prefix': 'trend',
            'parameters': {
                'fast_window': [5, 10, 15],
                'slow_window': [20, 30, 40]
            }
        },
        {
            'name': 'mean_rev_rule',
            'prefix': 'mean_rev',
            'parameters': {
                'rsi_window': [10, 14, 18], 
                'rsi_overbought': [65, 70, 75],
                'rsi_oversold': [25, 30, 35]
            }
        }
    ],
    'optimizer': {
        'type': 'genetic',
        'population_size': 50,
        'n_generations': 30,
        'mutation_rate': 0.1
    },
    'objective': {
        'type': 'composite',
        'components': [
            {
                'type': 'sharpe',
                'weight': 0.6
            },
            {
                'type': 'drawdown',
                'weight': 0.4,
                'direction': 'minimize'
            }
        ]
    }
}

optimizer_manager = OptimizerManager(backtest_runner=backtest_func)
joint_results = optimizer_manager.run_from_config(optimization_config)
```

### 3. Component Interface for Optimization

Here's an implementation of the Optimizable interface/mixin for components:

```python
class OptimizableComponent:
    """Mixin that makes a component optimizable."""
    
    def get_parameter_space(self) -> Dict[str, Any]:
        """
        Get parameter space for optimization.
        
        Returns:
            Dictionary mapping parameter names to possible values.
        """
        # Default implementation returns empty dict
        return {}
    
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """
        Set parameters on the component.
        
        Args:
            params: Dictionary of parameter values.
        """
        # Default implementation sets attributes directly
        for name, value in params.items():
            if hasattr(self, name):
                setattr(self, name, value)
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get current parameter values.
        
        Returns:
            Dictionary of current parameter values.
        """
        # Default implementation gets attributes directly
        params = {}
        for name in self.get_parameter_space().keys():
            if hasattr(self, name):
                params[name] = getattr(self, name)
        return params
    
    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate parameter values.
        
        Args:
            params: Dictionary of parameter values.
            
        Returns:
            Tuple of (valid, message).
        """
        # Default implementation approves all parameters
        return True, ""
```

Using the interface with a component:

```python
class MACrossoverRule(Rule, OptimizableComponent):
    """Moving average crossover rule."""
    
    def __init__(self, fast_window=10, slow_window=30, **kwargs):
        super().__init__(**kwargs)
        self.fast_window = fast_window
        self.slow_window = slow_window
    
    def get_parameter_space(self):
        """Return parameter space for optimization."""
        return {
            'fast_window': [5, 10, 15, 20],
            'slow_window': [20, 30, 40, 50]
        }
    
    def validate_parameters(self, params):
        """Validate parameters have correct relationship."""
        fast = params.get('fast_window', self.fast_window)
        slow = params.get('slow_window', self.slow_window)
        
        if fast >= slow:
            return False, "Fast window must be smaller than slow window"
            
        return True, ""
```

### 4. Using OptimizerManager for a Complex Workflow

Here's a comprehensive example using OptimizerManager:

```python
# Create optimizer manager
optimizer_manager = OptimizerManager(backtest_runner=backtest_func)

# Register optimizers
optimizer_manager.register_optimizer('grid', GridOptimizer())
optimizer_manager.register_optimizer('genetic', GeneticOptimizer())
optimizer_manager.register_optimizer('bayesian', BayesianOptimizer())

# Define optimization config
optimization_config = {
    # Strategy optimization
    'strategy': {
        # Stage 1: Optimize regime detector for regime identification
        'regime_detector': {
            'parameters': {
                'volatility_window': [15, 20, 25],
                'volatility_threshold': [0.01, 0.015, 0.02],
                'trend_ma_window': [40, 50, 60],
                'trend_threshold': [0.03, 0.05, 0.07]
            },
            'optimizer': 'grid',
            'objective': 'accuracy'  # Custom objective for regime detection accuracy
        },
        
        # Stage 2: Joint optimization of regime-specific parameters
        'regime_rules': {
            'trend': {
                'trend_rule': {
                    'parameters': {
                        'fast_window': [5, 10, 15],
                        'slow_window': [20, 30, 40]
                    }
                },
                'volatility_rule': {
                    'parameters': {
                        'breakout_window': [10, 15, 20],
                        'breakout_multiplier': [1.5, 2.0, 2.5]
                    }
                }
            },
            'mean_reversion': {
                'mean_rev_rule': {
                    'parameters': {
                        'rsi_window': [10, 14, 18],
                        'rsi_overbought': [65, 70, 75],
                        'rsi_oversold': [25, 30, 35]
                    }
                }
            },
            'volatile': {
                'volatility_rule': {
                    'parameters': {
                        'breakout_window': [5, 10, 15],
                        'breakout_multiplier': [1.0, 1.5, 2.0]
                    }
                }
            }
        },
        'optimizer': 'bayesian',
        'objective': 'sharpe'
    },
    
    # Risk management optimization
    'risk': {
        'position_sizer': {
            'parameters': {
                'base_size': [0.01, 0.02, 0.03],
                'volatility_factor': [0.5, 1.0, 1.5],
                'max_position_size': [0.05, 0.1, 0.15]
            },
            'optimizer': 'grid',
            'objective': 'sortino'
        },
        
        'risk_manager': {
            'parameters': {
                'stop_loss_pct': [0.01, 0.02, 0.03],
                'take_profit_pct': [0.02, 0.03, 0.04],
                'max_drawdown_pct': [0.1, 0.15, 0.2]
            },
            'optimizer': 'genetic',
            'objective': {
                'type': 'composite',
                'components': [
                    {'type': 'sharpe', 'weight': 0.4},
                    {'type': 'drawdown', 'weight': 0.4, 'direction': 'minimize'},
                    {'type': 'win_rate', 'weight': 0.2}
                ]
            }
        }
    },
    
    # Meta-label optimization (signal filtering)
    'meta_labeling': {
        'parameters': {
            'confidence_threshold': [0.3, 0.4, 0.5, 0.6, 0.7],
            'min_profit_potential': [0.005, 0.01, 0.015, 0.02],
            'feature_set': ['basic', 'extended', 'full']
        },
        'optimizer': 'bayesian',
        'objective': 'f1_score'  # Classification metric for meta-labeling
    }
}

# Create workflow from config
workflow = optimizer_manager.create_workflow('sequential', optimization_config)

# Run optimization
results = optimizer_manager.run_workflow(workflow)

# Save results
optimizer_manager.save_results('optimization_results.pkl')
```
