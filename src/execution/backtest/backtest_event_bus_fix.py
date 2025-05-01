"""
Patch module for BacktestCoordinator to ensure event bus is properly reset.

This module monkey patches the BacktestCoordinator.run method to explicitly reset
the event bus before each run, fixing the signal duplication issue.
"""
import logging
import functools
from src.execution.backtest.backtest import BacktestCoordinator

logger = logging.getLogger(__name__)

# Store reference to the original run method
original_run = BacktestCoordinator.run

@functools.wraps(original_run)
def patched_run(self, symbols=None, start_date=None, end_date=None, 
               initial_capital=100000.0, timeframe=None):
    """
    Patched run method with explicit event bus reset.
    
    This patched method explicitly resets the event bus before each run 
    to prevent rule_id processing state from persisting between runs.
    """
    # Reset the event bus first to clear processed rule_ids
    if hasattr(self, 'event_bus') and self.event_bus:
        logger.info("Explicitly resetting event bus before run")
        self.event_bus.reset()
        logger.info("Event bus reset complete")
    
    # Call the original run method
    return original_run(self, symbols, start_date, end_date, initial_capital, timeframe)

# Apply the monkey patch
logger.info("Applying patch to BacktestCoordinator.run")
BacktestCoordinator.run = patched_run
logger.info("BacktestCoordinator.run successfully patched to include explicit event bus reset")
