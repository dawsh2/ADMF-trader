#!/usr/bin/env python
"""
Integration test for EOD position closing with broker integration.
"""

import logging
import unittest
from datetime import datetime, timedelta
import pandas as pd
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import core components
from src.core.component import Component
from src.core.event_system.event_bus import EventBus
from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType
from src.core.trade_repository import TradeRepository

# Import execution components
from src.execution.backtest.backtest_coordinator import BacktestCoordinator


class MockDataHandler(Component):
    """Mock data handler that can generate data across multiple days."""
    
    def __init__(self, name, data=None):
        super().__init__(name)
        self.data = data if data is not None else self.generate_data()
        self.current_index = 0
        
    def initialize(self, context):
        super().initialize(context)
        self.event_bus = context.get('event_bus')
        logger.info(f"Initialized {self.name} with {len(self.data)} bars")
        
    def generate_data(self, days=3, symbols=None):
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
        
    def update(self):
        """Process the next bar."""
        if self.current_index >= len(self.data):
            logger.info("No more data to process")
            return False
            
        # Get current bar
        row = self.data.iloc[self.current_index]
        
        # Create bar event
        bar_data = {
            'symbol': row['symbol'],
            'timestamp': row['timestamp'],
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row.get('volume', 0)
        }
        
        # Publish bar event
        self.event_bus.publish(Event(EventType.BAR, bar_data))
        logger.debug(f"Published bar for {row['symbol']} at {row['timestamp']}")
        
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


class MockStrategy(Component):
    """Mock strategy that generates positions on the first day."""
    
    def __init__(self, name):
        super().__init__(name)
        self.orders_generated = False
        
    def initialize(self, context):
        super().initialize(context)
        self.event_bus = context.get('event_bus')
        
        # Subscribe to bar events
        self.event_bus.subscribe(EventType.BAR, self.on_bar)
        
    def on_bar(self, event):
        """Process bar events."""
        # Only generate orders once
        if self.orders_generated:
            return
            
        # Get bar data
        bar_data = event.get_data()
        symbol = bar_data.get('symbol')
        timestamp = bar_data.get('timestamp')
        
        # Generate a long order
        order_data = {
            'id': f"order_{uuid.uuid4()}",
            'symbol': symbol,
            'order_type': 'MARKET',
            'direction': 'BUY',
            'quantity': 100,
            'timestamp': timestamp,
            'status': 'CREATED',
            'rule_id': 'test_rule'
        }
        
        # Publish order event
        self.event_bus.publish(Event(EventType.ORDER, order_data))
        logger.info(f"Generated BUY order for {symbol}")
        
        # Mark orders as generated
        self.orders_generated = True


