#!/usr/bin/env python
"""
Simple test script to verify the EOD position closing functionality.
"""

import logging
import sys
from datetime import datetime, timedelta
import pandas as pd
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_test_data(days=3, symbols=None):
    """Generate test data with multiple days."""
    symbols = symbols or ['SPY']
    start_date = datetime(2023, 1, 1)
    data = []
    
    # Create data for each symbol
    for symbol in symbols:
        # Create data for each day
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            
            # Create multiple bars per day
            for hour in range(9, 16):  # 9 AM to 4 PM
                bar_time = current_date.replace(hour=hour)
                base_price = 100 + day * 2  # Price increases each day
                
                # Add some intraday variation
                open_price = base_price + (hour - 9) * 0.5
                high_price = open_price + 1.0
                low_price = open_price - 0.5
                close_price = open_price + 0.25
                
                # Add the bar
                data.append({
                    'symbol': symbol,
                    'timestamp': bar_time,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': 1000
                })
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    return df.sort_values('timestamp').reset_index(drop=True)

def save_test_data(df, filename='test_data.csv'):
    """Save test data to CSV."""
    os.makedirs('data/test_eod', exist_ok=True)
    file_path = f'data/test_eod/{filename}'
    df.to_csv(file_path, index=False)
    logger.info(f"Saved test data to {file_path}")
    return file_path

def create_test_config(symbols=None, file_path=None, close_positions_eod=True):
    """Create a test configuration."""
    config = {
        'backtest': {
            'close_positions_eod': close_positions_eod,
            'broker': {
                'slippage': {
                    'model': 'fixed',
                    'slippage_percent': 0.1
                },
                'commission': {
                    'commission_type': 'percentage',
                    'rate': 0.1,
                    'min_commission': 1.0
                }
            }
        },
        'data': {
            'source': 'csv',
            'file_path': file_path,
            'symbols': symbols or ['SPY']
        },
        'strategy': {
            'name': 'TestStrategy',
            'symbols': symbols or ['SPY'],
            'params': {
                'buy_every': 3  # Buy every 3 bars
            }
        }
    }
    
    # Save config to file
    os.makedirs('config/test_eod', exist_ok=True)
    config_path = 'config/test_eod/test_config.yaml'
    
    import yaml
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    logger.info(f"Saved test config to {config_path}")
    return config

