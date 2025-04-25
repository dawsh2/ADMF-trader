# Enhanced Optimization Module Specification

## Overview

This document outlines the specification for an enhanced optimization module that enables flexible, modular, and configurable optimization of various trading system components. The design supports multiple optimization methods, targets, metrics, and sequences that can be combined and configured to create sophisticated optimization workflows.

## Module Structure

```
strategy/optimization/
├── __init__.py
├── targets/
│   ├── __init__.py
│   ├── target_base.py              # Base optimization target interface
│   ├── rule_parameters.py          # Rule parameter optimization target
│   ├── rule_weights.py             # Rule weight optimization target
│   ├── regime_detector.py          # Regime detector optimization target
│   └── position_sizing.py          # Position sizing optimization target
├── methods/
│   ├── __init__.py
│   ├── method_base.py              # Base optimization method interface
│   ├── grid_search.py              # Grid search optimization
│   ├── genetic.py                  # Genetic algorithm optimization
│   ├── bayesian.py                 # Bayesian optimization
│   └── particle_swarm.py           # Particle swarm optimization
├── metrics/
│   ├── __init__.py
│   ├── metric_base.py              # Base metric interface
│   ├── return_metrics.py           # Return-based metrics (total, annualized)
│   ├── risk_metrics.py             # Risk-based metrics (drawdown, volatility)
│   ├── risk_adjusted_metrics.py    # Risk-adjusted metrics (Sharpe, Sortino)
│   └── custom_metrics.py           # Custom metric definitions
├── sequences/
│   ├── __init__.py
│   ├── sequence_base.py            # Base sequence interface
│   ├── sequential.py               # Sequential optimization
│   ├── parallel.py                 # Parallel optimization
│   ├── hierarchical.py             # Hierarchical optimization
│   ├── regime_specific.py          # Regime-specific optimization
│   └── walk_forward.py             # Walk-forward optimization
├── constraints/
│   ├── __init__.py
│   ├── constraint_base.py          # Base constraint interface
│   ├── parameter_constraints.py    # Parameter value constraints
│   ├── relationship_constraints.py # Parameter relationship constraints
│   └── performance_constraints.py  # Performance-based constraints
├── results/
│   ├── __init__.py
│   ├── optimization_result.py      # Optimization result container
│   ├── result_analysis.py          # Result analysis utilities
│   └── visualization.py            # Result visualization utilities
├── manager.py                      # Optimization manager
└── utils.py                        # Optimization utilities
```

## Core Interfaces

### 1. Optimization Target

The `OptimizationTarget` interface defines how components can be optimized:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional

class OptimizationTarget(ABC):
    """Base interface for any component that can be optimized."""
    
    @abstractmethod
    def get_parameter_space(self) -> Dict[str, List[Any]]:
        """
        Get the parameter space for optimization.
        
        Returns:
            Dict mapping parameter names to lists of possible values
        """
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get current parameter values.
        
        Returns:
            Dict mapping parameter names to current values
        """
        pass
    
    @abstractmethod
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """
        Set parameters to specified values.
        
        Args:
            params: Dict mapping parameter names to values
        """
        pass
    
    @abstractmethod
    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a set of parameters.
        
        Args:
            params: Dict mapping parameter names to values
            
        Returns:
            (is_valid, error_message)
        """
        pass
    
    def reset(self) -> None:
        """Reset target to initial state."""
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this optimization target.
        
        Returns:
            Dict of metadata including target type, description, etc.
        """
        return {
            "type": self.__class__.__name__,
            "description": self.__doc__ or "No description available"
        }
```

### 2. Optimization Method

The `OptimizationMethod` interface defines how optimization algorithms work:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional, Tuple

class OptimizationMethod(ABC):
    """Base interface for optimization methods."""
    
    @abstractmethod
    def optimize(self, 
                parameter_space: Dict[str, List[Any]],
                objective_function: Callable[[Dict[str, Any]], float],
                constraints: Optional[List[Callable[[Dict[str, Any]], bool]]] = None,
                **kwargs) -> Dict[str, Any]:
        """
        Perform optimization.
        
        Args:
            parameter_space: Dict mapping parameter names to possible values
            objective_function: Function that evaluates parameter combinations
            constraints: Optional list of constraint functions
            **kwargs: Additional method-specific parameters
            
        Returns:
            Dict containing optimization results
        """
        pass
    
    @abstractmethod
    def get_best_result(self) -> Optional[Dict[str, Any]]:
        """
        Get the best result found during optimization.
        
        Returns:
            Dict with best parameters and score, or None if not optimized
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this optimization method.
        
        Returns:
            Dict of metadata including method name, description, etc.
        """
        return {
            "name": self.__class__.__name__,
            "description": self.__doc__ or "No description available"
        }
```

### 3. Optimization Metric

The `OptimizationMetric` interface defines how performance is measured:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class OptimizationMetric(ABC):
    """Base interface for optimization metrics."""
    
    @abstractmethod
    def calculate(self, 
                 equity_curve: Any, 
                 trades: List[Dict[str, Any]], 
                 **kwargs) -> float:
        """
        Calculate metric value.
        
        Args:
            equity_curve: Equity curve data
            trades: List of trade records
            **kwargs: Additional parameters
            
        Returns:
            Metric value (higher is better)
        """
        pass
    
    @property
    def higher_is_better(self) -> bool:
        """
        Whether higher values of this metric are better.
        
        Returns:
            True if higher is better, False otherwise
        """
        return True
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this metric.
        
        Returns:
            Dict of metadata including metric name, description, etc.
        """
        return {
            "name": self.__class__.__name__,
            "description": self.__doc__ or "No description available",
            "higher_is_better": self.higher_is_better
        }
