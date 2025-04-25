# test_backtest.py
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

def create_sample_data(data_dir, symbols, start_date, end_date, random_seed=42):
    """Create sample OHLCV data with GUARANTEED moving average crossovers."""
    os.makedirs(data_dir, exist_ok=True)
    
    np.random.seed(random_seed)
    
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    dates = pd.date_range(start=start, end=end, freq='B')  # Business days
    
    for symbol in symbols:
        # Create price data with FORCED crossovers
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
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        # Create DataFrame with proper datetime index
        df = pd.DataFrame(data, index=dates[:len(data)])
        
        # Save to CSV
        filename = os.path.join(data_dir, f"{symbol}_1d.csv")
        df.to_csv(filename)
        logger.info(f"Created sample data for {symbol}: {filename} with {len(data)} bars")
    
    return dates[:len(data)]

def run_backtest(data_dir, symbols, start_date, end_date, initial_cash=100000.0, force_new_data=True):
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
        
        # Create new sample data
        create_sample_data(data_dir, symbols, start_date, end_date)
    
    # Create components
    event_bus = EventBus()
    event_manager = EventManager(event_bus)
    
    # Create event emitter for bar events
    bar_emitter = BarEmitter("bar_emitter", event_bus)
    
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
    # Run backtest with sample data
    data_dir = 'data'
    start_date = '2022-01-01'
    end_date = '2022-12-31'
    symbols = ['AAPL', 'MSFT']
    
    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Force new data creation
    results = run_backtest(data_dir, symbols, start_date, end_date, force_new_data=True)
    
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
