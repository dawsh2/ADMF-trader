# event_debugger.py
#!/usr/bin/env python
"""
Event System Debugger - A tool to diagnose event flow issues in the ADMF-Trader system.
"""

import logging
import sys
import time
import uuid
from enum import Enum
from typing import Dict, List, Any, Optional

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('event_debug.log', mode='w')
    ]
)

# Create specialized logger
logger = logging.getLogger("EventDebugger")

# Import core components
try:
    from src.core.events.event_bus import EventBus
    from src.core.events.event_types import EventType, Event
    from src.core.events.event_utils import create_order_event, create_fill_event
    from src.execution.order_manager import OrderManager, OrderStatus
    from src.execution.broker.broker_simulator import SimulatedBroker
    from src.risk.portfolio.portfolio import PortfolioManager
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

# Event tracing wrapper for event bus
class TracingEventBus:
    """Wrapper around EventBus to trace all events."""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.event_log = []
        
        # Monkey patch the emit method
        self._original_emit = event_bus.emit
        event_bus.emit = self._traced_emit
    
    def _traced_emit(self, event):
        """Traced version of emit that logs events."""
        event_type = event.get_type().name
        timestamp = event.get_timestamp()
        
        # Log the event
        logger.debug(f"EVENT EMITTED: {event_type} at {timestamp}")
        
        # Store event details
        event_details = {
            'type': event_type,
            'timestamp': timestamp,
            'data': event.data,
            'id': event.get_id()
        }
        self.event_log.append(event_details)
        
        # Special handling for specific event types
        if event_type == 'ORDER':
            logger.debug(f"  Order: {event.data.get('direction')} {event.data.get('quantity')} {event.data.get('symbol')} @ {event.data.get('price')}")
            logger.debug(f"  Order ID: {event.data.get('order_id')}")
        elif event_type == 'FILL':
            logger.debug(f"  Fill: {event.data.get('direction')} {event.data.get('quantity')} {event.data.get('symbol')} @ {event.data.get('price')}")
            logger.debug(f"  Order ID: {event.data.get('order_id')}")
        
        # Forward to actual emit method
        return self._original_emit(event)
    
    def get_event_log(self):
        """Get the recorded event log."""
        return self.event_log
    
    def print_event_summary(self):
        """Print a summary of emitted events."""
        event_counts = {}
        for event in self.event_log:
            event_type = event['type']
            if event_type not in event_counts:
                event_counts[event_type] = 0
            event_counts[event_type] += 1
        
        logger.info("=== Event Summary ===")
        for event_type, count in event_counts.items():
            logger.info(f"{event_type}: {count} events")

# Debugging helpers
def inspect_object(obj, name="Object"):
    """Inspect an object's attributes and methods."""
    logger.debug(f"=== Inspecting {name} ===")
    
    # Get non-callable attributes
    logger.debug("Attributes:")
    for attr in dir(obj):
        if not attr.startswith('_') and not callable(getattr(obj, attr)):
            try:
                value = getattr(obj, attr)
                logger.debug(f"  {attr}: {value}")
            except Exception as e:
                logger.debug(f"  {attr}: Error accessing - {e}")
    
    # Get methods
    logger.debug("Methods:")
    for attr in dir(obj):
        if not attr.startswith('_') and callable(getattr(obj, attr)):
            logger.debug(f"  {attr}()")