```

### 4. Optimization Sequence

The `OptimizationSequence` interface defines how optimization steps are organized:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class OptimizationSequence(ABC):
    """Base interface for optimization sequences."""
    
    @abstractmethod
    def execute(self, 
               manager: 'OptimizationManager',
               targets: List[str],
               methods: Dict[str, str], 
               metrics: Dict[str, str],
               **kwargs) -> Dict[str, Any]:
        """
        Execute the optimization sequence.
        
        Args:
            manager: Optimization manager instance
            targets: List of target names to optimize
            methods: Dict mapping target names to method names
            metrics: Dict mapping target names to metric names
            **kwargs: Additional sequence-specific parameters
            
        Returns:
            Dict containing optimization results
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this sequence.
        
        Returns:
            Dict of metadata including sequence name, description, etc.
        """
        return {
            "name": self.__class__.__name__,
            "description": self.__doc__ or "No description available"
        }
```

## Key Component Implementations

### 1. Optimization Manager

The `OptimizationManager` coordinates all optimization activities:

```python
from typing import Dict, Any, List, Optional, Callable, Type
import logging

logger = logging.getLogger(__name__)

class OptimizationManager:
    """
    Central manager for coordination of optimization activities.
    """
    
    def __init__(self, container=None, config=None):
        """
        Initialize the optimization manager.
        
        Args:
            container: Optional DI container
            config: Optional configuration
        """
        self.container = container
        self.config = config
        
        # Component registries
        self.targets = {}      # name -> OptimizationTarget
        self.methods = {}      # name -> OptimizationMethod
        self.metrics = {}      # name -> OptimizationMetric
        self.sequences = {}    # name -> OptimizationSequence
        self.constraints = {}  # name -> constraint function
        
        # Results storage
        self.results = {}      # key -> optimization result
        
        # Initialize from container/config if provided
        if container and config:
            self._initialize_from_container()
    
    def register_target(self, name: str, target: 'OptimizationTarget') -> 'OptimizationManager':
        """
        Register an optimization target.
        
        Args:
            name: Target name
            target: OptimizationTarget instance
            
        Returns:
            Self for method chaining
        """
        self.targets[name] = target
        logger.debug(f"Registered optimization target: {name}")
        return self
    
    def register_method(self, name: str, method: 'OptimizationMethod') -> 'OptimizationManager':
        """
        Register an optimization method.
        
        Args:
            name: Method name
            method: OptimizationMethod instance
            
        Returns:
            Self for method chaining
        """
        self.methods[name] = method
        logger.debug(f"Registered optimization method: {name}")
        return self
    
    def register_metric(self, name: str, metric: 'OptimizationMetric') -> 'OptimizationManager':
        """
        Register an optimization metric.
        
        Args:
            name: Metric name
            metric: OptimizationMetric instance
            
        Returns:
            Self for method chaining
        """
        self.metrics[name] = metric
        logger.debug(f"Registered optimization metric: {name}")
        return self
    
    def register_sequence(self, name: str, sequence: 'OptimizationSequence') -> 'OptimizationManager':
        """
        Register an optimization sequence.
        
        Args:
            name: Sequence name
            sequence: OptimizationSequence instance
            
        Returns:
            Self for method chaining
        """
        self.sequences[name] = sequence
        logger.debug(f"Registered optimization sequence: {name}")
        return self
    
    def register_constraint(self, name: str, constraint: Callable[[Dict[str, Any]], bool]) -> 'OptimizationManager':
        """
        Register a constraint function.
        
        Args:
            name: Constraint name
            constraint: Constraint function
            
        Returns:
            Self for method chaining
        """
        self.constraints[name] = constraint
        logger.debug(f"Registered optimization constraint: {name}")
        return self
    
    def run_optimization(self, 
                        sequence_name: str,
                        targets: List[str],
                        methods: Dict[str, str] = None,
                        metrics: Dict[str, str] = None,
                        constraints: Dict[str, List[str]] = None,
                        **kwargs) -> Dict[str, Any]:
        """
        Run an optimization sequence.
        
        Args:
            sequence_name: Name of sequence to run
            targets: List of target names to optimize
            methods: Dict mapping target names to method names (default: use first registered method)
            metrics: Dict mapping target names to metric names (default: use first registered metric)
            constraints: Dict mapping target names to lists of constraint names
            **kwargs: Additional sequence-specific parameters
            
        Returns:
            Dict containing optimization results
        """
        # Validate sequence
        if sequence_name not in self.sequences:
            raise ValueError(f"Unknown optimization sequence: {sequence_name}")
            
        # Validate targets
        for target_name in targets:
            if target_name not in self.targets:
                raise ValueError(f"Unknown optimization target: {target_name}")
        
        # Use defaults for methods and metrics if not provided
        if methods is None:
            # Use first registered method for all targets
            first_method = next(iter(self.methods))
            methods = {target: first_method for target in targets}
            
        if metrics is None:
            # Use first registered metric for all targets
            first_metric = next(iter(self.metrics))
            metrics = {target: first_metric for target in targets}
            
        # Ensure all targets have method and metric
        for target in targets:
            if target not in methods:
                # Use first registered method as default
                methods[target] = next(iter(self.methods))
            if target not in metrics:
                # Use first registered metric as default
                metrics[target] = next(iter(self.metrics))
        
        # Validate methods and metrics
        for target, method_name in methods.items():
            if method_name not in self.methods:
                raise ValueError(f"Unknown optimization method: {method_name}")
                
        for target, metric_name in metrics.items():
            if metric_name not in self.metrics:
                raise ValueError(f"Unknown optimization metric: {metric_name}")
        
        # Process constraints
        processed_constraints = {}
        if constraints:
            for target_name, constraint_names in constraints.items():
                target_constraints = []
                for constraint_name in constraint_names:
                    if constraint_name not in self.constraints:
                        raise ValueError(f"Unknown constraint: {constraint_name}")
                    target_constraints.append(self.constraints[constraint_name])
                processed_constraints[target_name] = target_constraints
        
        # Execute sequence
        sequence = self.sequences[sequence_name]
        result = sequence.execute(
            manager=self,
            targets=targets,
            methods=methods,
            metrics=metrics,
            constraints=processed_constraints,
            **kwargs
        )
        
        # Store result
        result_key = f"{sequence_name}_{','.join(targets)}_{kwargs.get('result_key', 'default')}"
        self.results[result_key] = result
        
        return result
    
    def get_result(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a stored optimization result."""
        return self.results.get(key)
    
    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored optimization results."""
        return self.results.copy()
    
    def create_objective_function(self, 
                                 target_name: str, 
                                 metric_name: str, 
                                 data_handler=None,
                                 **kwargs) -> Callable[[Dict[str, Any]], float]:
        """
        Create an objective function for a target and metric.
        
        Args:
            target_name: Target name
            metric_name: Metric name
            data_handler: Data handler for backtesting
            **kwargs: Additional parameters for backtesting
            
        Returns:
            Objective function that takes parameters and returns metric value
        """
        target = self.targets[target_name]
        metric = self.metrics[metric_name]
        
        # Create backtester if not provided
        backtester = kwargs.get('backtester')
        if backtester is None and self.container:
            backtester = self.container.get('backtester')
        
        def objective_function(params: Dict[str, Any]) -> float:
            # Apply parameters to target
            target.set_parameters(params)
            
            # Run backtest
            if 'run_backtest' in kwargs:
                # Use custom backtest function if provided
                equity_curve, trades = kwargs['run_backtest'](
                    target, data_handler, **kwargs.get('backtest_params', {})
                )
            elif backtester:
                # Use provided backtester
                equity_curve, trades = backtester.run(
                    target, data_handler, **kwargs.get('backtest_params', {})
                )
            else:
                # Use default backtest function from utils
                from strategy.optimization.utils import run_backtest
                equity_curve, trades = run_backtest(
                    target, data_handler, **kwargs.get('backtest_params', {})
                )
            
            # Calculate metric
            value = metric.calculate(equity_curve, trades, **kwargs.get('metric_params', {}))
            
            # Invert if lower is better
            if not metric.higher_is_better:
                value = -value
                
            return value
            
        return objective_function
    
    def _initialize_from_container(self) -> None:
        """Initialize components from DI container."""
        # Initialize targets
        target_section = self.config.get_section('optimization.targets')
        for name, config in target_section.as_dict().items():
            target_class = self.container.get(f"target.{config['class']}")
            target = target_class(name, config.get('parameters', {}))
            self.register_target(name, target)
            
        # Initialize methods
        method_section = self.config.get_section('optimization.methods')
        for name, config in method_section.as_dict().items():
            method_class = self.container.get(f"method.{config['class']}")
            method = method_class(**config.get('parameters', {}))
            self.register_method(name, method)
            
        # Initialize metrics
        metric_section = self.config.get_section('optimization.metrics')
        for name, config in metric_section.as_dict().items():
            metric_class = self.container.get(f"metric.{config['class']}")
            metric = metric_class(**config.get('parameters', {}))
            self.register_metric(name, metric)
            
        # Initialize sequences
        sequence_section = self.config.get_section('optimization.sequences')
        for name, config in sequence_section.as_dict().items():
            sequence_class = self.container.get(f"sequence.{config['class']}")
            sequence = sequence_class(**config.get('parameters', {}))
            self.register_sequence(name, sequence)
            
        # Initialize constraints
        constraint_section = self.config.get_section('optimization.constraints')
        for name, config in constraint_section.as_dict().items():
            constraint_factory = self.container.get(f"constraint.{config['class']}")
            constraint = constraint_factory(**config.get('parameters', {}))
            self.register_constraint(name, constraint)
```

