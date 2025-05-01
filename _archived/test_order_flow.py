#!/usr/bin/env python
"""
Test script for order flow in ADMF-Trader.

This script tests the interaction between:
- Order Registry
- Risk Manager
- Order Manager
- Broker
- Portfolio

It creates orders in various ways and verifies proper flow.
"""
import logging
import datetime
import sys
import os
import uuid
from time import sleep

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_order_flow.log', mode='w')
    ]
)
logger = logging.getLogger("OrderFlowTest")

# Import required components
from src.core.events.event_bus import EventBus
from src.core.events.event_utils import create_order_event, create_signal_event
from src.core.events.event_types import EventType
from src.execution.order_manager import OrderManager, OrderStatus
from src.execution.order_registry import OrderRegistry
from src.risk.portfolio.portfolio import PortfolioManager
from src.risk.managers.simple import SimpleRiskManager
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
    
    # CRITICAL FIX: Provide order_manager reference to risk_manager
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

def test_create_order_direct():
    """Test creating an order directly via order manager."""
    logger.info("=== Test: Create Order Direct ===")
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    order_manager = components['order_manager']
    order_registry = components['order_registry']
    broker = components['broker']
    
    # Create an order directly
    order_id = order_manager.create_order(
        symbol="TEST",
        order_type="MARKET",
        direction="BUY",
        quantity=100,
        price=100.0
    )
    
    logger.info(f"Created order: {order_id}")
    
    # CRITICAL FIX: Significantly increase wait time to ensure event processing completes
    sleep(1.0)
    
    # Verify order is in registry
    order = order_registry.get_order(order_id)
    
    if order:
        logger.info(f"Order found in registry: {order}")
        logger.info(f"Order status: {order.status}")
        
        # Order should be filled
        if order.status == OrderStatus.FILLED:
            logger.info("✓ Order successfully filled")
            return True
        else:
            logger.error(f"✗ Order not filled, status: {order.status}")
            return False
    else:
        logger.error("✗ Order not found in registry")
        return False

def test_create_order_from_signal():
    """Test creating an order from a signal via risk manager."""
    logger.info("=== Test: Create Order From Signal ===")
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    portfolio = components['portfolio']
    order_registry = components['order_registry']
    risk_manager = components['risk_manager']
    
    # Create a signal event
    signal_event = create_signal_event(
        signal_value=1,  # BUY
        price=100.0,
        symbol="TEST",
        rule_id="test_rule"
    )
    
    # Emit the signal
    logger.info("Emitting signal event")
    event_bus.emit(signal_event)
    
    # CRITICAL FIX: Significantly increase wait time to ensure event processing completes
    sleep(1.0)
    
    # Check for orders in registry
    orders = order_registry.get_completed_orders()
    
    if orders:
        order = orders[0]
        logger.info(f"Order created from signal: {order}")
        logger.info(f"Order status: {order.status}")
        
        # Check fill status
        if order.status == OrderStatus.FILLED:
            logger.info("✓ Order from signal successfully filled")
            
            # Check portfolio
            positions = portfolio.positions
            if "TEST" in positions:
                logger.info(f"✓ Position created: {positions['TEST']}")
                return True
            else:
                logger.error("✗ No position created in portfolio")
                return False
        else:
            logger.error(f"✗ Order not filled, status: {order.status}")
            return False
    else:
        logger.error("✗ No orders created from signal")
        return False

def test_create_sell_after_buy():
    """Test creating a sell order after a buy order."""
    logger.info("=== Test: Create Sell After Buy ===")
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    portfolio = components['portfolio']
    order_registry = components['order_registry']
    risk_manager = components['risk_manager']
    
    # 1. Create a BUY signal
    buy_signal = create_signal_event(
        signal_value=1,  # BUY
        price=100.0,
        symbol="TEST",
        rule_id="test_buy"
    )
    
    # Emit the BUY signal
    logger.info("Emitting BUY signal")
    event_bus.emit(buy_signal)
    
    # CRITICAL FIX: Significantly increase wait time to ensure event processing completes
    sleep(1.0)
    
    # Check that we have a position
    buy_position = portfolio.get_position("TEST")
    if not buy_position or buy_position.quantity <= 0:
        logger.error("✗ No position created from BUY signal")
        return False
        
    logger.info(f"Position after BUY: {buy_position}")
    
    # 2. Create a SELL signal for the same symbol
    sell_signal = create_signal_event(
        signal_value=-1,  # SELL
        price=110.0,  # Higher price for profit
        symbol="TEST",
        rule_id="test_sell"
    )
    
    # Emit the SELL signal
    logger.info("Emitting SELL signal")
    event_bus.emit(sell_signal)
    
    # CRITICAL FIX: Significantly increase wait time to ensure event processing completes
    sleep(1.0)
    
    # Check position after sell
    sell_position = portfolio.get_position("TEST")
    
    if sell_position is None or sell_position.quantity == 0:
        logger.info("✓ Position closed after SELL")
        
        # Check for profit in portfolio
        cash_after = portfolio.cash
        if cash_after > 100000.0:
            logger.info(f"✓ Made profit: ${cash_after - 100000.0:.2f}")
            return True
        else:
            logger.error(f"✗ No profit made, cash: ${cash_after:.2f}")
            return False
    else:
        logger.error(f"✗ Position not fully closed: {sell_position}")
        return False

