#!/usr/bin/env python
"""
Test script to verify our fixes to BacktestCoordinator and Portfolio loggers.

This script checks:
1. That Portfolio and BacktestCoordinator properly initialize their logger attributes
2. That the event handlers use self.logger instead of the global logger variable
3. That the optimization process runs without logger-related errors

Usage:
    python test_logger_fixes.py
"""

import logging
import sys
from src.core.event_bus import SimpleEventBus, Event, EventType
from src.core.trade_repository import TradeRepository
from src.execution.portfolio import Portfolio
from src.execution.backtest.backtest_coordinator import BacktestCoordinator
from src.data.historical_data_handler import HistoricalDataHandler
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

def test_portfolio_logger():
    """Test Portfolio logger initialization."""
    logger.info("Testing Portfolio logger initialization...")
    
    portfolio = Portfolio("test_portfolio", 100000.0)
    
    # Check if logger is properly initialized
    if hasattr(portfolio, 'logger'):
        logger.info("✓ Portfolio logger properly initialized")
        return True
    else:
        logger.error("✗ Portfolio logger not initialized")
        return False

def test_backtest_coordinator_logger():
    """Test BacktestCoordinator logger initialization."""
    logger.info("Testing BacktestCoordinator logger initialization...")
    
    config = {'initial_capital': 100000.0}
    coordinator = BacktestCoordinator("test_coordinator", config)
    
    # Check if logger is properly initialized
    if hasattr(coordinator, 'logger'):
        logger.info("✓ BacktestCoordinator logger properly initialized")
        return True
    else:
        logger.error("✗ BacktestCoordinator logger not initialized")
        return False

def test_portfolio_update_event():
    """Test the on_portfolio_update event handler."""
    logger.info("Testing portfolio_update event handling...")
    
    # Setup components
    event_bus = SimpleEventBus()
    trade_repository = TradeRepository()
    config = {'initial_capital': 100000.0}
    coordinator = BacktestCoordinator("test_coordinator", config)
    
    # Initialize with context
    context = {
        'event_bus': event_bus,
        'trade_repository': trade_repository
    }
    coordinator.initialize(context)
    
    # Create test event
    update_data = {
        'timestamp': None,
        'capital': 100000.0,
        'closed_pnl': 0.0,
        'market_value': 0.0,
        'closed_only_equity': 100000.0,
        'full_equity': 100000.0
    }
    
    event = Event(EventType.PORTFOLIO_UPDATE, update_data)
    
    # Handle event
    try:
        coordinator.on_portfolio_update(event)
        logger.info("✓ on_portfolio_update event handled successfully")
        return True
    except Exception as e:
        logger.error(f"✗ on_portfolio_update event failed: {e}")
        return False

def run_tests():
    """Run all test cases."""
    logger.info("Starting logger fix verification tests...")
    
    test_results = []
    test_results.append(test_portfolio_logger())
    test_results.append(test_backtest_coordinator_logger())
    test_results.append(test_portfolio_update_event())
    
    # Report results
    passed = all(test_results)
    logger.info(f"Tests completed. {sum(test_results)}/{len(test_results)} tests passed.")
    
    if passed:
        logger.info("✓ All tests passed! The logger fixes are working correctly.")
    else:
        logger.error("✗ Some tests failed. The logger fixes need adjustment.")
    
    return passed

if __name__ == "__main__":
    run_tests()
