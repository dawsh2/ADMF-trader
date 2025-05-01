# Signal-Interpreter Architecture Refactoring

## Overview

This refactoring implements a cleaner separation between strategy signal generation and position management, following the strategy provided in the refactoring document. The main goal is to simplify the system architecture by enforcing clear component responsibilities:

1. **Strategies** focus solely on analyzing market data and generating signals
2. **Risk Manager** handles position state tracking and trading decisions

## Key Changes

### 1. Strategy Module

- Strategies now only emit directional signals (1, -1, 0) based on market analysis
- Removed all position tracking logic from strategies
- Simplified the Strategy base class to focus on signal generation
- Created pure implementations that follow the single responsibility principle
- Added examples of ensemble strategies that combine multiple signal sources

### 2. Risk Manager Module

- Enhanced the risk manager to compare signals against current positions
- Centralized position tracking and rule ID generation in the risk manager
- Improved decision-making logic to handle direction changes
- Implemented position size calculation based on risk parameters
- Created proper tracking of signal groups for trade management

### 3. Implementation Details

#### Strategy Base Class
The Strategy base class has been simplified to focus only on signal generation:

```python
class Strategy(Component):
    """Base class for all trading strategies."""
    
    def on_bar(self, bar_event):
        """
        Process a bar event and emit a directional signal based on market analysis.
        
        Returns:
            Optional signal event with directional value (1, -1, 0)
        """
        pass
```

#### SimpleMACrossoverStrategy
The MA Crossover strategy now focuses only on generating signals:

```python
class SimpleMACrossoverStrategy(Strategy):
    """Moving Average Crossover strategy implementation."""
    
    def on_bar(self, bar_event):
        # Calculate moving averages
        fast_ma = self._calculate_fast_ma()
        slow_ma = self._calculate_slow_ma()
        
        # Determine signal based purely on indicator relationship
        if fast_ma > slow_ma:
            signal_value = 1  # Bullish
        elif fast_ma < slow_ma:
            signal_value = -1  # Bearish
        else:
            signal_value = 0  # Neutral
            
        # Create signal event
        return create_signal_event(
            signal_value=signal_value,
            price=bar_event.get_close(),
            symbol=bar_event.get_symbol(),
            timestamp=bar_event.get_timestamp()
        )
```

#### EnhancedRiskManager
The risk manager now handles position tracking and trading decisions:

```python
class EnhancedRiskManager(RiskManagerBase):
    """Enhanced risk manager with position tracking."""
    
    def on_signal(self, signal_event):
        # Extract signal details
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        
        # Get current position direction
        current_direction = self._get_position_direction(symbol)
        
        # Only act if signal differs from current position
        if signal_value != current_direction and signal_value != 0:
            # Create a new signal group for this direction change
            if symbol not in self.signal_groups:
                self.signal_groups[symbol] = 0
                
            self.signal_groups[symbol] += 1
            group_id = self.signal_groups[symbol]
            
            # Create rule ID for tracking
            direction_name = "BUY" if signal_value > 0 else "SELL"
            rule_id = f"{symbol}_{direction_name}_group_{group_id}"
            
            # Process signal and generate order
            return self._create_order(signal_event, rule_id)
        
        return None
    
    def _get_position_direction(self, symbol):
        """Determine current position direction from portfolio."""
        position = self.portfolio_manager.get_position(symbol)
        if position is None or position.quantity == 0:
            return 0  # Flat
        return 1 if position.quantity > 0 else -1  # Long or Short
```

## Benefits

1. **Cleaner Code**: Each component has a single, focused responsibility
2. **Easier Strategy Development**: New strategies only need to focus on market analysis
3. **Consistent Position Management**: All position tracking logic is centralized
4. **Better Testability**: Components are more isolated with clearer inputs/outputs
5. **Reduced Code Duplication**: Common position logic is implemented once

## Usage Examples

### Creating a Simple Strategy

```python
class MyStrategy(Strategy):
    def on_bar(self, bar_event):
        # Market analysis logic
        signal_value = self.analyze_market(bar_event)
        
        # Return signal without any position consideration
        return create_signal_event(
            signal_value=signal_value,
            price=bar_event.get_close(),
            symbol=bar_event.get_symbol(),
            timestamp=bar_event.get_timestamp()
        )
```

### Creating an Ensemble Strategy

```python
ensemble = EnsembleStrategy(event_bus, data_handler)
ensemble.add_strategy(MovingAverageCrossoverStrategy(event_bus, data_handler))
ensemble.add_strategy(RSIStrategy(event_bus, data_handler))
ensemble.add_strategy(BollingerBandsStrategy(event_bus, data_handler))

# The ensemble strategy will combine signals from all sub-strategies
# and emit a consolidated signal based on majority vote or other method
```

### System Bootstrap

```python
# Create components
data_handler = DataHandler(...)
event_bus = EventBus()
portfolio = PortfolioManager(...)

# Create strategies - they only generate signals
ma_strategy = SimpleMACrossoverStrategy(event_bus, data_handler)

# Create risk manager - handles position management
risk_manager = EnhancedRiskManager(event_bus, portfolio)

# Create order manager
order_manager = OrderManager(event_bus)

# Create broker
broker = Broker(event_bus)

# Run the system
...
```
