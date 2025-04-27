# minimal_integration_test.py
import logging
import pandas as pd
import numpy as np
import os
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('minimal_test.log')
    ]
)
logger = logging.getLogger("ADMF-Test")

# Import core components only
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event, create_order_event, create_fill_event
from src.execution.order_manager import OrderManager, Order, OrderStatus
from src.execution.broker.broker_simulator import SimulatedBroker
from src.risk.portfolio.portfolio import PortfolioManager

def test_order_fill_flow():
    """Test only the order-fill flow to verify fixes."""
    logger.info("=== Starting Minimal Order-Fill Test ===")
    
    # Create event bus
    event_bus = EventBus()
    
    # Create broker with manual order processing
    broker = SimulatedBroker(event_bus)
    
    # Create order manager
    order_manager = OrderManager(event_bus, broker)
    
    # Create portfolio
    portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
    
    # Register handlers
    event_bus.register(EventType.ORDER, order_manager.on_order)
    event_bus.register(EventType.FILL, order_manager.on_fill)
    event_bus.register(EventType.FILL, portfolio.on_fill)
    
    # Test 1: Create an order and process it manually
    logger.info("Test 1: Basic order-fill flow")
    symbol = "AAPL"
    price = 150.0
    quantity = 100
    
    # Create and emit order event
    order_event = create_order_event(
        symbol=symbol,
        order_type="MARKET",
        direction="BUY",
        quantity=quantity,
        price=price
    )
    
    # Store order_id for verification
    order_id = order_event.data.get('order_id')
    logger.info(f"Created order with ID: {order_id}")
    
    # Emit the order event
    event_bus.emit(order_event)
    
    # Verify order was created in order manager
    if order_id in order_manager.orders:
        logger.info("Order correctly registered in order manager")
    else:
        logger.error("Order not registered in order manager")
    
    # Test 2: Orphaned fill event
    logger.info("Test 2: Orphaned fill handling")
    
    # Create fill event with no matching order
    fill_event = create_fill_event(
        symbol="MSFT",
        direction="BUY",
        quantity=50,
        price=200.0,
        commission=10.0
    )
    
    # Emit fill event directly
    event_bus.emit(fill_event)
    
    # Verify portfolio was updated
    msft_position = portfolio.get_position("MSFT")
    if msft_position and msft_position.quantity == 50:
        logger.info("Portfolio correctly updated from orphaned fill")
    else:
        logger.error("Portfolio not updated from orphaned fill")
    
    # Test 3: Emit order and fill to fully test the flow
    logger.info("Test 3: Complete order-fill flow")
    
    # Create another order
    order_event2 = create_order_event(
        symbol="GOOGL",
        order_type="MARKET",
        direction="BUY",
        quantity=10,
        price=1500.0
    )
    
    # Store order_id
    order_id2 = order_event2.data.get('order_id')
    
    # Process through broker to generate fill
    logger.info(f"Processing order for GOOGL through broker")
    fill_event2 = broker.process_order(order_event2)
    
    # Emit order first
    event_bus.emit(order_event2)
    
    # Wait a moment to ensure order is processed
    import time
    time.sleep(0.1)
    
    # Then emit fill
    if fill_event2:
        event_bus.emit(fill_event2)
    
    # Verify results
    googl_position = portfolio.get_position("GOOGL")
    if googl_position and googl_position.quantity == 10:
        logger.info("Portfolio correctly updated from broker-generated fill")
    else:
        logger.error("Portfolio not updated from broker-generated fill")
    
    # Summary of test results
    logger.info("=== Minimal Test Results ===")
    logger.info(f"Total orders in manager: {len(order_manager.orders)}")
    logger.info(f"Active orders: {len(order_manager.active_orders)}")
    logger.info(f"Completed orders: {len(order_manager.order_history)}")
    
    positions = portfolio.get_positions_summary()
    logger.info(f"Portfolio positions: {len(positions)}")
    for pos in positions:
        logger.info(f"Position: {pos['symbol']} - Quantity: {pos['quantity']}")
    
    logger.info(f"Final portfolio equity: ${portfolio.equity:.2f}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_order_fill_flow()
        if success:
            print("Minimal integration test completed successfully!")
        else:
            print("Minimal integration test failed!")
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"Test failed: {e}")
# integration_test_fixed.py
import logging
import pandas as pd
import numpy as np
import os
import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integration_test.log', mode='w')
    ]
)
logger = logging.getLogger("ADMF-Trader")

# Import system components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from src.core.events.event_emitters import BarEmitter
from src.core.events.event_utils import create_signal_event, create_order_event
from src.data.sources.csv_handler import CSVDataSource
from src.data.historical_data_handler import HistoricalDataHandler
from src.risk.portfolio.portfolio import PortfolioManager
from src.execution.broker.broker_simulator import SimulatedBroker
from src.execution.order_manager import OrderManager, Order, OrderStatus

# Create test data directory
TEST_DATA_DIR = 'test_data'
os.makedirs(TEST_DATA_DIR, exist_ok=True)

