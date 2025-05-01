#!/usr/bin/env python
"""
Test script to specifically test the EnhancedRuleIdFilter.
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
        logging.FileHandler('filter_test.log', mode='w')
    ]
)
logger = logging.getLogger("FilterTest")

# Import required components
from test_order_flow import create_test_components, create_signal_event
from modified_rule_id_filter import EnhancedRuleIdFilter

def test_enhanced_filter():
    """Test the enhanced rule ID filter."""
    logger.info("=== Test: Enhanced Rule ID Filter ===")
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    order_registry = components['order_registry']
    
    # Install the enhanced filter
    rule_filter = EnhancedRuleIdFilter(event_bus)
    logger.info(f"Installed filter: {rule_filter}")
    
    # Get initial order count
    initial_order_count = len(order_registry.orders)
    logger.info(f"Initial order count: {initial_order_count}")
    
    # Create a unique rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Generated unique rule_id: {rule_id}")
    
    # Create signals with the same rule_id
    signal1 = create_signal_event(signal_value=1, price=100.0, symbol="TEST", rule_id=rule_id)
    signal2 = create_signal_event(signal_value=1, price=100.0, symbol="TEST", rule_id=rule_id)
    
    # Log the signals
    logger.info(f"Signal 1 event ID: {signal1.get_id()}")
    logger.info(f"Signal 2 event ID: {signal2.get_id()}")
    logger.info(f"Both signals have the same rule_id: {rule_id}")
    
    # Reset filter state
    rule_filter.reset()
    logger.info("Reset filter state")
    
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
        success = True
    else:
        logger.error(f"✗ EnhancedRuleIdFilter failed to deduplicate, counts: {initial_order_count} -> {mid_order_count} -> {final_order_count}")
        success = False
    
    # Clean up - safely restore original emit method
    try:
        rule_filter.restore_emit()
        logger.info("Successfully restored original emit method")
    except Exception as e:
        logger.error(f"Error restoring emit method: {e}")
    
    return success

if __name__ == "__main__":
    success = test_enhanced_filter()
    sys.exit(0 if success else 1)
