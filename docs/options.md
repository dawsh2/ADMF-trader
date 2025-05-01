## Introduction

This document outlines the modifications needed to extend your ADMF-Trader system to support options spread trading for backtesting purposes. Your current component-based architecture provides a strong foundation that can be extended rather than rewritten.

## Required Architecture Extensions

### 1. Options Data Source Component

```python
# src/data/sources/alpaca_options_source.py
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionBarsRequest, OptionSnapshotRequest
from datetime import datetime

class AlpacaOptionsDataSource:
    """Data source for options data from Alpaca."""
    
    def __init__(self, api_key, secret_key):
        self.client = OptionHistoricalDataClient(api_key, secret_key)
        
    def get_option_chain(self, underlying, expiration_date=None, strikes=None, option_types=None):
        """Fetch full options chain for an underlying asset."""
        # Implementation to query and build full options chain
        # This will likely require multiple API calls to build the chain
        
    def get_option_bars(self, symbols, timeframe, start_date, end_date):
        """Fetch historical bar data for option contracts."""
        request_params = OptionBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=timeframe,
            start=start_date,
            end=end_date
        )
        return self.client.get_option_bars(request_params)
        
    def get_option_snapshots(self, symbols):
        """Get current snapshots including IV and greeks."""
        request_params = OptionSnapshotRequest(
            symbol_or_symbols=symbols
        )
        return self.client.get_option_snapshot(request_params)
```

### 2. Domain Models for Options and Spreads

```python
# src/data/models/option_contract.py
class OptionContract:
    """Represents a single option contract."""
    
    def __init__(self, symbol, underlying, strike, expiration, option_type, multiplier=100):
        self.symbol = symbol  # Full option symbol
        self.underlying = underlying
        self.strike = strike
        self.expiration = expiration
        self.option_type = option_type  # 'call' or 'put'
        self.multiplier = multiplier
        
    @classmethod
    def from_symbol(cls, symbol):
        """Create an OptionContract by parsing an OCC-format symbol."""
        # Example: AAPL230616C00150000
        # Implementation to parse the symbol into components
        
    def calculate_intrinsic_value(self, underlying_price):
        """Calculate intrinsic value of the option."""
        if self.is_call():
            return max(0, underlying_price - self.strike) * self.multiplier
        else:
            return max(0, self.strike - underlying_price) * self.multiplier
    
    def is_call(self):
        return self.option_type.lower() == 'call'
        
    def is_put(self):
        return self.option_type.lower() == 'put'
```

```python
# src/data/models/option_spread.py
class OptionSpread:
    """Represents an option spread strategy with multiple legs."""
    
    def __init__(self, name, underlying):
        self.name = name
        self.underlying = underlying
        self.legs = []  # List of (OptionContract, ratio) tuples
        
    def add_leg(self, contract, ratio=1):
        """Add a leg to the spread (positive ratio for buy, negative for sell)."""
        self.legs.append((contract, ratio))
        
    def get_net_price(self, prices):
        """Calculate net price of the spread given prices for each leg."""
        total = 0
        for (contract, ratio) in self.legs:
            if contract.symbol in prices:
                total += prices[contract.symbol] * ratio * contract.multiplier
        return total
        
    def max_profit(self, prices=None):
        """Calculate maximum theoretical profit for the spread."""
        # Implementation varies by spread type
        
    def max_loss(self, prices=None):
        """Calculate maximum theoretical loss for the spread."""
        # Implementation varies by spread type
        
    @classmethod
    def create_vertical_spread(cls, underlying, expiration, long_strike, 
                              short_strike, option_type, contract_builder):
        """Factory method to create a vertical spread."""
        name = f"{underlying} {option_type.upper()} {long_strike}/{short_strike} Vertical"
        spread = cls(name, underlying)
        
        long_contract = contract_builder(underlying, expiration, long_strike, option_type)
        short_contract = contract_builder(underlying, expiration, short_strike, option_type)
        
        spread.add_leg(long_contract, 1)   # Buy one
        spread.add_leg(short_contract, -1) # Sell one
        
        return spread
```

### 3. Extended Historical Data Handler

