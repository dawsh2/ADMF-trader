# test_backtest_fixed.py
import logging
import pandas as pd
import numpy as np
import datetime
import os
import shutil  # For deleting directories
from src.core.events.event_bus import EventBus
from src.core.events.event_manager import EventManager
from src.core.events.event_emitters import BarEmitter
from src.data.sources.csv_handler import CSVDataSource
from src.data.historical_data_handler import HistoricalDataHandler
from src.risk.portfolio.portfolio import PortfolioManager
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event, create_order_event
from src.execution.broker.broker_simulator import SimulatedBroker
from src.execution.order_manager import OrderManager

# Set up logging - use DEBUG level for more details
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============= PATCHING CODE =============

def event_tracer(event_bus):
    """
    Add tracing to the event bus to see all events
    """
    original_emit = event_bus.emit
    original_register = event_bus.register
    
    # Include ALL possible event types
    from src.core.events.event_types import EventType
    event_count = {et.name: 0 for et in EventType}
    event_count['ALL'] = 0
    
    handlers = {}
    
    def traced_emit(event):
        event_type = event.get_type().name
        event_count['ALL'] += 1
        if event_type in event_count:
            event_count[event_type] += 1
        else:
            # Fallback for event types not in the dictionary
            event_count[event_type] = 1
            
        print(f"EVENT EMIT: {event_type} #{event_count[event_type]}")
        return original_emit(event)
    
    def traced_register(event_type, handler):
        handler_name = getattr(handler, '__name__', str(handler.__class__.__name__)) 
        if event_type.name not in handlers:
            handlers[event_type.name] = []
        handlers[event_type.name].append(handler_name)
        print(f"HANDLER REGISTERED: {event_type.name} -> {handler_name}")
        return original_register(event_type, handler)
    
    # Replace methods with traced versions
    event_bus.emit = traced_emit
    event_bus.register = traced_register
    
    # Function to print stats
    def print_stats():
        print("\nEVENT STATISTICS:")
        for event_type, count in sorted(event_count.items()):
            print(f"  {event_type}: {count}")
        
        print("\nREGISTERED HANDLERS:")
        for event_type, handler_list in sorted(handlers.items()):
            print(f"  {event_type}: {', '.join(handler_list)}")
    
    # Add stats method to event bus
    event_bus.print_tracer_stats = print_stats
    
    return event_bus

def patch_bar_emitter():
    """Patch BarEmitter to ensure it's running"""
    from src.core.events.event_emitters import BarEmitter
    
    # Save original methods
    original_emit = BarEmitter.emit
    original_start = BarEmitter.start
    
    def patched_start(self):
        """Patched start method that logs"""
        logger.info(f"Starting bar emitter {self.name}")
        self.running = True  # This is the critical line - ensure it's running
        return original_start(self)
    
    def patched_emit(self, event):
        """Patched emit method with logging"""
        if not self.running:
            logger.warning(f"Bar emitter {self.name} not running, cannot emit event")
            return False
            
        result = original_emit(self, event)
        if result:
            symbol = event.get_symbol() if hasattr(event, 'get_symbol') else "unknown"
            price = event.get_close() if hasattr(event, 'get_close') else "unknown"
            logger.debug(f"Bar emitter emitted event for {symbol}, price: {price}")
        return result
    
    # Apply patches
    BarEmitter.start = patched_start
    BarEmitter.emit = patched_emit
    
    logger.info("BarEmitter patched successfully")
    
    return True

# Add this function to test_backtest.py

