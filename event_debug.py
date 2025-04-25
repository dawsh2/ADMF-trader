#!/usr/bin/env python
"""
Order-Fill Flow Debug Script

This script specifically focuses on debugging the order-fill association
by tracking and displaying event IDs throughout the flow.
"""
import logging
import datetime
import uuid
import time

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_order_flow.log', mode='w')
    ]
)
logger = logging.getLogger("OrderFlowDebug")

# Import core components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from src.core.events.event_utils import create_signal_event, create_order_event, create_fill_event
from src.execution.broker.broker_simulator import SimulatedBroker
from src.execution.order_manager import OrderManager

def run_order_flow_test():
    """Test focusing specifically on order-fill association."""
    logger.info("=== Starting Order-Fill Flow Debug ===")
    
    # Create components
    event_bus = EventBus()
    
    # Create broker with custom logging
    broker = SimulatedBroker(event_bus)
    
    # Create order manager with custom logging
    order_manager = OrderManager(event_bus, broker)
    
    # Register event handlers
    event_bus.register(EventType.ORDER, order_manager.on_order)
    event_bus.register(EventType.ORDER, broker.on_order)
    event_bus.register(EventType.FILL, order_manager.on_fill)
    
    # Event flow tracking
    tracked_ids = {}
    
    # 1. Create an order directly (not via signal)
    logger.info("Step 1: Creating order")
    order_id = str(uuid.uuid4())
    logger.info(f"Generated order_id: {order_id}")
    
    # Store in tracking
    tracked_ids['original_order_id'] = order_id
    
    # Create order event with explicit order_id in data
    order_data = {
        'symbol': 'AAPL',
        'order_type': 'MARKET',
        'direction': 'BUY',
        'quantity': 100,
        'price': 150.0,
        'order_id': order_id  # Explicitly set
    }
    
    # Create order event
    order_event = create_order_event(
        symbol=order_data['symbol'],
        order_type=order_data['order_type'],
        direction=order_data['direction'],
        quantity=order_data['quantity'],
        price=order_data['price']
    )
    
    # Add order_id to event data
    order_event.data['order_id'] = order_id
    
    # Store event ID for tracking
    tracked_ids['order_event_id'] = order_event.get_id()
    
    logger.info(f"Created order event (ID: {order_event.get_id()}) with order_id: {order_id}")
    logger.info(f"Order event data: {order_event.data}")
    
    # 2. Register a callback to capture fill event
    def fill_callback(fill_event):
        logger.info(f"Fill callback received event (ID: {fill_event.get_id()})")
        tracked_ids['fill_event_id'] = fill_event.get_id()
        if hasattr(fill_event, 'data'):
            logger.info(f"Fill event data: {fill_event.data}")
            if 'order_id' in fill_event.data:
                tracked_ids['fill_order_id'] = fill_event.data['order_id']
                logger.info(f"Fill has order_id: {fill_event.data['order_id']}")
    
    event_bus.register(EventType.FILL, fill_callback)
    
    # 3. Process the order by broker directly
    logger.info("Step 2: Processing order through broker")
    fill_event = broker.process_order(order_event)
    
    if fill_event:
        logger.info(f"Broker returned fill event (ID: {fill_event.get_id()})")
        logger.info(f"Fill event data: {fill_event.data}")
        
        # Store fill details
        tracked_ids['broker_fill_id'] = fill_event.get_id()
        if hasattr(fill_event, 'data') and 'order_id' in fill_event.data:
            tracked_ids['broker_fill_order_id'] = fill_event.data['order_id']
    
    # 4. Emit order to test full event flow
    logger.info("Step 3: Emitting order through event bus")
    
    # Create a fresh order for a clean test
    new_order_id = str(uuid.uuid4())
    logger.info(f"Generated new order_id: {new_order_id}")
    tracked_ids['new_order_id'] = new_order_id
    
    new_order_event = create_order_event(
        symbol='MSFT',
        order_type='MARKET',
        direction='BUY',
        quantity=50,
        price=250.0
    )
    
    # Add order_id to event data
    new_order_event.data['order_id'] = new_order_id
    tracked_ids['new_order_event_id'] = new_order_event.get_id()
    
    logger.info(f"Emitting order event (ID: {new_order_event.get_id()}) with order_id: {new_order_id}")
    event_bus.emit(new_order_event)
    
    # Wait a moment for processing
    time.sleep(0.1)
    
    # 5. Verify created orders in order manager
    logger.info("Step 4: Checking order manager state")
    logger.info(f"Order manager has {len(order_manager.orders)} orders")
    
    for oid, order in order_manager.orders.items():
        logger.info(f"Order in manager: {oid} - Symbol: {order.symbol}, Direction: {order.direction}")
        tracked_ids[f"manager_order_{oid[-8:]}"] = oid
    
    # 6. Print status of all tracked IDs
    logger.info("=== ID Tracking Summary ===")
    for key, value in tracked_ids.items():
        logger.info(f"{key}: {value}")
    
    # 7. Check for ID matches
    if 'original_order_id' in tracked_ids and 'fill_order_id' in tracked_ids:
        if tracked_ids['original_order_id'] == tracked_ids['fill_order_id']:
            logger.info("✅ SUCCESS: Original order ID matches fill order ID")
        else:
            logger.error("❌ FAIL: Original order ID does not match fill order ID")
            
    if 'new_order_id' in tracked_ids:
        # Check if any order in manager matches
        found = False
        for key, value in tracked_ids.items():
            if key.startswith("manager_order_") and value == tracked_ids['new_order_id']:
                logger.info(f"✅ SUCCESS: New order ID found in order manager")
                found = True
                break
        
        if not found:
            logger.error("❌ FAIL: New order ID not found in order manager")
    
    return tracked_ids

if __name__ == "__main__":
    logger.info("Order flow debug script starting")
    try:
        results = run_order_flow_test()
        logger.info("Debug script completed successfully")
    except Exception as e:
        logger.error(f"Error in debug script: {e}", exc_info=True)
