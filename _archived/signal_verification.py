#!/usr/bin/env python
"""
Signal flow verification script to validate fixes to the order registry and event flow.
"""
import os
import logging
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('signal_verification.log', mode='w')
    ]
)
logger = logging.getLogger("ADMF-Verifier")

# Import system components
from src.core.di.container import Container
from src.core.events.event_bus import EventBus
from src.core.events.event_manager import EventManager
from src.core.events.event_emitters import BarEmitter
from src.core.events.event_types import EventType
from src.data.sources.csv_handler import CSVDataSource
from src.data.historical_data_handler import HistoricalDataHandler
from src.risk.portfolio.portfolio import PortfolioManager
from src.risk.managers.simple import SimpleRiskManager
from src.execution.broker.broker_simulator import SimulatedBroker
from src.execution.backtest.backtest import BacktestCoordinator
from src.analytics.performance.calculator import PerformanceCalculator
from src.analytics.reporting.report_generator import ReportGenerator
from src.execution.order_manager import OrderManager
from src.execution.order_registry import OrderRegistry

# Event tracer class to monitor signal flow
class EventTracer:
    """Trace events through the system."""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.bar_events = []
        self.signal_events = []
        self.order_events = []
        self.fill_events = []
        self.all_events = []
        self.handlers_called = {}  # Track which handlers were called
        self._register_handlers()
    
    def _register_handlers(self):
        """Register handlers for all event types."""
        # Use high priority to ensure we see events first
        self.event_bus.register(EventType.BAR, self._on_bar, priority=1000)
        self.event_bus.register(EventType.SIGNAL, self._on_signal, priority=1000)
        self.event_bus.register(EventType.ORDER, self._on_order, priority=1000)
        self.event_bus.register(EventType.FILL, self._on_fill, priority=1000)
    
    def _on_bar(self, event):
        """Record bar event."""
        bar_data = {
            'id': id(event),
            'timestamp': event.get_timestamp(),
            'symbol': event.get_symbol(),
            'price': event.get_close()
        }
        self.bar_events.append(bar_data)
        self.all_events.append(('BAR', event.get_timestamp(), bar_data))
        logger.debug(f"TRACE: Bar event {event.get_symbol()} {event.get_close():.2f}")
    
    def _on_signal(self, event):
        """Record signal event."""
        signal_data = {
            'id': id(event),
            'timestamp': event.get_timestamp(),
            'symbol': event.get_symbol(),
            'signal_value': event.get_signal_value(),
            'price': event.get_price()
        }
        self.signal_events.append(signal_data)
        self.all_events.append(('SIGNAL', event.get_timestamp(), signal_data))
        logger.debug(f"TRACE: Signal event {event.get_symbol()} {event.get_signal_value()}")
    
    def _on_order(self, event):
        """Record order event."""
        order_data = {
            'id': id(event),
            'timestamp': event.get_timestamp(),
            'symbol': event.get_symbol(),
            'order_id': event.get_order_id(),
            'direction': event.get_direction(),
            'quantity': event.get_quantity(),
            'price': event.get_price()
        }
        self.order_events.append(order_data)
        self.all_events.append(('ORDER', event.get_timestamp(), order_data))
        logger.debug(f"TRACE: Order event {event.get_symbol()} {event.get_direction()}")
    
    def _on_fill(self, event):
        """Record fill event."""
        fill_data = {
            'id': id(event),
            'timestamp': event.get_timestamp(),
            'symbol': event.get_symbol(),
            'order_id': event.get_order_id(),
            'direction': event.get_direction(),
            'quantity': event.get_quantity(),
            'price': event.get_price()
        }
        self.fill_events.append(fill_data)
        self.all_events.append(('FILL', event.get_timestamp(), fill_data))
        logger.debug(f"TRACE: Fill event {event.get_symbol()} {event.get_direction()}")
    
    def track_handler_call(self, event_type, component_name):
        """Track when a component handler is called."""
        key = f"{event_type}:{component_name}"
        self.handlers_called[key] = self.handlers_called.get(key, 0) + 1
    
    def print_summary(self):
        """Print summary of event flow."""
        print("\nEvent Flow Summary:")
        print(f"  Bar events: {len(self.bar_events)}")
        print(f"  Signal events: {len(self.signal_events)}")
        print(f"  Order events: {len(self.order_events)}")
        print(f"  Fill events: {len(self.fill_events)}")
        
        # Check for expected counts
        signal_count = len(self.signal_events)
        order_count = len(self.order_events)
        fill_count = len(self.fill_events)
        
        print("\nSignal to Order to Fill Ratios:")
        if signal_count > 0:
            print(f"  Orders per signal: {order_count / signal_count:.2f}")
        if order_count > 0:
            print(f"  Fills per order: {fill_count / order_count:.2f}")
        
        # Check for signals by type
        buy_signals = len([s for s in self.signal_events if s['signal_value'] > 0])
        sell_signals = len([s for s in self.signal_events if s['signal_value'] < 0])
        print(f"\nSignal breakdown:")
        print(f"  BUY signals: {buy_signals}")
        print(f"  SELL signals: {sell_signals}")
        
        # Check handler calls
        print("\nHandler call counts:")
        for key, count in sorted(self.handlers_called.items()):
            print(f"  {key}: {count}")
    
    def analyze_duplicates(self):
        """Analyze event flow for duplicates."""
        # Check for duplicate signals
        symbols = set(s['symbol'] for s in self.signal_events)
        duplicates = []
        
        for symbol in symbols:
            symbol_signals = [s for s in self.signal_events if s['symbol'] == symbol]
            symbol_signals.sort(key=lambda x: x['timestamp'])
            
            # Check for signals close in time
            for i in range(len(symbol_signals) - 1):
                s1 = symbol_signals[i]
                s2 = symbol_signals[i + 1]
                
                # Check if signals are close in time and same direction
                time_diff = (s2['timestamp'] - s1['timestamp']).total_seconds()
                if time_diff < 0.01 and s1['signal_value'] == s2['signal_value']:
                    duplicates.append((s1, s2, time_diff))
        
        if duplicates:
            print(f"\nFound {len(duplicates)} potential duplicate signals:")
            for s1, s2, time_diff in duplicates[:5]:
                print(f"  {s1['symbol']} value={s1['signal_value']}, time diff: {time_diff*1000:.2f}ms")
        else:
            print("\nNo duplicate signals found - FIX SUCCESSFUL!")

