#!/usr/bin/env python
"""
Comprehensive test for the new signal deduplication mechanism.

This test covers:
1. Direct signal processing
2. Signal preprocessor
3. Enhanced risk manager
4. Signal management service
"""
import logging
import sys
import uuid
import datetime
import time
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deduplication_test.log', mode='w')
    ]
)
logger = logging.getLogger("DeduplicationTest")

# Import required components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import Event, EventType
from src.core.events.event_utils import create_signal_event
from src.core.events.signal_preprocessor import SignalPreprocessor
from src.core.events.direct_signal_processor import DirectSignalProcessor
from src.core.events.signal_management_service import SignalManagementService
from src.risk.managers.enhanced_risk_manager import EnhancedRiskManager
from src.risk.portfolio.portfolio import PortfolioManager

# Helper to create a test portfolio
def create_test_portfolio():
    """Create a simple portfolio for testing."""
    portfolio = PortfolioManager()
    portfolio.cash = 100000.0
    portfolio.equity = 100000.0
    return portfolio

# Test 1: Direct Signal Processing
def test_direct_signal_processing():
    """Test that direct signal processing correctly deduplicates signals."""
    logger.info("=== Test: Direct Signal Processing ===")
    
    # Create components
    event_bus = EventBus()
    portfolio = create_test_portfolio()
    risk_manager = EnhancedRiskManager(event_bus, portfolio, "test_risk_manager")
    
    # Create direct signal processor
    direct_processor = DirectSignalProcessor(event_bus, risk_manager)
    
    # Create a unique rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Using rule_id: {rule_id}")
    
    # Create two identical signals with the same rule_id using event_utils
    signal1 = create_signal_event(
        signal_value=1.0,
        price=100.0,
        symbol="TEST",
        rule_id=rule_id
    )
    
    time.sleep(0.1)  # Ensure different timestamps
    
    signal2 = create_signal_event(
        signal_value=1.0,
        price=100.0,
        symbol="TEST",
        rule_id=rule_id
    )
    
    # Process first signal
    logger.info("Processing first signal")
    result1 = direct_processor.process_signal(signal1)
    
    # Check result
    if result1 is None:
        logger.error("First signal was rejected, expected acceptance")
        return False
    
    # Process second signal (should be rejected)
    logger.info("Processing second signal with same rule_id")
    result2 = direct_processor.process_signal(signal2)
    
    # Check result
    if result2 is not None:
        logger.error("Second signal was accepted, expected rejection for duplicate rule_id")
        return False
    
    logger.info("✓ Direct signal processing correctly identified duplicate signals")
    return True

# Test 2: Signal Preprocessor
def test_signal_preprocessor():
    """Test that the signal preprocessor correctly identifies and blocks duplicate signals."""
    logger.info("=== Test: Signal Preprocessor ===")
    
    # Create components
    event_bus = EventBus()
    
    # Create signal preprocessor
    preprocessor = SignalPreprocessor(event_bus)
    
    # Create a unique rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Using rule_id: {rule_id}")
    
    # Create two signals with the same rule_id using event_utils
    signal1 = create_signal_event(
        signal_value=1.0,
        price=100.0,
        symbol="TEST",
        rule_id=rule_id
    )
    
    signal2 = create_signal_event(
        signal_value=1.0,
        price=100.0,
        symbol="TEST",
        rule_id=rule_id
    )
    
    # Test the first signal
    logger.info("Processing first signal through preprocessor")
    preprocessor.preprocess_signal(signal1)
    
    # Check if signal was consumed
    if hasattr(signal1, 'consumed') and signal1.consumed:
        logger.error("First signal was wrongly consumed by preprocessor")
        return False
    
    # Test the second signal
    logger.info("Processing second signal with same rule_id through preprocessor")
    preprocessor.preprocess_signal(signal2)
    
    # Check if signal was consumed
    if not (hasattr(signal2, 'consumed') and signal2.consumed):
        logger.error("Second signal was not consumed by preprocessor as expected")
        return False
    
    logger.info("✓ Signal preprocessor correctly identifies and blocks duplicate signals")
    return True

# Test 3: Enhanced Risk Manager
def test_enhanced_risk_manager():
    """Test that the enhanced risk manager correctly deduplicates signals."""
    logger.info("=== Test: Enhanced Risk Manager ===")
    
    # Create components
    event_bus = EventBus()
    portfolio = create_test_portfolio()
    
    # Create enhanced risk manager
    risk_manager = EnhancedRiskManager(event_bus, portfolio, "test_enhanced_risk_manager")
    
    # Create a unique rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Using rule_id: {rule_id}")
    
    # Create two signals with the same rule_id using event_utils
    signal1 = create_signal_event(
        signal_value=1.0,
        price=100.0,
        symbol="TEST",
        rule_id=rule_id
    )
    
    signal2 = create_signal_event(
        signal_value=1.0,
        price=100.0,
        symbol="TEST",
        rule_id=rule_id
    )
    
    # Process first signal
    logger.info("Processing first signal through risk manager")
    result1 = risk_manager.on_signal(signal1)
    
    # Check if order was created
    if result1 is None:
        logger.error("First signal did not produce an order as expected")
        return False
    
    # Process second signal
    logger.info("Processing second signal with same rule_id through risk manager")
    result2 = risk_manager.on_signal(signal2)
    
    # Check if second signal was rejected
    if result2 is not None:
        logger.error("Second signal produced an order, expected rejection")
        return False
    
    logger.info("✓ Enhanced risk manager correctly deduplicates signals")
    return True