def run_basic_order_flow_test():
    """Run a basic test of the order-fill flow."""
    logger.info("=== Starting Basic Order Flow Test ===")
    
    # Create event bus with tracing
    event_bus = EventBus()
    tracing_bus = TracingEventBus(event_bus)
    
    # Create components
    broker = SimulatedBroker(event_bus)
    order_manager = OrderManager(event_bus, broker)
    portfolio = PortfolioManager(event_bus)
    
    # Set up correct event flow
    logger.info("Setting up event handlers...")
    event_bus.register(EventType.ORDER, order_manager.on_order)
    event_bus.register(EventType.ORDER, broker.on_order)
    event_bus.register(EventType.FILL, order_manager.on_fill)
    event_bus.register(EventType.FILL, portfolio.on_fill)
    
    # Test 1: Create an order and let it flow through the system
    logger.info("Test 1: Normal order flow")
    order_id = str(uuid.uuid4())
    
    # Create order event with explicit ID
    order_event = create_order_event(
        symbol="AAPL",
        order_type="MARKET",
        direction="BUY",
        quantity=100,
        price=150.0
    )
    order_event.data['order_id'] = order_id
    
    logger.info(f"Created order with ID: {order_id}")
    
    # Emit the order event
    logger.info("Emitting order event...")
    try:
        event_bus.emit(order_event)
        logger.info("Order event emitted successfully")
    except Exception as e:
        logger.error(f"Error emitting order: {e}", exc_info=True)
    
    # Wait for processing
    time.sleep(0.5)
    
    # Test 2: Create fill event directly to test orphaned fills
    logger.info("Test 2: Orphaned fill event")
    
    # Create a fill event with no corresponding order
    fill_event = create_fill_event(
        symbol="TSLA",
        direction="BUY",
        quantity=10,
        price=800.0,
        commission=8.0
    )
    
    # Emit the fill event
    logger.info("Emitting orphaned fill event...")
    try:
        event_bus.emit(fill_event)
        logger.info("Fill event emitted successfully")
    except Exception as e:
        logger.error(f"Error emitting fill: {e}", exc_info=True)
    
    # Wait for processing
    time.sleep(0.5)
    
    # Test 3: Two orders then fills for same symbol to test matching logic
    logger.info("Test 3: Multiple orders for same symbol")
    
    # Create two orders for same symbol
    order_id1 = str(uuid.uuid4())
    order_id2 = str(uuid.uuid4())
    
    order_event1 = create_order_event(
        symbol="MSFT",
        order_type="MARKET",
        direction="BUY",
        quantity=50,
        price=300.0
    )
    order_event1.data['order_id'] = order_id1
    
    order_event2 = create_order_event(
        symbol="MSFT",
        order_type="MARKET",
        direction="BUY",
        quantity=25,
        price=305.0
    )
    order_event2.data['order_id'] = order_id2
    
    # Emit the orders
    logger.info(f"Emitting first MSFT order with ID: {order_id1}")
    event_bus.emit(order_event1)
    
    logger.info(f"Emitting second MSFT order with ID: {order_id2}")
    event_bus.emit(order_event2)
    
    # Wait for processing
    time.sleep(0.5)
    
    # Event summary
    tracing_bus.print_event_summary()
    
    # Verify order_manager state
    logger.info("=== OrderManager State ===")
    logger.info(f"Total orders: {len(order_manager.orders)}")
    logger.info(f"Active orders: {len(order_manager.active_orders)}")
    
    # Inspect OrderStatus to verify it's accessible
    try:
        logger.info("OrderStatus values: " + str([status.name for status in OrderStatus]))
    except Exception as e:
        logger.error(f"Error accessing OrderStatus: {e}", exc_info=True)
    
    # Inspect specific problem areas
    inspect_object(order_manager, "OrderManager")
    inspect_object(broker, "SimulatedBroker")
    
    logger.info("Test completed")
    return tracing_bus.get_event_log()

def patch_order_manager():
    """Apply runtime patches to fix OrderManager issues."""
    logger.info("Patching OrderManager.on_fill method")
    
    # Store the original method
    original_on_fill = OrderManager.on_fill
    
    # Create a fixed version
    def patched_on_fill(self, fill_event):
        """Patched fill handler with proper imports."""
        logger.debug("Executing patched on_fill method")
        try:
            # Import here to ensure OrderStatus is available
            from src.execution.order_manager import OrderStatus
            
            # Extract fill details
            symbol = fill_event.get_symbol()
            direction = fill_event.get_direction()
            quantity = fill_event.get_quantity()
            price = fill_event.get_price()
            order_id = fill_event.data.get('order_id')
            
            logger.debug(f"Processing fill: {direction} {quantity} {symbol} @ {price:.2f}")
            logger.debug(f"Fill has order_id: {order_id}")
            
            # Find the order
            order = None
            if order_id and order_id in self.orders:
                order = self.orders[order_id]
                logger.debug(f"Found matching order by ID: {order_id}")
            else:
                # Try to match by symbol and direction
                matching_orders = [
                    o for o in [self.orders[oid] for oid in self.active_orders]
                    if o.symbol == symbol and o.direction == direction
                ]
                
                if matching_orders:
                    # Use the oldest matching order
                    order = min(matching_orders, key=lambda o: o.created_time)
                    order_id = order.order_id
                    logger.debug(f"Found matching order by symbol/direction: {order_id}")
                
            # If no order found, create a synthetic one
            if order is None:
                logger.warning(f"Creating synthetic order for orphaned fill: {symbol} {direction}")
                
                # Use Order class directly
                from src.execution.order_manager import Order
                
                # Create an order ID if needed
                if not order_id:
                    order_id = str(uuid.uuid4())
                
                # Create synthetic order
                order = Order(
                    symbol=symbol,
                    order_type='MARKET',
                    direction=direction,
                    quantity=quantity,
                    price=price
                )
                
                # Register the order
                self.orders[order_id] = order
                self.active_orders.add(order_id)
                self.stats['orders_created'] += 1
                
                logger.info(f"Created order: {order}")
            
            # Update the order
            status_name = 'FILLED' if quantity >= order.get_remaining_quantity() else 'PARTIAL'
            order.update_status(status_name, fill_quantity=quantity, fill_price=price)
            
            # Handle completed orders
            if order.is_filled():
                if order_id in self.active_orders:
                    self.active_orders.remove(order_id)
                self.order_history.append(order)
                self.stats['orders_filled'] += 1
            
            # Emit order status event
            self._emit_order_status_event(order)
            
            logger.info(f"Updated order with fill: {order}")
            return True
            
        except Exception as e:
            logger.error(f"Error in patched on_fill: {e}", exc_info=True)
            return False
    
    # Apply the patch
    OrderManager.on_fill = patched_on_fill
    logger.info("Patch applied to OrderManager.on_fill")