### 2. Specific Target Implementations

Here are examples of concrete optimization target implementations:

#### Rule Parameters Target

```python
from typing import Dict, Any, List, Tuple, Optional

class RuleParametersTarget(OptimizationTarget):
    """Optimization target for trading rule parameters."""
    
    def __init__(self, rules=None, parameter_space=None):
        """
        Initialize the rule parameters target.
        
        Args:
            rules: List of rules or rule container
            parameter_space: Optional explicit parameter space
        """
        self.rules = rules or []
        self._parameter_space = parameter_space or self._build_parameter_space()
        
    def get_parameter_space(self) -> Dict[str, List[Any]]:
        """Get the parameter space for optimization."""
        return self._parameter_space
        
    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameter values."""
        params = {}
        for rule in self.rules:
            rule_params = rule.get_parameters()
            for name, value in rule_params.items():
                # Prefix parameters with rule name to avoid conflicts
                params[f"{rule.name}.{name}"] = value
        return params
        
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Set parameters to specified values."""
        # Group parameters by rule
        rule_params = {}
        for full_name, value in params.items():
            if '.' in full_name:
                rule_name, param_name = full_name.split('.', 1)
                if rule_name not in rule_params:
                    rule_params[rule_name] = {}
                rule_params[rule_name][param_name] = value
        
        # Apply parameters to rules
        for rule in self.rules:
            if rule.name in rule_params:
                rule.set_parameters(rule_params[rule.name])
        
    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate a set of parameters."""
        # Group parameters by rule
        rule_params = {}
        for full_name, value in params.items():
            if '.' in full_name:
                rule_name, param_name = full_name.split('.', 1)
                if rule_name not in rule_params:
                    rule_params[rule_name] = {}
                rule_params[rule_name][param_name] = value
        
        # Validate parameters for each rule
        for rule in self.rules:
            if rule.name in rule_params:
                valid, error = rule.validate_parameters(rule_params[rule.name])
                if not valid:
                    return False, f"Invalid parameters for rule {rule.name}: {error}"
        
        return True, None
        
    def _build_parameter_space(self) -> Dict[str, List[Any]]:
        """Build parameter space from rules."""
        space = {}
        for rule in self.rules:
            rule_space = getattr(rule, 'parameter_space', {})
            for name, values in rule_space.items():
                # Prefix parameters with rule name to avoid conflicts
                space[f"{rule.name}.{name}"] = values
        return space
```