# Test 4: Signal Management Service
def test_signal_management_service():
    """Test that the signal management service correctly manages signals."""
    logger.info("=== Test: Signal Management Service ===")
    
    # Create components
    event_bus = EventBus()
    portfolio = create_test_portfolio()
    risk_manager = EnhancedRiskManager(event_bus, portfolio, "test_risk_manager")
    preprocessor = SignalPreprocessor(event_bus)
    
    # Create signal management service
    signal_service = SignalManagementService(event_bus, risk_manager, preprocessor)
    
    # Create a unique rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Using rule_id: {rule_id}")
    
    # Create signal data
    signal_data1 = {
        'symbol': 'TEST',
        'signal_value': 1.0,
        'price': 100.0,
        'rule_id': rule_id
    }
    
    signal_data2 = {
        'symbol': 'TEST',
        'signal_value': 1.0,
        'price': 100.0,
        'rule_id': rule_id
    }
    
    # Submit first signal
    logger.info("Submitting first signal to management service")
    result1 = signal_service.submit_signal(signal_data1)
    
    # Check if signal was accepted
    if result1 is None:
        logger.error("First signal was rejected by management service")
        return False
    
    # Submit second signal with same rule_id
    logger.info("Submitting second signal with same rule_id to management service")
    result2 = signal_service.submit_signal(signal_data2)
    
    # Check if signal was rejected
    if result2 is not None:
        logger.error("Second signal was accepted by management service, expected rejection")
        return False
    
    # Check statistics
    stats = signal_service.get_stats()
    logger.info(f"Signal management service stats: {stats}")
    
    if stats['signals_received'] != 2 or stats['signals_processed'] != 1 or stats['signals_rejected'] != 1:
        logger.error("Unexpected statistics in signal management service")
        return False
    
    logger.info("✓ Signal management service correctly manages signals")
    return True

# Test 5: Integration Test with Event Bus
def test_integration_with_event_bus():
    """Test the entire signal flow through the event bus with our new components."""
    logger.info("=== Test: Integration with Event Bus ===")
    
    # Create components
    event_bus = EventBus()
    portfolio = create_test_portfolio()
    risk_manager = EnhancedRiskManager(event_bus, portfolio, "test_risk_manager")
    preprocessor = SignalPreprocessor(event_bus)
    
    # Create signal management service and register with event bus
    signal_service = SignalManagementService(event_bus, risk_manager, preprocessor)
    
    # Orders received count (for validation)
    orders_received = 0
    
    # Create order handler
    def order_handler(order_event):
        nonlocal orders_received
        orders_received += 1
        logger.info(f"Order received: {order_event.get_id()}")
    
    # Register order handler
    event_bus.register(EventType.ORDER, order_handler)
    
    # Create a unique rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Using rule_id: {rule_id}")
    
    # Create two identical signals using event_utils
    signal1 = create_signal_event(
        signal_value=1.0,
        price=100.0,
        symbol="TEST",
        rule_id=rule_id
    )
    
    signal2 = create_signal_event(
        signal_value=1.0,
        price=100.0,
        symbol="TEST",
        rule_id=rule_id
    )
    
    # Emit first signal
    logger.info("Emitting first signal through event bus")
    event_bus.emit(signal1)
    
    # Check if order was created
    time.sleep(0.1)  # Give time for event processing
    if orders_received != 1:
        logger.error(f"Expected 1 order, got {orders_received}")
        return False
    
    # Emit second signal with same rule_id
    logger.info("Emitting second signal with same rule_id through event bus")
    event_bus.emit(signal2)
    
    # Check if second signal was rejected (order count should not increase)
    time.sleep(0.1)  # Give time for event processing
    if orders_received != 1:
        logger.error(f"Expected still 1 order, got {orders_received}")
        return False
    
    logger.info("✓ Full integration test passed, signals correctly deduplicated")
    return True

# Run all tests
def run_all_tests():
    """Run all deduplication tests."""
    logger.info("======= Starting Deduplication Tests =======")
    
    tests = [
        test_direct_signal_processing,
        test_signal_preprocessor,
        test_enhanced_risk_manager,
        test_signal_management_service,
        test_integration_with_event_bus
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
    
    # Print summary
    logger.info("\n======= Test Results Summary =======")
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info(f"\nPassed: {passed}, Failed: {failed}, Total: {len(tests)}")
    
    return passed, failed, len(tests)

if __name__ == "__main__":
    passed, failed, total = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