# Simple test strategy with event tracking
class TestStrategy:
    """Simple moving average strategy with event tracking."""
    
    def __init__(self, event_bus, data_handler, tracer, name=None, parameters=None):
        self.event_bus = event_bus
        self.data_handler = data_handler
        self.tracer = tracer
        self.name = name or "test_strategy"
        self.parameters = parameters or {}
        
        # Default parameters
        self.fast_window = self.parameters.get('fast_window', 5)  # Use small window for more signals
        self.slow_window = self.parameters.get('slow_window', 20)
        self.symbols = self.parameters.get('symbols', [])
        
        # State
        self.data = {symbol: [] for symbol in self.symbols}
        self.signal_count = 0
        
        # Register for bar events
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
    
    def configure(self, config=None):
        """Configure the strategy."""
        if config:
            if hasattr(config, 'as_dict'):
                self.parameters = config.as_dict()
            else:
                self.parameters = dict(config)
            
            self.fast_window = self.parameters.get('fast_window', 5)
            self.slow_window = self.parameters.get('slow_window', 20)
            self.symbols = self.parameters.get('symbols', [])
            
            # Reset data
            self.data = {symbol: [] for symbol in self.symbols}
    
    def on_bar(self, bar_event):
        """Handle bar events."""
        # Track that this handler was called
        self.tracer.track_handler_call('BAR', self.name)
        
        symbol = bar_event.get_symbol()
        if symbol not in self.symbols:
            return
        
        # Store bar data
        close_price = bar_event.get_close()
        timestamp = bar_event.get_timestamp()
        
        if symbol not in self.data:
            self.data[symbol] = []
            
        self.data[symbol].append({
            'timestamp': timestamp,
            'close': close_price
        })
        
        # Wait until we have enough data
        if len(self.data[symbol]) <= self.slow_window:
            return
        
        # Calculate moving averages
        closes = [bar['close'] for bar in self.data[symbol]]
        fast_ma = sum(closes[-self.fast_window:]) / self.fast_window
        slow_ma = sum(closes[-self.slow_window:]) / self.slow_window
        
        # Check for crossover
        prev_fast_ma = sum(closes[-(self.fast_window+1):-1]) / self.fast_window
        prev_slow_ma = sum(closes[-(self.slow_window+1):-1]) / self.slow_window
        
        # Generate signal on crossover
        from src.core.events.event_utils import create_signal_event
        
        if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
            # Buy signal
            self.signal_count += 1
            signal = create_signal_event(
                signal_value=1,  # Buy
                price=close_price,
                symbol=symbol,
                timestamp=timestamp
            )
            logger.info(f"Strategy: BUY signal #{self.signal_count} for {symbol} at {close_price:.2f}")
            self.event_bus.emit(signal)
            
        elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
            # Sell signal
            self.signal_count += 1
            signal = create_signal_event(
                signal_value=-1,  # Sell
                price=close_price,
                symbol=symbol,
                timestamp=timestamp
            )
            logger.info(f"Strategy: SELL signal #{self.signal_count} for {symbol} at {close_price:.2f}")
            self.event_bus.emit(signal)
    
    def reset(self):
        """Reset strategy state."""
        self.data = {symbol: [] for symbol in self.symbols}
        self.signal_count = 0