#### Rule Weights Target

```python
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

class RuleWeightsTarget(OptimizationTarget):
    """Optimization target for trading rule weights."""
    
    def __init__(self, rules=None, weight_range=(0.0, 1.0), weight_step=0.1):
        """
        Initialize the rule weights target.
        
        Args:
            rules: List of rules or rule container
            weight_range: Range of weights (min, max)
            weight_step: Step size for weight grid
        """
        self.rules = rules or []
        self.weight_range = weight_range
        self.weight_step = weight_step
        self._parameter_space = self._build_parameter_space()
        
    def get_parameter_space(self) -> Dict[str, List[Any]]:
        """Get the parameter space for optimization."""
        return self._parameter_space
        
    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameter values."""
        params = {}
        for rule in self.rules:
            # Get weight of rule
            weight = getattr(rule, 'weight', 1.0)
            params[f"{rule.name}.weight"] = weight
        return params
        
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Set parameters to specified values."""
        # Extract weights
        weights = {}
        for full_name, value in params.items():
            if '.weight' in full_name:
                rule_name = full_name.split('.weight')[0]
                weights[rule_name] = value
        
        # Apply weights to rules
        for rule in self.rules:
            if rule.name in weights:
                setattr(rule, 'weight', weights[rule.name])
        
    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate a set of parameters."""
        # Validate weight values
        for name, value in params.items():
            if '.weight' in name:
                if not self.weight_range[0] <= value <= self.weight_range[1]:
                    return False, f"Weight {name} out of range: {value}"
        
        # Additional validation could include:
        # - Sum of weights = 1.0
        # - Minimum weight thresholds
        # - Relative weight constraints
        
        return True, None
        
    def _build_parameter_space(self) -> Dict[str, List[Any]]:
        """Build parameter space for weights."""
        space = {}
        weight_values = np.arange(
            self.weight_range[0], 
            self.weight_range[1] + self.weight_step/2,  # Include upper bound
            self.weight_step
        ).tolist()
        
        for rule in self.rules:
            space[f"{rule.name}.weight"] = weight_values
            
        return space
```

### 3. Specific Sequence Implementations

Here are examples of concrete optimization sequence implementations:

#### Sequential Optimization

