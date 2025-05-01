#!/usr/bin/env python
"""
A minimal test script to validate our fix for the risk manager deduplication.
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
        logging.FileHandler('simple_test.log', mode='w')
    ]
)
logger = logging.getLogger("SimpleTest")

# Import required components
from src.core.events.event_utils import create_signal_event
from src.core.events.event_bus import EventBus
from src.risk.portfolio.portfolio import PortfolioManager
from src.risk.managers.simple import SimpleRiskManager
from src.execution.order_manager import OrderManager
from src.execution.order_registry import OrderRegistry
from src.execution.broker.broker_simulator import SimulatedBroker

def main():
    """Run a simple test for rule_id deduplication."""
    logger.info("Starting simple rule_id deduplication test")
    
    # Create components
    event_bus = EventBus()
    portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
    order_registry = OrderRegistry(event_bus)
    order_manager = OrderManager(event_bus, None, order_registry)
    broker = SimulatedBroker(event_bus, order_registry)
    order_manager.set_broker(broker)
    
    # Create risk manager with reference to order manager
    risk_manager = SimpleRiskManager(event_bus, portfolio, "test_risk_manager")
    risk_manager.position_size = 100
    risk_manager.order_manager = order_manager
    
    # Create a unique rule_id
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
    
    # Log signal IDs
    logger.info(f"Signal 1 ID: {signal1.get_id()}")
    logger.info(f"Signal 2 ID: {signal2.get_id()}")
    
    # Clear any existing processed rule_ids
    risk_manager.processed_rule_ids.clear()
    logger.info("Cleared risk manager processed_rule_ids")
    
    # Process first signal
    logger.info("Processing first signal...")
    result1 = risk_manager.on_signal(signal1)
    logger.info(f"First signal result: {result1}")
    
    # Check if rule_id was recorded
    logger.info(f"rule_id in processed_rule_ids: {rule_id in risk_manager.processed_rule_ids}")
    
    # Process second signal
    logger.info("Processing second signal...")
    result2 = risk_manager.on_signal(signal2)
    logger.info(f"Second signal result: {result2}")
    
    # Test result
    if result1 is not None and result2 is None:
        logger.info("SUCCESS: First signal created order, second signal was deduplicated!")
        return 0
    else:
        logger.error(f"FAILED: First signal result: {result1}, Second signal result: {result2}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
