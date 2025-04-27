#!/usr/bin/env python
"""
Detailed Order-Fill Flow Debug Script

This script precisely tracks the flow of order IDs through the entire
order -> fill event sequence to identify where problems occur.
"""
import logging
import datetime
import uuid
import time
import types
import sys
import traceback
import json

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('detailed_order_flow_debug.log', mode='w')
    ]
)
logger = logging.getLogger("DetailedDebug")

# Import core components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event, OrderEvent, FillEvent
from src.core.events.event_utils import create_signal_event, create_order_event, create_fill_event
from src.execution.broker.broker_simulator import SimulatedBroker
from src.execution.order_manager import OrderManager, Order, OrderStatus

def inspect_function(func_name, module_name=None):
    """Inspect a function's source code and arguments."""
    import inspect
    
    # Try to import the module if provided
    if module_name:
        try:
            module = __import__(module_name, fromlist=[''])
            func = getattr(module, func_name)
        except (ImportError, AttributeError):
            logger.error(f"Could not import {func_name} from {module_name}")
            return None
    else:
        # Try to find the function in current globals
        func = globals().get(func_name)
        if not func:
            logger.error(f"Function {func_name} not found in globals")
            return None
    
    # Get the source code
    try:
        source = inspect.getsource(func)
        logger.info(f"Source for {func_name}:\n{source}")
    except Exception as e:
        logger.error(f"Could not get source for {func_name}: {e}")
    
    # Get the signature
    try:
        sig = inspect.signature(func)
        logger.info(f"Signature for {func_name}: {sig}")
    except Exception as e:
        logger.error(f"Could not get signature for {func_name}: {e}")
    
    return func

def trace_event_data(event, label="Event"):
    """Print detailed info about an event."""
    logger.info(f"--- {label} Details ---")
    logger.info(f"Event Type: {event.get_type().name}")
    logger.info(f"Event ID: {event.get_id()}")
    logger.info(f"Event Timestamp: {event.get_timestamp()}")
    
    # Print data dictionary
    if hasattr(event, 'data'):
        logger.info(f"Event Data: {json.dumps(event.data, default=str)}")
    
    # Print specific fields based on event type
    if hasattr(event, 'get_symbol'):
        logger.info(f"Symbol: {event.get_symbol()}")
    if hasattr(event, 'get_direction'):
        logger.info(f"Direction: {event.get_direction()}")
    if hasattr(event, 'get_quantity'):
        logger.info(f"Quantity: {event.get_quantity()}")
    if hasattr(event, 'get_price'):
        logger.info(f"Price: {event.get_price()}")
    
    logger.info("-" * 40)