```python
from typing import Dict, Any, List, Optional

class SequentialOptimization(OptimizationSequence):
    """
    Sequentially optimize targets one after another.
    """
    
    def execute(self, 
               manager: 'OptimizationManager',
               targets: List[str],
               methods: Dict[str, str], 
               metrics: Dict[str, str],
               **kwargs) -> Dict[str, Any]:
        """
        Execute sequential optimization.
        
        Args:
            manager: Optimization manager instance
            targets: List of target names to optimize
            methods: Dict mapping target names to method names
            metrics: Dict mapping target names to metric names
            **kwargs: Additional parameters including:
                - data_handler: Data handler for backtesting
                - constraints: Dict mapping target names to lists of constraint functions
                - backtest_params: Parameters for backtesting
                
        Returns:
            Dict containing optimization results
        """
        results = {}
        data_handler = kwargs.get('data_handler')
        constraints = kwargs.get('constraints', {})
        
        # Optimize each target sequentially
        for i, target_name in enumerate(targets):
            target = manager.targets[target_name]
            method = manager.methods[methods[target_name]]
            metric_name = metrics[target_name]
            
            logger.info(f"Optimizing target {i+1}/{len(targets)}: {target_name}")
            logger.info(f"Using method: {methods[target_name]}, metric: {metric_name}")
            
            # Create objective function
            objective = manager.create_objective_function(
                target_name=target_name,
                metric_name=metric_name,
                data_handler=data_handler,
                **kwargs
            )
            
            # Get parameter space
            parameter_space = target.get_parameter_space()
            
            # Get constraints
            target_constraints = constraints.get(target_name, [])
            
            # Run optimization
            result = method.optimize(
                parameter_space=parameter_space,
                objective_function=objective,
                constraints=target_constraints,
                **kwargs.get(f'method_params_{target_name}', {})
            )
            
            # Apply best parameters
            best_params = result.get('best_params', {})
            target.set_parameters(best_params)
            
            # Store result
            results[target_name] = result
            
            logger.info(f"Optimization complete for {target_name}")
            logger.info(f"Best parameters: {best_params}")
            logger.info(f"Best score: {result.get('best_score')}")
            
        return {
            'sequence': 'sequential',
            'target_results': results,
            'combined_result': {
                'targets': targets,
                'methods': methods,
                'metrics': metrics
            }
        }
```

#### Regime-Specific Optimization

```python
from typing import Dict, Any, List, Optional

class RegimeSpecificOptimization(OptimizationSequence):
    """
    Optimize targets separately for each detected market regime.
    """
    
    def execute(self, 
               manager: 'OptimizationManager',
               targets: List[str],
               methods: Dict[str, str], 
               metrics: Dict[str, str],
               **kwargs) -> Dict[str, Any]:
        """
        Execute regime-specific optimization.
        
        Args:
            manager: Optimization manager instance
            targets: List of target names to optimize
            methods: Dict mapping target names to method names
            metrics: Dict mapping target names to metric names
            **kwargs: Additional parameters including:
                - data_handler: Data handler for backtesting
                - regime_detector: Regime detector to use
                - regime_detector_target: Alternative - name of target that is a regime detector
                - constraints: Dict mapping target names to lists of constraint functions
                - backtest_params: Parameters for backtesting
                - min_regime_data: Minimum data points required for regime optimization
                
        Returns:
            Dict containing optimization results
        """
        data_handler = kwargs.get('data_handler')
        constraints = kwargs.get('constraints', {})
        min_regime_data = kwargs.get('min_regime_data', 100)
        
        # Get regime detector
        regime_detector = kwargs.get('regime_detector')
        if regime_detector is None:
            # Try to get from targets
            regime_detector_name = kwargs.get('regime_detector_target')
            if regime_detector_name and regime_detector_name in manager.targets:
                regime_detector = manager.targets[regime_detector_name]
        
        if regime_detector is None:
            raise ValueError("No regime detector provided")
            
        # Identify regimes in data
        logger.info("Identifying market regimes in data")
        regimes = regime_detector.identify_regimes(data_handler)
        
        logger.info(f"Found {len(regimes)} distinct regimes")
        for regime_type, regime_data in regimes.items():
            logger.info(f"  Regime {regime_type}: {len(regime_data)} data points")
            
        # Optimize for each regime
        regime_results = {}
        for regime_type, regime_data in regimes.items():
            # Skip regimes with insufficient data
            if len(regime_data) < min_regime_data:
                logger.info(f"Skipping regime {regime_type}: insufficient data ({len(regime_data)} < {min_regime_data})")
                continue
                
            logger.info(f"Optimizing for regime: {regime_type}")
            
            # Create regime-specific data handler
            regime_data_handler = self._create_regime_data_handler(data_handler, regime_data)
            
            # Optimize targets for this regime
            regime_kwargs = dict(kwargs)
            regime_kwargs['data_handler'] = regime_data_handler
            regime_kwargs['result_key'] = f"regime_{regime_type}"
            
            # Use sequential optimization for each regime
            sequential = manager.sequences.get('sequential')
            if sequential:
                regime_result = sequential.execute(
                    manager=manager,
                    targets=targets,
                    methods=methods,
                    metrics=metrics,
                    **regime_kwargs
                )
                
                # Store results
                regime_results[regime_type] = regime_result
            else:
                logger.warning("Sequential optimization sequence not available, skipping regime optimization")
                
        return {
            'sequence': 'regime_specific',
            'regimes': list(regimes.keys()),
            'regime_results': regime_results,
            'combined_result': {
                'targets': targets,
                'methods': methods,
                'metrics': metrics
            }
        }
        
    def _create_regime_data_handler(self, data_handler, regime_data):
        """Create a data handler containing only data for a specific regime."""
        # This is a placeholder - actual implementation would depend on data handler interface
        from strategy.optimization.utils import create_regime_data_handler
        return create_regime_data_handler(data_handler, regime_data)
```

## Configuration Examples

### Rule Parameter Optimization with Grid Search

```yaml
# In optimization_config.yaml
optimization:
  targets:
    ma_rule_params:
      class: RuleParametersTarget
      parameters:
        rules:
          - ma_crossover_rule
          - ma_filter_rule
  
  methods:
    grid_search:
      class: GridSearchMethod
      parameters:
        verbose: true
  
  metrics:
    sharpe_ratio:
      class: SharpeRatioMetric
      parameters:
        risk_free_rate: 0.0
        annualization_factor: 252
  
  sequences:
    sequential:
      class: SequentialOptimization
      parameters: {}
```

