#!/usr/bin/env python
"""
Debug script for strategy factory and strategy initialization.

This script helps diagnose issues with strategy discovery and initialization.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from src.strategy.strategy_factory import StrategyFactory

def debug_strategy_factory():
    """Debug the strategy factory."""
    # Define strategy directories
    strategy_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'strategy', 'implementations')
    ]
    
    # Create strategy factory
    factory = StrategyFactory(strategy_dirs)
    
    # Print debug info
    factory.print_debug_info()
    
    # Try to get strategy names
    strategy_names = factory.get_strategy_names()
    logger.info(f"Available strategies: {strategy_names}")
    
    # Try to create a strategy
    strategy_name = 'simple_ma_crossover'
    try:
        logger.info(f"Creating strategy '{strategy_name}'...")
        strategy = factory.create_strategy(
            strategy_name, 
            name='test_strategy',
            fast_period=10,
            slow_period=30,
            position_size=100
        )
        logger.info(f"Strategy created successfully: {strategy}")
        
        # Print strategy attributes
        logger.info(f"Strategy attributes:")
        logger.info(f"  fast_period: {strategy.fast_period}")
        logger.info(f"  slow_period: {strategy.slow_period}")
        logger.info(f"  position_size: {strategy.position_size}")
        logger.info(f"  is_strategy: {strategy.is_strategy}")
    except Exception as e:
        logger.error(f"Error creating strategy: {e}")

if __name__ == '__main__':
    debug_strategy_factory()