class TestEodClosingIntegration(unittest.TestCase):
    """Integration test for EOD position closing with broker integration."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create event bus
        self.event_bus = EventBus()
        
        # Create trade repository
        self.trade_repository = TradeRepository()
        
        # Create context
        self.context = {
            'event_bus': self.event_bus,
            'trade_repository': self.trade_repository
        }
        
        # Track events for testing
        self.order_events = []
        self.fill_events = []
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.ORDER, self.capture_order_event)
        self.event_bus.subscribe(EventType.FILL, self.capture_fill_event)
        
    def capture_order_event(self, event):
        """Capture order events for testing."""
        self.order_events.append(event.get_data())
        
    def capture_fill_event(self, event):
        """Capture fill events for testing."""
        self.fill_events.append(event.get_data())
        
    def test_eod_closing_with_broker(self):
        """Test end-of-day position closing with broker integration."""
        # Create mock data handler
        data_handler = MockDataHandler('data_handler')
        
        # Create mock strategy
        strategy = MockStrategy('strategy')
        
        # Create mock portfolio and position manager
        class MockPositionManager(Component):
            """Mock position manager for testing."""
            
            def __init__(self, name):
                super().__init__(name)
                self.positions = {}
                
            def initialize(self, context):
                super().initialize(context)
                self.event_bus = context.get('event_bus')
                
                # Subscribe to fill events to track positions
                self.event_bus.subscribe(EventType.FILL, self.on_fill)
                
            def on_fill(self, event):
                """Process fill events to update positions."""
                fill_data = event.get_data()
                symbol = fill_data.get('symbol')
                direction = fill_data.get('direction')
                quantity = fill_data.get('quantity', 0)
                
                # Adjust quantity based on direction
                adjusted_quantity = quantity if direction == 'BUY' else -quantity
                
                # Update position
                if symbol not in self.positions:
                    self.positions[symbol] = {
                        'symbol': symbol,
                        'quantity': adjusted_quantity,
                        'average_price': fill_data.get('price', 0)
                    }
                else:
                    # Update existing position
                    current_quantity = self.positions[symbol]['quantity']
                    new_quantity = current_quantity + adjusted_quantity
                    
                    self.positions[symbol]['quantity'] = new_quantity
                    
                    # If position is closed, clean up
                    if new_quantity == 0:
                        del self.positions[symbol]
                
            def get_all_positions(self):
                """Get all current positions."""
                return self.positions
                
            def get_position(self, symbol):
                """Get position for a specific symbol."""
                return self.positions.get(symbol)
        
        class MockPortfolio(Component):
            """Mock portfolio for testing."""
            
            def __init__(self, name, position_manager):
                super().__init__(name)
                self.position_manager = position_manager
                self.initial_capital = 100000.0
                self.cash = self.initial_capital
                self.realized_pnl = 0.0
                
            def initialize(self, context):
                super().initialize(context)
                self.event_bus = context.get('event_bus')
                
                # Subscribe to fill events to track cash changes
                self.event_bus.subscribe(EventType.FILL, self.on_fill)
                
            def on_fill(self, event):
                """Process fill events to update cash."""
                fill_data = event.get_data()
                direction = fill_data.get('direction')
                quantity = fill_data.get('quantity', 0)
                price = fill_data.get('price', 0)
                commission = fill_data.get('commission', 0)
                
                # Calculate cash change
                trade_value = price * quantity
                
                # Adjust cash based on direction
                if direction == 'BUY':
                    self.cash -= trade_value
                else:  # SELL
                    self.cash += trade_value
                    
                # Subtract commission
                self.cash -= commission
                
            def get_position_manager(self):
                """Get the position manager."""
                return self.position_manager
                
            def get_capital(self):
                """Get current cash."""
                return self.cash
                
            def close_all_positions(self, reason=None):
                """Close all positions (delegated to position manager)."""
                positions = self.position_manager.get_all_positions()
                
                if not positions:
                    return
                    
                for symbol, position in positions.items():
                    # Create closing order with opposite direction
                    quantity = position.get('quantity', 0)
                    if quantity == 0:
                        continue
                        
                    direction = "SELL" if quantity > 0 else "BUY"
                    close_quantity = abs(quantity)
                    
                    # Create order event
                    close_order = {
                        'id': f"close_{symbol}_{uuid.uuid4()}",
                        'symbol': symbol,
                        'order_type': 'MARKET',
                        'direction': direction,
                        'quantity': close_quantity,
                        'timestamp': datetime.now(),
                        'status': 'CREATED',
                        'reason': reason or 'POSITION_CLOSE'
                    }
                    
                    # Publish order event
                    self.event_bus.publish(Event(EventType.ORDER, close_order))
        
        # Create position manager and portfolio
        position_manager = MockPositionManager('position_manager')
        portfolio = MockPortfolio('portfolio', position_manager)
        
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
        
        # Add components to backtest
        backtest.add_component('data_handler', data_handler)
        backtest.add_component('strategy', strategy)
        backtest.add_component('position_manager', position_manager)
        backtest.add_component('portfolio', portfolio)
        
        # Initialize backtest
        backtest.initialize(self.context)
        
        # Setup components
        backtest.setup()
        
        # Run backtest
        results = backtest.run()
        
        # Verify that EOD position closing events were generated
        # We should have at least one order for the initial position and one for the EOD closing
        self.assertGreaterEqual(len(self.order_events), 2, "Should have at least 2 orders (initial + EOD closing)")
        
        # Find EOD closing orders (marked with reason='EOD_POSITION_CLOSE')
        eod_orders = [o for o in self.order_events if o.get('reason') == 'EOD_POSITION_CLOSE']
        self.assertGreaterEqual(len(eod_orders), 1, "Should have at least one EOD closing order")
        
        # Check that the EOD closing order direction is opposite to the initial position
        initial_order = next(o for o in self.order_events if o.get('reason') != 'EOD_POSITION_CLOSE')
        eod_order = eod_orders[0]
        
        # Initial order is BUY, so EOD order should be SELL
        self.assertEqual(initial_order['direction'], 'BUY')
        self.assertEqual(eod_order['direction'], 'SELL')
        
        # Check that positions were closed at end of day (should have fill events for EOD orders)
        eod_fills = [f for f in self.fill_events if f.get('order_id') in [o.get('id') for o in eod_orders]]
        self.assertGreaterEqual(len(eod_fills), 1, "Should have at least one fill for EOD closing orders")
        
        # Verify that the EOD fill closes the correct quantity
        self.assertEqual(eod_fills[0]['quantity'], initial_order['quantity'])


if __name__ == "__main__":
    unittest.main()