### Rule Weight Optimization with Genetic Algorithm by Regime

```yaml
# In optimization_config.yaml
optimization:
  targets:
    rule_weights:
      class: RuleWeightsTarget
      parameters:
        rules:
          - ma_crossover_rule
          - rsi_rule
          - bollinger_rule
        weight_range: [0.0, 1.0]
        weight_step: 0.1
    
    regime_detector:
      class: RegimeDetectorTarget
      parameters:
        detector: trend_regime_detector
  
  methods:
    genetic:
      class: GeneticMethod
      parameters:
        population_size: 50
        generations: 50
        mutation_rate: 0.1
        crossover_rate: 0.7
    
    grid_search:
      class: GridSearchMethod
      parameters:
        verbose: true
  
  metrics:
    sharpe_ratio:
      class: SharpeRatioMetric
      parameters:
        risk_free_rate: 0.0
        annualization_factor: 252
    
    total_return:
      class: TotalReturnMetric
      parameters: {}
  
  sequences:
    regime_specific:
      class: RegimeSpecificOptimization
      parameters:
        min_regime_data: 100
```

## Usage Examples

### Basic Rule Parameter Optimization

```python
# Initialize optimizer
optimization_manager = container.get("optimization_manager")

# Register components
optimization_manager.register_target(
    "ma_rule_params", 
    RuleParametersTarget(rules=[ma_crossover_rule, ma_filter_rule])
)
optimization_manager.register_method(
    "grid_search", 
    GridSearchMethod(verbose=True)
)
optimization_manager.register_metric(
    "sharpe_ratio", 
    SharpeRatioMetric(risk_free_rate=0.0, annualization_factor=252)
)
optimization_manager.register_sequence(
    "sequential", 
    SequentialOptimization()
)

# Run optimization
result = optimization_manager.run_optimization(
    sequence_name="sequential",
    targets=["ma_rule_params"],
    methods={"ma_rule_params": "grid_search"},
    metrics={"ma_rule_params": "sharpe_ratio"},
    data_handler=data_handler
)

# Print results
print(f"Best parameters: {result['target_results']['ma_rule_params']['best_params']}")
print(f"Best score: {result['target_results']['ma_rule_params']['best_score']}")
```

### Regime-Specific Rule Weight Optimization

```python
# Initialize optimizer
optimization_manager = container.get("optimization_manager")

# Register components (assuming rule parameters already optimized)
optimization_manager.register_target(
    "rule_weights", 
    RuleWeightsTarget(rules=[ma_crossover_rule, rsi_rule, bollinger_rule])
)
optimization_manager.register_target(
    "regime_detector",
    RegimeDetectorTarget(detector=trend_regime_detector)
)
optimization_manager.register_method(
    "genetic", 
    GeneticMethod(population_size=50, generations=50)
)
optimization_manager.register_method(
    "grid_search", 
    GridSearchMethod(verbose=True)
)
optimization_manager.register_metric(
    "sharpe_ratio", 
    SharpeRatioMetric()
)
optimization_manager.register_sequence(
    "regime_specific", 
    RegimeSpecificOptimization()
)

# Run optimization
result = optimization_manager.run_optimization(
    sequence_name="regime_specific",
    targets=["rule_weights"],
    methods={"rule_weights": "genetic", "regime_detector": "grid_search"},
    metrics={"rule_weights": "sharpe_ratio", "regime_detector": "sharpe_ratio"},
    data_handler=data_handler,
    regime_detector_target="regime_detector"
)

# Print results
print("Optimization results by regime:")
for regime_type, regime_result in result['regime_results'].items():
    print(f"\nRegime: {regime_type}")
    rule_weights_result = regime_result['target_results']['rule_weights']
    print(f"Best weights: {rule_weights_result['best_params']}")
    print(f"Best score: {rule_weights_result['best_score']}")
```

### Comprehensive Multi-Stage Optimization

This example shows a complex optimization workflow with multiple stages:

```python
# Stage 1: Optimize Regime Detector Parameters
regime_result = optimization_manager.run_optimization(
    sequence_name="sequential",
    targets=["regime_detector"],
    methods={"regime_detector": "grid_search"},
    metrics={"regime_detector": "classification_accuracy"},
    data_handler=data_handler
)

# Stage 2: Optimize Rule Parameters by Regime
rule_params_result = optimization_manager.run_optimization(
    sequence_name="regime_specific",
    targets=["ma_rule_params", "rsi_rule_params"],
    methods={
        "ma_rule_params": "grid_search", 
        "rsi_rule_params": "grid_search"
    },
    metrics={
        "ma_rule_params": "sharpe_ratio", 
        "rsi_rule_params": "sharpe_ratio"
    },
    data_handler=data_handler,
    regime_detector_target="regime_detector"
)

# Stage 3: Optimize Rule Weights by Regime
rule_weights_result = optimization_manager.run_optimization(
    sequence_name="regime_specific",
    targets=["rule_weights"],
    methods={"rule_weights": "genetic"},
    metrics={"rule_weights": "sharpe_ratio"},
    data_handler=data_handler,
    regime_detector_target="regime_detector"
)

# Collect and analyze all results
comprehensive_result = {
    'regime_detector': regime_result,
    'rule_parameters': rule_params_result,
    'rule_weights': rule_weights_result
}

# Print final optimized strategy configuration
print("\nFinal Optimized Strategy Configuration:")
print("\nRegime Detector:")
print(f"  Parameters: {regime_result['target_results']['regime_detector']['best_params']}")

print("\nRule Parameters by Regime:")
for regime_type, regime_result in rule_params_result['regime_results'].items():
    print(f"\n  Regime: {regime_type}")
    for target_name, target_result in regime_result['target_results'].items():
        print(f"    {target_name}: {target_result['best_params']}")

print("\nRule Weights by Regime:")
for regime_type, regime_result in rule_weights_result['regime_results'].items():
    print(f"\n  Regime: {regime_type}")
    print(f"    Weights: {regime_result['target_results']['rule_weights']['best_params']}")
```

