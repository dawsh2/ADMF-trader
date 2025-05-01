#!/usr/bin/env python
"""
Test script to debug the SignalEvent and Event objects.
"""
import logging
import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('signal_event_test.log', mode='w')
    ]
)
logger = logging.getLogger("SignalEventTest")

# Import required components
from src.core.events.event_types import Event, EventType
from src.core.events.event_utils import create_signal_event
from src.risk.managers.enhanced_risk_manager import EnhancedRiskManager
from src.risk.portfolio.portfolio import PortfolioManager
from src.core.events.event_bus import EventBus

def test_signal_event_creation():
    """Test creation of signal events using different methods."""
    logger.info("=== Test: Signal Event Creation ===")
    
    # Method 1: Using event_utils helper
    signal1 = create_signal_event(
        signal_value=1.0,
        price=100.0,
        symbol="TEST",
        rule_id="test_rule_1"
    )
    
    # Method 2: Manual creation of Event
    signal2 = Event(
        EventType.SIGNAL,
        {
            'symbol': "TEST",
            'signal_value': 1.0,
            'price': 100.0,
            'rule_id': "test_rule_2"
        },
        datetime.datetime.now()
    )
    
    # Check the signal events
    logger.info(f"Signal 1 type: {type(signal1)}")
    logger.info(f"Signal 2 type: {type(signal2)}")
    
    # Check available methods
    logger.info(f"Signal 1 has get_symbol: {hasattr(signal1, 'get_symbol')}")
    logger.info(f"Signal 2 has get_symbol: {hasattr(signal2, 'get_symbol')}")
    
    # Check data attributes
    logger.info(f"Signal 1 has data: {hasattr(signal1, 'data')}")
    logger.info(f"Signal 2 has data: {hasattr(signal2, 'data')}")
    
    if hasattr(signal1, 'data'):
        logger.info(f"Signal 1 data: {signal1.data}")
    
    if hasattr(signal2, 'data'):
        logger.info(f"Signal 2 data: {signal2.data}")
    
    return True

def test_enhanced_risk_manager():
    """Test that the EnhancedRiskManager can handle different signal event types."""
    logger.info("=== Test: Enhanced Risk Manager with Signal Events ===")
    
    # Create components
    event_bus = EventBus()
    portfolio = PortfolioManager(event_bus)
    risk_manager = EnhancedRiskManager(event_bus, portfolio, "test_risk_manager")
    
    # Create signal events using both methods
    signal1 = create_signal_event(
        signal_value=1.0,
        price=100.0,
        symbol="TEST",
        rule_id="test_rule_1"
    )
    
    signal2 = Event(
        EventType.SIGNAL,
        {
            'symbol': "TEST",
            'signal_value': 1.0,
            'price': 100.0,
            'rule_id': "test_rule_2"
        },
        datetime.datetime.now()
    )
    
    # Process the signals
    logger.info("Processing signal created with helper function")
    result1 = risk_manager.on_signal(signal1)
    logger.info(f"Result 1: {result1}")
    
    logger.info("Processing signal created manually")
    result2 = risk_manager.on_signal(signal2)
    logger.info(f"Result 2: {result2}")
    
    return True

def run_all_tests():
    """Run all tests."""
    tests = [
        test_signal_event_creation,
        test_enhanced_risk_manager
    ]
    
    results = {}
    
    for test_func in tests:
        test_name = test_func.__name__
        logger.info(f"\nRunning test: {test_name}")
        
        try:
            result = test_func()
            results[test_name] = result
            logger.info(f"Test {test_name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            logger.error(f"Test {test_name} raised exception: {e}", exc_info=True)
            results[test_name] = False
    
    return all(results.values())

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
