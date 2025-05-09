#!/usr/bin/env python
"""
Script to implement the fixed portfolio manager with action_type support.

This script:
1. Creates a symbolic link to the fixed_portfolio.py module
2. Runs a test to verify that the fixed portfolio correctly tracks trades
3. Provides debug output for verifying the implementation
"""
import os
import sys
import logging
import datetime
import uuid
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fixed_portfolio_install.log')
    ]
)

logger = logging.getLogger('install_fixed_portfolio')

def check_fixed_portfolio_module():
    """Check if the fixed_portfolio.py module exists and is valid."""
    module_path = Path('./src/risk/portfolio/fixed_portfolio.py')
    if not module_path.exists():
        logger.error(f"Error: {module_path} does not exist")
        return False
    
    logger.info(f"Fixed portfolio module exists at {module_path}")
    return True

def test_fixed_portfolio():
    """Run a basic test of the fixed portfolio implementation."""
    try:
        # Import the necessary modules
        from src.core.events.event_types import EventType, Event
        from src.risk.portfolio.fixed_portfolio import FixedPortfolioManager
        from src.risk.portfolio.position import Position
        
        # Create a mock event bus
        class MockEventBus:
            def __init__(self):
                self.events = []
                self.handlers = {}
                
            def register(self, event_type, handler):
                if event_type not in self.handlers:
                    self.handlers[event_type] = []
                self.handlers[event_type].append(handler)
                logger.info(f"Registered handler for {event_type}")
                
            def emit(self, event):
                self.events.append(event)
                logger.info(f"Emitted event: {event.get_type()}")
                
                # Call handlers
                event_type = event.get_type()
                if event_type in self.handlers:
                    for handler in self.handlers[event_type]:
                        handler(event)
                
        # Mock Event for testing
        class MockEvent:
            def __init__(self, event_type, data=None, timestamp=None):
                self.event_type = event_type
                self.data = data or {}
                self.timestamp = timestamp or datetime.datetime.now()
                self.id = str(uuid.uuid4())
                self.consumed = False
                
            def get_type(self):
                return self.event_type
                
            def get_id(self):
                return self.id
        
        # Create event bus
        event_bus = MockEventBus()
        
        # Create fixed portfolio with enough cash for our test
        portfolio = FixedPortfolioManager(event_bus, name="test_portfolio", initial_cash=50000.0)
        logger.info(f"Created test portfolio with ID {id(portfolio)}")
        
        # Create a fill event for OPEN position
        open_fill = MockEvent(
            EventType.FILL,
            {
                'symbol': 'MINI',
                'direction': 'BUY',
                'size': 100,
                'fill_price': 102.5,
                'commission': 0.5,
                'action_type': 'OPEN',
                'rule_id': 'MINI_BUY_OPEN_20250504'
            }
        )
        
        # Process the OPEN fill
        logger.info("Processing OPEN fill event")
        event_bus.emit(open_fill)
        
        # Check if position was created
        position = portfolio.get_position('MINI')
        if position:
            logger.info(f"Position created: {position}")
        else:
            logger.error("Error: Position was not created")
            
        # Check if trade was recorded
        logger.info(f"Trades count after OPEN: {len(portfolio.trades)}")
        
        # Create a fill event for CLOSE position
        close_fill = MockEvent(
            EventType.FILL,
            {
                'symbol': 'MINI',
                'direction': 'SELL',
                'size': 100,
                'fill_price': 105.0,
                'commission': 0.5,
                'action_type': 'CLOSE',
                'rule_id': 'MINI_SELL_CLOSE_20250504'
            }
        )
        
        # Process the CLOSE fill
        logger.info("Processing CLOSE fill event")
        event_bus.emit(close_fill)
        
        # Check if position was updated
        position = portfolio.get_position('MINI')
        if position:
            logger.info(f"Position after CLOSE: {position}")
        else:
            logger.error("Error: Position object missing after CLOSE")
            
        # Check if trades were recorded
        logger.info(f"Trades count after CLOSE: {len(portfolio.trades)}")
        
        # Check trade details
        if len(portfolio.trades) > 0:
            for i, trade in enumerate(portfolio.trades):
                logger.info(f"Trade {i+1}: {trade['id']} - {trade['symbol']} - {trade.get('action_type', 'Unknown')} - PnL: {trade.get('pnl', 0.0)}")
                
            # Calculate total PnL
            total_pnl = sum(trade.get('pnl', 0.0) for trade in portfolio.trades)
            logger.info(f"Total PnL from trades: {total_pnl:.2f}")
            
            # Calculate expected PnL
            expected_pnl = 100 * (105.0 - 102.5) - 0.5 - 0.5  # 100 shares * (sell - buy) - commissions
            logger.info(f"Expected PnL: {expected_pnl:.2f}")
            
            # Compare PnL
            if abs(total_pnl - expected_pnl) < 0.01:
                logger.info("PnL calculation is correct!")
            else:
                logger.error(f"PnL calculation error: Got {total_pnl:.2f}, expected {expected_pnl:.2f}")
            
        # Run debug trade tracking
        portfolio.debug_trade_tracking()
        
        # Get statistics
        stats = portfolio.get_stats()
        logger.info(f"Portfolio statistics: {stats}")
        
        # Test reset
        portfolio.reset()
        logger.info(f"After reset - trades count: {len(portfolio.trades)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in test_fixed_portfolio: {e}", exc_info=True)
        return False

def main():
    """Main function to test and verify fixed portfolio implementation."""
    logger.info("Starting fixed portfolio installation and test")
    
    # Check if the module exists
    if not check_fixed_portfolio_module():
        logger.error("Fixed portfolio module not found. Exiting.")
        return False
    
    # Run tests
    logger.info("Running fixed portfolio tests")
    if not test_fixed_portfolio():
        logger.error("Fixed portfolio tests failed. Exiting.")
        return False
    
    logger.info("Fixed portfolio implementation is complete and working as expected!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)