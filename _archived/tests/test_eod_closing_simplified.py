#!/usr/bin/env python
"""
Simplified test for the EOD position closing feature.
"""

import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_eod_closing():
    """Test EOD position closing functionality."""
    # Import core components
    from src.core.component import Component
    from src.core.event_system.event_bus import EventBus  
    from src.core.event_system.event import Event
    from src.core.event_system.event_types import EventType
    from src.execution.backtest.backtest_coordinator import BacktestCoordinator
    
    # Create event bus
    event_bus = EventBus()
    
    # Create backtest coordinator with EOD position closing enabled
    config = {'close_positions_eod': True}
    backtest = BacktestCoordinator('test_backtest', config)
    
    # Initialize with minimal context
    context = {'event_bus': event_bus}
    backtest.initialize(context)
    
    # Verify EOD position closing is enabled
    assert backtest.close_positions_eod == True
    
    # Create a mock position manager
    class MockPositionManager(Component):
        def __init__(self, name):
            super().__init__(name)
            self.positions = {
                'SPY': {'symbol': 'SPY', 'quantity': 100}
            }
            
        def get_all_positions(self):
            return self.positions
            
        def initialize(self, context):
            super().initialize(context)
    
    # Create a mock portfolio
    class MockPortfolio(Component):
        def __init__(self, name):
            super().__init__(name)
            self.position_manager = MockPositionManager('position_manager')
            self.initial_capital = 100000.0
            
        def initialize(self, context):
            super().initialize(context)
            self.position_manager.initialize(context)
            
        def get_position_manager(self):
            return self.position_manager
            
        def get_capital(self):
            return 100000.0
    
    # Add portfolio to components
    portfolio = MockPortfolio('portfolio')
    backtest.add_component('portfolio', portfolio)
    
    # Track order events
    orders = []
    def capture_order(event):
        orders.append(event.get_data())
    
    event_bus.subscribe(EventType.ORDER, capture_order)
    
    # Manual test of _close_all_positions
    # We need to monkeypatch the Event constructor or modify the method for testing
    
    # Create a function to test day change detection
    day1 = datetime(2023, 1, 1)
    day2 = datetime(2023, 1, 2)
    
    # Set current day
    backtest.current_day = day1.date()
    
    # Verify _close_all_positions works
    # Create a test method to be called when _close_all_positions would be called
    close_positions_called = False
    
    original_method = backtest._close_all_positions
    
    def mock_close_positions(day):
        nonlocal close_positions_called
        close_positions_called = True
        assert day == day1.date()
    
    # Replace the method for testing
    backtest._close_all_positions = mock_close_positions
    
    # Create a bar event for day 2
    bar_data = {
        'symbol': 'SPY',
        'timestamp': day2,
        'open': 100,
        'high': 101,
        'low': 99,
        'close': 100.5
    }
    bar_event = Event(EventType.BAR, bar_data)
    
    # Process the event
    backtest.on_bar_eod_check(bar_event)
    
    # Check that _close_all_positions was called
    assert close_positions_called == True
    
    # Check that current day was updated
    assert backtest.current_day == day2.date()
    
    logger.info("EOD position closing test passed!")
    return True

if __name__ == "__main__":
    test_eod_closing()