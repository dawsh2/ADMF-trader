#!/usr/bin/env python
"""
Direct test for risk manager deduplication that bypasses the event bus 
to ensure the deduplication logic in the risk manager works correctly.
"""
import logging
import datetime
import uuid
import sys
from time import sleep

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('direct_test.log', mode='w')
    ]
)
logger = logging.getLogger("DirectTest")

# Import required components from test_order_flow
from test_order_flow import create_test_components
from src.core.events.event_utils import create_signal_event

def test_risk_manager_direct_deduplication():
    """Test that the risk manager correctly deduplicates signals when called directly."""
    logger.info("=== Test: Direct Risk Manager Deduplication ===")
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    risk_manager = components['risk_manager']
    order_registry = components['order_registry']
    order_manager = components['order_manager']
    
    # For debugging purposes - log the risk manager instance
    logger.info(f"Risk manager instance: {risk_manager}")
    
    # Ensure all previous rule_ids are cleared
    risk_manager.processed_rule_ids.clear()
    logger.info(f"Cleared processed_rule_ids: {risk_manager.processed_rule_ids}")
    
    # Get initial order count
    initial_order_count = len(order_registry.orders)
    logger.info(f"Initial order count: {initial_order_count}")
    
    # Create a signal with a unique identifier in the rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Generated unique rule_id: {rule_id}")
    
    # Create signals with different timestamps but same rule_id
    import time
    timestamp1 = datetime.datetime.now()
    time.sleep(0.1)  # Ensure different timestamps
    timestamp2 = datetime.datetime.now()
    
    # Create the same signal twice with the same rule_id but different event IDs
    signal1 = create_signal_event(
        signal_value=1,  # BUY
        price=100.0,
        symbol="TEST",
        rule_id=rule_id,
        timestamp=timestamp1
    )
    
    signal2 = create_signal_event(
        signal_value=1,  # BUY
        price=100.0,
        symbol="TEST",
        rule_id=rule_id,
        timestamp=timestamp2
    )
    
    # Log the IDs to ensure they're different
    logger.info(f"Signal 1 event ID: {signal1.get_id()}")
    logger.info(f"Signal 2 event ID: {signal2.get_id()}")
    logger.info(f"Both signals have the same rule_id: {rule_id}")
    
    # Process signals directly through risk manager instead of event_bus
    logger.info(f"Processing first signal with rule_id: {rule_id} directly through risk manager")
    result1 = risk_manager.on_signal(signal1)
    logger.info(f"First signal result: {result1}")
    
    # Check if rule_id was recorded
    logger.info(f"rule_id in processed_rule_ids: {rule_id in risk_manager.processed_rule_ids}")
    
    # Check order count after first signal
    sleep(1.0)  # Give time for order to be processed
    mid_order_count = len(order_registry.orders)
    logger.info(f"Order count after first signal: {mid_order_count}")
    
    # Process second signal directly through risk manager
    logger.info(f"Processing second signal with same rule_id: {rule_id} directly through risk manager")
    result2 = risk_manager.on_signal(signal2)
    logger.info(f"Second signal result: {result2}")
    
    # Check order count after second signal
    sleep(1.0)  # Give time for order to be processed
    final_order_count = len(order_registry.orders)
    logger.info(f"Order count after second signal: {final_order_count}")
    
    # We should see one new order from the first signal, but none from the second
    if (mid_order_count > initial_order_count) and (final_order_count == mid_order_count):
        logger.info("✓ Risk manager correctly deduplicated the signal")
        return True
    else:
        logger.error(f"✗ Risk manager failed to deduplicate, counts: {initial_order_count} -> {mid_order_count} -> {final_order_count}")
        return False

if __name__ == "__main__":
    result = test_risk_manager_direct_deduplication()
    sys.exit(0 if result else 1)
