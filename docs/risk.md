# Risk Management Module Specification

## Overview

The Risk Management module is responsible for position tracking, portfolio management, and risk control. This module will be separated from the strategy module and consolidated with existing position and portfolio components to create a cohesive risk management system.

## Module Structure

```
risk/
├── __init__.py
├── position/
│   ├── __init__.py
│   ├── position.py              # Position tracking class
│   ├── position_tracker.py      # Multi-position tracking
│   └── position_utils.py        # Position calculation utilities
├── portfolio/
│   ├── __init__.py
│   ├── portfolio_manager.py     # Portfolio management class
│   ├── portfolio_analytics.py   # Portfolio-level analytics
│   └── allocation.py            # Asset allocation utilities
├── execution/
│   ├── __init__.py
│   ├── sizing.py                # Position sizing
│   ├── limits.py                # Trading limits and constraints
│   └── validation.py            # Order validation
├── managers/
│   ├── __init__.py
│   ├── risk_manager_base.py     # Base risk manager interface
│   ├── standard_risk_manager.py # Standard implementation
│   └── adaptive_risk_manager.py # Regime-adaptive risk management
└── metrics/
    ├── __init__.py
    ├── exposure.py              # Exposure metrics
    ├── drawdown.py              # Drawdown metrics
    └── concentration.py         # Concentration and correlation metrics
```

## Key Components

### 1. Position Module

#### 1.1 Position Class

The `Position` class tracks a single position in an instrument with accurate cost basis and P&L calculation.

**Key Functionality:**
- Track quantity, cost basis, and realized P&L
- Support long and short positions
- Calculate unrealized P&L
- Track position history
- Support position adjustments (increase/decrease)
- Calculate position metrics (return, duration, etc.)

**Interface:**
```python
class Position:
    def __init__(self, symbol: str, quantity: float = 0, cost_basis: float = 0.0)
    def add_quantity(self, quantity: float, price: float, timestamp=None) -> float
    def reduce_quantity(self, quantity: float, price: float, timestamp=None) -> float
    def market_value(self, price: float) -> float
    def unrealized_pnl(self, price: float) -> float
    def realized_pnl() -> float
    def total_pnl(self, price: float) -> float
    def average_price() -> float
    def position_age(self, current_time=None) -> datetime.timedelta
    def position_direction() -> str  # "LONG", "SHORT", or "FLAT"
    def to_dict() -> dict
```

#### 1.2 Position Tracker

The `PositionTracker` manages multiple positions across different instruments.

**Key Functionality:**
- Track positions across multiple instruments
- Update positions based on fills
- Calculate aggregate position metrics
- Support position queries and filtering
- Track historical positions
- Generate position-related events

**Interface:**
```python
class PositionTracker:
    def __init__(self)
    def update_position(self, symbol: str, quantity: float, price: float, timestamp=None) -> Position
    def get_position(self, symbol: str) -> Optional[Position]
    def get_all_positions() -> Dict[str, Position]
    def get_total_exposure() -> float
    def get_exposure_by_direction() -> Dict[str, float]
    def get_position_history(self, symbol: str) -> List[Dict]
    def reset() -> None
```

### 2. Portfolio Module

#### 2.1 Portfolio Manager

The `PortfolioManager` tracks the state of the entire portfolio including cash, positions, and overall performance.

**Key Functionality:**
- Track cash balance
- Maintain position values
- Calculate equity curve
- Process fills to update portfolio state
- Calculate portfolio returns
- Generate portfolio-level events
- Support portfolio rebalancing

**Interface:**
```python
class PortfolioManager:
    def __init__(self, initial_cash: float = 0.0)
    def on_fill(self, fill_event) -> None
    def update_market_data(self, market_prices: Dict[str, float]) -> None
    def get_equity() -> float
    def get_cash() -> float
    def get_position_value() -> float
    def get_position(self, symbol: str) -> Optional[Position]
    def get_all_positions() -> Dict[str, Position]
    def get_portfolio_summary() -> Dict[str, Any]
    def get_returns() -> pd.Series
    def get_equity_curve() -> pd.DataFrame
    def reset() -> None
```

#### 2.2 Portfolio Analytics

The `PortfolioAnalytics` provides analysis of portfolio performance and characteristics.

**Key Functionality:**
- Calculate portfolio metrics (Sharpe, Sortino, etc.)
- Analyze drawdowns
- Calculate correlation matrix
- Calculate beta and other risk metrics
- Generate portfolio snapshots
- Support stress testing

