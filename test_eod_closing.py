#!/usr/bin/env python
"""
Test script for the enhanced BacktestCoordinator with EOD position closing.
"""

import logging
import os
from datetime import datetime, timedelta
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import core components
from src.core.component import Component
from src.core.events.event_bus import EventBus
from src.core.events.event import Event
from src.core.events.event_types import Event, EventType
from src.core.trade_repository import TradeRepository

# Import execution components
from src.execution.backtest.backtest_coordinator import BacktestCoordinator

# Import data handling components
from src.data.data_handler import DataHandler

# Import portfolio components
from src.risk.portfolio.portfolio import Portfolio
from src.risk.position_manager import PositionManager

# Mock components for testing
class MockDataHandler(Component):
    """Mock data handler for testing."""
    
    def __init__(self, name, data, start_date=None, end_date=None):
        super().__init__(name)
        self.data = data
        self.current_index = 0
        self.start_date = start_date
        self.end_date = end_date
        
    def initialize(self, context):
        super().initialize(context)
        self.event_bus = context.get('event_bus')
        logger.info(f"Initialized {self.name} with {len(self.data)} bars")
        
    def update(self):
        """Process the next bar."""
        if self.current_index >= len(self.data):
            logger.info("No more data to process")
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
            'volume': bar.get('volume', 0)
        }
        
        # Publish bar event
        self.event_bus.publish(Event(EventType.BAR, bar_data))
        logger.debug(f"Published bar for {bar['symbol']} at {bar['timestamp']}")
        
        # Increment index
        self.current_index += 1
        
        return True
        
    def get_current_timestamp(self):
        """Get the timestamp of the current bar."""
        if self.current_index > 0 and self.current_index <= len(self.data):
            return self.data.iloc[self.current_index-1]['timestamp']
        return datetime.now()
        
    def get_current_price(self, symbol):
        """Get the current price for a symbol."""
        if self.current_index > 0 and self.current_index <= len(self.data):
            bar = self.data.iloc[self.current_index-1]
            if bar['symbol'] == symbol:
                return bar['close']
        return 100.0  # Default price


class MockStrategy(Component):
    """Mock strategy for testing."""
    
    def __init__(self, name, config=None):
        super().__init__(name)
        self.config = config or {}
        self.symbols = self.config.get('symbols', ['SPY'])
        self.bars_processed = 0
        
    def initialize(self, context):
        super().initialize(context)
        self.event_bus = context.get('event_bus')
        
        # Subscribe to bar events
        self.event_bus.subscribe(EventType.BAR, self.on_bar)
        logger.info(f"Initialized {self.name} with symbols: {self.symbols}")
        
    def on_bar(self, event):
        """Process bar events."""
        # Get bar data
        bar_data = event.get_data()
        symbol = bar_data.get('symbol')
        
        # Only process bars for our symbols
        if symbol not in self.symbols:
            return
            
        # Generate a signal every 5 bars
        self.bars_processed += 1
        
        # Generate a signal every 3 bars (alternating buy/sell)
        if self.bars_processed % 3 == 0:
            direction = "LONG" if (self.bars_processed // 3) % 2 == 0 else "SHORT"
            
            # Create signal event
            signal_data = {
                'symbol': symbol,
                'direction': direction,
                'strength': 1.0,
                'timestamp': bar_data.get('timestamp'),
                'rule_id': f"test_rule_{self.bars_processed}"
            }
            
            # Publish signal event
            self.event_bus.publish(Event(EventType.SIGNAL, signal_data))
            logger.info(f"Generated {direction} signal for {symbol}")


class MockSignalProcessor(Component):
    """Mock signal processor for testing."""
    
    def __init__(self, name, config=None):
        super().__init__(name)
        self.config = config or {}
        
    def initialize(self, context):
        super().initialize(context)
        self.event_bus = context.get('event_bus')
        
        # Subscribe to signal events
        self.event_bus.subscribe(EventType.SIGNAL, self.on_signal)
        logger.info(f"Initialized {self.name}")
        
    def on_signal(self, event):
        """Process signal events and generate orders."""
        # Get signal data
        signal_data = event.get_data()
        symbol = signal_data.get('symbol')
        direction = signal_data.get('direction')
        
        # Convert signal to order
        order_direction = "BUY" if direction == "LONG" else "SELL"
        
        # Create order event
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
        self.event_bus.publish(Event(EventType.ORDER, order_data))
        logger.info(f"Generated {order_direction} order for {symbol}")


def generate_test_data(days=10, symbols=None):
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


def run_test():
    """Run the test for the BacktestCoordinator with EOD position closing."""
    # Generate test data
    symbols = ['SPY', 'AAPL']
    test_data = generate_test_data(days=5, symbols=symbols)
    
    # Create components
    event_bus = EventBus()
    data_handler = MockDataHandler('data_handler', test_data)
    strategy = MockStrategy('test_strategy', {'symbols': symbols})
    signal_processor = MockSignalProcessor('signal_processor')
    trade_repository = TradeRepository()
    
    # Create portfolio components
    position_manager = PositionManager('position_manager')
    portfolio = Portfolio('portfolio', {'initial_capital': 100000.0})
    
    # Create backtest configuration with EOD position closing
    config = {
        'close_positions_eod': True,
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
    }
    
    # Create backtest coordinator
    backtest = BacktestCoordinator('backtest', config)
    
    # Create shared context
    context = {
        'event_bus': event_bus,
        'trade_repository': trade_repository,
        'config': config
    }
    
    # Add components to backtest
    backtest.add_component('data_handler', data_handler)
    backtest.add_component('strategy', strategy)
    backtest.add_component('signal_processor', signal_processor)
    backtest.add_component('position_manager', position_manager)
    backtest.add_component('portfolio', portfolio)
    
    # Initialize backtest
    backtest.initialize(context)
    
    # Setup components
    backtest.setup()
    
    # Run backtest
    results = backtest.run()
    
    # Print results
    logger.info(f"Backtest completed with final capital: {results.get('final_capital', 0):.2f}")
    logger.info(f"Trades executed: {results.get('statistics', {}).get('trades_executed', 0)}")
    logger.info(f"Positions closed EOD: {backtest.stats.get('positions_closed_eod', 0)}")
    
    return results


if __name__ == "__main__":
    import uuid
    run_test()