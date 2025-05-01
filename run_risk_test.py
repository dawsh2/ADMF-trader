#!/usr/bin/env python
"""
Test script that focuses only on the risk manager deduplication test.
"""
import logging
import os
from datetime import datetime
import uuid
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('risk_test_log.txt', mode='w')
    ]
)
logger = logging.getLogger("RiskManagerTest")

# Import required components 
from src.core.events.event_bus import EventBus
from src.core.events.event_utils import create_signal_event
from src.execution.order_registry import OrderRegistry
from src.risk.portfolio.portfolio import PortfolioManager
from src.risk.managers.simple import SimpleRiskManager

def test_risk_manager_deduplication():
    """Focused test that only tests the risk manager deduplication feature."""
    logger.info("=== Starting Risk Manager Deduplication Test ===")
    
    # Create core components
    event_bus = EventBus()
    portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
    order_registry = OrderRegistry(event_bus)
    
    # Create risk manager with standard settings
    risk_manager = SimpleRiskManager(event_bus, portfolio, "test_risk_manager")
    risk_manager.position_size = 100  # Standard position size
    
    # Get initial state
    initial_processed_ids = len(risk_manager.processed_rule_ids)
    logger.info(f"Initial processed rule IDs: {initial_processed_ids}")
    
    # Create a unique rule_id
    test_rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Generated test rule ID: {test_rule_id}")
    
    # Create 2 signal events with the same rule_id
    signal1 = create_signal_event(
        signal_value=1,  # BUY
        price=100.0,
        symbol="TEST",
        rule_id=test_rule_id,
        timestamp=datetime.now()
    )
    
    # Create a slight delay to ensure different timestamps
    time.sleep(0.1)
    
    signal2 = create_signal_event(
        signal_value=1,  # BUY
        price=100.0,
        symbol="TEST",
        rule_id=test_rule_id,
        timestamp=datetime.now()
    )
    
    # Emit the first signal
    logger.info(f"Emitting FIRST signal with rule_id: {test_rule_id}")
    event_bus.emit(signal1)
    
    # Check if the rule_id was processed
    time.sleep(1.0)  # Allow time for processing
    if test_rule_id in risk_manager.processed_rule_ids:
        logger.info(f"✅ FIRST signal rule_id was added to processed_rule_ids")
    else:
        logger.error(f"❌ FIRST signal rule_id was NOT added to processed_rule_ids")
        
    # Track processed count after first signal
    processed_after_first = len(risk_manager.processed_rule_ids)
    logger.info(f"After first signal, processed rule IDs: {processed_after_first}")
    
    # Emit the second signal
    logger.info(f"Emitting SECOND signal with same rule_id: {test_rule_id}")
    event_bus.emit(signal2)
    
    # Allow time for processing
    time.sleep(1.0)
    
    # Check final state
    processed_after_second = len(risk_manager.processed_rule_ids)
    logger.info(f"After second signal, processed rule IDs: {processed_after_second}")
    
    # The test passes if the second signal didn't create a new processed rule ID
    # This means processed_after_first == processed_after_second
    if processed_after_second == processed_after_first:
        logger.info("✅ TEST PASSED: Second signal with same rule_id was correctly deduplicated!")
        return True
    else:
        logger.error("❌ TEST FAILED: Second signal created duplicate entry!")
        return False

if __name__ == "__main__":
    # Run the test
    result = test_risk_manager_deduplication()
    
    # Report result
    print(f"\nTest result: {'PASSED' if result else 'FAILED'}")
    exit(0 if result else 1)