**Interface:**
```python
class PortfolioAnalytics:
    def __init__(self, portfolio_manager: PortfolioManager)
    def calculate_returns() -> pd.Series
    def calculate_metrics() -> Dict[str, float]
    def analyze_drawdowns() -> List[Dict]
    def calculate_correlation_matrix() -> pd.DataFrame
    def calculate_beta(benchmark_returns: pd.Series) -> float
    def generate_snapshot() -> Dict[str, Any]
    def run_stress_test(scenario: Dict) -> Dict[str, Any]
```

### 3. Execution Module

#### 3.1 Position Sizing

The `PositionSizer` calculates appropriate position sizes based on various methods.

**Key Functionality:**
- Multiple sizing methods (fixed, percent of equity, percent risk, volatility-based)
- Account for current positions
- Apply risk limits
- Support position scaling
- Adapt to market conditions

**Interface:**
```python
class PositionSizer:
    def __init__(self, method: str = 'fixed', **params)
    def calculate_position_size(self, symbol: str, direction: str, price: float, 
                              portfolio: PortfolioManager, context: Dict = None) -> float
    def set_method(self, method: str, **params) -> None
    def get_parameters() -> Dict[str, Any]
    def set_parameters(self, params: Dict[str, Any]) -> None
```

#### 3.2 Trading Limits

The `LimitManager` enforces various trading and risk limits.

**Key Functionality:**
- Position size limits
- Exposure limits (total, per-instrument, etc.)
- Trading frequency limits
- Drawdown-based limits
- Volatility-based limits
- Custom limit definitions

**Interface:**
```python
class LimitManager:
    def __init__(self, limits: Dict[str, Any] = None)
    def validate_order(self, order, portfolio: PortfolioManager) -> Tuple[bool, str]
    def add_limit(self, limit_type: str, limit_value: Any) -> None
    def remove_limit(self, limit_type: str) -> None
    def update_limit(self, limit_type: str, limit_value: Any) -> None
    def get_limits() -> Dict[str, Any]
    def get_limit_usage() -> Dict[str, float]
```

### 4. Risk Managers

#### 4.1 Risk Manager Base

The `RiskManagerBase` defines the interface for risk managers that convert signals to orders.

**Key Functionality:**
- Process signals to generate orders
- Apply risk limits and constraints
- Position sizing
- Risk control
- Signal filtering based on risk criteria

**Interface:**
```python
class RiskManagerBase(ABC):
    def __init__(self, portfolio_manager: PortfolioManager)
    @abstractmethod
    def on_signal(self, signal_event) -> Optional[OrderEvent]
    @abstractmethod
    def evaluate_trade(self, symbol: str, direction: str, quantity: float, price: float) -> bool
    def set_parameters(self, params: Dict[str, Any]) -> None
    def get_parameters() -> Dict[str, Any]
    def reset() -> None
```

#### 4.2 Standard Risk Manager

The `StandardRiskManager` implements a standard risk management approach.

**Key Functionality:**
- Signal to order conversion
- Position sizing based on strategy
- Risk limit application
- Support for multiple instruments
- Comprehensive risk controls

**Interface:**
```python
class StandardRiskManager(RiskManagerBase):
    def __init__(self, portfolio_manager: PortfolioManager, position_sizer: PositionSizer, 
               limit_manager: LimitManager)
    def on_signal(self, signal_event) -> Optional[OrderEvent]
    def evaluate_trade(self, symbol: str, direction: str, quantity: float, price: float) -> bool
    def set_risk_limits(self, limits: Dict[str, Any]) -> None
    def get_risk_statistics() -> Dict[str, Any]
```

#### 4.3 Adaptive Risk Manager

The `AdaptiveRiskManager` dynamically adjusts risk parameters based on market regimes.

**Key Functionality:**
- Regime-specific risk parameters
- Dynamic position sizing
- Adaptive risk limits
- Performance-based risk adjustment
- Market volatility adaptation

**Interface:**
```python
class AdaptiveRiskManager(RiskManagerBase):
    def __init__(self, portfolio_manager: PortfolioManager, position_sizer: PositionSizer, 
               limit_manager: LimitManager, regime_detector=None)
    def on_signal(self, signal_event) -> Optional[OrderEvent]
    def on_regime_change(self, regime_event) -> None
    def set_regime_parameters(self, regime: str, params: Dict[str, Any]) -> None
    def get_regime_parameters(self, regime: str) -> Dict[str, Any]
    def get_current_regime() -> str
    def get_regime_statistics() -> Dict[str, Any]
```