class SimpleConfig:
    """Simple configuration class for testing."""
    
    def __init__(self, config_dict=None):
        self.config_dict = config_dict or {}
    
    def get_section(self, section_name):
        """Get a configuration section."""
        return SimpleSection(section_name, self.config_dict.get(section_name, {}))

class SimpleSection:
    """Simple configuration section."""
    
    def __init__(self, name, values=None):
        self.name = name
        self.values = values or {}
    
    def get(self, key, default=None):
        """Get a configuration value."""
        return self.values.get(key, default)
    
    def as_dict(self):
        """Get all values as a dictionary."""
        return dict(self.values)
    
    def get_section(self, name):
        """Get a nested configuration section."""
        value = self.values.get(name, {})
        if not isinstance(value, dict):
            value = {}
        return SimpleSection(f"{self.name}.{name}", value)
    
    def get_float(self, key, default=0.0):
        """Get a configuration value as a float."""
        value = self.get(key, default)
        return float(value)
    
    def get_int(self, key, default=0):
        """Get a configuration value as an int."""
        value = self.get(key, default)
        return int(value)

def create_test_data(data_dir='./test_data', num_days=30, frequency='1d'):
    """Create synthetic test data for verification."""
    os.makedirs(data_dir, exist_ok=True)
    
    symbols = ['AAPL', 'MSFT']
    end_date = datetime.datetime.now().date()
    start_date = end_date - datetime.timedelta(days=num_days)
    
    # Generate date range
    if frequency == '1d':
        dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
    else:
        # For intraday data
        dates = pd.date_range(start=start_date, end=end_date, freq='30min')
    
    np.random.seed(42)  # For reproducibility
    
    for symbol in symbols:
        # Create price data with forced crossovers
        base_price = 100.0 if symbol == 'AAPL' else 200.0
        prices = []
        
        # Create a sine wave pattern for predictable crossovers
        for i in range(len(dates)):
            t = i / len(dates)
            # Multiple frequency components to create crossovers
            sine_component = 15 * np.sin(t * 20 * np.pi) + 7 * np.sin(t * 5 * np.pi)
            # Add slight trend and noise
            price = base_price + sine_component + i * 0.01 + np.random.normal(0, 0.5)
            prices.append(max(price, 1.0))  # Ensure positive prices
        
        # Generate OHLCV data
        data = []
        for i, date in enumerate(dates):
            close = prices[i]
            high = close * (1 + abs(np.random.normal(0, 0.01)))
            low = close * (1 - abs(np.random.normal(0, 0.01)))
            open_price = low + (high - low) * np.random.random()
            volume = int(np.random.exponential(100000))
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(data)
        filename = os.path.join(data_dir, f"{symbol}_{frequency}.csv")
        df.to_csv(filename, index=False)
        logger.info(f"Created test data for {symbol} with {len(data)} bars")

