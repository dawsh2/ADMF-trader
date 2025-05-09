#!/usr/bin/env python
"""
Debug the MA Crossover strategy test failure.
"""
import os
import sys
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the current directory to the path
script_dir = os.path.abspath(os.path.dirname(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

def debug_ma_strategy():
    """Detailed debugging of the MA Crossover strategy."""
    from src.core.events.event_bus import EventBus
    from src.core.events.event_types import EventType
    from src.strategy.implementations.ma_crossover import MACrossoverStrategy
    
    try:
        # Create event bus
        event_bus = EventBus()
        
        # Create strategy with explicit parameters
        parameters = {
            'fast_window': 2,
            'slow_window': 5,
            'price_key': 'close',
            'symbols': ['TEST']
        }
        
        logger.debug(f"Creating strategy with parameters: {parameters}")
        strategy = MACrossoverStrategy(event_bus, None, parameters=parameters)
        
        # Verify attribute existence
        logger.debug("Checking strategy attributes:")
        for attr in ['data', 'fast_ma', 'slow_ma', 'current_position']:
            exists = hasattr(strategy, attr)
            logger.debug(f"  Has '{attr}': {exists}")
            if exists:
                value = getattr(strategy, attr)
                logger.debug(f"  Value of '{attr}': {value}")
                logger.debug(f"  Type of '{attr}': {type(value)}")
        
        # Verify the symbols list
        logger.debug(f"Strategy symbols: {strategy.symbols}")
        
        # Try resetting the strategy
        logger.debug("Resetting strategy...")
        strategy.reset()
        
        # Verify attributes after reset
        logger.debug("Checking strategy attributes after reset:")
        for attr in ['data', 'fast_ma', 'slow_ma', 'current_position']:
            exists = hasattr(strategy, attr)
            logger.debug(f"  Has '{attr}': {exists}")
            if exists:
                value = getattr(strategy, attr)
                logger.debug(f"  Value of '{attr}': {value}")
                logger.debug(f"  Type of '{attr}': {type(value)}")
                
                if isinstance(value, dict):
                    logger.debug(f"  Keys in '{attr}': {value.keys()}")
                    for key in value:
                        logger.debug(f"    '{attr}[{key}]': {value[key]}")
        
        # Now run the key assertions from our test
        try:
            logger.debug("Running assertions...")
            assert hasattr(strategy, 'data'), "Missing 'data' attribute"
            assert hasattr(strategy, 'fast_ma'), "Missing 'fast_ma' attribute"
            assert hasattr(strategy, 'slow_ma'), "Missing 'slow_ma' attribute"
            assert hasattr(strategy, 'current_position'), "Missing 'current_position' attribute"
            
            assert isinstance(strategy.data, dict), "'data' is not a dictionary"
            assert isinstance(strategy.fast_ma, dict), "'fast_ma' is not a dictionary"
            assert isinstance(strategy.slow_ma, dict), "'slow_ma' is not a dictionary"
            assert isinstance(strategy.current_position, dict), "'current_position' is not a dictionary"
            
            logger.debug("All basic assertions passed")
            
            assert 'TEST' in strategy.data, "'TEST' key missing from 'data'"
            assert isinstance(strategy.data['TEST'], list), "'data['TEST']' is not a list"
            
            logger.debug("All assertions passed successfully")
        except AssertionError as e:
            logger.error(f"Assertion failed: {e}")
            raise
            
        return True
    except Exception as e:
        logger.error(f"Error in debug_ma_strategy: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = debug_ma_strategy()
    if success:
        logger.info("MA Strategy debugging completed successfully")
        sys.exit(0)
    else:
        logger.error("MA Strategy debugging failed")
        sys.exit(1)