```python
# src/data/historical_options_handler.py
class HistoricalOptionsHandler:
    """Handler for historical options data processing."""
    
    def __init__(self, options_data_source, bar_emitter, underlying_data_handler=None):
        self.options_data_source = options_data_source
        self.bar_emitter = bar_emitter
        self.underlying_data_handler = underlying_data_handler
        self.option_contracts = {}  # symbol -> OptionContract
        self.option_chains = {}     # underlying -> expiration -> option_type -> strike -> OptionContract
        
    def load_option_chain(self, underlying, start_date, end_date, 
                          expiration_date=None, strikes=None, option_types=None):
        """Load option chain data for a specific underlying."""
        chain = self.options_data_source.get_option_chain(
            underlying, expiration_date, strikes, option_types
        )
        
        # Store contracts in both formats for easy lookup
        for contract in chain:
            self.option_contracts[contract.symbol] = contract
            
            # Build option chain structure
            if contract.underlying not in self.option_chains:
                self.option_chains[contract.underlying] = {}
                
            exp = contract.expiration
            if exp not in self.option_chains[contract.underlying]:
                self.option_chains[contract.underlying][exp] = {"call": {}, "put": {}}
                
            opt_type = contract.option_type.lower()
            self.option_chains[contract.underlying][exp][opt_type][contract.strike] = contract
        
        # Load price data for all contracts
        contract_symbols = [c.symbol for c in chain]
        self._load_option_price_data(contract_symbols, start_date, end_date)
    
    def _load_option_price_data(self, symbols, start_date, end_date):
        """Load price data for specified option symbols."""
        # Use the data source to get historical bars
        bars_data = self.options_data_source.get_option_bars(
            symbols, "1d", start_date, end_date
        )
        
        # Process and store the data
        # This is where you'd adapt the data to your existing system format
    
    def build_spread(self, spread_type, underlying, params):
        """Build a spread of the specified type with given parameters."""
        # Factory method to create different types of spreads
        if spread_type == "vertical":
            return self._build_vertical_spread(underlying, params)
        elif spread_type == "iron_condor":
            return self._build_iron_condor(underlying, params)
        # Add other spread types as needed
    
    def _build_vertical_spread(self, underlying, params):
        """Build a vertical spread."""
        # Extract parameters
        expiration = params.get("expiration")
        long_strike = params.get("long_strike")
        short_strike = params.get("short_strike")
        option_type = params.get("option_type", "call")
        
        # Create spread using the chain data
        return OptionSpread.create_vertical_spread(
            underlying, expiration, long_strike, short_strike, option_type,
            self._get_contract_from_chain
        )
    
    def _get_contract_from_chain(self, underlying, expiration, strike, option_type):
        """Get a contract from the cached option chain."""
        try:
            return self.option_chains[underlying][expiration][option_type][strike]
        except KeyError:
            # Handle missing contract
            return None
```

### 4. Event System Enhancements

```python
# src/core/events/event_types.py (additions)
class EventType:
    # Existing types...
    
    # New event types for options
    OPTION_BAR = "OPTION_BAR"
    OPTION_QUOTE = "OPTION_QUOTE"
    OPTION_GREEK = "OPTION_GREEK"
    
    # Spread-specific events
    SPREAD_SIGNAL = "SPREAD_SIGNAL"
    SPREAD_ORDER = "SPREAD_ORDER"
    SPREAD_FILL = "SPREAD_FILL"
```

```python
# src/core/events/event_utils.py (additions)
def create_option_bar_event(symbol, bar_data, timestamp=None):
    """Create event for option bar data."""
    return Event(
        EventType.OPTION_BAR,
        {
            'symbol': symbol,
            'open': bar_data.get('open'),
            'high': bar_data.get('high'),
            'low': bar_data.get('low'),
            'close': bar_data.get('close'),
            'volume': bar_data.get('volume'),
            'timestamp': timestamp or datetime.now()
        }
    )

def create_spread_signal_event(spread, signal_value, underlying_price, timestamp=None):
    """Create an event for a spread signal."""
    return Event(
        EventType.SPREAD_SIGNAL,
        {
            'spread_name': spread.name,
            'underlying': spread.underlying,
            'legs': [{'symbol': contract.symbol, 'ratio': ratio} 
                    for contract, ratio in spread.legs],
            'signal_value': signal_value,
            'underlying_price': underlying_price,
            'timestamp': timestamp or datetime.now()
        }
    )
```

### 5. Strategy Components for Options

