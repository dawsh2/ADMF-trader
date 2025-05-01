#!/usr/bin/env python3
"""
Simple test to verify the BacktestCoordinator event bus reset fix.

This script directly tests that the event bus reset is properly called at
the beginning of the BacktestCoordinator.run method.
"""
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def verify_event_bus_reset_fix():
    """Verify that the event bus reset fix is applied correctly."""
    try:
        # Import the BacktestCoordinator
        from src.execution.backtest.backtest import BacktestCoordinator
        from src.core.events.event_bus import EventBus
        
        # Create a coordinator instance
        coordinator = BacktestCoordinator()
        
        # Create a mock event bus with a reset method that we can track
        class MockEventBus(EventBus):
            def __init__(self):
                super().__init__()
                self.reset_called = 0
                
            def reset(self):
                self.reset_called += 1
                logger.info(f"EVENT BUS RESET called {self.reset_called} times")
                super().reset()
        
        # Set up the mock event bus
        event_bus = MockEventBus()
        coordinator.event_bus = event_bus
        
        # Run the coordinator with minimal parameters
        symbols = ['TEST']
        start_date = '2020-01-01'
        end_date = '2020-01-02'
        
        # Call the run method - this should trigger the reset
        logger.info("Calling coordinator.run()...")
        try:
            coordinator.run(symbols=symbols, start_date=start_date, end_date=end_date)
        except Exception as e:
            # We expect an error since we don't have all components set up
            # but the reset should still be called at the beginning
            logger.info(f"Expected error in run method: {e}")
        
        # Check if reset was called
        if event_bus.reset_called > 0:
            logger.info("SUCCESS: Event bus reset was called properly!")
            logger.info("The fix is successfully implemented.")
            return True
        else:
            logger.error("FAILURE: Event bus reset was NOT called!")
            logger.error("The fix is NOT properly implemented.")
            return False
            
    except Exception as e:
        logger.error(f"Error during verification: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("VERIFYING BACKTEST COORDINATOR EVENT BUS RESET FIX")
    logger.info("=" * 60)
    
    success = verify_event_bus_reset_fix()
    
    logger.info("=" * 60)
    if success:
        logger.info("EVENT BUS RESET FIX VERIFIED SUCCESSFULLY!")
        sys.exit(0)
    else:
        logger.info("EVENT BUS RESET FIX VERIFICATION FAILED!")
        sys.exit(1)