def run_eod_closing_test():
    """Run a simple test to verify the EOD position closing functionality."""
    # Generate and save test data
    df = generate_test_data(days=3, symbols=['SPY'])
    file_path = save_test_data(df)
    
    # Create test config
    config = create_test_config(symbols=['SPY'], file_path=file_path)
    
    # Create a mock strategy class
    from src.core.component import Component
    from src.core.event_system.event_bus import EventBus
    from src.core.event_system.event import Event
    from src.core.event_system.event_types import EventType
    
    class TestStrategy(Component):
        """Test strategy that generates buy orders every few bars."""
        
        def __init__(self, name, config=None):
            super().__init__(name)
            self.config = config or {}
            self.symbols = self.config.get('symbols', ['SPY'])
            self.buy_every = self.config.get('params', {}).get('buy_every', 3)
            self.bars_processed = 0
            self.logger = logging.getLogger(f"{__name__}.{name}")
            
        def initialize(self, context):
            super().initialize(context)
            self.event_bus = context.get('event_bus')
            self.logger.info(f"Initialized with symbols: {self.symbols}, buy_every: {self.buy_every}")
            
            # Subscribe to bar events
            self.event_bus.subscribe(EventType.BAR, self.on_bar)
            
        def on_bar(self, event):
            """Process bar events."""
            # Get bar data
            bar_data = event.get_data()
            symbol = bar_data.get('symbol')
            
            # Only process bars for our symbols
            if symbol not in self.symbols:
                return
                
            # Generate a signal every N bars
            self.bars_processed += 1
            
            if self.bars_processed % self.buy_every == 0:
                # Create signal event
                signal_data = {
                    'symbol': symbol,
                    'direction': 'LONG',
                    'strength': 1.0,
                    'timestamp': bar_data.get('timestamp'),
                    'rule_id': f"test_rule_{self.bars_processed}"
                }
                
                # Publish signal event
                event = Event(EventType.SIGNAL, signal_data)
                self.event_bus.publish(event)
                self.logger.info(f"Generated LONG signal for {symbol}")
    
    # Import the components we need
    from src.core.event_system.event_bus import EventBus
    from src.core.trade_repository import TradeRepository
    from src.execution.backtest.backtest_coordinator import BacktestCoordinator
    from src.execution.broker.simulated_broker import SimulatedBroker
    from src.execution.broker.market_simulator import MarketSimulator
    
    # Create components
    event_bus = EventBus()
    trade_repository = TradeRepository()
    strategy = TestStrategy('test_strategy', config['strategy'])
    
    # Create a simple signal processor
    class SimpleSignalProcessor(Component):
        """Processes signals and generates orders."""
        
        def __init__(self, name):
            super().__init__(name)
            self.logger = logging.getLogger(f"{__name__}.{name}")
            
        def initialize(self, context):
            super().initialize(context)
            self.event_bus = context.get('event_bus')
            self.logger.info("Initialized")
            
            # Subscribe to signal events
            self.event_bus.subscribe(EventType.SIGNAL, self.on_signal)
            
        def on_signal(self, event):
            """Process signal events."""
            # Get signal data
            signal_data = event.get_data()
            symbol = signal_data.get('symbol')
            direction = signal_data.get('direction')
            
            # Convert signal to order
            order_direction = "BUY" if direction == "LONG" else "SELL"
            
            # Create order event
            import uuid
            order_data = {
                'id': f"order_{uuid.uuid4()}",
                'symbol': symbol,
                'order_type': 'MARKET',
                'direction': order_direction,
                'quantity': 100,  # Fixed quantity for testing
                'timestamp': signal_data.get('timestamp'),
                'status': 'CREATED',
                'rule_id': signal_data.get('rule_id')
            }
            
            # Publish order event
            order_event = Event(EventType.ORDER, order_data)
            self.event_bus.publish(order_event)
            self.logger.info(f"Generated {order_direction} order for {symbol}")
    
    # Create a simple data handler
    class SimpleDataHandler(Component):
        """Reads data from CSV and publishes bar events."""
        
        def __init__(self, name, config):
            super().__init__(name)
            self.config = config
            self.file_path = config.get('file_path')
            self.symbols = config.get('symbols', [])
            self.current_index = 0
            self.logger = logging.getLogger(f"{__name__}.{name}")
            
            # Load data
            self.data = pd.read_csv(self.file_path)
            
            # Convert timestamp to datetime
            self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
            
            # Filter for configured symbols
            if self.symbols:
                self.data = self.data[self.data['symbol'].isin(self.symbols)]
                
            # Sort by timestamp
            self.data = self.data.sort_values('timestamp').reset_index(drop=True)
            
        def initialize(self, context):
            super().initialize(context)
            self.event_bus = context.get('event_bus')
            self.logger.info(f"Initialized with {len(self.data)} bars for symbols: {self.symbols}")
            
        def update(self):
            """Process the next bar."""
            if self.current_index >= len(self.data):
                self.logger.info("No more data to process")
                return False
                
            # Get current bar
            bar = self.data.iloc[self.current_index]
            
            # Create bar event
            bar_data = {
                'symbol': bar['symbol'],
                'timestamp': bar['timestamp'],
                'open': bar['open'],
                'high': bar['high'],
                'low': bar['low'],
                'close': bar['close'],
                'volume': bar['volume']
            }
            
            # Publish bar event
            event = Event(EventType.BAR, bar_data)
            self.event_bus.publish(event)
            
            # Increment index
            self.current_index += 1
            
            return True
            
        def get_current_timestamp(self):
            """Get current timestamp."""
            if self.current_index > 0 and self.current_index <= len(self.data):
                return self.data.iloc[self.current_index - 1]['timestamp']
            return datetime.now()
            
        def get_current_price(self, symbol):
            """Get current price for a symbol."""
            if self.current_index > 0 and self.current_index <= len(self.data):
                recent_bars = self.data.iloc[:self.current_index]
                symbol_bars = recent_bars[recent_bars['symbol'] == symbol]
                if not symbol_bars.empty:
                    return symbol_bars.iloc[-1]['close']
            return 100.0  # Default price
    
    # Create simple portfolio and position manager
    from src.risk.portfolio.portfolio import Portfolio
    from src.risk.position_manager import PositionManager
    
    position_manager = PositionManager('position_manager')
    portfolio = Portfolio('portfolio', {'initial_capital': 100000.0})
    
    # Create context
    context = {
        'event_bus': event_bus,
        'trade_repository': trade_repository,
        'config': config['backtest']
    }
    
    # Create data handler
    data_handler = SimpleDataHandler('data_handler', config['data'])
    
    # Create signal processor
    signal_processor = SimpleSignalProcessor('signal_processor')
    
    # Create broker components
    market_simulator = MarketSimulator('market_simulator')
    broker = SimulatedBroker('broker', config['backtest']['broker'])
    
    # Create backtest coordinator
    backtest = BacktestCoordinator('backtest', config['backtest'])
    
    # Register components
    backtest.add_component('data_handler', data_handler)
    backtest.add_component('strategy', strategy)
    backtest.add_component('signal_processor', signal_processor)
    backtest.add_component('position_manager', position_manager)
    backtest.add_component('portfolio', portfolio)
    backtest.add_component('market_simulator', market_simulator)
    backtest.add_component('broker', broker)
    
    # Initialize and setup
    backtest.initialize(context)
    backtest.setup()
    
    # Create an event listener to track EOD closing orders
    class OrderTracker:
        def __init__(self):
            self.orders = []
            self.fills = []
            self.eod_closing_orders = []
            
        def on_order(self, event):
            order_data = event.get_data()
            self.orders.append(order_data)
            
            # Check if this is an EOD closing order
            if order_data.get('reason') == 'EOD_POSITION_CLOSE':
                self.eod_closing_orders.append(order_data)
                
        def on_fill(self, event):
            fill_data = event.get_data()
            self.fills.append(fill_data)
    
    # Create tracker
    tracker = OrderTracker()
    
    # Subscribe to events
    event_bus.subscribe(EventType.ORDER, tracker.on_order)
    event_bus.subscribe(EventType.FILL, tracker.on_fill)
    
    # Run backtest
    results = backtest.run()
    
    # Check for EOD closing orders
    logger.info(f"Total orders: {len(tracker.orders)}")
    logger.info(f"Fills: {len(tracker.fills)}")
    logger.info(f"EOD closing orders: {len(tracker.eod_closing_orders)}")
    
    # Verify EOD closing occurred
    if tracker.eod_closing_orders:
        logger.info("EOD position closing is working correctly!")
        logger.info(f"EOD orders: {tracker.eod_closing_orders}")
        return True
    else:
        logger.error("No EOD closing orders were found!")
        return False

if __name__ == "__main__":
    success = run_eod_closing_test()
    sys.exit(0 if success else 1)