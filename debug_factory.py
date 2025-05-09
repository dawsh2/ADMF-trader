#!/usr/bin/env python
"""
Debug script to examine strategy factory and strategies in the ADMF-Trader system.
"""

import os
import sys
import logging

from src.core.system_bootstrap import Bootstrap

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    """Debug strategy factory."""
    logger.info("Starting strategy factory debug")
    
    # Bootstrap the system
    bootstrap = Bootstrap(config_files=["config/head_test.yaml"])
    
    try:
        # Set up the system
        container, config = bootstrap.setup()
        
        # Get the strategy factory
        strategy_factory = container.get("strategy_factory")
        if strategy_factory:
            logger.info(f"Strategy factory found: {strategy_factory}")
            
            # Get all registered strategy types
            if hasattr(strategy_factory, 'get_strategy_types'):
                strategy_types = strategy_factory.get_strategy_types()
                logger.info(f"Registered strategy types: {strategy_types}")
            else:
                logger.warning("Strategy factory does not have get_strategy_types method")
            
            # Try to create the strategy
            try:
                logger.info("Attempting to create 'simple_ma_crossover' strategy")
                strategy = strategy_factory.create_strategy("simple_ma_crossover", config)
                logger.info(f"Strategy created: {strategy}")
            except Exception as e:
                logger.error(f"Error creating strategy: {e}")
        else:
            logger.error("Strategy factory not found in container")
            
            # Try to get other objects from container
            for name in ["event_bus", "data_handler", "portfolio", "risk_manager"]:
                obj = container.get(name)
                logger.info(f"{name}: {obj}")
        
        # Get strategy config from config object
        strategies_config = config.get_section("strategies")
        if strategies_config:
            logger.info(f"Strategies in config: {strategies_config.keys()}")
            
            # Check if ma_crossover exists in config
            if "simple_ma_crossover" in strategies_config:
                logger.info(f"simple_ma_crossover config: {strategies_config.get('simple_ma_crossover')}")
                
                # Check if it's enabled
                if strategies_config.get("simple_ma_crossover").get("enabled", False):
                    logger.info("simple_ma_crossover is enabled")
                else:
                    logger.warning("simple_ma_crossover is disabled")
            else:
                logger.warning("simple_ma_crossover not found in config")
        else:
            logger.error("No strategies section in config")
        
    except Exception as e:
        logger.error(f"Debug failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
