#!/usr/bin/env python
"""
Run a very simple test of our fixes.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basics():
    """Test the very basics of our fixes."""
    # Import classes (this will fail if there are syntax errors)
    from src.core.events.event_bus import EventBus
    from src.core.events.event_types import Event, EventType
    from src.core.events.event_utils import create_order_event, create_signal_event
    from src.risk.portfolio.portfolio import PortfolioManager
    from src.strategy.implementations.ma_crossover import MACrossoverStrategy
    
    # Create instances
    event_bus = EventBus()
    
    # Test event bus has_handlers method
    assert hasattr(event_bus, 'has_handlers')
    
    # Test order creation
    order = create_order_event("BUY", 100, "TEST", "MARKET", 100.0)
    assert order.data.get('direction') == "BUY"
    
    # Test portfolio methods
    portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
    assert hasattr(portfolio, 'get_positions')
    assert hasattr(portfolio, 'get_equity_curve')
    
    # Test strategy methods
    params = {
        'fast_window': 2,
        'slow_window': 5,
        'price_key': 'close',
        'symbols': ['TEST']
    }
    strategy = MACrossoverStrategy(event_bus, None, parameters=params)
    strategy.reset()
    
    logger.info("All basic tests passed!")
    return True

if __name__ == "__main__":
    if test_basics():
        sys.exit(0)
    else:
        sys.exit(1)