def setup_verification_container(tracer):
    """Set up container with components for verification."""
    container = Container()
    
    # Create configuration
    config_dict = {
        'backtest': {
            'symbols': ['AAPL', 'MSFT'],
            'data_dir': './test_data',
            'timeframe': '1d',
            'initial_capital': 100000.0
        },
        'strategy': {
            'ma_crossover': {
                'fast_window': 5,
                'slow_window': 20,
                'symbols': ['AAPL', 'MSFT']
            }
        },
        'risk_manager': {
            'position_size': 100,
            'max_position_pct': 0.1
        }
    }
    config = SimpleConfig(config_dict)
    
    # Create and register basic components
    event_bus = EventBus()
    event_manager = EventManager(event_bus)
    
    container.register_instance("event_bus", event_bus)
    container.register_instance("event_manager", event_manager)
    container.register_instance("config", config)
    container.register_instance("tracer", tracer)
    
    # Set up data components
    bar_emitter = BarEmitter("bar_emitter", event_bus)
    bar_emitter.start()
    container.register_instance("bar_emitter", bar_emitter)
    
    data_source = CSVDataSource('./test_data')
    container.register_instance("data_source", data_source)
    
    data_handler = HistoricalDataHandler(data_source, bar_emitter)
    container.register_instance("data_handler", data_handler)
    
    # Create portfolio
    portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
    container.register_instance("portfolio", portfolio)
    
    # Create risk manager
    risk_manager = SimpleRiskManager(event_bus, portfolio)
    risk_manager.position_size = 100
    container.register_instance("risk_manager", risk_manager)
    
    # Create strategy
    strategy = TestStrategy(event_bus, data_handler, tracer, 
                          parameters=config.get_section('strategy').get_section('ma_crossover').as_dict())
    container.register_instance("strategy", strategy)
    
    # Create order registry
    order_registry = OrderRegistry(event_bus)
    container.register_instance("order_registry", order_registry)
    
    # Create broker
    broker = SimulatedBroker(event_bus, order_registry)
    container.register_instance("broker", broker)
    
    # Create order manager
    order_manager = OrderManager(event_bus, broker, order_registry)
    container.register_instance("order_manager", order_manager)
    
    # Create analytics
    calculator = PerformanceCalculator()
    container.register_instance("calculator", calculator)
    
    report_generator = ReportGenerator(calculator)
    container.register_instance("report_generator", report_generator)
    
    # Create backtest coordinator
    backtest = BacktestCoordinator(container, config)
    container.register_instance("backtest", backtest)
    
    return container

def run_verification_test():
    """Run verification test with fixed signal processing."""
    logger.info("Starting signal flow verification test")
    
    # Create test data
    create_test_data()
    
    # Create event tracer
    event_bus = EventBus()
    tracer = EventTracer(event_bus)
    
    # Set up container
    container = setup_verification_container(tracer)
    
    # Get the backtest coordinator
    backtest = container.get("backtest")
    
    # Set up and run backtest
    backtest.setup()
    results = backtest.run(
        symbols=['AAPL', 'MSFT'],
        start_date='2023-01-01',
        end_date='2023-01-31'
    )
    
    # Check results
    strategy = container.get("strategy")
    logger.info(f"Strategy created {strategy.signal_count} signals")
    
    # Get event flow summary
    tracer.print_summary()
    
    # Check for duplicated signals
    tracer.analyze_duplicates()
    
    # Print trade results
    trades = results.get('trades', [])
    print(f"\nTrade Results: {len(trades)} trades executed")
    
    if trades:
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losses = sum(1 for t in trades if t.get('pnl', 0) < 0)
        print(f"  Win/Loss: {wins}/{losses} ({wins/len(trades)*100:.1f}% win rate)")
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        print(f"  Total P&L: ${total_pnl:.2f}")
    
    return {
        'success': True,
        'expected_signals': strategy.signal_count,
        'actual_signals': len(tracer.signal_events),
        'orders': len(tracer.order_events),
        'fills': len(tracer.fill_events),
        'trades': len(trades)
    }

if __name__ == "__main__":
    try:
        results = run_verification_test()
        
        print("\n=== Signal Flow Verification Results ===")
        print(f"Expected signals: {results['expected_signals']}")
        print(f"Actual signals: {results['actual_signals']}")
        print(f"Orders created: {results['orders']}")
        print(f"Fills processed: {results['fills']}")
        print(f"Trades completed: {results['trades']}")
        
        # Check if fix was successful
        if results['expected_signals'] == results['actual_signals']:
            print("\nFIX SUCCESSFUL! Signal count matches expected count.")
        else:
            print("\nFIX INCOMPLETE. Signal count still doesn't match expected count.")
            
    except Exception as e:
        logger.error(f"Verification test failed: {e}", exc_info=True)
        print(f"Error: {e}")
