#!/usr/bin/env python
"""
Test script for the new Order Registry pattern.

This script creates a simple test environment to demonstrate
the Order Registry pattern's benefits in coordinating order flow.
"""
import logging
import datetime
import time
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('order_registry_test.log', mode='w')
    ]
)
logger = logging.getLogger("OrderRegistryTest")

# Import core components
from src.core.events.event_bus import EventBus
from src.core.events.event_manager import EventManager
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_signal_event, create_order_event

# Import execution components
from src.execution.order_registry import OrderRegistry
from src.execution.order_manager import OrderManager, OrderStatus
from src.execution.broker.broker_simulator import SimulatedBroker

# Import portfolio components
from src.risk.portfolio.portfolio import PortfolioManager

def test_order_creation_flow():
    """
    Test the flow of order creation, processing, and fills using the Order Registry.
    """
    logger.info("=== Starting Order Registry Test ===")
    
    # Create core components
    event_bus = EventBus()
    event_manager = EventManager(event_bus)
    
    # Create order registry
    logger.info("Creating Order Registry")
    order_registry = OrderRegistry(event_bus)
    
    # Create execution components
    logger.info("Creating Order Manager and Broker")
    order_manager = OrderManager(event_bus, None, order_registry)
    broker = SimulatedBroker(event_bus, order_registry)
    order_manager.broker = broker
    
    # Create portfolio manager
    logger.info("Creating Portfolio Manager")
    portfolio = PortfolioManager(event_bus)
    
    # Register components with event manager
    logger.info("Registering components with Event Manager")
    event_manager.register_component('portfolio', portfolio, [EventType.FILL])
    
    # Add some slippage and commission to make it realistic
    broker.slippage = 0.001  # 0.1% slippage
    broker.commission = 0.001  # 0.1% commission
    
    # Set initial portfolio cash
    portfolio.cash = 100000.0
    portfolio.equity = 100000.0
    
    # Create a test signal
    logger.info("Creating test signal")
    test_signal = create_signal_event(
        signal_value=1,  # Buy signal
        price=100.0,
        symbol='AAPL'
    )
    
    # Emit the signal and track order flow
    logger.info("Emitting signal")
    event_bus.emit(test_signal)
    
    # Wait a short time for all events to propagate
    logger.info("Waiting for events to propagate")
    time.sleep(0.1)
    
    # Check order registry state
    logger.info("Checking Order Registry state")
    registry_stats = order_registry.get_stats()
    logger.info(f"Order Registry stats: {registry_stats}")
    
    # Get all orders in registry
    orders = order_registry.orders
    logger.info(f"Orders in registry: {len(orders)}")
    
    for order_id, order in orders.items():
        logger.info(f"Order {order_id}: {order.symbol} {order.direction} {order.quantity} @ {order.price}, " +
                    f"Status: {order.status.value}, Filled: {order.filled_quantity}")
    
    # Check fill events in portfolio
    logger.info("Checking Portfolio state")
    logger.info(f"Portfolio cash: {portfolio.cash:.2f}")
    logger.info(f"Portfolio equity: {portfolio.equity:.2f}")
    
    # Check positions
    positions = portfolio.positions
    logger.info(f"Portfolio positions: {len(positions)}")
    
    for symbol, position in positions.items():
        logger.info(f"Position {symbol}: Quantity={position.quantity}, " +
                    f"Cost Basis={position.cost_basis:.2f}, " +
                    f"Value={position.market_value:.2f}")
        
    # Test cancellation
    if len(orders) > 0:
        # Create another order to cancel
        logger.info("Creating another order to test cancellation")
        order_id = order_manager.create_order(
            symbol='MSFT',
            order_type='LIMIT',
            direction='BUY',
            quantity=200,
            price=150.0
        )
        
        # Wait for order to be processed
        time.sleep(0.1)
        
        # Cancel the order
        logger.info(f"Cancelling order {order_id}")
        order_manager.cancel_order(order_id)
        
        # Wait for cancellation to process
        time.sleep(0.1)
        
        # Check order status
        order = order_registry.get_order(order_id)
        if order:
            logger.info(f"Cancelled order status: {order.status.value}")
        
    # Done
    logger.info("=== Order Registry Test Complete ===")
    
    # Return components for further inspection
    return {
        'event_bus': event_bus,
        'order_registry': order_registry,
        'order_manager': order_manager,
        'broker': broker,
        'portfolio': portfolio
    }

def test_race_condition_handling():
    """
    Test that the Order Registry handles race conditions properly.
    """
    logger.info("=== Starting Race Condition Test ===")
    
    # Create core components
    event_bus = EventBus()
    order_registry = OrderRegistry(event_bus)
    order_manager = OrderManager(event_bus, None, order_registry)
    broker = SimulatedBroker(event_bus, order_registry)
    order_manager.broker = broker
    
    # Create an order directly
    logger.info("Creating test order")
    order_id = order_manager.create_order(
        symbol='GOOGL',
        order_type='MARKET',
        direction='BUY',
        quantity=50,
        price=1500.0
    )
    
    # Creating a fill event before order is registered in broker
    # This tests the system's ability to handle out-of-order events
    logger.info("Creating fill event immediately (testing race condition)")
    from src.core.events.event_utils import create_fill_event
    
    # Create fill with matching order_id
    fill_event = create_fill_event(
        symbol='GOOGL',
        direction='BUY',
        quantity=50,
        price=1500.0,
        commission=0.0,
        order_id=order_id
    )
    
    # Emit fill immediately
    event_bus.emit(fill_event)
    
    # Wait a short time
    time.sleep(0.1)
    
    # Check order state in registry
    order = order_registry.get_order(order_id)
    if order:
        logger.info(f"Order status after race condition test: {order.status.value}")
        logger.info(f"Order filled quantity: {order.filled_quantity}")
        
        if order.status == OrderStatus.FILLED:
            logger.info("Race condition handling PASSED: Order was correctly filled.")
        else:
            logger.info("Race condition handling FAILED: Order was not filled correctly.")
    else:
        logger.error(f"Order {order_id} not found in registry after race condition test")
    
    logger.info("=== Race Condition Test Complete ===")
    return order_registry

if __name__ == "__main__":
    # Run the order creation flow test
    components = test_order_creation_flow()
    
    # Print registry order count
    order_registry = components['order_registry']
    logger.info(f"Order Registry contains {len(order_registry.orders)} orders")
    
    # Wait a bit
    time.sleep(0.5)
    
    # Run the race condition test
    race_registry = test_race_condition_handling()
    logger.info(f"Race Test Registry contains {len(race_registry.orders)} orders")
    
    # Done
    print("\nTests complete! Check order_registry_test.log for detailed results.")
