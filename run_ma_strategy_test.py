#!/usr/bin/env python
"""
Focus test on just the MA Crossover strategy.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the current directory to the path
script_dir = os.path.abspath(os.path.dirname(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

def test_strategy():
    """Test only the MA Crossover strategy with more debugging."""
    from src.core.events.event_bus import EventBus
    from src.core.events.event_types import EventType, BarEvent
    from src.strategy.implementations.ma_crossover import MACrossoverStrategy
    
    # Create event bus
    event_bus = EventBus()
    
    # Create strategy
    parameters = {
        'fast_window': 2,
        'slow_window': 5,
        'price_key': 'close',
        'symbols': ['TEST']
    }
    
    logger.info(f"Creating strategy with parameters: {parameters}")
    strategy = MACrossoverStrategy(event_bus, None, parameters=parameters)
    
    # Check strategy object
    logger.info(f"Strategy object: {strategy}")
    logger.info(f"Strategy name: {strategy.name}")
    logger.info(f"Strategy symbols: {strategy.symbols}")
    
    # Verify fields are initialized
    logger.info(f"Strategy has data attribute: {hasattr(strategy, 'data')}")
    logger.info(f"Strategy has fast_ma attribute: {hasattr(strategy, 'fast_ma')}")
    logger.info(f"Strategy has slow_ma attribute: {hasattr(strategy, 'slow_ma')}")
    logger.info(f"Strategy has current_position attribute: {hasattr(strategy, 'current_position')}")
    
    # Show actual values
    logger.info(f"Strategy data: {strategy.data}")
    logger.info(f"Strategy fast_ma: {strategy.fast_ma}")
    logger.info(f"Strategy slow_ma: {strategy.slow_ma}")
    logger.info(f"Strategy current_position: {strategy.current_position}")
    
    logger.info("Resetting strategy...")
    
    # Try to reset the strategy
    strategy.reset()
    
    # Show values after reset
    logger.info(f"Strategy data after reset: {strategy.data}")
    logger.info(f"Strategy fast_ma after reset: {strategy.fast_ma}")
    logger.info(f"Strategy slow_ma after reset: {strategy.slow_ma}")
    logger.info(f"Strategy current_position after reset: {strategy.current_position}")
    
    # Check if TEST symbol exists in all dictionaries
    logger.info(f"'TEST' in data: {'TEST' in strategy.data}")
    logger.info(f"'TEST' in fast_ma: {'TEST' in strategy.fast_ma}")
    logger.info(f"'TEST' in slow_ma: {'TEST' in strategy.slow_ma}")
    logger.info(f"'TEST' in current_position: {'TEST' in strategy.current_position}")
    
    # Check what's in strategy_base.py reset method
    logger.info("Checking Strategy base class reset method...")
    import inspect
    from src.strategy.strategy_base import Strategy
    logger.info(inspect.getsource(Strategy.reset))
    
    return True

if __name__ == "__main__":
    test_strategy()
