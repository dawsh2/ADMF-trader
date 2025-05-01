#!/usr/bin/env python
"""
Test the fixes for the risk manager deduplication feature
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
        logging.FileHandler('fixed_test.log', mode='w')
    ]
)
logger = logging.getLogger("FixedTest")

# Import required components
from src.core.events.event_utils import create_signal_event
from src.core.events.event_bus import EventBus
from src.risk.portfolio.portfolio import PortfolioManager
from src.risk.managers.simple import SimpleRiskManager
from src.execution.order_manager import OrderManager
from src.execution.order_registry import OrderRegistry
from src.execution.broker.broker_simulator import SimulatedBroker

def create_test_components():
    """Create all components needed for testing."""
    # Create event bus
    event_bus = EventBus()
    
    # Create portfolio manager
    portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
    
    # Create order registry (centralized order tracking)
    order_registry = OrderRegistry(event_bus)
    
    # Create order manager (processes orders)
    order_manager = OrderManager(event_bus, None, order_registry)
    
    # Create broker (executes orders)
    broker = SimulatedBroker(event_bus, order_registry)
    
    # Set broker on order manager
    order_manager.set_broker(broker)
    
    # Create risk manager (creates orders from signals, manages position size)
    risk_manager = SimpleRiskManager(event_bus, portfolio, "test_risk_manager")
    risk_manager.position_size = 100  # Standard position size
    
    # CRITICAL: Provide order_manager reference to risk_manager
    risk_manager.order_manager = order_manager
    
    # Return all components
    return {
        'event_bus': event_bus,
        'portfolio': portfolio,
        'order_registry': order_registry,
        'order_manager': order_manager,
        'broker': broker,
        'risk_manager': risk_manager
    }

def test_risk_manager_deduplication():
    """Test that the risk manager correctly deduplicates signals."""
    logger.info("=== Test: Risk Manager Deduplication ===")
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    risk_manager = components['risk_manager']
    order_registry = components['order_registry']
    
    # Ensure risk_manager.processed_rule_ids is cleared
    risk_manager.processed_rule_ids.clear()
    logger.info("Cleared processed_rule_ids")
    
    # Get initial order count
    initial_order_count = len(order_registry.orders)
    logger.info(f"Initial order count: {initial_order_count}")
    
    # Create a signal with a unique identifier in the rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Generated rule_id: {rule_id}")
    
    # Create two identical signals with the same rule_id
    timestamp1 = datetime.datetime.now()
    signal1 = create_signal_event(
        signal_value=1,
        price=100.0,
        symbol="TEST",
        rule_id=rule_id,
        timestamp=timestamp1
    )
    
    timestamp2 = datetime.datetime.now()
    signal2 = create_signal_event(
        signal_value=1,
        price=100.0,
        symbol="TEST",
        rule_id=rule_id,
        timestamp=timestamp2
    )
    
    # Process first signal directly through risk manager
    logger.info(f"Processing first signal with rule_id: {rule_id}")
    result1 = risk_manager.on_signal(signal1)
    logger.info(f"First signal result: {result1}")
    
    # Check if rule_id was recorded correctly
    logger.info(f"rule_id in processed_rule_ids after first signal: {rule_id in risk_manager.processed_rule_ids}")
    
    # Check order count after first signal
    sleep(1.0)  # Give time for order to be processed
    mid_order_count = len(order_registry.orders)
    logger.info(f"Order count after first signal: {mid_order_count}")
    
    # Process second signal directly through risk manager
    logger.info(f"Processing second signal with same rule_id: {rule_id}")
    result2 = risk_manager.on_signal(signal2)
    logger.info(f"Second signal result: {result2}")
    
    # Check order count after second signal
    sleep(1.0)  # Give time for order to be processed
    final_order_count = len(order_registry.orders)
    logger.info(f"Order count after second signal: {final_order_count}")
    
    # We should see one new order from the first signal, but none from the second
    if (mid_order_count > initial_order_count) and (final_order_count == mid_order_count):
        logger.info("SUCCESS: Risk manager correctly deduplicated the signal")
        return True
    else:
        logger.error(f"FAILURE: Risk manager failed to deduplicate, counts: {initial_order_count} -> {mid_order_count} -> {final_order_count}")
        return False

if __name__ == "__main__":
    result = test_risk_manager_deduplication()
    sys.exit(0 if result else 1)
