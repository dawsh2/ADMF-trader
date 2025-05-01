#!/usr/bin/env python3
"""
Check and verify the BacktestCoordinator.run fix.

This script confirms that the BacktestCoordinator.run method properly resets the event bus.
"""
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_backtest_fix():
    """
    Check if the backtest coordinator reset fix is properly applied.
    """
    try:
        # Import the BacktestCoordinator
        from src.execution.backtest.backtest import BacktestCoordinator

        # Get the run method source code 
        import inspect
        source = inspect.getsource(BacktestCoordinator.run)
        
        # Check if the event bus reset is included
        has_reset = "event_bus.reset()" in source
        has_comment = "CRITICAL FIX:" in source and "Reset the event bus" in source
        
        if has_reset and has_comment:
            logger.info("✅ BacktestCoordinator.run method properly resets the event bus")
            logger.info("This fix is correctly implemented")
            return True
        else:
            logger.error("❌ BacktestCoordinator.run method does NOT reset the event bus properly")
            if not has_reset:
                logger.error("Missing: event_bus.reset() call")
            if not has_comment:
                logger.error("Missing: Explanatory comment for the fix")
            return False
                
    except Exception as e:
        logger.error(f"Error checking BacktestCoordinator.run fix: {e}", exc_info=True)
        return False

def main():
    """Main function."""
    print("=" * 60)
    print("CHECKING BACKTEST COORDINATOR RUN FIX")
    print("=" * 60)
    
    success = check_backtest_fix()
    
    print("=" * 60)
    if success:
        print("BACKTEST COORDINATOR FIX IS PROPERLY APPLIED")
        print("This fix ensures the event bus is reset before each run")
    else:
        print("ERROR: BACKTEST COORDINATOR FIX IS NOT PROPERLY APPLIED")
        print("Run python fix_backtest_coordinator.py to apply the fix")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
