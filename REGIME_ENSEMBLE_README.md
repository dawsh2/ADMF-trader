# Regime Ensemble Strategy

This document provides an overview of the Regime Ensemble Strategy implementation and optimization in the ADMF-trader system.

## Overview

The Regime Ensemble Strategy is a sophisticated trading approach that:

1. Detects different market regimes (trending, mean-reverting, volatile, neutral)
2. Applies different trading rules with adaptive weights for each regime
3. Combines signals from multiple sub-strategies into a unified trading decision

This strategy demonstrates superior adaptability to changing market conditions compared to single-strategy approaches.

## Implementations

Two implementations are provided:

1. **RegimeEnsembleStrategy** (regime_ensemble_strategy.py)
   - Fully-featured implementation with direct event bus and data handler dependencies
   - Used for regular backtesting and live trading

2. **SimpleRegimeEnsembleStrategy** (simple_regime_ensemble.py)
   - Simplified implementation optimized for parameter optimization
   - More flexible initialization that doesn't require event bus or data handler at construction time

## Strategy Components

The strategy consists of three main trading rules:

1. **Trend Following** (MA Crossover)
   - Fast and slow moving average crossovers
   - Signal strength based on MA separation
   - Configurable window periods

2. **Mean Reversion** (RSI)
   - Relative Strength Index (RSI) based mean reversion
   - Overbought/oversold thresholds
   - Configurable window period

3. **Volatility Breakout**
   - Price channel breakouts using Average True Range (ATR)
   - Dynamic breakout thresholds
   - Configurable lookback window and ATR multiplier

## Regime Detection

The strategy detects four market regimes:

1. **Trend** - Strong directional price movement aligned with the longer-term moving average
2. **Mean Reversion** - Price oscillating around a central value with no clear direction
3. **Volatile** - High volatility period with unpredictable price movements
4. **Neutral** - Default regime when no clear pattern is detected

Each regime uses different weights for the trading rules:

| Regime | Trend Following | Mean Reversion | Volatility Breakout |
|--------|----------------|----------------|---------------------|
| Trend  | 1.0            | 0.2            | 0.5                 |
| Mean Reversion | 0.2    | 1.0            | 0.3                 |
| Volatile | 0.3          | 0.3            | 1.0                 |
| Neutral  | 0.5          | 0.5            | 0.5                 |

## Configuration

### Basic Configuration (simple_regime_optimization.yaml)

```yaml
# Mode
mode: backtest

# Basic settings
backtest:
  initial_capital: 100000.0
  symbols: ['SPY']
  timeframe: "1min"
  optimize: true

# Strategy configuration
strategy:
  name: simple_regime_ensemble
  default_params:
    # Regime detection parameters
    volatility_window: 60
    volatility_threshold: 0.002
    trend_ma_window: 120
    trend_threshold: 0.01
    
    # Trading rule parameters
    fast_ma_window: 20
    slow_ma_window: 60
    rsi_window: 30
    rsi_overbought: 70
    rsi_oversold: 30
    breakout_window: 60
    breakout_multiplier: 1.5
```

### Parameter Space for Optimization

```yaml
parameter_space:
  # Regime detection parameters
  - name: volatility_window
    type: integer
    min: 30
    max: 90
    step: 30
    
  # Strategy parameters
  - name: fast_ma_window
    type: integer
    min: 10
    max: 30
    step: 10
    
  - name: slow_ma_window
    type: integer
    min: 30
    max: 90
    step: 30
```

## Usage

### Running a Backtest

```bash
python main.py --config config/simple_regime_optimization.yaml
```

### Performing Optimization

```bash
python main.py --config config/simple_regime_optimization.yaml --optimize
```

## Implementation Notes

### SimpleRegimeEnsembleStrategy

The SimpleRegimeEnsembleStrategy was specifically designed to work well with the optimization framework:

1. It doesn't require event_bus or data_handler at initialization time
2. It retrieves these dependencies from the context during initialize()
3. It contains a complete implementation of all the trading rules and regime detection
4. The strategy is automatically discovered by the StrategyFactory

### Key Parameters for Tuning

- **Regime Detection:**
  - `volatility_threshold` - Determines when markets are classified as volatile
  - `trend_threshold` - Determines when markets are classified as trending

- **Trading Rules:**
  - `fast_ma_window` / `slow_ma_window` - Control the sensitivity of trend detection
  - `rsi_overbought` / `rsi_oversold` - Control the entry/exit points for mean reversion
  - `breakout_multiplier` - Controls the sensitivity of volatility breakout signals

## Extending the Strategy

To extend the strategy with new features:

1. **Add new sub-strategies:**
   - Implement a new signal calculation method
   - Add appropriate weights in the regime_weights dictionary

2. **Enhance regime detection:**
   - Modify the _detect_regime method to use additional indicators
   - Create new regime types in the MarketRegime class

3. **Add optimization dimensions:**
   - Add new parameters to the strategy constructor
   - Include them in the parameter_space configuration

## Performance Considerations

For large datasets or complex optimizations:

1. Use a limited parameter space for initial testing
2. Consider using random search instead of grid search
3. Implement a train/test split to prevent overfitting 
4. Analyze regime-specific performance metrics