def fix_event_type_issues():
    """Fix issues with Event types and methods"""
    from src.execution.order_manager import OrderManager
    from src.execution.broker.broker_simulator import SimulatedBroker
    from src.core.events.event_types import OrderEvent, Event
    
    # Save original methods
    original_on_order_manager = OrderManager.on_order
    original_on_order_broker = SimulatedBroker.on_order
    
    def patched_on_order_manager(self, order_event):
        """Patched on_order method that checks event type"""
        # Check if we have a proper OrderEvent
        if not isinstance(order_event, OrderEvent) and isinstance(order_event, Event):
            # This is a generic Event, likely with status update
            # Just log it and ignore instead of trying to process it
            if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
                if order_event.data.get('type') == 'STATUS':
                    logger.info(f"Received order status update: {order_event.data}")
                    return
            logger.warning(f"Received generic Event instead of OrderEvent: {order_event.data}")
            return
            
        # Process regular OrderEvent
        return original_on_order_manager(self, order_event)
    
    def patched_on_order_broker(self, order_event):
        """Patched on_order method that checks event type"""
        # Check if we have a proper OrderEvent
        if not isinstance(order_event, OrderEvent) and isinstance(order_event, Event):
            # This is a generic Event, likely with status update
            logger.warning(f"Broker received generic Event instead of OrderEvent: {order_event.data}")
            return
            
        # Process regular OrderEvent
        return original_on_order_broker(self, order_event)
    
    # Apply patches
    OrderManager.on_order = patched_on_order_manager
    SimulatedBroker.on_order = patched_on_order_broker
    
    logger.info("Event type handling patched successfully")

def patch_historical_data_handler():
    """Patch HistoricalDataHandler to fix date handling"""
    from src.data.historical_data_handler import HistoricalDataHandler
    from collections import deque
    import pandas as pd
    
    # Save original methods
    original_load_data = HistoricalDataHandler.load_data
    original_get_next_bar = HistoricalDataHandler.get_next_bar

    def patched_load_data(self, symbols, start_date=None, end_date=None, timeframe='1m'):
        """Patched load_data method with better date handling"""
        # Convert single symbol to list
        if isinstance(symbols, str):
            symbols = [symbols]

        # Convert string dates to datetime objects if needed
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)

        # Load data for each symbol
        for symbol in symbols:
            try:
                df = self.data_source.get_data(symbol, start_date, end_date, timeframe)
                if df.empty:
                    logger.warning(f"No data found for {symbol}")
                    continue

                # Ensure DataFrame has proper columns and types
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                if not all(col in df.columns for col in required_cols):
                    missing = [col for col in required_cols if col not in df.columns]
                    logger.warning(f"Symbol {symbol} missing columns: {missing}")
                    continue

                # Convert numeric columns to float
                for col in ['open', 'high', 'low', 'close']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # Convert volume to int - THIS LINE HAS THE ERROR
                if 'volume' in df.columns:
                    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)

                # Ensure index is a DatetimeIndex
                if 'date' in df.columns:
                    # Convert date column to datetime and set as index
                    logger.info(f"Converting date column to DatetimeIndex for {symbol}")
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                elif not isinstance(df.index, pd.DatetimeIndex):
                    logger.info(f"Converting index to DatetimeIndex for {symbol}")
                    df.index = pd.to_datetime(df.index)

                # Log date range
                if not df.empty:
                    logger.info(f"Date range for {symbol}: {df.index[0]} to {df.index[-1]}")

                # Store data
                self.data_frames[symbol] = df
                self.current_idx[symbol] = 0
                self.bars_history[symbol] = deque(maxlen=self.max_bars_history)

                logger.info(f"Loaded {len(df)} bars for {symbol}")

                # Log a sample of data
                if not df.empty:
                    logger.debug(f"Sample data for {symbol}:\n{df.head(1)}")
            except Exception as e:
                logger.error(f"Error loading data for {symbol}: {e}", exc_info=True)
                self.stats['errors'] += 1
    
    def patched_get_next_bar(self, symbol):
        """Patched get_next_bar to ensure events are created and emitted properly"""
        # Check if we have data for this symbol
        if symbol not in self.data_frames:
            logger.warning(f"No data loaded for symbol: {symbol}")
            return None
            
        df = self.data_frames[symbol]
        idx = self.current_idx[symbol]
        
        # Check if we've reached the end of the data
        if idx >= len(df):
            logger.debug(f"End of data reached for {symbol}")
            return None
            
        # Get the row
        row = df.iloc[idx]
        
        # Get timestamp from index (should be a DatetimeIndex)
        timestamp = df.index[idx]
        
        # Debug info for the first few bars
        if idx < 3 or idx % 50 == 0:
            logger.debug(f"Processing bar {idx} for {symbol}: timestamp={timestamp}, close={row['close']}")
        
        try:
            # Extract data from row
            open_price = float(row['open'])
            high_price = float(row['high'])
            low_price = float(row['low'])
            close_price = float(row['close'])
            volume = int(row['volume'])
            
            # Create bar event
            from src.core.events.event_utils import create_bar_event
            bar = create_bar_event(
                symbol=symbol,
                timestamp=timestamp,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume
            )
            
            # Store in history
            if symbol in self.bars_history:
                self.bars_history[symbol].append(bar)
            
            # Increment index
            self.current_idx[symbol] = idx + 1
            
            # Explicitly emit the bar event using the bar_emitter
            if self.bar_emitter is not None and hasattr(self.bar_emitter, 'emit'):
                if idx < 3 or idx % 50 == 0:
                    logger.debug(f"Emitting bar event for {symbol}, idx={idx}")
                self.bar_emitter.emit(bar)
                self.stats['bars_processed'] += 1
            else:
                logger.warning(f"Bar emitter not available or missing emit method")
                
            return bar
            
        except Exception as e:
            logger.error(f"Error creating bar event for {symbol} at index {idx}: {e}", exc_info=True)
            self.current_idx[symbol] = idx + 1
            self.stats['errors'] += 1
            return None
    
    # Apply patches
    HistoricalDataHandler.load_data = patched_load_data
    HistoricalDataHandler.get_next_bar = patched_get_next_bar
    
    logger.info("HistoricalDataHandler patched successfully")
    return True