## Integration with Event System

The optimization module integrates with the event system to allow event-driven optimization workflows:

```python
# Define optimization event types
class OptimizationEvent(Event):
    """Base class for optimization events."""
    
    def __init__(self, event_type, data=None, timestamp=None):
        super().__init__(EventType.OPTIMIZATION, data, timestamp)

class OptimizationRequestEvent(OptimizationEvent):
    """Event requesting optimization."""
    
    def __init__(self, target_name, method_name, metric_name, data_handler=None, timestamp=None):
        data = {
            'target_name': target_name,
            'method_name': method_name,
            'metric_name': metric_name,
            'data_handler': data_handler
        }
        super().__init__(EventType.OPTIMIZATION_REQUEST, data, timestamp)

class OptimizationResultEvent(OptimizationEvent):
    """Event containing optimization results."""
    
    def __init__(self, target_name, result, timestamp=None):
        data = {
            'target_name': target_name,
            'result': result
        }
        super().__init__(EventType.OPTIMIZATION_RESULT, data, timestamp)
```

```python
# Create optimization event handler
class OptimizationEventHandler:
    """Handler for optimization events."""
    
    def __init__(self, optimization_manager):
        self.optimization_manager = optimization_manager
    
    def on_optimization_request(self, event):
        """Handle optimization request event."""
        target_name = event.data['target_name']
        method_name = event.data['method_name']
        metric_name = event.data['metric_name']
        data_handler = event.data['data_handler']
        
        # Run optimization
        result = self.optimization_manager.run_optimization(
            sequence_name="sequential",
            targets=[target_name],
            methods={target_name: method_name},
            metrics={target_name: metric_name},
            data_handler=data_handler
        )
        
        # Emit result event
        result_event = OptimizationResultEvent(target_name, result)
        self.event_bus.emit(result_event)
```

## Testing Strategy

### Unit Tests

For each component, implement thorough unit tests:

```python
class TestOptimizationTarget(unittest.TestCase):
    def setUp(self):
        # Create test rules
        self.rule1 = MockRule("rule1", {"param1": 10, "param2": 20})
        self.rule2 = MockRule("rule2", {"param3": 30, "param4": 40})
        self.rules = [self.rule1, self.rule2]
        
        # Create target
        self.target = RuleParametersTarget(self.rules)
    
    def test_get_parameters(self):
        params = self.target.get_parameters()
        self.assertEqual(params["rule1.param1"], 10)
        self.assertEqual(params["rule1.param2"], 20)
        self.assertEqual(params["rule2.param3"], 30)
        self.assertEqual(params["rule2.param4"], 40)
    
    def test_set_parameters(self):
        new_params = {
            "rule1.param1": 15,
            "rule2.param3": 35
        }
        self.target.set_parameters(new_params)
        
        # Check that parameters were updated
        self.assertEqual(self.rule1.params["param1"], 15)
        self.assertEqual(self.rule1.params["param2"], 20)  # Unchanged
        self.assertEqual(self.rule2.params["param3"], 35)
        self.assertEqual(self.rule2.params["param4"], 40)  # Unchanged
    
    def test_validate_parameters(self):
        # Valid parameters
        valid_params = {
            "rule1.param1": 15,
            "rule2.param3": 35
        }
        is_valid, _ = self.target.validate_parameters(valid_params)
        self.assertTrue(is_valid)
        
        # Invalid parameters
        invalid_params = {
            "rule1.param1": -1,  # Invalid value
            "rule2.param3": 35
        }
        is_valid, error = self.target.validate_parameters(invalid_params)
        self.assertFalse(is_valid)
        self.assertIn("rule1", error)
```

### Integration Tests

Test component integration and optimization workflows:

