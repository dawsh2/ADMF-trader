#!/usr/bin/env python
"""
Signal Flow Diagnostic for ADMF-Trader

This script diagnoses signal flow issues by:
1. Setting up a minimal environment
2. Tracing events through the system
3. Identifying duplicated signals
4. Validating event handling order
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
        logging.FileHandler('signal_diagnostic.log', mode='w')
    ]
)
logger = logging.getLogger("ADMF-Diagnostic")

# Import system components (adjust imports as needed)
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
from src.core.events.event_utils import create_signal_event

class SignalDiagnosticTracer:
    """Traces signal-related events through the system."""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.bar_events = []
        self.signal_events = []
        self.order_events = []
        self.fill_events = []
        self.state_change_events = []
        self.all_events = []
        self._register_handlers()
        
    def _register_handlers(self):
        """Register handlers for events."""
        # Register with highest priority to ensure we see events first
        self.event_bus.register(EventType.BAR, self._on_bar, priority=1000)
        self.event_bus.register(EventType.SIGNAL, self._on_signal, priority=1000)
        self.event_bus.register(EventType.ORDER, self._on_order, priority=1000)
        self.event_bus.register(EventType.FILL, self._on_fill, priority=1000)
        
        # If you have ORDER_STATE_CHANGE events
        if hasattr(EventType, 'ORDER_STATE_CHANGE'):
            self.event_bus.register(EventType.ORDER_STATE_CHANGE, 
                                 self._on_state_change, priority=1000)
        
    def _on_bar(self, event):
        """Record bar event."""
        self.bar_events.append({
            'id': id(event),
            'timestamp': event.timestamp,
            'symbol': event.data.get('symbol'),
            'close': event.data.get('close'),
            'handlers': []  # Will track which components handle this
        })
        self.all_events.append(('BAR', event.timestamp, id(event), event.data.get('symbol')))
        logger.debug(f"TRACER: Bar event id={id(event)} for {event.data.get('symbol')}")
        
    def _on_signal(self, event):
        """Record signal event."""
        signal_data = {
            'id': id(event),
            'timestamp': event.timestamp,
            'symbol': event.data.get('symbol'),
            'value': event.data.get('signal_value'),
            'price': event.data.get('price'),
            'handlers': [],
            'source_event': None  # Will try to trace which bar generated this
        }
        self.signal_events.append(signal_data)
        self.all_events.append(('SIGNAL', event.timestamp, id(event), 
                             f"{event.data.get('symbol')} val={event.data.get('signal_value')}"))
        
        logger.debug(f"TRACER: Signal event id={id(event)} for {event.data.get('symbol')} " 
                    f"value={event.data.get('signal_value')}")
        
    def _on_order(self, event):
        """Record order event."""
        order_data = {
            'id': id(event),
            'timestamp': event.timestamp,
            'order_id': event.data.get('order_id'),
            'symbol': event.data.get('symbol'),
            'direction': event.data.get('direction'),
            'quantity': event.data.get('quantity'),
            'price': event.data.get('price'),
            'handlers': [],
            'source_event': None  # Will try to trace which signal generated this
        }
        self.order_events.append(order_data)
        self.all_events.append(('ORDER', event.timestamp, id(event), 
                             f"{event.data.get('symbol')} {event.data.get('direction')}"))
        
        logger.debug(f"TRACER: Order event id={id(event)} for {event.data.get('symbol')} " 
                    f"direction={event.data.get('direction')}")
        
    def _on_fill(self, event):
        """Record fill event."""
        fill_data = {
            'id': id(event),
            'timestamp': event.timestamp,
            'order_id': event.data.get('order_id'),
            'symbol': event.data.get('symbol'),
            'direction': event.data.get('direction'),
            'quantity': event.data.get('quantity'),
            'price': event.data.get('price'),
            'handlers': [],
            'source_event': None  # Will try to trace which order generated this
        }
        self.fill_events.append(fill_data)
        self.all_events.append(('FILL', event.timestamp, id(event), 
                             f"{event.data.get('symbol')} {event.data.get('direction')}"))
        
        logger.debug(f"TRACER: Fill event id={id(event)} for {event.data.get('symbol')} " 
                    f"direction={event.data.get('direction')}")
        
    def _on_state_change(self, event):
        """Record order state change event."""
        state_data = {
            'id': id(event),
            'timestamp': event.timestamp,
            'order_id': event.data.get('order_id'),
            'status': event.data.get('status'),
            'transition': event.data.get('transition'),
            'handlers': []
        }
        self.state_change_events.append(state_data)
        self.all_events.append(('STATE_CHANGE', event.timestamp, id(event), 
                             f"order={event.data.get('order_id')} status={event.data.get('status')}"))
        
        logger.debug(f"TRACER: State change event id={id(event)} for order {event.data.get('order_id')} " 
                    f"status={event.data.get('status')}")
    
    def track_handler(self, event_type, event_id, handler_name):
        """Track which component handled an event."""
        if event_type == EventType.BAR:
            for event in self.bar_events:
                if event['id'] == event_id:
                    event['handlers'].append(handler_name)
                    break
        elif event_type == EventType.SIGNAL:
            for event in self.signal_events:
                if event['id'] == event_id:
                    event['handlers'].append(handler_name)
                    break
        elif event_type == EventType.ORDER:
            for event in self.order_events:
                if event['id'] == event_id:
                    event['handlers'].append(handler_name)
                    break
        elif event_type == EventType.FILL:
            for event in self.fill_events:
                if event['id'] == event_id:
                    event['handlers'].append(handler_name)
                    break
        
    def print_event_sequence(self, limit=50):
        """Print the sequence of events."""
        print("\nEvent Sequence (first 50):")
        for i, (type_name, timestamp, event_id, desc) in enumerate(self.all_events[:limit]):
            print(f"  {i+1}. {type_name} at {timestamp} - {desc} (id={event_id})")
    
    def print_summary(self):
        """Print summary of events."""
        print("\nEvent Summary:")
        print(f"  Bar events: {len(self.bar_events)}")
        print(f"  Signal events: {len(self.signal_events)}")
        print(f"  Order events: {len(self.order_events)}")
        print(f"  Fill events: {len(self.fill_events)}")
        print(f"  State change events: {len(self.state_change_events)}")
        
        # Check for signals without handlers
        signals_without_handlers = [s for s in self.signal_events if not s['handlers']]
        if signals_without_handlers:
            print(f"\nWARNING: Found {len(signals_without_handlers)} signals without handlers!")
        
        # Check for duplicate signals
        symbols = set(s['symbol'] for s in self.signal_events)
        print("\nSignals per symbol:")
        for symbol in symbols:
            symbol_signals = [s for s in self.signal_events if s['symbol'] == symbol]
            buys = len([s for s in symbol_signals if s['value'] > 0])
            sells = len([s for s in symbol_signals if s['value'] < 0])
            print(f"  {symbol}: {len(symbol_signals)} total - {buys} buys, {sells} sells")
    
    def print_component_activity(self):
        """Print which components handled which events."""
        # Collect all handler names
        handlers = set()
        for events in [self.bar_events, self.signal_events, self.order_events, self.fill_events]:
            for event in events:
                handlers.update(event['handlers'])
        
        print("\nComponent Activity:")
        for handler in sorted(handlers):
            bars = sum(1 for e in self.bar_events if handler in e['handlers'])
            signals = sum(1 for e in self.signal_events if handler in e['handlers'])
            orders = sum(1 for e in self.order_events if handler in e['handlers'])
            fills = sum(1 for e in self.fill_events if handler in e['handlers'])
            print(f"  {handler}: {bars} bars, {signals} signals, {orders} orders, {fills} fills")

    def identify_duplicated_signals(self, tolerance_seconds=0.001):
        """Try to identify duplicated signals."""
        # Group signals by symbol and value
        duplicates = []
        for symbol in set(s['symbol'] for s in self.signal_events):
            symbol_signals = [s for s in self.signal_events if s['symbol'] == symbol]
            # Sort by timestamp
            symbol_signals.sort(key=lambda x: x['timestamp'])
            
            # Check for signals close in time
            for i in range(len(symbol_signals) - 1):
                for j in range(i + 1, len(symbol_signals)):
                    time_diff = abs((symbol_signals[j]['timestamp'] - 
                                   symbol_signals[i]['timestamp']).total_seconds())
                    if (time_diff < tolerance_seconds and 
                        symbol_signals[i]['value'] == symbol_signals[j]['value']):
                        duplicates.append((symbol_signals[i], symbol_signals[j], time_diff))
        
        if duplicates:
            print(f"\nFound {len(duplicates)} potential duplicated signals:")
            for orig, dup, time_diff in duplicates[:10]:  # Show first 10
                print(f"  {orig['symbol']} value={orig['value']} - " 
                     f"Time diff: {time_diff*1000:.2f}ms")
                print(f"    Original handlers: {orig['handlers']}")
                print(f"    Duplicate handlers: {dup['handlers']}")
        else:
            print("\nNo duplicated signals found.")
        
        return duplicates

# Simple MA Strategy with detailed logging
class DiagnosticMAStrategy:
    """Simple Moving Average Crossover Strategy with diagnostics."""
    
    def __init__(self, event_bus, data_handler, tracer, name=None, parameters=None):
        """Initialize the strategy."""
        self.event_bus = event_bus
        self.data_handler = data_handler
        self.tracer = tracer  # Diagnostic tracer
        self.name = name or "diagnostic_ma"
        self.parameters = parameters or {}
        
        # Default parameters
        self.fast_window = self.parameters.get('fast_window', 10)
        self.slow_window = self.parameters.get('slow_window', 30)
        self.symbols = self.parameters.get('symbols', [])
        
        # Internal state
        self.data = {symbol: [] for symbol in self.symbols}
        self.signal_count = 0
        self.configured = False
        self.expected_signals = 0  # Will calculate this
        
        logger.info(f"Diagnostic Strategy initialized with fast_window={self.fast_window}, "
                   f"slow_window={self.slow_window}")
        
        # Register for bar events
        if self.event_bus:
            # Use a wrapper method to track event handlers
            self.event_bus.register(EventType.BAR, self._on_bar_wrapper)
    
    def _on_bar_wrapper(self, event):
        """Wrapper to track which component handled the event."""
        self.tracer.track_handler(EventType.BAR, id(event), self.name)
        self.on_bar(event)
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        if hasattr(config, 'as_dict'):
            self.parameters = config.as_dict()
        else:
            self.parameters = dict(config)
            
        # Update parameters
        self.fast_window = self.parameters.get('fast_window', 10)
        self.slow_window = self.parameters.get('slow_window', 30)
        self.symbols = self.parameters.get('symbols', [])
        
        # Initialize data storage for each symbol
        self.data = {symbol: [] for symbol in self.symbols}
        
        self.configured = True
        logger.info(f"Diagnostic Strategy configured with parameters: {self.parameters}")
    
    def on_bar(self, bar_event):
        """Handle bar events with detailed diagnostics."""
        event_id = id(bar_event)
        symbol = bar_event.get_symbol()
        
        logger.debug(f"Strategy receiving bar event id={event_id} for {symbol}")
        
        if symbol not in self.symbols:
            logger.debug(f"Ignoring bar for {symbol} - not in tracked symbols {self.symbols}")
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
            logger.debug(f"Not enough data for {symbol}: {len(self.data[symbol])}/{self.slow_window}")
            return
        
        # Calculate moving averages
        closes = [bar['close'] for bar in self.data[symbol]]
        fast_ma = sum(closes[-self.fast_window:]) / self.fast_window
        slow_ma = sum(closes[-self.slow_window:]) / self.slow_window
        
        # Check for crossover
        prev_fast_ma = sum(closes[-(self.fast_window+1):-1]) / self.fast_window
        prev_slow_ma = sum(closes[-(self.slow_window+1):-1]) / self.slow_window
        
        logger.debug(f"MA Values for {symbol}: fast={fast_ma:.2f} slow={slow_ma:.2f} " 
                    f"prev_fast={prev_fast_ma:.2f} prev_slow={prev_slow_ma:.2f}")
        
        # Generate signal on crossover
        if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
            # Buy signal
            self.signal_count += 1
            logger.info(f"SIGNAL GENERATION: #{self.signal_count} BUY signal for {symbol} at {close_price:.2f}")
            
            signal = create_signal_event(
                signal_value=1,  # Buy
                price=close_price,
                symbol=symbol,
                timestamp=timestamp
            )
            
            logger.info(f"EMITTING SIGNAL: #{self.signal_count} ID={id(signal)}")
            # Store the originating bar event ID for tracing
            self.event_bus.emit(signal)
            
        elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
            # Sell signal
            self.signal_count += 1
            logger.info(f"SIGNAL GENERATION: #{self.signal_count} SELL signal for {symbol} at {close_price:.2f}")
            
            signal = create_signal_event(
                signal_value=-1,  # Sell
                price=close_price,
                symbol=symbol,
                timestamp=timestamp
            )
            
            logger.info(f"EMITTING SIGNAL: #{self.signal_count} ID={id(signal)}")
            self.event_bus.emit(signal)
    
    def analyze_signals(self):
        """Analyze expected vs actual signal count."""
        total_expected = 0
        
        # Calculate expected signals based on data and MA parameters
        for symbol, bars in self.data.items():
            if len(bars) <= self.slow_window:
                continue
                
            # Calculate MAs for each bar
            closes = [bar['close'] for bar in bars]
            crossovers = 0
            
            for i in range(self.slow_window, len(closes)):
                fast_ma = sum(closes[i-self.fast_window:i]) / self.fast_window
                slow_ma = sum(closes[i-self.slow_window:i]) / self.slow_window
                prev_fast_ma = sum(closes[i-self.fast_window-1:i-1]) / self.fast_window
                prev_slow_ma = sum(closes[i-self.slow_window-1:i-1]) / self.slow_window
                
                # Count crossovers
                if (prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma) or \
                   (prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma):
                    crossovers += 1
            
            logger.info(f"Analysis: Symbol {symbol} should have {crossovers} crossovers")
            total_expected += crossovers
        
        self.expected_signals = total_expected
        logger.info(f"Analysis: Expected total signals: {total_expected}, Actual: {self.signal_count}")
        return total_expected

# Create Simple Config
class SimpleConfig:
    """Simplified configuration for use in diagnostics."""
    
    def __init__(self, config_dict=None):
        self.config_dict = config_dict or {}
    
    def get_section(self, section_name):
        """Get a configuration section."""
        return SimpleSection(section_name, self.config_dict.get(section_name, {}))

class SimpleSection:
    """Simplified configuration section."""
    
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

def create_test_data(symbols, start_date, end_date, data_dir='./data'):
    """Create test data with sine wave patterns to ensure MA crossovers."""
    logger.info(f"Creating test data for {symbols}")
    
    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Convert dates to datetime objects if needed
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    # Generate date range
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
    
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
        filename = os.path.join(data_dir, f"{symbol}_1d.csv")
        df.to_csv(filename, index=False)
        logger.info(f"Created test data for {symbol} with {len(data)} bars")
    
    return True

def create_diagnostic_config():
    """Create configuration for the diagnostic run."""
    config_dict = {
        'backtest': {
            'initial_capital': 100000.0,
            'symbols': ['AAPL', 'MSFT'],
            'data_dir': './diagnostic_data',
            'timeframe': '1d',
        },
        'strategy': {
            'ma_crossover': {
                'fast_window': 5,  # Use fast window for more signals in test
                'slow_window': 20,
                'symbols': ['AAPL', 'MSFT'],
            }
        },
        'risk_manager': {
            'position_size': 100,
            'max_position_pct': 0.1,  # Max 10% of equity per position
        },
        'broker': {
            'slippage': 0.001,  # 0.1% slippage
            'commission': 0.001,  # 0.1% commission
        }
    }
    
    # Create SimpleConfig object
    return SimpleConfig(config_dict)

def setup_diagnostic_container(config, tracer):
    """Set up container specifically for signal flow diagnostics."""
    container = Container()
    
    # Register core components
    event_bus = EventBus()
    event_manager = EventManager(event_bus)
    
    container.register_instance('event_bus', event_bus)
    container.register_instance('event_manager', event_manager)
    container.register_instance('config', config)
    container.register_instance('tracer', tracer)
    
    # Register event emitters
    bar_emitter = BarEmitter("bar_emitter", event_bus)
    bar_emitter.start()  # Explicitly start the emitter
    container.register_instance('bar_emitter', bar_emitter)
    
    # Register data components
    data_source = CSVDataSource(config.get_section('backtest').get('data_dir', './diagnostic_data'))
    container.register_instance('data_source', data_source)
    
    data_handler = HistoricalDataHandler(data_source, bar_emitter)
    container.register_instance('data_handler', data_handler)
    
    # Register portfolio and risk management
    portfolio = PortfolioManager(
        event_bus, 
        initial_cash=config.get_section('backtest').get_float('initial_capital', 100000.0)
    )
    container.register_instance('portfolio', portfolio)
    
    risk_manager = SimpleRiskManager(
        event_bus,
        portfolio,
        name="simple_risk_manager"
    )
    risk_manager.position_size = config.get_section('risk_manager').get_int('position_size', 100)
    risk_manager.max_position_pct = config.get_section('risk_manager').get_float('max_position_pct', 0.1)
    container.register_instance('risk_manager', risk_manager)
    
    # Register specialized diagnostic strategy
    strategy_params = config.get_section('strategy').get_section('ma_crossover').as_dict()
    strategy = DiagnosticMAStrategy(event_bus, data_handler, tracer, name="diagnostic_ma", parameters=strategy_params)
    container.register_instance('strategy', strategy)
    
    # Create order registry
    order_registry = OrderRegistry(event_bus)
    container.register_instance('order_registry', order_registry)
    
    # Register execution components
    broker = SimulatedBroker(event_bus, order_registry)
    broker.slippage = config.get_section('broker').get_float('slippage', 0.0)
    broker.commission = config.get_section('broker').get_float('commission', 0.0)
    container.register_instance('broker', broker)
    
    # Create order manager
    order_manager = OrderManager(event_bus, broker, order_registry)
    container.register_instance('order_manager', order_manager)
    
    # Register analytics components
    calculator = PerformanceCalculator()
    container.register_instance('calculator', calculator)
    
    report_generator = ReportGenerator(calculator)
    container.register_instance('report_generator', report_generator)
    
    # Register backtest coordinator
    backtest = BacktestCoordinator(container, config)
    container.register_instance('backtest', backtest)
    
    # CRITICAL: Register components with event manager in CORRECT ORDER for diagnostics
    # 1. Tracer must see all events first
    event_manager.register_component('tracer', tracer, 
                                    [EventType.BAR, EventType.SIGNAL, EventType.ORDER, EventType.FILL])
    
    # 2. Data handler for bar events
    event_manager.register_component('data_handler', data_handler, [EventType.BAR])
    
    # 3. Strategy to generate signals from bars
    event_manager.register_component('strategy', strategy, [EventType.BAR]) 
    
    # 4. Risk manager to generate orders from signals
    event_manager.register_component('risk_manager', risk_manager, [EventType.SIGNAL])
    
    # 5. Order registry to track orders
    event_manager.register_component('order_registry', order_registry, 
                                    [EventType.ORDER, EventType.FILL])
    
    # 6. Order manager to process orders
    event_manager.register_component('order_manager', order_manager, 
                                    [EventType.ORDER, EventType.FILL])
    
    # 7. Broker processes orders
    event_manager.register_component('broker', broker, [EventType.ORDER])
    
    # 8. Portfolio processes fills last
    event_manager.register_component('portfolio', portfolio, [EventType.FILL])
    
    return container

def run_signal_diagnostics():
    """Run signal flow diagnostic test."""
    logger.info("=== Starting ADMF-Trader Signal Flow Diagnostic ===")
    
    # Create test data in separate directory for this test
    symbols = ['AAPL', 'MSFT']
    start_date = '2023-01-01'
    end_date = '2023-01-31'  # Shorter period for faster testing
    data_dir = './diagnostic_data'
    
    create_test_data(symbols, start_date, end_date, data_dir)
    
    # Create configuration
    config = create_diagnostic_config()
    
    # Create event bus and tracer
    event_bus = EventBus()
    tracer = SignalDiagnosticTracer(event_bus)
    
    # Set up container with all components
    container = setup_diagnostic_container(config, tracer)
    
    # Get components we need for diagnostics
    data_handler = container.get('data_handler')
    strategy = container.get('strategy')
    backtest = container.get('backtest')
    
    # Load data for symbols
    for symbol in symbols:
        data_handler.load_security_data(symbol, start_date, end_date)
    
    # First, analyze expected signals based on data
    expected_signals = strategy.analyze_signals()
    logger.info(f"DIAGNOSTIC: Expecting {expected_signals} signals based on data analysis")
    
    # Run the backtest
    logger.info("Starting diagnostic backtest...")
    results = backtest.run(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000.0,
        timeframe='1d'
    )
    
    # Print diagnostic information
    print("\n=== Signal Flow Diagnostic Results ===")
    print(f"Expected signals: {expected_signals}")
    print(f"Strategy signal count: {strategy.signal_count}")
    print(f"Tracer signal count: {len(tracer.signal_events)}")
    
    # Analyze events
    tracer.print_summary()
    tracer.print_component_activity()
    
    # Look for duplicated signals
    duplicates = tracer.identify_duplicated_signals()
    
    # Print sequence of events for detailed analysis
    tracer.print_event_sequence()
    
    # Report on key findings
    print("\n=== Key Diagnostic Findings ===")
    if strategy.signal_count != expected_signals:
        print(f"ISSUE: Strategy generated {strategy.signal_count} signals but expected {expected_signals}")
        
    if len(tracer.signal_events) != strategy.signal_count:
        print(f"ISSUE: Tracer recorded {len(tracer.signal_events)} signals but strategy reports {strategy.signal_count}")
    
    if duplicates:
        print(f"ISSUE: Found {len(duplicates)} duplicated signals")
        print("RECOMMENDATION: Check event processing order and duplicated event handlers")
    
    print("\nCheck signal_diagnostic.log for detailed event flow information")
    
    return {
        'success': True,
        'expected_signals': expected_signals,
        'actual_signals': strategy.signal_count,
        'traced_signals': len(tracer.signal_events),
        'duplicates': len(duplicates) if duplicates else 0
    }

if __name__ == "__main__":
    try:
        results = run_signal_diagnostics()
        
        if results and results.get('success'):
            print("\n=== Signal Flow Diagnostic Completed Successfully! ===")
            
            # Print key metrics
            print(f"\nExpected signals: {results.get('expected_signals')}")
            print(f"Actual signals: {results.get('actual_signals')}")
            print(f"Traced signals: {results.get('traced_signals')}")
            print(f"Duplicated signals: {results.get('duplicates')}")
            
            if results.get('duplicates') > 0:
                print("\nPROBLEM IDENTIFIED: Signal duplication detected!")
                print("Fix event handling order and remove duplicate event handlers.")
            elif results.get('expected_signals') != results.get('actual_signals'):
                print("\nPROBLEM IDENTIFIED: Signal count mismatch!")
                print("Check strategy implementation and event emission.")
            else:
                print("\nNo signal flow issues detected.")
        else:
            print("\n=== Signal Flow Diagnostic Failed! ===")
            print("See logs for details.")
    except Exception as e:
        logger.error(f"Diagnostic failed with error: {e}", exc_info=True)
        print(f"Error: {e}")