def patch_broker():
    """Apply runtime patches to fix SimulatedBroker issues."""
    logger.info("Patching SimulatedBroker.process_order method")
    
    # Store the original method
    original_process_order = SimulatedBroker.process_order
    
    # Create a fixed version
    def patched_process_order(self, order_event):
        """Patched process_order that properly preserves order_id."""
        logger.debug("Executing patched process_order method")
        self.stats['orders_processed'] += 1
        
        try:
            symbol = order_event.get_symbol()
            direction = order_event.get_direction()
            quantity = order_event.get_quantity()
            price = order_event.get_price()
            
            # Extract order_id from event data
            order_id = order_event.data.get('order_id')
            logger.debug(f"Processing order with ID: {order_id}")
            
            # Apply slippage to price
            if direction == 'BUY':
                fill_price = price * (1.0 + self.slippage)
            else:  # SELL
                fill_price = price * (1.0 - self.slippage)
            
            # Calculate commission
            commission = abs(quantity * fill_price) * self.commission
            
            # Create fill event
            from src.core.events.event_utils import create_fill_event
            
            fill_event = create_fill_event(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                price=fill_price,
                commission=commission,
                timestamp=order_event.get_timestamp()
            )
            
            # Make sure order_id is transferred to fill event
            if order_id:
                fill_event.data['order_id'] = order_id
                logger.debug(f"Added order_id {order_id} to fill event")
            
            self.stats['fills_generated'] += 1
            logger.info(f"Broker emitted fill event for {symbol}")
            
            return fill_event
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error processing order: {e}", exc_info=True)
            return None
    
    # Apply the patch
    SimulatedBroker.process_order = patched_process_order
    logger.info("Patch applied to SimulatedBroker.process_order")
    
    # Now patch the on_order method
    logger.info("Patching SimulatedBroker.on_order method")
    
    original_on_order = SimulatedBroker.on_order
    
    def patched_on_order(self, order_event):
        """Patched on_order with better error handling."""
        logger.debug("Executing patched on_order method")
        try:
            # Process the order
            fill_event = self.process_order(order_event)
            
            # If a fill was generated, emit it
            if fill_event and self.event_bus:
                # Small delay to ensure order is processed first
                time.sleep(0.01)
                
                # Verify order_id is in fill event
                if 'order_id' in order_event.data and 'order_id' not in fill_event.data:
                    fill_event.data['order_id'] = order_event.data['order_id']
                    logger.debug(f"Ensured order_id is in fill event: {fill_event.data['order_id']}")
                
                # Emit the fill event
                self.event_bus.emit(fill_event)
                logger.debug(f"Emitted fill event for {fill_event.get_symbol()}")
        except Exception as e:
            logger.error(f"Error in patched on_order: {e}", exc_info=True)
    
    # Apply the patch
    SimulatedBroker.on_order = patched_on_order
    logger.info("Patch applied to SimulatedBroker.on_order")

if __name__ == "__main__":
    logger.info("Starting ADMF-Trader Event System Debugger")
    
    # Apply patches
    patch_order_manager()
    patch_broker()
    
    # Run the test
    event_log = run_basic_order_flow_test()
    
    logger.info("Event debugging completed!")
    logger.info(f"Total events logged: {len(event_log)}")
    
    # Save event log to file for analysis
    import json
    with open('event_log.json', 'w') as f:
        json.dump(event_log, f, indent=2, default=str)
    
    logger.info("Event log saved to event_log.json")
