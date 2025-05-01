#!/usr/bin/env python
"""
Implementation test for the new signal deduplication architecture.

This test verifies that our solution works with the existing system by:
1. Running the old approach (direct risk manager test)
2. Running the new approach with signal preprocessor
3. Running the new approach with signal management service
4. Comparing results to ensure consistent behavior
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
        logging.FileHandler('implementation_test.log', mode='w')
    ]
)
logger = logging.getLogger("ImplementationTest")

# Import required components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import Event, EventType
from src.core.events.bootstrap_event_flow import create_event_system, submit_signal
from src.core.events.event_utils import create_signal_event

# Import test components
from direct_test import test_risk_manager_direct_deduplication
from modified_rule_id_filter import EnhancedRuleIdFilter
from test_order_flow import create_test_components

def test_original_approach():
    """Run the original direct test to establish a baseline."""
    logger.info("\n=== Test: Original Direct Approach ===")
    result = test_risk_manager_direct_deduplication()
    logger.info(f"Original direct test result: {'PASS' if result else 'FAIL'}")
    return result

def test_filtered_approach():
    """Run the EnhancedRuleIdFilter approach as a comparison."""
    logger.info("\n=== Test: EnhancedRuleIdFilter Approach ===")
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    
    # Install the enhanced filter
    rule_filter = EnhancedRuleIdFilter(event_bus)
    logger.info(f"Installed EnhancedRuleIdFilter: {rule_filter}")
    
    # Get initial order count
    order_registry = components['order_registry']
    initial_order_count = len(order_registry.orders)
    logger.info(f"Initial order count: {initial_order_count}")
    
    # Create a unique rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Generated unique rule_id: {rule_id}")
    
    # Create signals with the same rule_id
    from test_order_flow import create_signal_event
    signal1 = create_signal_event(signal_value=1, price=100.0, symbol="TEST", rule_id=rule_id)
    signal2 = create_signal_event(signal_value=1, price=100.0, symbol="TEST", rule_id=rule_id)
    
    # Log the signals
    logger.info(f"Signal 1 event ID: {signal1.get_id()}")
    logger.info(f"Signal 2 event ID: {signal2.get_id()}")
    logger.info(f"Both signals have the same rule_id: {rule_id}")
    
    # Reset state to ensure clean test
    rule_filter.reset()
    logger.info("Reset filter before test")
    
    # Emit first signal
    logger.info(f"Emitting first signal with rule_id: {rule_id}")
    event_bus.emit(signal1)
    
    # Check order count after first signal
    time.sleep(1.0)
    mid_order_count = len(order_registry.orders)
    logger.info(f"Order count after first signal: {mid_order_count}")
    
    # Emit second signal with same rule_id
    logger.info(f"Emitting second signal with same rule_id: {rule_id}")
    event_bus.emit(signal2)
    
    # Check order count after second signal
    time.sleep(1.0)
    final_order_count = len(order_registry.orders)
    logger.info(f"Order count after second signal: {final_order_count}")
    
    # Verify that only one order was created
    if mid_order_count > initial_order_count and final_order_count == mid_order_count:
        logger.info("✓ EnhancedRuleIdFilter correctly deduplicated the signal")
        result = True
    else:
        logger.error(f"✗ EnhancedRuleIdFilter failed to deduplicate, counts: {initial_order_count} -> {mid_order_count} -> {final_order_count}")
        result = False
    
    # Cleanup and restore original emit method
    try:
        rule_filter.restore_emit()
        logger.info("Successfully restored original emit method")
    except Exception as e:
        logger.error(f"Error restoring emit method: {e}")
        
    return result

def test_new_architecture():
    """Test the new signal deduplication architecture."""
    logger.info("\n=== Test: New Architecture Approach ===")
    
    # Create system using bootstrap
    components = create_event_system()
    event_bus = components['event_bus']
    risk_manager = components['risk_manager']
    signal_service = components['signal_service']
    
    # Track order events
    orders_created = []
    
    def order_handler(order_event):
        orders_created.append(order_event)
        logger.info(f"Order created: {order_event.get_id()}")
    
    # Register order handler
    event_bus.register(EventType.ORDER, order_handler)
    
    # Create a unique rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Using rule_id: {rule_id}")
    
    # Create two signals with the same rule_id
    signal_data1 = {
        'symbol': 'TEST',
        'signal_value': 1.0,
        'price': 100.0,
        'rule_id': rule_id,
        'timestamp': datetime.datetime.now()
    }
    
    signal_data2 = {
        'symbol': 'TEST',
        'signal_value': 1.0,
        'price': 100.0,
        'rule_id': rule_id,
        'timestamp': datetime.datetime.now() + datetime.timedelta(seconds=1)
    }
    
    # Submit first signal
    logger.info("Submitting first signal")
    result1 = submit_signal(components, signal_data1)
    
    # Check if first signal was accepted
    if result1 is None:
        logger.error("First signal was rejected, expected acceptance")
        return False
        
    # Count orders after first signal
    time.sleep(0.1)  # Allow time for event processing
    orders_after_first = len(orders_created)
    logger.info(f"Orders after first signal: {orders_after_first}")
    
    # Submit second signal with same rule_id
    logger.info("Submitting second signal with same rule_id")
    result2 = submit_signal(components, signal_data2)
    
    # Check if second signal was rejected
    if result2 is not None:
        logger.warning("Second signal was not rejected as expected")
    
    # Count orders after second signal
    time.sleep(0.1)  # Allow time for event processing
    orders_after_second = len(orders_created)
    logger.info(f"Orders after second signal: {orders_after_second}")
    
    # We should see one order from the first signal but no additional orders from the second
    if orders_after_first == 1 and orders_after_second == 1:
        logger.info("✓ New architecture correctly deduplicated signals")
        return True
    else:
        logger.error(f"✗ New architecture failed to deduplicate signals correctly: {orders_after_first} -> {orders_after_second}")
        return False

def test_direct_signal_process():
    """Test direct signal processing with manual setup."""
    logger.info("\n=== Test: Manual Direct Signal Processing ===")
    
    # Create components the old way
    components = create_test_components()
    event_bus = components['event_bus']
    risk_manager = components['risk_manager']
    
    # Create and add signal preprocessor
    from src.core.events.signal_preprocessor import SignalPreprocessor
    signal_preprocessor = SignalPreprocessor(event_bus)
    
    # Create direct processor
    from src.core.events.direct_signal_processor import DirectSignalProcessor
    direct_processor = DirectSignalProcessor(event_bus, risk_manager, signal_preprocessor)
    
    # Track order events
    orders_created = []
    
    def order_handler(order_event):
        orders_created.append(order_event)
        logger.info(f"Order created: {order_event.get_id()}")
    
    # Register order handler
    event_bus.register(EventType.ORDER, order_handler)
    
    # Create a signal event with rule_id
    from test_order_flow import create_signal_event
    rule_id = f"test_rule_{uuid.uuid4()}"
    
    # Create two identical signals
    signal1 = create_signal_event(signal_value=1, price=100.0, symbol="TEST", rule_id=rule_id)
    signal2 = create_signal_event(signal_value=1, price=100.0, symbol="TEST", rule_id=rule_id)
    
    # Process directly
    logger.info("Processing first signal directly")
    result1 = direct_processor.process_signal_and_emit(signal1)
    
    # Check order count
    time.sleep(0.1)
    orders_after_first = len(orders_created)
    logger.info(f"Orders after first signal: {orders_after_first}")
    
    # Process second signal
    logger.info("Processing second signal directly")
    result2 = direct_processor.process_signal_and_emit(signal2)
    
    # Check order count again
    time.sleep(0.1)
    orders_after_second = len(orders_created)
    logger.info(f"Orders after second signal: {orders_after_second}")
    
    # Verify deduplication worked
    if orders_after_first == 1 and orders_after_second == 1:
        logger.info("✓ Direct signal processing correctly deduplicated signals")
        return True
    else:
        logger.error(f"✗ Direct signal processing failed to deduplicate signals correctly: {orders_after_first} -> {orders_after_second}")
        return False

def run_all_tests():
    """Run all implementation tests."""
    logger.info("======= Starting Implementation Tests =======")
    
    tests = [
        test_original_approach,
        test_filtered_approach,
        test_new_architecture,
        test_direct_signal_process
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