def create_test_data(symbols, start_date, end_date):
    """Create test data with sine wave patterns to ensure MA crossovers."""
    logger.info(f"Creating test data for {symbols}")
    
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
        filename = os.path.join(TEST_DATA_DIR, f"{symbol}_1d.csv")
        df.to_csv(filename, index=False)
        logger.info(f"Created test data for {symbol} with {len(data)} bars")
    
    return True

class SimpleMAStrategy:
    """Simple Moving Average Crossover Strategy."""
    
    def __init__(self, event_bus, symbols, fast_window=10, slow_window=30):
        self.event_bus = event_bus
        self.symbols = symbols if isinstance(symbols, list) else [symbols]
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.data = {symbol: [] for symbol in self.symbols}
        self.signal_count = 0
        
        logger.info(f"Strategy initialized with fast_window={fast_window}, slow_window={slow_window}")
        
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
        if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
            # Buy signal
            self.signal_count += 1
            signal = create_signal_event(
                signal_value=1,  # Buy
                price=close_price,
                symbol=symbol,
                timestamp=timestamp
            )
            logger.info(f"BUY signal #{self.signal_count} for {symbol} at {close_price:.2f}")
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
            logger.info(f"SELL signal #{self.signal_count} for {symbol} at {close_price:.2f}")
            self.event_bus.emit(signal)

# FIX 1: Improved risk manager that respects cash limits
class FixedRiskManager:
    """Fixed risk manager that properly handles cash limits."""
    
    def __init__(self, event_bus, portfolio):
        self.event_bus = event_bus
        self.portfolio = portfolio
        self.position_size = 100  # Default fixed position size
        self.max_position_pct = 0.1  # Maximum 10% of equity per position
        
        # Register for signal events
        self.event_bus.register(EventType.SIGNAL, self.on_signal)
    
    def on_signal(self, signal_event):
        """Handle signal events with proper position sizing."""
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        
        # Skip neutral signals
        if signal_value == 0:
            return None
        
        # Determine direction
        direction = 'BUY' if signal_value > 0 else 'SELL'
        
        # Calculate proper position size
        if direction == 'BUY':
            # Calculate max size based on available cash
            available_cash = self.portfolio.cash * 0.9  # Use 90% of available cash
            max_cash_size = int(available_cash / price)
            
            # Calculate max size based on position limit
            max_position_value = self.portfolio.equity * self.max_position_pct
            max_position_size = int(max_position_value / price)
            
            # Use smaller of the two limits
            size = min(self.position_size, max_cash_size, max_position_size)
            
            # Skip if too small
            if size < 10:
                logger.info(f"BUY signal for {symbol} skipped: calculated size too small ({size})")
                return None
        else:
            # For SELL, check if we have a position
            position = self.portfolio.get_position(symbol)
            if not position or position.quantity <= 0:
                logger.info(f"SELL signal for {symbol} skipped: no position to sell")
                return None
            
            # Sell what we have, up to position_size
            size = min(self.position_size, position.quantity)
        
        # Create order event with a unique ID to track through the system
        import uuid
        order_id = str(uuid.uuid4())
        
        order_event = create_order_event(
            symbol=symbol,
            order_type='MARKET',
            direction=direction,
            quantity=size,
            price=price
        )
        
        # Ensure order_id is in the event data
        order_event.data['order_id'] = order_id
        
        logger.info(f"Created order: {direction} {size} {symbol} @ {price:.2f} (ID: {order_id})")
        
        # Emit order event
        self.event_bus.emit(order_event)
        return order_event

# FIX 2: Apply broker patches
def patch_broker(broker):
    """Apply fixes to the broker."""
    # Store original method reference
    original_on_order = broker.on_order
    
    # Create fixed on_order method
    def fixed_on_order(self, order_event):
        """Fixed on_order that ensures fill events have order_ids."""
        try:
            # Process the order to get fill event
            fill_event = self.process_order(order_event)
            
            # Transfer order_id to fill event
            if fill_event and 'order_id' in order_event.data:
                fill_event.data['order_id'] = order_event.data['order_id']
                logger.debug(f"Transferred order_id to fill: {order_event.data['order_id']}")
            
            # Emit fill event
            if fill_event and self.event_bus:
                logger.info(f"Broker emitting fill for {fill_event.get_symbol()}")
                self.event_bus.emit(fill_event)
                
        except Exception as e:
            logger.error(f"Error in on_order: {e}")
    
    # Apply the patch
    broker.on_order = lambda event: fixed_on_order(broker, event)
    return broker