```python
# src/strategy/components/features/implied_volatility.py
class ImpliedVolatility(Feature):
    """Feature that calculates or extracts implied volatility from options data."""
    
    def extract(self, data, indicators=None):
        """Extract implied volatility features from data."""
        # Implementation to calculate or look up IV from data
```

```python
# src/strategy/components/rules/vertical_spread_rule.py
class VerticalSpreadRule(Rule):
    """Rule for vertical spread entry/exit signals."""
    
    def __init__(self, name=None, parameters=None):
        super().__init__(name, parameters)
        self.entry_iv_threshold = self.parameters.get('entry_iv_threshold', 0.3)
        self.exit_iv_threshold = self.parameters.get('exit_iv_threshold', 0.2)
        
    def generate_signal(self, data, features=None):
        """Generate signals for vertical spread trading."""
        if 'implied_volatility' not in features:
            return 0
            
        iv = features['implied_volatility'].latest
        
        # Entry logic (buy spread when IV is high)
        if iv > self.entry_iv_threshold:
            return 1
            
        # Exit logic (sell spread when IV decreases)
        if iv < self.exit_iv_threshold:
            return -1
            
        return 0
```

### 6. Spread-Specific Position and Risk Management

```python
# src/risk/portfolio/spread_position.py
class SpreadPosition(Position):
    """Position that represents an options spread."""
    
    def __init__(self, spread, quantity, entry_prices=None, entry_time=None):
        self.spread = spread  # The OptionSpread object
        self.quantity = quantity  # Number of spread units
        self.entry_prices = entry_prices or {}  # Prices of each leg at entry
        self.entry_time = entry_time or datetime.now()
        
    def market_value(self, current_prices):
        """Calculate current market value of the spread position."""
        return self.spread.get_net_price(current_prices) * self.quantity
        
    def unrealized_pnl(self, current_prices):
        """Calculate unrealized P&L for the spread position."""
        entry_value = self.spread.get_net_price(self.entry_prices)
        current_value = self.spread.get_net_price(current_prices)
        return (current_value - entry_value) * self.quantity
        
    def to_dict(self):
        """Convert position to dictionary for serialization."""
        return {
            'spread_name': self.spread.name,
            'underlying': self.spread.underlying,
            'quantity': self.quantity,
            'legs': [{'symbol': contract.symbol, 'ratio': ratio} 
                    for contract, ratio in self.spread.legs],
            'entry_prices': self.entry_prices,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None
        }
```

```python
# src/risk/managers/spread_risk_manager.py
class SpreadRiskManager:
    """Risk manager for option spread strategies."""
    
    def __init__(self, event_bus, portfolio, order_registry=None, name=None):
        self.event_bus = event_bus
        self.portfolio = portfolio
        self.order_registry = order_registry
        self.name = name or "spread_risk_manager"
        
        # Risk parameters
        self.max_positions = 5  # Maximum concurrent spread positions
        self.max_risk_per_trade = 0.02  # Maximum risk as fraction of portfolio
        self.max_risk_per_underlying = 0.05  # Maximum risk per underlying
        
        # Register for events
        self.event_bus.register(EventType.SPREAD_SIGNAL, self.on_spread_signal)
        
    def on_spread_signal(self, signal_event):
        """Process spread signals and generate orders if appropriate."""
        # Extract signal information
        spread_name = signal_event.data.get('spread_name')
        underlying = signal_event.data.get('underlying')
        signal_value = signal_event.data.get('signal_value')
        legs = signal_event.data.get('legs', [])
        
        # Get current portfolio state for risk checks
        portfolio_value = self.portfolio.get_portfolio_value()
        current_positions = self.portfolio.get_positions_by_underlying(underlying)
        
        # Perform risk checks
        if not self._validate_risk(signal_value, legs, portfolio_value, current_positions):
            return
            
        # Create spread order event
        order_event = self._create_spread_order_event(signal_event)
        self.event_bus.emit(order_event)
        
    def _validate_risk(self, signal_value, legs, portfolio_value, current_positions):
        """Validate that this trade meets risk management criteria."""
        # Implement risk validation logic
        return True
        
    def _create_spread_order_event(self, signal_event):
        """Create an order event from a spread signal event."""
        # Implementation to create the spread order
```

### 7. Order Management for Spreads

