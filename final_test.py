#!/usr/bin/env python
"""
Final integrated test for the signal deduplication solution.

This test:
1. Fixes the event bus emit method to handle weakref methods
2. Tests the EnhancedRuleIdFilter with the fixed event bus
3. Verifies deduplication works without errors
"""
import logging
import datetime
import uuid
import time
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('final_test.log', mode='w')
    ]
)
logger = logging.getLogger("FinalTest")

# First, apply the event bus fix
logger.info("Applying event bus fix...")
from fix_event_bus import patch_event_bus_emit
if not patch_event_bus_emit():
    logger.error("Failed to apply event bus fix, test will likely fail")
    sys.exit(1)

# Import components
from test_order_flow import create_test_components, create_signal_event
from modified_rule_id_filter import EnhancedRuleIdFilter

def test_final_deduplication():
    """
    Final test of the deduplication solution with fixed event bus.
    """
    logger.info("\n=== FINAL TEST: Signal Deduplication with Fixed Event Bus ===")
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    order_registry = components['order_registry']
    
    # Install the enhanced filter
    filter = EnhancedRuleIdFilter(event_bus)
    logger.info(f"Installed EnhancedRuleIdFilter with fixed event bus")
    
    # Get initial order count
    initial_order_count = len(order_registry.orders)
    logger.info(f"Initial order count: {initial_order_count}")
    
    # Create a unique rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Generated unique rule_id: {rule_id}")
    
    # Create two identical signals with the same rule_id
    signal1 = create_signal_event(
        signal_value=1, 
        price=100.0, 
        symbol="TEST", 
        rule_id=rule_id
    )
    
    signal2 = create_signal_event(
        signal_value=1, 
        price=100.0, 
        symbol="TEST", 
        rule_id=rule_id
    )
    
    # Log signal information
    logger.info(f"Signal 1 ID: {signal1.get_id()}")
    logger.info(f"Signal 2 ID: {signal2.get_id()}")
    logger.info(f"Both signals have rule_id: {rule_id}")
    
    # Reset filter state
    filter.reset()
    logger.info("Filter reset")
    
    # Emit first signal
    logger.info(f"Emitting first signal with rule_id: {rule_id}")
    result1 = event_bus.emit(signal1)
    logger.info(f"First signal emit result: {result1} handlers called")
    
    # Check order count after first signal
    time.sleep(1.0)  # Allow time for processing
    mid_order_count = len(order_registry.orders)
    logger.info(f"Order count after first signal: {mid_order_count}")
    
    # Emit second signal with same rule_id
    logger.info(f"Emitting second signal with same rule_id: {rule_id}")
    result2 = event_bus.emit(signal2)
    logger.info(f"Second signal emit result: {result2} handlers called")
    
    # Check order count after second signal
    time.sleep(1.0)  # Allow time for processing
    final_order_count = len(order_registry.orders)
    logger.info(f"Order count after second signal: {final_order_count}")
    
    # Verify deduplication worked
    if mid_order_count > initial_order_count and final_order_count == mid_order_count:
        logger.info("✓ Deduplication SUCCESS - only first signal created an order")
        success = True
    else:
        logger.error(f"✗ Deduplication FAILED - order counts: {initial_order_count} -> {mid_order_count} -> {final_order_count}")
        success = False
    
    # Clean up - restore original emit method
    try:
        filter.restore_emit()
        logger.info("Successfully restored original emit method")
    except Exception as e:
        logger.error(f"Error restoring emit method: {e}")
    
    return success

if __name__ == "__main__":
    result = test_final_deduplication()
    sys.exit(0 if result else 1)