```python
class TestOptimizationWorkflow(unittest.TestCase):
    def setUp(self):
        # Create components
        self.container = Container()
        self.config = Config()
        self.optimization_manager = OptimizationManager(self.container, self.config)
        
        # Register components
        self.rules = [MockRule("rule1"), MockRule("rule2")]
        self.target = RuleParametersTarget(self.rules)
        self.method = GridSearchMethod()
        self.metric = SharpeRatioMetric()
        self.sequence = SequentialOptimization()
        
        self.optimization_manager.register_target("rule_params", self.target)
        self.optimization_manager.register_method("grid", self.method)
        self.optimization_manager.register_metric("sharpe", self.metric)
        self.optimization_manager.register_sequence("sequential", self.sequence)
        
        # Create mock data handler
        self.data_handler = MockDataHandler()
    
    def test_basic_optimization(self):
        # Run optimization
        result = self.optimization_manager.run_optimization(
            sequence_name="sequential",
            targets=["rule_params"],
            methods={"rule_params": "grid"},
            metrics={"rule_params": "sharpe"},
            data_handler=self.data_handler
        )
        
        # Check result structure
        self.assertIn("target_results", result)
        self.assertIn("rule_params", result["target_results"])
        self.assertIn("best_params", result["target_results"]["rule_params"])
        self.assertIn("best_score", result["target_results"]["rule_params"])
    
    def test_regime_specific_optimization(self):
        # Create and register regime detector
        regime_detector = MockRegimeDetector()
        self.optimization_manager.register_target("regime_detector", RegimeDetectorTarget(regime_detector))
        self.optimization_manager.register_sequence("regime_specific", RegimeSpecificOptimization())
        
        # Run optimization
        result = self.optimization_manager.run_optimization(
            sequence_name="regime_specific",
            targets=["rule_params"],
            methods={"rule_params": "grid"},
            metrics={"rule_params": "sharpe"},
            data_handler=self.data_handler,
            regime_detector_target="regime_detector"
        )
        
        # Check result structure
        self.assertIn("regime_results", result)
        self.assertTrue(len(result["regime_results"]) >= 1)
        
        # Check each regime has results
        for regime_type, regime_result in result["regime_results"].items():
            self.assertIn("target_results", regime_result)
            self.assertIn("rule_params", regime_result["target_results"])
            self.assertIn("best_params", regime_result["target_results"]["rule_params"])
```

### System Tests

Test end-to-end optimization scenarios:

```python
class TestEndToEndOptimization(unittest.TestCase):
    def setUp(self):
        # Create full system
        self.bootstrap = Bootstrap(config_files=["test_config.yaml"])
        self.container, self.config = self.bootstrap.setup()
        
        # Get components
        self.optimization_manager = self.container.get("optimization_manager")
        self.data_handler = self.container.get("data_handler")
        self.backtester = self.container.get("backtester")
    
    def test_multi_stage_optimization(self):
        # Stage 1: Optimize regime detector
        regime_result = self.optimization_manager.run_optimization(
            sequence_name="sequential",
            targets=["regime_detector"],
            data_handler=self.data_handler
        )
        
        # Check regime detector results
        self.assertIn("target_results", regime_result)
        self.assertIn("regime_detector", regime_result["target_results"])
        
        # Stage 2: Optimize rule parameters by regime
        rule_params_result = self.optimization_manager.run_optimization(
            sequence_name="regime_specific",
            targets=["rule_params"],
            data_handler=self.data_handler,
            regime_detector_target="regime_detector"
        )
        
        # Check rule parameter results
        self.assertIn("regime_results", rule_params_result)
        
        # Stage 3: Optimize rule weights by regime
        rule_weights_result = self.optimization_manager.run_optimization(
            sequence_name="regime_specific",
            targets=["rule_weights"],
            data_handler=self.data_handler,
            regime_detector_target="regime_detector"
        )
        
        # Check rule weight results
        self.assertIn("regime_results", rule_weights_result)
        
        # Run backtest with optimized parameters
        strategy = self.container.get("strategy")
        results = self.backtester.run(strategy, self.data_handler)
        
        # Verify performance improvements
        self.assertGreater(results["metrics"]["sharpe_ratio"], 1.0)
```

## Implementation Plan

### Phase 1: Core Interfaces (1 week)

1. Implement OptimizationTarget base interface
2. Implement OptimizationMethod base interface
3. Implement OptimizationMetric base interface
4. Implement OptimizationSequence base interface
5. Create OptimizationManager class

### Phase 2: Basic Components (1 week)

1. Implement RuleParametersTarget
2. Implement RuleWeightsTarget
3. Implement GridSearchMethod
4. Implement GeneticMethod
5. Implement basic metrics (Sharpe, total return)
6. Implement SequentialOptimization sequence

### Phase 3: Regime Components (1 week)

1. Implement RegimeDetectorTarget
2. Implement RegimeSpecificOptimization sequence
3. Create regime data handling utilities
4. Implement regime-specific visualization tools

### Phase 4: Advanced Components (1 week)

1. Implement additional optimization methods
2. Implement advanced optimization sequences
3. Implement multi-objective optimization
4. Create comprehensive testing framework

### Phase 5: Integration (1 week)

1. Integrate with event system
2. Integrate with configuration system
3. Integrate with DI container
4. Create comprehensive examples

## Conclusion

This enhanced optimization module specification provides a comprehensive framework for flexible, modular optimization of trading system components. It enables sophisticated optimization workflows including:

1. Sequential optimization of different components
2. Regime-specific parameter and weight optimization
3. Different optimization methods for different components
4. Independent metrics for each optimization phase
5. Integration with the event system for dynamic optimization

The modular design ensures that new optimization targets, methods, metrics, and sequences can be easily added without modifying the core framework. This flexibility allows traders to create and test advanced optimization strategies while maintaining a clean, maintainable codebase.
