#!/usr/bin/env python
"""
Implementation script to use the fixed BacktestCoordinator.

This script replaces the standard BacktestCoordinator with our fixed version
that addresses the division by zero error and improves equity tracking.
"""

import logging
import sys
import importlib
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

def apply_fixes():
    """Apply fixes by injecting our FixedBacktestCoordinator class."""
    
    try:
        # First, ensure the fixed file exists
        if not os.path.exists('fixed_backtest_coordinator.py'):
            logger.error("Fixed coordinator file not found. Run the script in the correct directory.")
            return False
            
        # Import the fixed coordinator class
        from fixed_backtest_coordinator import FixedBacktestCoordinator
        
        # Get the original module
        import src.execution.backtest.backtest_coordinator
        original_module = sys.modules['src.execution.backtest.backtest_coordinator']
        
        # Replace the BacktestCoordinator class with our fixed version
        logger.info("Replacing BacktestCoordinator with FixedBacktestCoordinator...")
        original_module.BacktestCoordinator = FixedBacktestCoordinator
        
        # Check if replacement was successful
        if original_module.BacktestCoordinator == FixedBacktestCoordinator:
            logger.info("✓ Successfully replaced BacktestCoordinator class.")
            return True
        else:
            logger.error("✗ Failed to replace BacktestCoordinator class.")
            return False
            
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def run_optimization():
    """Run the optimization with the fixed BacktestCoordinator."""
    
    try:
        # Import and run the main module
        import main
        
        # Set command line arguments to run optimization
        sys.argv = ['main.py', 'optimize', '--config', 'config/ma_crossover_optimization.yaml']
        
        # Run the main function
        logger.info("Running optimization with fixed BacktestCoordinator...")
        main.main()
        
        logger.info("✓ Optimization completed successfully with fixed BacktestCoordinator.")
        return True
    except Exception as e:
        logger.error(f"Error running optimization: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting PnL backtest with fixed coordinator...")
    
    if apply_fixes():
        run_optimization()
    else:
        logger.error("Failed to apply fixes. Aborting optimization.")