def run_detailed_order_flow_test():
    """Very detailed debug test that precisely tracks order ID flow."""
    logger.info("================================================")
    logger.info("=== Starting Detailed Order-Fill Flow Debug ===")
    logger.info("================================================")
    
    # Track important data for debug
    debug_data = {
        'ids': {},
        'events': {},
        'function_details': {}
    }
    
    # 1. Inspect key functions to verify parameters and implementation
    logger.info("STEP 1: Inspecting key functions")
    
    # Inspect create_fill_event function
    logger.info("Inspecting create_fill_event function...")
    create_fill_func = inspect_function('create_fill_event', 'src.core.events.event_utils')
    debug_data['function_details']['create_fill_event'] = create_fill_func is not None
    
    # 2. Create components
    logger.info("STEP 2: Creating system components")
    event_bus = EventBus()
    broker = SimulatedBroker(event_bus)
    order_manager = OrderManager(event_bus, broker)
    
    # Register handlers for the test
    event_bus.register(EventType.ORDER, order_manager.on_order)
    event_bus.register(EventType.FILL, order_manager.on_fill)
    
    # 3. Add instrumentation to broker's process_order method
    logger.info("STEP 3: Instrumenting broker's process_order method")
    original_process_order = broker.process_order
    
    def instrumented_process_order(self, order_event):
        """Instrumented version of process_order with detailed logging."""
        logger.info(">>> BROKER.process_order entry point")
        
        # Log the input order event
        trace_event_data(order_event, "Input Order Event")
        
        # Record order_id from event data
        order_id = None
        if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
            order_id = order_event.data.get('order_id')
            if order_id:
                logger.info(f"Extracted order_id from event data: {order_id}")
                debug_data['ids']['broker_extracted_order_id'] = order_id
            else:
                logger.warning("No order_id found in order event data!")
        
        # Call original method
        fill_event = original_process_order(order_event)
        
        # Log the output fill event
        if fill_event:
            trace_event_data(fill_event, "Output Fill Event")
            
            # Check if order_id carried through
            fill_order_id = None
            if hasattr(fill_event, 'data') and isinstance(fill_event.data, dict):
                fill_order_id = fill_event.data.get('order_id')
                if fill_order_id:
                    logger.info(f"Fill event contains order_id: {fill_order_id}")
                    debug_data['ids']['broker_fill_order_id'] = fill_order_id
                else:
                    logger.warning("Fill event does not contain order_id!")
                    # Try to fix it
                    if order_id:
                        fill_event.data['order_id'] = order_id
                        logger.info(f"Manually added order_id to fill event: {order_id}")
            
            debug_data['events']['broker_fill'] = fill_event
        else:
            logger.warning("Broker did not return a fill event!")
        
        logger.info("<<< BROKER.process_order exit point")
        return fill_event
    
    # Apply instrumentation
    broker.process_order = types.MethodType(instrumented_process_order, broker)
    
    # 4. Add instrumentation to order manager's on_order and on_fill methods
    logger.info("STEP 4: Instrumenting order manager methods")
    
    original_on_order = order_manager.on_order
    def instrumented_on_order(self, order_event):
        """Instrumented version of on_order with detailed logging."""
        logger.info(">>> ORDER_MANAGER.on_order entry point")
        
        # Log the input order event
        trace_event_data(order_event, "Input Order Event")
        
        # Record order_id from event data
        order_id = None
        if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
            order_id = order_event.data.get('order_id')
            if order_id:
                logger.info(f"Found order_id in event data: {order_id}")
                debug_data['ids']['manager_received_order_id'] = order_id
            else:
                logger.warning("No order_id found in order event data!")
        
        # Call original method
        result = original_on_order(order_event)
        
        # Log the result
        logger.info(f"on_order returned: {result}")
        
        # Check if order was stored correctly
        if order_id:
            if order_id in self.orders:
                logger.info(f"Order {order_id} correctly stored in order manager")
                debug_data['ids']['manager_stored_order_id'] = order_id
            else:
                logger.warning(f"Order {order_id} NOT found in order manager storage!")
                logger.info(f"Orders in manager: {list(self.orders.keys())}")
        
        logger.info("<<< ORDER_MANAGER.on_order exit point")
        return result
    
    original_on_fill = order_manager.on_fill
    def instrumented_on_fill(self, fill_event):
        """Instrumented version of on_fill with detailed logging."""
        logger.info(">>> ORDER_MANAGER.on_fill entry point")
        
        # Log the input fill event
        trace_event_data(fill_event, "Input Fill Event")
        
        # Record order_id from fill data
        fill_order_id = None
        if hasattr(fill_event, 'data') and isinstance(fill_event.data, dict):
            fill_order_id = fill_event.data.get('order_id')
            if fill_order_id:
                logger.info(f"Found order_id in fill event data: {fill_order_id}")
                debug_data['ids']['manager_received_fill_order_id'] = fill_order_id
            else:
                logger.warning("No order_id found in fill event data!")
        
        # Show all orders in manager before processing
        logger.info(f"Orders in manager before fill: {list(self.orders.keys())}")
        
        # Call original method
        try:
            result = original_on_fill(fill_event)
            logger.info(f"on_fill completed successfully")
        except Exception as e:
            logger.error(f"on_fill threw exception: {e}")
            logger.error(traceback.format_exc())
        
        logger.info("<<< ORDER_MANAGER.on_fill exit point")
        return result
    
    # Apply instrumentation
    order_manager.on_order = types.MethodType(instrumented_on_order, order_manager)
    order_manager.on_fill = types.MethodType(instrumented_on_fill, order_manager)
    
    # 5. Direct test with known, fixed order ID
    logger.info("STEP 5: Direct test with fixed order ID")
    test_order_id = str(uuid.uuid4())
    logger.info(f"Generated test order ID: {test_order_id}")
    debug_data['ids']['original_order_id'] = test_order_id
    
    # Create order event manually
    order_event = OrderEvent(
        symbol='AAPL',
        order_type='MARKET',
        direction='BUY',
        quantity=100,
        price=150.0
    )
    
    # Explicitly add order_id to data
    order_event.data['order_id'] = test_order_id
    logger.info(f"Added order_id to order event data: {test_order_id}")
    debug_data['events']['original_order'] = order_event
    
    # Process DIRECTLY through broker
    logger.info("Processing order DIRECTLY through broker...")
    fill_event = broker.process_order(order_event)
    
    # Check result
    if fill_event:
        logger.info("Broker returned a fill event")
        
        # Check if order_id made it through
        fill_order_id = None
        if hasattr(fill_event, 'data') and isinstance(fill_event.data, dict):
            fill_order_id = fill_event.data.get('order_id')
            if fill_order_id:
                logger.info(f"Fill contains order_id: {fill_order_id}")
                debug_data['ids']['direct_fill_order_id'] = fill_order_id
                
                # Compare IDs
                if fill_order_id == test_order_id:
                    logger.info("✓ Original order ID matches fill order ID in direct test!")
                else:
                    logger.error("✗ Original order ID does not match fill order ID!")
                    logger.error(f"  Original: {test_order_id}")
                    logger.error(f"  Fill: {fill_order_id}")
            else:
                logger.error("Fill event does not contain order_id!")
    else:
        logger.error("No fill event returned from broker!")
    
    # 6. Full event flow test with another order
    logger.info("STEP 6: Full event flow test")
    flow_order_id = str(uuid.uuid4())
    logger.info(f"Generated flow test order ID: {flow_order_id}")
    debug_data['ids']['flow_order_id'] = flow_order_id
    
    # Create new order for flow test
    flow_order_event = OrderEvent(
        symbol='MSFT',
        order_type='MARKET', 
        direction='BUY',
        quantity=50,
        price=250.0
    )
    
    # Add order_id to data
    flow_order_event.data['order_id'] = flow_order_id
    logger.info(f"Added order_id to flow order event data: {flow_order_id}")
    debug_data['events']['flow_order'] = flow_order_event
    
    # Send through event bus
    logger.info("Emitting order event through event bus...")
    event_bus.emit(flow_order_event)
    
    # Wait a moment for processing
    time.sleep(0.1)
    
    # 7. Direct test forcing order creation in manager
    logger.info("STEP 7: Direct test of order manager")
    direct_order_id = str(uuid.uuid4())
    logger.info(f"Generated direct order ID: {direct_order_id}")
    debug_data['ids']['direct_order_id'] = direct_order_id
    
    # Create order object directly
    direct_order = Order(
        symbol='GOOGL',
        order_type='MARKET',
        direction='BUY',
        quantity=25,
        price=100.0,
        order_id=direct_order_id
    )
    
    # Manually add to order manager
    order_manager.orders[direct_order_id] = direct_order
    order_manager.active_orders.add(direct_order_id)
    logger.info(f"Manually added order {direct_order_id} to order manager")
    
    # Create fill event with matching order_id
    direct_fill = FillEvent(
        symbol='GOOGL',
        direction='BUY',
        quantity=25,
        price=100.0,
        commission=0.0
    )
    
    # Add order_id to data
    direct_fill.data['order_id'] = direct_order_id
    logger.info(f"Added order_id to direct fill event data: {direct_order_id}")
    
    # Process through on_fill directly
    logger.info("Calling on_fill method directly...")
    order_manager.on_fill(direct_fill)
    
    # 8. Results analysis
    logger.info("STEP 8: Analyzing results")
    
    # Verify orders in manager
    logger.info(f"Final orders in manager: {list(order_manager.orders.keys())}")
    
    # Log all tracked IDs
    logger.info("All tracked IDs:")
    for id_name, id_value in debug_data['ids'].items():
        logger.info(f"  {id_name}: {id_value}")
    
    # Check key matches
    if 'original_order_id' in debug_data['ids'] and 'direct_fill_order_id' in debug_data['ids']:
        if debug_data['ids']['original_order_id'] == debug_data['ids']['direct_fill_order_id']:
            logger.info("✓ Direct test: Original order ID matches fill order ID")
        else:
            logger.error("✗ Direct test: Original order ID does not match fill order ID")
    
    if 'flow_order_id' in debug_data['ids'] and 'manager_stored_order_id' in debug_data['ids']:
        if debug_data['ids']['flow_order_id'] in order_manager.orders:
            logger.info("✓ Flow test: Order ID found in order manager")
        else:
            logger.error("✗ Flow test: Order ID not found in order manager")
    
    logger.info("=== Detailed Order-Fill Flow Debug Complete ===")
    return debug_data

if __name__ == "__main__":
    try:
        logger.info("Starting detailed order flow debug script")
        debug_results = run_detailed_order_flow_test()
        logger.info("Debug script completed successfully")
    except Exception as e:
        logger.error(f"Error in debug script: {e}", exc_info=True)