```python
# src/execution/orders/spread_order.py
class SpreadOrder:
    """Order for an options spread with multiple legs."""
    
    def __init__(self, spread, direction, quantity, order_id=None, parent_id=None):
        self.spread = spread
        self.direction = direction  # BUY or SELL
        self.quantity = quantity
        self.order_id = order_id or str(uuid.uuid4())
        self.parent_id = parent_id
        self.leg_orders = []
        self.status = "CREATED"
        self.filled_legs = set()
        
    def add_leg_order(self, leg_order):
        """Add a leg order to this spread order."""
        self.leg_orders.append(leg_order)
        
    def update_status(self, new_status, leg_order_id=None):
        """Update the status of this spread order."""
        if leg_order_id:
            self.filled_legs.add(leg_order_id)
            
        # If all legs are filled, mark the spread as filled
        if len(self.filled_legs) == len(self.leg_orders):
            self.status = "FILLED"
        elif new_status == "REJECTED":
            self.status = "REJECTED"
        elif new_status == "CANCELED":
            self.status = "CANCELED"
        
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'order_id': self.order_id,
            'spread_name': self.spread.name,
            'direction': self.direction,
            'quantity': self.quantity,
            'status': self.status,
            'legs': [order.to_dict() for order in self.leg_orders]
        }
```

```python
# src/execution/order_manager.py (additions)
class OrderManager:
    # Existing methods...
    
    def create_spread_order(self, spread, direction, quantity, price_limits=None):
        """Create an order for an option spread."""
        # Create parent order for the spread
        spread_order = SpreadOrder(
            spread=spread,
            direction=direction,
            quantity=quantity
        )
        
        # Register the spread order if registry exists
        if self.order_registry:
            self.order_registry.register_order(spread_order)
        
        # Create child orders for each leg
        for contract, ratio in spread.legs:
            # Adjust direction based on ratio and spread direction
            leg_direction = direction
            if (ratio < 0 and direction == 'BUY') or (ratio > 0 and direction == 'SELL'):
                leg_direction = 'SELL' if direction == 'BUY' else 'BUY'
                
            leg_quantity = abs(ratio) * quantity
            
            # Set price limit for the leg if provided
            price_limit = None
            if price_limits and contract.symbol in price_limits:
                price_limit = price_limits[contract.symbol]
            
            # Create leg order
            leg_order = self.create_order(
                symbol=contract.symbol,
                order_type='LIMIT' if price_limit else 'MARKET',
                direction=leg_direction,
                quantity=leg_quantity,
                price=price_limit,
                parent_id=spread_order.order_id
            )
            spread_order.add_leg_order(leg_order)
            
        # Create spread order event
        order_event = Event(
            EventType.SPREAD_ORDER,
            spread_order.to_dict()
        )
        self.event_bus.emit(order_event)
        
        return spread_order
```

### 8. Broker Simulation for Spreads

```python
# src/execution/broker/broker_simulator.py (additions)
class SimulatedBroker:
    # Existing methods...
    
    def _register_handlers(self):
        """Register event handlers."""
        # Existing registrations...
        self.event_bus.register(EventType.SPREAD_ORDER, self.on_spread_order)
    
    def on_spread_order(self, order_event):
        """Handle spread order events."""
        # The spread order event should have already created the leg orders
        # which will be processed individually by our existing order handler
        # Here we just need to track the parent spread order
        
        # In a more sophisticated implementation, you could model
        # the relationship between legs, partial fills, etc.
```

### 9. Analytics for Spread Strategies

```python
# src/analytics/performance/spread_metrics.py
class SpreadPerformanceCalculator:
    """Calculate performance metrics for spread strategies."""
    
    def calculate_metrics(self, trades, positions, equity_curve):
        """Calculate spread-specific performance metrics."""
        metrics = {}
        
        # Calculate standard metrics
        metrics['total_trades'] = len(trades)
        
        # Winning/losing trades
        win_trades = [t for t in trades if t.get('pnl', 0) > 0]
        metrics['win_count'] = len(win_trades)
        metrics['win_rate'] = len(win_trades) / len(trades) if trades else 0
        
        # Spread-specific metrics
        metrics['avg_days_held'] = self._calculate_avg_days_held(trades)
        metrics['return_on_risk'] = self._calculate_return_on_risk(trades)
        
        return metrics
        
    def _calculate_avg_days_held(self, trades):
        """Calculate average holding period for spread trades."""
        if not trades:
            return 0
            
        days_held = []
        for trade in trades:
            entry_time = trade.get('entry_time')
            exit_time = trade.get('exit_time')
            
            if entry_time and exit_time:
                entry_dt = datetime.fromisoformat(entry_time)
                exit_dt = datetime.fromisoformat(exit_time)
                days = (exit_dt - entry_dt).days
                days_held.append(days)
                
        return sum(days_held) / len(days_held) if days_held else 0
        
    def _calculate_return_on_risk(self, trades):
        """Calculate return on risk for spread trades."""
        if not trades:
            return 0
            
        total_return = sum(trade.get('pnl', 0) for trade in trades)
        total_risk = sum(trade.get('max_risk', 0) for trade in trades)
        
        return total_return / total_risk if total_risk else 0
```

