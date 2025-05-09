#!/usr/bin/env python3
"""
A simple script to run the MA Crossover strategy fixes
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("run_fix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('run_fix')

def main():
    """Run the MA Crossover symbol fixes"""
    logger.info("Starting MA Crossover strategy symbol fixes")
    
    try:
        # Import the fix functions
        from src.fix_strategy_symbols import fix_ma_crossover_strategy, force_config_symbols
        
        # Run the fixes
        fix_ma_crossover_strategy()
        config_path = force_config_symbols()
        
        logger.info("Fixes completed successfully")
        logger.info(f"Fixed configuration: {config_path}")
        
        # Print instructions for running the optimization
        print("\nFixes applied successfully!")
        print("\nTo run the optimization with the fixed configuration, use:")
        print(f"python main.py optimize --config {config_path}")
        
    except Exception as e:
        logger.error(f"Error running fixes: {e}")
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())