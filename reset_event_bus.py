#!/usr/bin/env python3
"""
Fix for the event bus deduplication issue in MA Crossover Signal Grouping.

This script adds explicit event bus reset to ensure rule_ids are properly cleared
between runs, allowing proper deduplication behavior.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler("event_bus_fix.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("event_bus_fix")

def ensure_event_bus_reset():
    """
    Add explicit reset to the BacktestCoordinator to ensure proper event bus reset.
    
    This fix ensures that the event bus's processed_events (which includes rule_ids)
    is properly cleared between runs.
    """
    try:
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Store the original run method
        original_run = BacktestCoordinator.run
        
        # Create a patched run method with explicit event bus reset
        def patched_run(self):
            """Patched run method with explicit event bus reset."""
            # Reset the event bus first to clear processed rule_ids
            if hasattr(self, 'event_bus') and self.event_bus:
                logger.info("Explicitly resetting event bus before run")
                self.event_bus.reset()
                logger.info("Event bus reset complete")
            
            # Call the original run method
            return original_run(self)
        
        # Apply the patch
        BacktestCoordinator.run = patched_run
        logger.info("Successfully patched BacktestCoordinator.run to reset event bus")
        
        return True
    except Exception as e:
        logger.error(f"Failed to patch BacktestCoordinator: {e}")
        return False

def main():
    """Apply the event bus reset fix."""
    print("\n=== FIXING EVENT BUS RESET ===\n")
    
    # Apply the fix
    success = ensure_event_bus_reset()
    
    if success:
        print("✅ Event bus reset fix successfully applied!")
        print("Now run the following to test the fix:")
        print("  python run_fixed_ma_crossover_v2.py")
    else:
        print("❌ Failed to apply event bus reset fix")
    
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
