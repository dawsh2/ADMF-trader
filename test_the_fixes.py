#!/usr/bin/env python
"""
Test the fixes that we've implemented.
"""
import os
import sys
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Make sure we're in the correct directory and add it to the path
script_dir = os.path.abspath(os.path.dirname(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

def test_event_bus():
    """Test the event bus with our fixes."""
    from src.core.events.event_bus import EventBus
    from src.core.events.event_types import EventType, Event
    
    # Create event bus
    event_bus = EventBus()
    
    # Create a tracking list
    events_received = []
    
    # Define handler
    def test_handler(event):
        logger.info(f"Received event: {event.get_type().name}")
        events_received.append(event)
        return "handler called"
    
    # Register handler
    event_bus.register(EventType.BAR, test_handler)
    
    # Verify registration
    assert event_bus.has_handlers(EventType.BAR)
    logger.info("Handler registration works!")
    
    # Create and emit an event
    event = Event(EventType.BAR, {"test": "data"})
    result = event_bus.emit(event)
    
    # Verify emission
    assert len(events_received) == 1
    assert events_received[0] == event
    logger.info("Event emission works!")
    
    return True

def test_create_order_event():
    """Test the create_order_event function with our fixes."""
    from src.core.events.event_utils import create_order_event
    
    # Create order event with the new parameter order
    order = create_order_event("BUY", 100, "TEST", "MARKET", 150.0)
    
    # Verify the order properties
    assert order.data.get("direction") == "BUY"
    assert order.data.get("quantity") == 100
    assert order.data.get("symbol") == "TEST"
    assert order.data.get("order_type") == "MARKET"
    assert order.data.get("price") == 150.0
    
    logger.info("Order creation works with the new parameter order!")
    
    return True

def test_strategy():
    """Test the MA Crossover strategy with our fixes."""
    from src.core.events.event_bus import EventBus
    from src.core.events.event_types import EventType, BarEvent
    from src.strategy.implementations.ma_crossover import MACrossoverStrategy
    import traceback
    
    try:
        # Create event bus
        event_bus = EventBus()
        
        # Create strategy
        parameters = {
            'fast_window': 2,
            'slow_window': 5,
            'price_key': 'close',
            'symbols': ['TEST']
        }
        
        strategy = MACrossoverStrategy(event_bus, None, parameters=parameters)
        
        # Verify strategy has the needed fields
        assert hasattr(strategy, 'data')
        assert hasattr(strategy, 'fast_ma')
        assert hasattr(strategy, 'slow_ma')
        assert hasattr(strategy, 'current_position')
        
        # Verify the fields are dictionaries
        assert isinstance(strategy.data, dict)
        assert isinstance(strategy.fast_ma, dict)
        assert isinstance(strategy.slow_ma, dict)
        assert isinstance(strategy.current_position, dict)
        
        logger.info("Strategy fields are properly initialized!")
        
        # Reset strategy 
        strategy.reset()
        
        # Verify data dictionary contains the TEST symbol
        assert 'TEST' in strategy.data, f"TEST not in strategy.data. Keys: {strategy.data.keys()}"
        assert isinstance(strategy.data['TEST'], list), f"data['TEST'] is not a list: {type(strategy.data['TEST'])}"
        
        logger.info("Strategy reset works correctly!")
        
        return True
    except Exception as e:
        logger.error(f"Error in test_strategy: {e}")
        logger.error(traceback.format_exc())
        return False

def test_portfolio():
    """Test the portfolio manager with our fixes."""
    from src.core.events.event_bus import EventBus
    from src.core.events.event_types import EventType, Event
    from src.risk.portfolio.portfolio import PortfolioManager
    
    # Create event bus
    event_bus = EventBus()
    
    # Create portfolio
    portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
    
    # Verify get_positions method exists
    assert callable(getattr(portfolio, 'get_positions', None))
    positions = portfolio.get_positions()
    assert isinstance(positions, dict)
    
    logger.info("Portfolio get_positions method works!")
    
    # Verify get_equity_curve method exists
    assert callable(getattr(portfolio, 'get_equity_curve', None))
    equity_curve = portfolio.get_equity_curve()
    assert isinstance(equity_curve, list)
    
    logger.info("Portfolio get_equity_curve method works!")
    
    return True

def main():
    """Run all tests."""
    logger.info("Running tests for our fixes...")
    
    # Run tests
    tests = [
        ("Event Bus", test_event_bus),
        ("Order Creation", test_create_order_event),
        ("MA Strategy", test_strategy),
        ("Portfolio Manager", test_portfolio)
    ]
    
    results = {}
    
    for name, test_func in tests:
        logger.info(f"Running test: {name}")
        start_time = time.time()
        
        try:
            result = test_func()
            success = bool(result)
        except Exception as e:
            logger.error(f"Error in test {name}: {e}")
            success = False
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"Test {name} {'PASSED' if success else 'FAILED'} in {duration:.4f} seconds")
        results[name] = success
    
    # Print summary
    logger.info("===== Test Results =====")
    all_passed = True
    for name, success in results.items():
        logger.info(f"{name}: {'✅ PASSED' if success else '❌ FAILED'}")
        if not success:
            all_passed = False
    
    logger.info("========================")
    
    if all_passed:
        logger.info("All tests passed! The fixes are working correctly.")
        return 0
    else:
        logger.error("Some tests failed. The fixes need more work.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
