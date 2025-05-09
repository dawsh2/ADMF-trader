#!/usr/bin/env python
"""
Test the MA Crossover strategy to verify our fixes.
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# Set up path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the fixed strategy
from src.core.events.event_bus import EventBus
from src.core.events.event_types import Event, EventType, BarEvent
from src.strategy.implementations.ma_crossover import MACrossoverStrategy

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_strategy_initialization():
    """Test strategy initialization and properties."""
    event_bus = EventBus()
    parameters = {
        'fast_window': 5,
        'slow_window': 15,
        'price_key': 'close',
        'symbols': ['TEST']
    }
    
    strategy = MACrossoverStrategy(event_bus, None, parameters=parameters)
    
    assert strategy.name == "ma_crossover"
    assert strategy.fast_window == 5
    assert strategy.slow_window == 15
    assert strategy.price_key == 'close'
    assert 'TEST' in strategy.symbols
    assert hasattr(strategy, 'data')
    assert hasattr(strategy, 'fast_ma')
    assert hasattr(strategy, 'slow_ma')
    logger.info("✅ Strategy initialization test passed")

def test_strategy_reset():
    """Test strategy reset."""
    event_bus = EventBus()
    parameters = {
        'fast_window': 5,
        'slow_window': 15,
        'price_key': 'close',
        'symbols': ['TEST']
    }
    
    strategy = MACrossoverStrategy(event_bus, None, parameters=parameters)
    
    # Add some mock data
    strategy.data = {'TEST': [{'price': 100, 'timestamp': datetime.now()}]}
    strategy.fast_ma = {'TEST': [90, 95, 100]}
    strategy.slow_ma = {'TEST': [85, 90, 95]}
    
    # Reset the strategy
    strategy.reset()
    
    # Verify state was reset
    assert strategy.data == {'TEST': []}
    assert strategy.fast_ma == {'TEST': []}
    assert strategy.slow_ma == {'TEST': []}
    logger.info("✅ Strategy reset test passed")

def test_strategy_signal_generation():
    """Test signal generation by the strategy."""
    event_bus = EventBus()
    parameters = {
        'fast_window': 3,
        'slow_window': 5,
        'price_key': 'close',
        'symbols': ['TEST']
    }
    
    strategy = MACrossoverStrategy(event_bus, None, parameters=parameters)
    
    # Create a list to track signals
    signals = []
    
    def signal_handler(event):
        if event.get_type() == EventType.SIGNAL:
            signals.append(event)
    
    # Register signal handler
    event_bus.register(EventType.SIGNAL, signal_handler)
    
    # Create a series of bar events with increasing then decreasing prices
    base_time = datetime.now()
    
    # Uptrend to generate a buy signal
    prices = [10, 10, 12, 15, 18, 22, 25, 30]
    
    for i, price in enumerate(prices):
        bar = BarEvent(
            symbol='TEST',
            timestamp=base_time + timedelta(minutes=i),
            open_price=price - 0.5,
            high_price=price + 1,
            low_price=price - 1,
            close_price=price,
            volume=1000
        )
        strategy.on_bar(bar)
    
    # Check if buy signal was generated
    buy_signals = [s for s in signals if s.data.get('signal_value') == 1]
    assert len(buy_signals) > 0
    logger.info(f"Generated {len(buy_signals)} buy signals")
    
    # Downtrend to generate a sell signal
    prices = [30, 28, 25, 20, 15, 10]
    
    for i, price in enumerate(prices):
        bar = BarEvent(
            symbol='TEST',
            timestamp=base_time + timedelta(minutes=i+len(prices)),
            open_price=price - 0.5,
            high_price=price + 1,
            low_price=price - 1,
            close_price=price,
            volume=1000
        )
        strategy.on_bar(bar)
    
    # Check if sell signal was generated
    sell_signals = [s for s in signals if s.data.get('signal_value') == -1]
    assert len(sell_signals) > 0
    logger.info(f"Generated {len(sell_signals)} sell signals")
    
    logger.info("✅ Strategy signal generation test passed")

def main():
    """Run strategy tests."""
    logger.info("Running MA Crossover strategy tests...")
    
    test_strategy_initialization()
    test_strategy_reset()
    test_strategy_signal_generation()
    
    logger.info("All strategy tests passed! ✅")
    return 0

if __name__ == "__main__":
    sys.exit(main())