### 5. Risk Metrics

#### 5.1 Exposure Metrics

The `ExposureMetrics` calculates various exposure-related metrics.

**Key Functionality:**
- Gross exposure calculation
- Net exposure calculation
- Long/short exposure calculation
- Sector/asset class exposure
- Geographic exposure
- Factor exposure

**Interface:**
```python
class ExposureMetrics:
    def __init__(self, portfolio_manager: PortfolioManager)
    def calculate_gross_exposure() -> float
    def calculate_net_exposure() -> float
    def calculate_exposure_by_direction() -> Dict[str, float]
    def calculate_sector_exposure(sector_mapping: Dict[str, str]) -> Dict[str, float]
    def calculate_factor_exposure(factor_betas: Dict[str, Dict[str, float]]) -> Dict[str, float]
    def generate_exposure_report() -> Dict[str, Any]
```

#### 5.2 Drawdown Metrics

The `DrawdownMetrics` calculates drawdown-related metrics.

**Key Functionality:**
- Current drawdown calculation
- Historical drawdown analysis
- Maximum drawdown calculation
- Drawdown duration analysis
- Drawdown recovery analysis
- Conditional drawdown metrics

**Interface:**
```python
class DrawdownMetrics:
    def __init__(self, portfolio_manager: PortfolioManager)
    def calculate_current_drawdown() -> float
    def calculate_maximum_drawdown() -> float
    def analyze_historical_drawdowns() -> List[Dict]
    def calculate_average_drawdown() -> float
    def calculate_average_recovery_time() -> float
    def generate_drawdown_report() -> Dict[str, Any]
```

## Event Integration

The Risk Management module will interact with the event system through the following events:

1. **Inputs:**
   - `SignalEvent`: Trading signals from strategies
   - `FillEvent`: Fill notifications from broker
   - `BarEvent`: Market data for mark-to-market
   - `RegimeEvent`: Market regime changes

2. **Outputs:**
   - `OrderEvent`: Orders generated from signals
   - `PositionEvent`: Position updates
   - `PortfolioEvent`: Portfolio state updates
   - `RiskLimitEvent`: Risk limit violations
   - `DrawdownEvent`: Drawdown alerts

## Configuration Integration

The Risk Management module will be configurable through the configuration system:

```yaml
risk:
  position_sizing:
    method: percent_risk
    params:
      risk_percent: 0.01
      max_position_size: 100000
  
  limits:
    max_exposure: 1.0
    max_position_size: 0.1
    max_concentration: 0.25
    max_drawdown: 0.2
  
  drawdown_control:
    enabled: true
    threshold: 0.1
    action: reduce_size
    reduction_factor: 0.5
  
  regime_adaptation:
    enabled: true
    regimes:
      bullish:
        risk_percent: 0.015
        max_exposure: 1.2
      bearish:
        risk_percent: 0.005
        max_exposure: 0.5
      volatile:
        risk_percent: 0.0075
        max_exposure: 0.75
```

## Implementation Plan

1. **Phase 1: Position and Portfolio Components**
   - Implement Position and PositionTracker classes
   - Implement PortfolioManager class
   - Implement basic portfolio analytics

2. **Phase 2: Execution Components**
   - Implement PositionSizer with multiple methods
   - Implement LimitManager for risk constraints
   - Implement order validation utilities

3. **Phase 3: Risk Managers**
   - Implement RiskManagerBase interface
   - Implement StandardRiskManager
   - Implement AdaptiveRiskManager

4. **Phase 4: Risk Metrics**
   - Implement ExposureMetrics
   - Implement DrawdownMetrics
   - Implement correlation and concentration metrics

5. **Phase 5: Integration and Testing**
   - Integrate with event system
   - Integrate with configuration system
   - Comprehensive testing of all components

## Dependencies

- Event System
- Configuration System
- Data Handling (for market data)
- Broker Interface (for order execution)

## Success Criteria

1. All risk management components function correctly and pass tests
2. Position tracking is accurate for both long and short positions
3. Portfolio valuation is accurate and consistent
4. Risk limits are properly enforced
5. Signal to order conversion follows risk parameters
6. Regime adaptation works correctly
7. Performance matches or exceeds the original implementation