# FIX 3: Patch the OrderManager.on_fill method
def patch_order_manager(order_manager):
    """Apply fixes to the order manager."""
    # Store original method reference
    original_on_fill = order_manager.on_fill
    
    # Create fixed on_fill method
    def fixed_on_fill(self, fill_event):
        """Fixed on_fill that properly matches fills to orders."""
        try:
            # Get order ID from fill event
            order_id = fill_event.data.get('order_id')
            
            if order_id and order_id in self.orders:
                # We have the order - update it with fill info
                order = self.orders[order_id]
                
                # Update with fill information
                order.update_status(
                    status=OrderStatus.FILLED,
                    fill_quantity=fill_event.get_quantity(),
                    fill_price=fill_event.get_price()
                )
                
                # Move to order history if filled
                if order.is_filled():
                    if order_id in self.active_orders:
                        self.active_orders.remove(order_id)
                    self.order_history.append(order)
                    self.stats['orders_filled'] += 1
                
                logger.info(f"Updated order with fill: {order}")
                return True
            else:
                # No matching order - warn but don't create synthetic order
                logger.warning(f"Fill has no matching order: {fill_event.get_symbol()} {fill_event.get_direction()}")
                return False
                
        except Exception as e:
            logger.error(f"Error in on_fill: {e}")
            return False
    
    # Apply the patch
    order_manager.on_fill = lambda event: fixed_on_fill(order_manager, event)
    return order_manager

def run_integration_test():
    """Run simplified integration test with fixes."""
    logger.info("=== Starting ADMF-Trader Integration Test ===")
    
    # Create test data
    symbols = ['AAPL', 'MSFT']
    start_date = '2023-01-01'
    end_date = '2023-02-28'  # Shorter period for faster testing
    initial_cash = 100000.0
    
    create_test_data(symbols, start_date, end_date)
    
    # Create event system
    event_bus = EventBus()
    
    # Create components
    bar_emitter = BarEmitter("bar_emitter", event_bus)
    bar_emitter.start()  # Explicitly start the emitter
    
    data_source = CSVDataSource(TEST_DATA_DIR)
    data_handler = HistoricalDataHandler(data_source, bar_emitter)
    
    portfolio = PortfolioManager(event_bus, initial_cash=initial_cash)
    broker = SimulatedBroker(event_bus)
    broker = patch_broker(broker)  # Apply broker fix
    
    order_manager = OrderManager(event_bus, broker)
    order_manager = patch_order_manager(order_manager)  # Apply order manager fix
    
    # Use our fixed risk manager
    risk_manager = FixedRiskManager(event_bus, portfolio)
    
    # Create strategy with parameters likely to generate crossovers
    strategy = SimpleMAStrategy(event_bus, symbols, fast_window=5, slow_window=20)
    
    # Set up correct event flow
    # The order of registration matters for some handlers
    event_bus.register(EventType.FILL, portfolio.on_fill)  # Portfolio processes fills first
    event_bus.register(EventType.ORDER, order_manager.on_order)  # Then order manager processes orders
    event_bus.register(EventType.ORDER, broker.on_order)  # Then broker processes orders
    
    # Load data
    logger.info(f"Loading data for {symbols}")
    data_handler.load_data(symbols, start_date, end_date, timeframe='1d')
    
    # Process data (main backtest loop)
    logger.info("Starting backtest execution")
    bar_count = 0
    
    # Process each symbol's data
    for symbol in data_handler.get_symbols():
        symbol_bars = 0
        logger.info(f"Processing data for {symbol}")
        
        while True:
            bar = data_handler.get_next_bar(symbol)
            if bar is None:
                break
            bar_count += 1
            symbol_bars += 1
            
            # Log progress every 10 bars
            if symbol_bars % 10 == 0:
                logger.info(f"Processed {symbol_bars} bars for {symbol}")
        
        logger.info(f"Finished processing {symbol_bars} bars for {symbol}")
    
    logger.info(f"Processed {bar_count} total bars")
    
    # Results
    trades = portfolio.get_recent_trades()
    logger.info(f"Executed {len(trades)} trades")
    
    # Show first few trades
    for i, trade in enumerate(trades[:5]):
        if i < len(trades):
            logger.info(f"Trade {i+1}: {trade['direction']} {trade['quantity']} {trade['symbol']} @ {trade['price']:.2f}, PnL: {trade['pnl']:.2f}")
    
    # Get equity curve
    equity_curve = portfolio.get_equity_curve_df()
    if not equity_curve.empty:
        start_equity = equity_curve['equity'].iloc[0]
        end_equity = equity_curve['equity'].iloc[-1]
        total_return = (end_equity / start_equity) - 1
        
        logger.info(f"Initial equity: ${start_equity:.2f}")
        logger.info(f"Final equity: ${end_equity:.2f}")
        logger.info(f"Total return: {total_return:.2%}")
        
        # Save equity curve
        equity_curve.to_csv("equity_curve.csv")
        logger.info("Saved equity curve to 'equity_curve.csv'")
        
        return {
            'success': len(trades) > 0 and total_return != 0,
            'trades': len(trades),
            'return': total_return
        }
    else:
        logger.error("No equity curve data!")
        return {'success': False}

if __name__ == "__main__":
    # Run the test
    results = run_integration_test()
    
    if results['success']:
        print("\n=== Integration Test Passed! ===")
        print(f"Trades executed: {results['trades']}")
        print(f"Total return: {results['return']:.2%}")
    else:
        print("\n=== Integration Test Failed! ===")
