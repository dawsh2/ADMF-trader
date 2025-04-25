# Strategy Migration Guide: Regime Detection & Optimization

## Overview

This guide outlines the process for migrating existing strategies to the new framework, with special focus on regime detection and optimization capabilities. These areas were identified as pain points in the original implementation.

## Table of Contents

1. [Migration Process Overview](#migration-process-overview)
2. [Regime Detection Migration](#regime-detection-migration)
3. [Optimization Migration](#optimization-migration)
4. [Strategy Validation](#strategy-validation)
5. [Migration Checklist](#migration-checklist)
6. [Troubleshooting Guide](#troubleshooting-guide)

## Migration Process Overview

### Key Changes in New Framework

1. **Module Organization**:
   - Risk management moved to its own module
   - Models renamed to strategy
   - Consistent configuration interface

2. **Event System**:
   - Enhanced event types
   - Improved event handling
   - Event-based component coordination

3. **Dependency Injection**:
   - Container-based component creation
   - Configuration-based setup
   - Component lifecycle management

### Migration Steps for Any Strategy

1. **Analysis**: Review the existing strategy implementation
2. **Conversion**: Migrate code to new class structure
3. **Configuration**: Create new configuration
4. **Testing**: Validate strategy behavior
5. **Optimization**: Tune and optimize

## Regime Detection Migration

### Original vs. New Implementation

#### Original Implementation

```python
# In src/models/filters/regime/regime_strategy.py
class RegimeAwareStrategy:
    def __init__(self, base_strategy, regime_detector):
        self.strategy = base_strategy
        self.regime_detector = regime_detector
        self.event_bus = None
        self.regime_parameters = { ... }
        self.active_regime = { ... }
        
    def on_bar(self, event):
        # Detect regime
        current_regime = self.regime_detector.update(event)
        
        # Switch parameters
        self._switch_parameters(symbol, current_regime, timestamp)
        
        # Process with current parameters
        return self.strategy.on_bar(event)
```

#### New Implementation

```python
# In src/strategy/regime/regime_wrapper.py
class RegimeAwareStrategy(StrategyBase):
    def __init__(self, name, config=None, container=None):
        super().__init__(name, config, container)
        
        # Get base strategy and detector from container
        self.strategy = self.container.get("strategy." + self.params.get("base_strategy"))
        self.regime_detector = self.container.get("regime." + self.params.get("detector"))
        
        # Load regime-specific parameters
        self.regime_parameters = {}
        self._load_regime_parameters()
        
        # Initialize regime state
        self.active_regime = {symbol: None for symbol in self.symbols}
        
    def on_bar(self, event):
        # Detect regime
        symbol = event.get_symbol()
        current_regime = self.regime_detector.update(event)
        
        # Handle regime change if needed
        if current_regime != self.active_regime.get(symbol):
            self._handle_regime_change(symbol, current_regime, event.get_timestamp())
            
        # Process with current regime parameters
        return self.strategy.on_bar(event)
```

### Migration Steps for Regime Detection

1. **Create New Regime Detector**:
   ```python
   # In src/strategy/regime/detector.py
   class RegimeDetector(RegimeDetectorBase):
       def __init__(self, name, config=None, container=None):
           super().__init__(name, config, container)
           # Initialize detector parameters
           
       def update(self, event):
           # Detect regime using new framework
           # Return regime type
   ```

2. **Create Configuration**:
   ```yaml
   # In regime_config.yaml
   regime:
     detectors:
       trend_detector:
         class: "TrendRegimeDetector"
         parameters:
           ma_window: 50
           threshold: 0.05
           
     parameters:
       uptrend:
         fast_window: 10
         slow_window: 30
       downtrend:
         fast_window: 5
         slow_window: 15
       sideways:
         fast_window: 8
         slow_window: 25
   ```

3. **Register Components**:
   ```python
   # In bootstrap.py
   container.register("regime.trend_detector", TrendRegimeDetector)
   container.register("strategy.regime_ma", RegimeAwareStrategy)
   
   # Configure
   config_factory.configure_component("regime.trend_detector", "regime.detectors.trend_detector")
   config_factory.configure_component("strategy.regime_ma", "strategy.regime_ma")
   ```

### Testing Regime Detection

1. **Component Testing**:
   ```python
   # Test detector
   detector = container.get("regime.trend_detector")
   regime = detector.update(bar_event)
   
   # Test strategy
   strategy = container.get("strategy.regime_ma")
   signal = strategy.on_bar(bar_event)
   ```

2. **Backtest Comparison**:
   ```python
   # Create backtest runner
   runner = BacktestRunner(config)
   
   # Run base strategy
   base_results = runner.run(container.get("strategy.ma_strategy"), data_handler)
   
   # Run regime-aware strategy
   regime_results = runner.run(container.get("strategy.regime_ma"), data_handler)
   
   # Compare results
   comparison = runner.compare_results(base_results, regime_results)
   ```

## Optimization Migration

### Original vs. New Implementation

#### Original Implementation

```python
# In src/models/optimization/walk_forward.py
class WalkForwardOptimizer:
    def optimize(self, param_space, fitness_function, **kwargs):
        # Create windows
        for window in windows:
            # Optimize parameters on train window
            train_result = base_optimizer.optimize(...)
            
            # Test on test window
            test_score = self._evaluate_parameters(...)
            
            # Store window results
            window_results.append(...)
            
        # Analyze results
        return optimization_result
```

#### New Implementation

```python
# In src/strategy/optimization/walk_forward.py
class WalkForwardOptimizer(OptimizerBase):
    def __init__(self, name, config=None, container=None):
        super().__init__(name, config, container)
        # Initialize with parameters from config
        
    def optimize(self, strategy, param_space, objective, **kwargs):
        # Create windows using configuration
        windows = self._create_windows(**kwargs)
        
        # Get base optimizer from container if specified
        base_optimizer = None
        if self.params.get("base_optimizer"):
            base_optimizer = self.container.get("optimizer." + self.params.get("base_optimizer"))
        
        for window in windows:
            # Optimize parameters on train window
            train_result = self._optimize_window(strategy, param_space, objective, window, base_optimizer)
            
            # Test on test window
            test_result = self._evaluate_window(strategy, train_result.best_params, objective, window)
            
            # Store window results
            self._store_window_result(window, train_result, test_result)
            
        # Analyze and return results
        return self._analyze_results()
```

### Migration Steps for Optimization

1. **Create New Optimizer**:
   ```python
   # In src/strategy/optimization/optimizer.py
   class StrategyOptimizer(OptimizerBase):
       def __init__(self, name, config=None, container=None):
           super().__init__(name, config, container)
           # Initialize optimizer parameters
           
       def optimize(self, strategy, param_space, objective, **kwargs):
           # Run optimization process
           # Return optimization result
   ```

2. **Create Configuration**:
   ```yaml
   # In optimization_config.yaml
   optimization:
     optimizers:
       walk_forward:
         class: "WalkForwardOptimizer"
         parameters:
           windows: 3
           train_ratio: 0.7
           test_ratio: 0.3
           base_optimizer: "grid_search"
           
       grid_search:
         class: "GridSearchOptimizer"
         parameters:
           verbose: true
           
     objectives:
       sharpe_ratio:
         class: "SharpeRatioObjective"
         parameters:
           risk_free_rate: 0.0
           annualization_factor: 252
   ```

3. **Register Components**:
   ```python
   # In bootstrap.py
   container.register("optimizer.grid_search", GridSearchOptimizer)
   container.register("optimizer.walk_forward", WalkForwardOptimizer)
   container.register("objective.sharpe_ratio", SharpeRatioObjective)
   
   # Configure
   config_factory.configure_component("optimizer.grid_search", "optimization.optimizers.grid_search")
   config_factory.configure_component("optimizer.walk_forward", "optimization.optimizers.walk_forward")
   config_factory.configure_component("objective.sharpe_ratio", "optimization.objectives.sharpe_ratio")
   ```

### Testing Optimization

1. **Component Testing**:
   ```python
   # Get optimizer
   optimizer = container.get("optimizer.walk_forward")
   
   # Get strategy
   strategy = container.get("strategy.ma_strategy")
   
   # Get objective
   objective = container.get("objective.sharpe_ratio")
   
   # Define parameter space
   param_space = {
       "fast_window": [5, 10, 15, 20],
       "slow_window": [20, 30, 40, 50]
   }
   
   # Run optimization
   result = optimizer.optimize(strategy, param_space, objective, data_handler=data_handler)
   
   # Print results
   print(f"Best parameters: {result.best_params}")
   print(f"Best score: {result.best_score}")
   ```

2. **Verification**:
   ```python
   # Run backtest with optimized parameters
   strategy.set_parameters(result.best_params)
   backtest_result = runner.run(strategy, data_handler)
   
   # Calculate metrics
   metrics = analytics.calculate_metrics(backtest_result.equity_curve, backtest_result.trades)
   
   # Verify objective matches optimization
   sharpe_ratio = metrics["sharpe_ratio"]
   print(f"Backtest Sharpe ratio: {sharpe_ratio}, Optimization result: {result.best_score}")
   ```

## Strategy Validation

### Validation Process

1. **Functionality Validation**:
   - Verify signals are generated as expected
   - Compare with original implementation signals
   - Ensure parameter changes are applied correctly

2. **Performance Validation**:
   - Run backtest with original and new implementations
   - Compare equity curves
   - Compare trade statistics

3. **Regime Detection Validation**:
   - Verify regime detection works as expected
   - Compare regime changes with original implementation
   - Ensure parameter switching occurs correctly

4. **Optimization Validation**:
   - Verify optimization produces expected results
   - Compare with original optimization results
   - Ensure optimal parameters work as expected

### Validation Tools

1. **Signal Validator**:
   ```python
   # In src/validation/signal_validator.py
   class SignalValidator:
       def compare_signals(self, original_signals, new_signals):
           # Compare signal timing and values
           # Return comparison metrics
   ```

2. **Performance Comparator**:
   ```python
   # In src/validation/performance_comparator.py
   class PerformanceComparator:
       def compare_equity_curves(self, original_equity, new_equity):
           # Compare equity curves
           # Return comparison metrics
           
       def compare_trades(self, original_trades, new_trades):
           # Compare trade statistics
           # Return comparison metrics
   ```

3. **Regime Validator**:
   ```python
   # In src/validation/regime_validator.py
   class RegimeValidator:
       def compare_regimes(self, original_regimes, new_regimes):
           # Compare regime transitions
           # Return comparison metrics
   ```

## Migration Checklist

### Prerequisites

- [ ] Understand the new framework architecture
- [ ] Review existing strategy implementation
- [ ] Identify dependencies and requirements

### Regime Detection Migration

- [ ] Implement new regime detector class
- [ ] Create regime parameter configurations
- [ ] Implement regime-aware strategy wrapper
- [ ] Test regime detection in isolation
- [ ] Verify regime parameter switching

### Optimization Migration

- [ ] Implement new optimization objective
- [ ] Configure optimization parameters
- [ ] Test optimization in isolation
- [ ] Verify optimization results
- [ ] Validate optimized parameters

### Integration

- [ ] Register all components with DI container
- [ ] Create complete configuration
- [ ] Run integration tests
- [ ] Verify event handling
- [ ] Compare with original implementation

### Validation

- [ ] Run backtest with new implementation
- [ ] Compare performance metrics
- [ ] Verify regime detection behavior
- [ ] Validate optimization results
- [ ] Document differences and improvements

## Troubleshooting Guide

### Common Issues

1. **Regime Detection Issues**:
   - **Symptom**: Incorrect regime detection
   - **Possible Causes**:
     - Inconsistent parameter usage
     - Different calculation methodology
     - Event processing order
   - **Solutions**:
     - Compare detector parameters with original
     - Add logging to track regime changes
     - Verify market data processing

2. **Optimization Issues**:
   - **Symptom**: Different optimization results
   - **Possible Causes**:
     - Different objective calculation
     - Window boundary differences
     - Parameter space definitions
   - **Solutions**:
     - Compare objective calculations
     - Verify window creation logic
     - Check parameter space definitions

3. **Integration Issues**:
   - **Symptom**: Components not working together
   - **Possible Causes**:
     - Missing dependencies
     - Incorrect event routing
     - Configuration errors
   - **Solutions**:
     - Verify component registration
     - Check event subscriptions
     - Validate configuration

### Debugging Tips

1. **Event Logging**:
   ```python
   # Add event logger
   event_logger = EventLogger(level=logging.DEBUG)
   event_bus.register(EventType.ALL, event_logger.log_event)
   ```

2. **Parameter Tracking**:
   ```python
   # Add parameter tracker
   def on_parameter_change(strategy, params):
       logger.debug(f"Parameters changed for {strategy.name}: {params}")
       
   strategy.add_parameter_listener(on_parameter_change)
   ```

3. **Regime Tracking**:
   ```python
   # Add regime tracker
   def on_regime_change(detector, symbol, old_regime, new_regime):
       logger.debug(f"Regime changed for {symbol}: {old_regime} -> {new_regime}")
       
   detector.add_regime_listener(on_regime_change)
   ```

## Example: Migrating Mean Reversion Strategy with Regime Detection

### Original Implementation

```python
# Original strategy in old framework
class MeanReversionStrategy:
    def __init__(self, lookback=20, z_threshold=1.5, price_key='close'):
        self.lookback = lookback
        self.z_threshold = z_threshold
        self.price_key = price_key
        self.prices = {}
        self.z_scores = {}
        
    def on_bar(self, event):
        # Strategy logic...
        return signal

# Original regime wrapper
class SimpleRegimeFilteredStrategy:
    def __init__(self, base_strategy, ma_window=50):
        self.strategy = base_strategy
        self.ma_window = ma_window
        self.symbols = self.strategy.symbols
        self.prices = {symbol: [] for symbol in self.symbols}
        self.filtered_signals = 0
        self.passed_signals = 0
        
    def on_bar(self, event):
        # Get signal from base strategy
        signal = self.strategy.on_bar(event)
        
        # Apply regime filtering
        if signal:
            symbol = event.get_symbol()
            price = event.get_close()
            
            # Update price history
            if symbol not in self.prices:
                self.prices[symbol] = []
            self.prices[symbol].append(price)
            
            # Apply simple MA regime filter
            if len(self.prices[symbol]) >= self.ma_window:
                ma = sum(self.prices[symbol][-self.ma_window:]) / self.ma_window
                
                # Only allow long signals in uptrend
                if signal.get_signal_value() > 0 and price > ma:
                    self.passed_signals += 1
                    return signal
                # Only allow short signals in downtrend
                elif signal.get_signal_value() < 0 and price < ma:
                    self.passed_signals += 1
                    return signal
                else:
                    self.filtered_signals += 1
                    return None
            else:
                # Not enough data, pass signal through
                self.passed_signals += 1
                return signal
        
        return None
```

### New Implementation

```python
# New strategy in new framework
class MeanReversionStrategy(StrategyBase):
    def __init__(self, name, config=None, container=None):
        super().__init__(name, config, container)
        
        # Get parameters from configuration
        self.lookback = self.params.get("lookback", 20)
        self.z_threshold = self.params.get("z_threshold", 1.5)
        self.price_key = self.params.get("price_key", "close")
        
        # Initialize state
        self.prices = {symbol: [] for symbol in self.symbols}
        self.z_scores = {symbol: [] for symbol in self.symbols}
        
    def on_bar(self, event):
        # Strategy logic (same as original)...
        return signal
        
    def get_parameters(self):
        return {
            "lookback": self.lookback,
            "z_threshold": self.z_threshold,
            "price_key": self.price_key
        }
        
    def set_parameters(self, params):
        if "lookback" in params:
            self.lookback = params["lookback"]
        if "z_threshold" in params:
            self.z_threshold = params["z_threshold"]
        if "price_key" in params:
            self.price_key = params["price_key"]

# New regime detector
class MovingAverageRegimeDetector(RegimeDetectorBase):
    def __init__(self, name, config=None, container=None):
        super().__init__(name, config, container)
        
        # Get parameters from configuration
        self.ma_window = self.params.get("ma_window", 50)
        
        # Initialize state
        self.prices = {}
        
    def update(self, event):
        symbol = event.get_symbol()
        price = event.get_close()
        
        # Initialize history if needed
        if symbol not in self.prices:
            self.prices[symbol] = []
            
        # Add price to history
        self.prices[symbol].append(price)
        
        # Keep history limited to what we need
        if len(self.prices[symbol]) > self.ma_window * 2:
            self.prices[symbol] = self.prices[symbol][-self.ma_window * 2:]
            
        # Not enough data for regime detection
        if len(self.prices[symbol]) < self.ma_window:
            return RegimeType.UNKNOWN
            
        # Calculate moving average
        ma = sum(self.prices[symbol][-self.ma_window:]) / self.ma_window
        
        # Determine regime
        if price > ma:
            return RegimeType.UPTREND
        else:
            return RegimeType.DOWNTREND

# New regime-aware strategy
class RegimeFilteredStrategy(StrategyBase):
    def __init__(self, name, config=None, container=None):
        super().__init__(name, config, container)
        
        # Get base strategy and detector from container or configuration
        base_strategy_name = self.params.get("base_strategy")
        detector_name = self.params.get("detector")
        
        if self.container:
            self.strategy = self.container.get("strategy." + base_strategy_name)
            self.detector = self.container.get("detector." + detector_name)
        else:
            # Direct initialization if no container
            self.strategy = MeanReversionStrategy(base_strategy_name, config)
            self.detector = MovingAverageRegimeDetector(detector_name, config)
        
        # Get symbols from base strategy
        self.symbols = self.strategy.symbols
        
        # Initialize counters
        self.filtered_signals = 0
        self.passed_signals = 0
        
        # Get allowed regimes
        self.allowed_regimes = {
            RegimeType.UPTREND: [SignalType.BUY],
            RegimeType.DOWNTREND: [SignalType.SELL]
        }
        
    def on_bar(self, event):
        # Get signal from base strategy
        signal = self.strategy.on_bar(event)
        
        # Apply regime filtering
        if signal:
            symbol = event.get_symbol()
            
            # Detect regime
            regime = self.detector.update(event)
            
            # Get allowed signal types for current regime
            allowed_signals = self.allowed_regimes.get(regime, [])
            
            # Check if signal is allowed
            if signal.get_signal_type() in allowed_signals:
                self.passed_signals += 1
                return signal
            else:
                self.filtered_signals += 1
                return None
        
        return None
```

### Configuration

```yaml
# In strategy_config.yaml
strategy:
  mean_reversion:
    class: "MeanReversionStrategy"
    parameters:
      lookback: 20
      z_threshold: 1.5
      price_key: "close"
      
  regime_filtered:
    class: "RegimeFilteredStrategy"
    parameters:
      base_strategy: "mean_reversion"
      detector: "ma_regime"
      
detector:
  ma_regime:
    class: "MovingAverageRegimeDetector"
    parameters:
      ma_window: 50
```

### Usage Example

```python
# Set up container
container = Container()
container.register_instance("config", config)
container.register_instance("event_bus", EventBus())

# Register components
container.register("strategy.mean_reversion", MeanReversionStrategy)
container.register("detector.ma_regime", MovingAverageRegimeDetector)
container.register("strategy.regime_filtered", RegimeFilteredStrategy)

# Configure components
config_factory = ConfigFactory(container, config)
config_factory.configure_component("strategy.mean_reversion", "strategy.mean_reversion")
config_factory.configure_component("detector.ma_regime", "detector.ma_regime")
config_factory.configure_component("strategy.regime_filtered", "strategy.regime_filtered")

# Get configured strategy
strategy = container.get("strategy.regime_filtered")

# Run backtest
runner = BacktestRunner(config)
results = runner.run(strategy, data_handler)

# Analyze results
calculator = PerformanceCalculator(results.equity_curve, results.trades)
metrics = calculator.calculate_metrics()

# Generate report
report_generator = ReportGenerator()
report = report_generator.generate_performance_report(calculator)
report_generator.save_report(report, "regime_filtered_report.html")
```

## Conclusion

This migration guide provides a comprehensive approach to migrating regime detection and optimization functionality from the old framework to the new framework. By following these steps, you can ensure that your strategies continue to work as expected while taking advantage of the improved architecture and features of the new framework.

Remember that the key to successful migration is thorough testing and validation at each step. If you encounter issues, refer to the troubleshooting guide or contact the development team for assistance.