### 10. Backtesting Coordinator Extensions

```python
# src/execution/backtest/spread_backtest.py
class SpreadBacktestCoordinator:
    """Coordinator for backtesting spread strategies."""
    
    def __init__(self, container, config):
        self.container = container
        self.config = config
        self.options_handler = None
        self.strategy = None
        
    def setup(self):
        """Set up the backtest components."""
        # Get components from container
        self.event_bus = self.container.get('event_bus')
        self.data_handler = self.container.get('data_handler')
        self.options_handler = self.container.get('options_handler')
        self.strategy = self.container.get('strategy')
        self.portfolio = self.container.get('portfolio')
        self.risk_manager = self.container.get('risk_manager')
        self.broker = self.container.get('broker')
        self.order_manager = self.container.get('order_manager')
        
        return True
        
    def run(self, underlying_symbols, option_params, start_date, end_date, 
            initial_capital=100000.0, timeframe='1d'):
        """Run a spread strategy backtest."""
        # Initialize portfolio
        self.portfolio.reset()
        self.portfolio.set_initial_cash(initial_capital)
        
        # Load underlying data
        for symbol in underlying_symbols:
            self.data_handler.load_security_data(symbol, start_date, end_date)
            
        # Load options data based on parameters
        for symbol in underlying_symbols:
            self.options_handler.load_option_chain(
                symbol, start_date, end_date, **option_params
            )
            
        # Run the backtest
        self.data_handler.run_backtest(start_date, end_date)
        
        # Generate results
        calculator = self.container.get('calculator')
        trades = self.portfolio.get_all_trades()
        positions = self.portfolio.get_all_positions()
        equity_curve = self.portfolio.get_equity_curve()
        
        metrics = calculator.calculate_metrics(trades, positions, equity_curve)
        
        return {
            'equity_curve': equity_curve,
            'trades': trades,
            'metrics': metrics
        }
```

## Implementation Approach

The changes outlined above build upon your existing architecture without requiring a full system rewrite. Here's the implementation approach:

1. **Start with Data Models**: Implement the option contract and spread classes first
2. **Create the Options Data Source**: Build the Alpaca options data connector
3. **Extend the Event System**: Add the new event types and utility functions
4. **Build Options Data Handler**: Create the historical options data handler
5. **Implement Spread Order Management**: Extend your order system for spreads
6. **Create Spread Risk Manager**: Implement the specialized risk manager
7. **Add Analytics**: Extend your analytics system for spread metrics
8. **Test Components**: Create unit tests for each component
9. **Integration Test**: Create a simple spread backtesting script

## Rewrite vs. Extension

Your current architecture follows a clean component-based design pattern that is well-suited for extension to handle options spreads. A complete rewrite isn't necessary for several reasons:

1. **Component Separation**: Your event-driven architecture with clear component boundaries makes extensions natural
2. **Hierarchical Design**: Your core design follows a hierarchical pattern that can accommodate new components
3. **Parameter Management**: Your system already has robust parameter management
4. **Event System**: Your event system can be extended for new event types

While designing for options from the ground up might yield some minor optimizations, the benefits likely don't justify the cost of a full rewrite. The proposed extensions maintain compatibility with your existing system while providing the specialized functionality needed for options spreads.

## Future Considerations

Once you've implemented the basic spread trading functionality, consider these enhancements:

1. **Greeks Calculation**: Add support for calculating and using option Greeks
2. **Volatility Surface Modeling**: Implement volatility surface construction for more accurate pricing
3. **Auto Spread Construction**: Add rules for dynamically selecting optimal spreads
4. **Improved Fill Simulation**: Enhance broker simulation with realistic spread execution modeling
5. **Advanced Spread Strategies**: Implement condors, butterflies, and calendar spreads