def test_order_registry_deduplication():
    """Test that the order registry correctly deduplicates orders."""
    logger.info("=== Test: Order Registry Deduplication ===")
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    order_registry = components['order_registry']
    
    # Create a unique order ID
    order_id = str(uuid.uuid4())
    
    # Create the same order event twice with the same ID
    order_event1 = create_order_event(
        symbol="TEST",
        order_type="MARKET",
        direction="BUY",
        quantity=100,
        price=100.0,
        order_id=order_id
    )
    
    order_event2 = create_order_event(
        symbol="TEST",
        order_type="MARKET",
        direction="BUY",
        quantity=100,
        price=100.0,
        order_id=order_id
    )
    
    # Emit the first order event
    logger.info(f"Emitting first order event with ID: {order_id}")
    event_bus.emit(order_event1)
    
    # CRITICAL FIX: Significantly increase wait time to ensure event processing completes
    sleep(1.0)
    
    # Verify order is in registry
    order1 = order_registry.get_order(order_id)
    if not order1:
        logger.error("✗ First order not found in registry")
        return False
        
    logger.info(f"First order registered: {order1}")
    
    # Get order count before second emission
    order_count_before = len(order_registry.orders)
    logger.info(f"Order count before second emission: {order_count_before}")
    
    # Emit the second identical order event
    logger.info(f"Emitting second order event with same ID: {order_id}")
    event_bus.emit(order_event2)
    
    # CRITICAL FIX: Significantly increase wait time to ensure event processing completes
    sleep(1.0)
    
    # Get order count after second emission
    order_count_after = len(order_registry.orders)
    logger.info(f"Order count after second emission: {order_count_after}")
    
    # Check if order count changed
    if order_count_after == order_count_before:
        logger.info("✓ Order registry correctly deduplicated the order")
        return True
    else:
        logger.error(f"✗ Order registry failed to deduplicate, counts: {order_count_before} -> {order_count_after}")
        return False

def test_risk_manager_deduplication():
    """Test that the risk manager correctly deduplicates signals."""
    logger.info("=== Test: Risk Manager Deduplication ===")
    
    # MODIFIED: Add more debug logging to understand test behavior
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    risk_manager = components['risk_manager']
    order_registry = components['order_registry']
    order_manager = components['order_manager']
    
    # For debugging purposes - log the risk manager instance
    logger.info(f"Risk manager instance: {risk_manager}")
    
    # Check initial variables to understand test state
    if hasattr(risk_manager, 'processed_rule_ids'):
        logger.info(f"Initial processed_rule_ids: {risk_manager.processed_rule_ids}")
    
    # Get initial order count
    initial_order_count = len(order_registry.orders)
    logger.info(f"Initial order count: {initial_order_count}")
    
    # Create a signal with a unique identifier in the rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Generated unique rule_id: {rule_id}")
    
    # CRITICAL FIX: Ensure signal objects have different IDs but same rule_id
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
    
    # MODIFIED: Clear any existing rule IDs before test
    if hasattr(risk_manager, 'processed_rule_ids'):
        risk_manager.processed_rule_ids.clear()
        logger.info("Cleared processed_rule_ids before test")
    
    # MODIFIED: Synchronous version for cleaner debugging
    # Emit the first signal
    logger.info(f"Emitting first signal with rule_id: {rule_id}")
    
    # Reset processed_rule_ids to ensure we're starting clean
    risk_manager.processed_rule_ids.clear()  # CRITICAL FIX: Clear processed_rule_ids before test
    
    # Use the event bus this time so the signal goes through the whole event flow
    event_bus.emit(signal1)
    
    # Check order count after first signal
    sleep(1.0)  # Give time for order to be processed
    mid_order_count = len(order_registry.orders)
    logger.info(f"Order count after first signal: {mid_order_count}")
    
    # Emit the second identical signal
    logger.info(f"Emitting second signal with same rule_id: {rule_id}")
    event_bus.emit(signal2)  # Use event bus for consistent testing
    
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

def run_all_tests():
    """Run all order flow tests."""
    logger.info("======= Starting Order Flow Tests =======")
    
    tests = [
        test_create_order_direct,
        test_create_order_from_signal,
        test_create_sell_after_buy,
        test_order_registry_deduplication,
        test_risk_manager_deduplication
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
    run_all_tests()