def create_sample_data_with_dates(data_dir, symbols, start_date, end_date, random_seed=42):
    """Create sample OHLCV data with properly formatted dates."""
    os.makedirs(data_dir, exist_ok=True)
    
    np.random.seed(random_seed)
    
    # Ensure dates are datetime objects
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
    
    for symbol in symbols:
        # Create price data with forced crossovers
        prices = []
        base_price = 100.0
        
        # Create a simple sine wave pattern with noise to ensure crossovers
        periods = 6  # Number of complete cycles
        amplitude = 20  # Price movement range
        for i in range(len(dates)):
            # Sine wave component
            cycle = np.sin(i * periods * 2 * np.pi / len(dates))
            # Add some noise
            noise = np.random.normal(0, 0.01)
            # Calculate price
            price = base_price + amplitude * cycle + noise * base_price
            prices.append(price)
        
        # Generate OHLCV data
        data = []
        for i, date in enumerate(dates):
            close = prices[i]
            # Generate intraday volatility
            high = close * (1 + abs(np.random.normal(0, 0.005)))
            low = close * (1 - abs(np.random.normal(0, 0.005)))
            open_price = low + (high - low) * np.random.random()
            
            # Generate volume with occasional spikes
            volume = int(1000000 * (1 + abs(np.random.normal(0, 0.2))))
            
            data.append({
                'date': date.strftime('%Y-%m-%d'),  # Format date as string
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(data)
        
        # Log a sample of data to verify date format
        logger.info(f"Date sample for {symbol}: {df['date'].iloc[0]}")
        
        filename = os.path.join(data_dir, f"{symbol}_1d.csv")
        df.to_csv(filename, index=False)  # Important: don't use index
        logger.info(f"Created sample data for {symbol}: {filename} with {len(data)} bars")
    
    return dates[:len(data)]

def inject_synthetic_signals(event_bus):
    """Inject synthetic signals to test the pipeline"""
    from src.core.events.event_utils import create_signal_event
    import datetime
    
    # Create a buy signal for AAPL
    signal_event = create_signal_event(
        signal_value=1,  # Buy
        price=100.0, 
        symbol='AAPL',
        timestamp=datetime.datetime.now()
    )
    
    print("\nEmitting synthetic BUY signal for AAPL...")
    event_bus.emit(signal_event)
    
    # Create a sell signal for MSFT
    signal_event = create_signal_event(
        signal_value=-1,  # Sell
        price=200.0,
        symbol='MSFT',
        timestamp=datetime.datetime.now()
    )
    
    print("Emitting synthetic SELL signal for MSFT...\n")
    event_bus.emit(signal_event)
    
    return True

# Patch the SimulatedBroker to add more logging
original_process_order = SimulatedBroker.process_order

def enhanced_process_order(self, order_event):
    """Enhanced process_order with more logging."""
    logger.info(f"Broker processing order: {order_event.get_direction()} {order_event.get_quantity()} {order_event.get_symbol()} @ {order_event.get_price():.2f}")
    result = original_process_order(self, order_event)
    if result:
        logger.info(f"Order filled: {order_event.get_direction()} {order_event.get_quantity()} {order_event.get_symbol()} @ {result.get_price():.2f}")
    else:
        logger.warning(f"Order not filled: {order_event.get_direction()} {order_event.get_quantity()} {order_event.get_symbol()}")
    return result

# Apply the patch
SimulatedBroker.process_order = enhanced_process_order

class SimpleRiskManager:
    """Simple implementation of a risk manager with fixed position sizing."""
    
    def __init__(self, event_bus, portfolio_manager, name=None):
        """Initialize simple risk manager."""
        self.event_bus = event_bus
        self.portfolio_manager = portfolio_manager
        self.name = name or "simple_risk_manager"
        self.position_size = 100  # Default fixed position size
        self.orders_created = 0
        
        logger.info(f"Initializing SimpleRiskManager with position_size={self.position_size}")
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.SIGNAL, self.on_signal)
    
    def on_signal(self, signal_event):
        """
        Handle signal events and create orders.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            Order event or None
        """
        # Extract signal details
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        timestamp = signal_event.get_timestamp()
        
        logger.info(f"Risk manager received signal: {signal_value} for {symbol} at {price:.2f}")
        
        # Determine direction from signal
        if signal_value > 0:
            direction = 'BUY'
        elif signal_value < 0:
            direction = 'SELL'
        else:
            # Neutral signal, no action
            logger.info(f"Neutral signal for {symbol}, no order created")
            return None
        
        # Calculate position size
        size = self.size_position(signal_event)
        
        logger.info(f"Calculated position size: {size} for {symbol}")
        
        # Skip if size is zero
        if size == 0:
            logger.info(f"Signal for {symbol} resulted in zero size, skipping")
            return None
        
        # Create order event
        order = create_order_event(
            symbol=symbol,
            order_type='MARKET',  # Default to market orders
            direction=direction,
            quantity=abs(size),  # Quantity is always positive
            price=price,
            timestamp=timestamp
        )
        
        # Emit order event
        if self.event_bus:
            self.event_bus.emit(order)
            self.orders_created += 1
            logger.info(f"Order #{self.orders_created} emitted: {direction} {abs(size)} {symbol} @ {price:.2f}")
        
        return order
    
    def size_position(self, signal_event):
        """
        Calculate position size for a signal using fixed size.
        
        Args:
            signal_event: Signal event to size
            
        Returns:
            int: Position size (positive or negative)
        """
        signal_value = signal_event.get_signal_value()
        
        # Apply direction to position size
        if signal_value > 0:
            return self.position_size
        elif signal_value < 0:
            return -self.position_size
        else:
            return 0
    
    def configure(self, config):
        """
        Configure the risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        # Extract parameters from config
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        # Set position size if provided
        if 'position_size' in config_dict:
            self.position_size = config_dict['position_size']

class SimpleMAStrategy:
    """Simple Moving Average Crossover Strategy."""
    
    def __init__(self, event_bus, symbols, fast_window=10, slow_window=30):
        self.event_bus = event_bus
        self.symbols = symbols if isinstance(symbols, list) else [symbols]
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.data = {symbol: [] for symbol in self.symbols}
        self.signal_count = 0
        
        logger.info(f"Initializing MA Strategy with fast={fast_window}, slow={slow_window}")
        
        # Register for bar events
        self.event_bus.register(EventType.BAR, self.on_bar)
    
    def on_bar(self, bar_event):
        """Handle bar events."""
        symbol = bar_event.get_symbol()
        if symbol not in self.symbols:
            return
        
        # Store bar data
        close_price = bar_event.get_close()
        timestamp = bar_event.get_timestamp()
        
        self.data[symbol].append({
            'timestamp': timestamp,
            'close': close_price
        })
        
        # Log every 25 bars
        bar_count = len(self.data[symbol])
        if bar_count % 25 == 0:
            logger.info(f"Processed {bar_count} bars for {symbol}, latest close: {close_price:.2f}")
        
        # Wait until we have enough data
        if bar_count < self.slow_window + 1:
            return
        
        # Calculate moving averages
        closes = [bar['close'] for bar in self.data[symbol]]
        fast_ma = sum(closes[-self.fast_window:]) / self.fast_window
        slow_ma = sum(closes[-self.slow_window:]) / self.slow_window
        
        # Check for crossover
        prev_fast_ma = sum(closes[-(self.fast_window+1):-1]) / self.fast_window
        prev_slow_ma = sum(closes[-(self.slow_window+1):-1]) / self.slow_window
        
        # Log MA values every 10 bars for debugging
        if bar_count % 10 == 0:
            logger.info(f"{symbol} MAs - Fast: {fast_ma:.2f}, Slow: {slow_ma:.2f}, Diff: {fast_ma-slow_ma:.2f}")
        
        # Generate signal on crossover
        if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
            # Buy signal
            signal = create_signal_event(
                signal_value=1,  # Buy
                price=close_price,
                symbol=symbol,
                timestamp=timestamp
            )
            self.event_bus.emit(signal)
            self.signal_count += 1
            logger.info(f"BUY signal #{self.signal_count} for {symbol} at {close_price:.2f} (Fast MA crossed above Slow MA)")
            
        elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
            # Sell signal
            signal = create_signal_event(
                signal_value=-1,  # Sell
                price=close_price,
                symbol=symbol,
                timestamp=timestamp
            )
            self.event_bus.emit(signal)
            self.signal_count += 1
            logger.info(f"SELL signal #{self.signal_count} for {symbol} at {close_price:.2f} (Fast MA crossed below Slow MA)")

def run_backtest(data_dir, symbols, start_date, end_date, initial_cash=100000.0, force_new_data=True, use_synthetic_signals=False):
    """Run a simple backtest."""
    # Force creation of new sample data if requested
    if force_new_data:
        logger.info("Forcing creation of new sample data")
        # Delete and recreate the data directory
        if os.path.exists(data_dir):
            # Delete all CSV files in the directory
            for file in os.listdir(data_dir):
                if file.endswith(".csv"):
                    os.remove(os.path.join(data_dir, file))
        
        # Create new sample data with proper dates
        create_sample_data_with_dates(data_dir, symbols, start_date, end_date)
    
    # Create components
    event_bus = EventBus()
    # Apply event tracing
    event_bus = event_tracer(event_bus)
    
    event_manager = EventManager(event_bus)
    
    # Create event emitter for bar events
    bar_emitter = BarEmitter("bar_emitter", event_bus)
    # Start the bar emitter explicitly
    bar_emitter.start()
    logger.info(f"Bar emitter running: {bar_emitter.running}")
    
    # Create data components
    data_source = CSVDataSource(data_dir)
    data_handler = HistoricalDataHandler(data_source, bar_emitter)
    
    # Create execution components
    portfolio = PortfolioManager(event_bus, initial_cash=initial_cash)
    broker = SimulatedBroker(event_bus)
    order_manager = OrderManager(event_bus, broker)
    
    # Create risk manager
    risk_manager = SimpleRiskManager(event_bus, portfolio)
    
    # Create strategy with faster moving averages to generate more signals
    # Use even faster MAs to ensure we get signals
    strategy = SimpleMAStrategy(event_bus, symbols, fast_window=5, slow_window=15)
    
    # Load data
    logger.info(f"Loading data for {symbols} from {start_date} to {end_date}")
    data_handler.load_data(symbols, start_date, end_date, timeframe='1d')
    
    if not data_handler.get_symbols():
        logger.error(f"No data loaded, check data directory: {data_dir}")
        return {'error': 'No data loaded'}
    
    # Register components with event manager
    event_manager.register_component('data_handler', data_handler)
    event_manager.register_component('portfolio', portfolio)
    event_manager.register_component('risk_manager', risk_manager)
    event_manager.register_component('broker', broker)
    event_manager.register_component('order_manager', order_manager)
    event_manager.register_component('strategy', strategy)
    
    # Optional: Inject synthetic signals to test pipeline
    if use_synthetic_signals:
        inject_synthetic_signals(event_bus)
    
    # Process all bars
    logger.info("Starting backtest")
    bar_count = 0
    
    # Process bar events for each symbol
    for symbol in data_handler.get_symbols():
        while True:
            bar = data_handler.get_next_bar(symbol)
            if bar is None:
                break
            bar_count += 1
                
    logger.info(f"Backtest complete, processed {bar_count} bars")
    
    # Print event stats
    event_bus.print_tracer_stats()
    
    # Get results
    equity_curve = portfolio.get_equity_curve_df()
    trades = portfolio.get_recent_trades()
    
    logger.info(f"Executed {len(trades)} trades")
    logger.info(f"Final equity: ${portfolio.equity:.2f}")
    
    return {
        'equity_curve': equity_curve,
        'trades': trades,
        'final_equity': portfolio.equity,
        'portfolio': portfolio
    }

def calculate_performance_metrics(equity_curve):
    """Calculate basic performance metrics."""
    if equity_curve.empty:
        return {}
    
    # Calculate returns
    equity_curve['returns'] = equity_curve['equity'].pct_change()
    
    # Calculate metrics
    total_return = (equity_curve['equity'].iloc[-1] / equity_curve['equity'].iloc[0]) - 1
    
    # Annualized metrics (assuming 252 trading days)
    trading_days = len(equity_curve)
    years = trading_days / 252
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    # Risk metrics
    daily_returns = equity_curve['returns'].dropna()
    volatility = daily_returns.std()
    annual_volatility = volatility * (252 ** 0.5)
    
    sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
    
    # Drawdown
    equity_curve['cum_max'] = equity_curve['equity'].cummax()
    equity_curve['drawdown'] = (equity_curve['cum_max'] - equity_curve['equity']) / equity_curve['cum_max']
    max_drawdown = equity_curve['drawdown'].max()
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'annual_volatility': annual_volatility,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'trading_days': trading_days
    }

if __name__ == "__main__":
    # Apply the patches
    patch_historical_data_handler()
    patch_bar_emitter()
    
    # Run backtest with sample data
    data_dir = 'data'
    start_date = '2022-01-01'
    end_date = '2022-12-31'
    symbols = ['AAPL', 'MSFT']
    
    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Force new data creation and run with synthetic signals
    # Set use_synthetic_signals=True to test the pipeline with synthetic signals
    def fix_status_event_handling():
        """Quick fix for status event handling"""
        from src.execution.order_manager import OrderManager
        from src.execution.broker.broker_simulator import SimulatedBroker

        # Save original methods
        original_on_order_mgr = OrderManager.on_order
        original_on_order_broker = SimulatedBroker.on_order

        # Create patched methods
        def safe_on_order_mgr(self, event):
            try:
                return original_on_order_mgr(self, event)
            except AttributeError as e:
                # Just log and ignore status update events
                logger.info(f"Ignoring non-standard order event: {e}")
                return False

        def safe_on_order_broker(self, event):
            try:
                return original_on_order_broker(self, event)
            except AttributeError as e:
                # Just log and ignore status update events
                logger.info(f"Broker ignoring non-standard order event: {e}")
                return False

        # Apply patches
        OrderManager.on_order = safe_on_order_mgr
        SimulatedBroker.on_order = safe_on_order_broker
        logger.info("Order handlers patched for safety")

    # Call the fix
    fix_status_event_handling()
    results = run_backtest(data_dir, symbols, start_date, end_date, force_new_data=True, use_synthetic_signals=False)
    
    # Print summary
    if 'error' in results:
        logger.error(results['error'])
    elif 'equity_curve' in results and not results['equity_curve'].empty:
        metrics = calculate_performance_metrics(results['equity_curve'])
        
        logger.info("\nPerformance Summary:")
        logger.info(f"Total Return: {metrics['total_return']:.2%}")
        logger.info(f"Annual Return: {metrics['annual_return']:.2%}")
        logger.info(f"Annual Volatility: {metrics['annual_volatility']:.2%}")
        logger.info(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        logger.info(f"Maximum Drawdown: {metrics['max_drawdown']:.2%}")
        logger.info(f"Trading Days: {metrics['trading_days']}")
        
        # Save equity curve to CSV for plotting
        if not results['equity_curve'].empty:
            results['equity_curve'].to_csv('equity_curve.csv')
            logger.info("Equity curve saved to 'equity_curve.csv'")
    else:
        logger.warning("No equity curve data available")
