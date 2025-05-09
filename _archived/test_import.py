#!/usr/bin/env python3
"""
Test importing from the optimization module
"""

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

def main():
    """Test importing the optimization module"""
    logger.info("Testing imports...")
    
    try:
        import importlib
        
        # Try to import the optimizer module
        logger.info("Trying to import src.strategy.optimization.optimizer...")
        optimizer_spec = importlib.util.find_spec('src.strategy.optimization.optimizer')
        
        if optimizer_spec is not None:
            logger.info("Module found!")
            
            # Try to load the module
            logger.info("Trying to load the module...")
            optimizer_module = importlib.import_module('src.strategy.optimization.optimizer')
            
            # Check if StrategyOptimizer exists
            logger.info("Checking if StrategyOptimizer exists...")
            if hasattr(optimizer_module, 'StrategyOptimizer'):
                logger.info("StrategyOptimizer found!")
                # Get the class
                optimizer_class = optimizer_module.StrategyOptimizer
                logger.info(f"StrategyOptimizer class: {optimizer_class}")
            else:
                logger.warning("StrategyOptimizer not found in module!")
                # List all attributes
                logger.info(f"Module attributes: {dir(optimizer_module)}")
        else:
            logger.warning("Module not found!")
    
    except Exception as e:
        logger.error(f"Error testing imports: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
