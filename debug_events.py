#!/usr/bin/env python
"""
Debug script for ADMF-Trader to track order flow and execution.

This script runs a simplified version of your trading system with enhanced
debug logging to track the complete lifecycle of orders from signal to fill.
"""
import os
import logging
import datetime
import pandas as pd
import numpy as np
import uuid
from typing import Dict, List, Any, Optional
import time

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for maximum verbosity
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_order_flow.log', mode='w')
    ]
)

# Set up component-specific loggers
logger = logging.getLogger("OrderFlowDebugger")
order_logger = logging.getLogger("OrderFlow")
event_logger = logging.getLogger("EventSystem")
broker_logger = logging.getLogger("BrokerDebug")
registry_logger = logging.getLogger("RegistryDebug")

# Import system components - adjust these imports based on your actual structure
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_order_event, create_fill_event, create_signal_event
from src.execution.order_registry import OrderRegistry
from src.execution.order_manager import OrderManager
from src.execution.broker.broker_simulator import SimulatedBroker
from src.risk.portfolio.portfolio import PortfolioManager

class EventDebugger:
    """Debugger to monitor all events in the system."""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.event_counts = {}
        self.tracked_orders = {}  # order_id -> status tracking
        
        # Register for all event types
        for event_type_name in dir(EventType):
            if not event_type_name.startswith('_'):
                try:
                    event_type_value = getattr(EventType, event_type_name)
                    if isinstance(event_type_value, str):  # Only register string event types
                        self.event_counts[event_type_value] = 0
                        self.event_bus.register(event_type_value, self._on_event)
                except (AttributeError, TypeError):
                    pass
    
    def _on_event(self, event):
        """Track all events passing through the system."""
        event_type = event.type
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        # Track order-related events
        if event_type == EventType.ORDER:
            order_id = event.data.get('order_id')
            if order_id:
                self.tracked_orders[order_id] = {
                    'status': 'CREATED',
                    'symbol': event.data.get('symbol'),
                    'direction': event.data.get('direction'),
                    'quantity': event.data.get('quantity'),
                    'price': event.data.get('price'),
                    'created_at': datetime.datetime.now(),
                    'events': [('ORDER', datetime.datetime.now(), event.data)]
                }
                event_logger.debug(f"ORDER created: {order_id} - {event.data.get('symbol')} {event.data.get('direction')} {event.data.get('quantity')} @ {event.data.get('price')}")
                
        elif event_type == EventType.FILL:
            order_id = event.data.get('order_id')
            if order_id in self.tracked_orders:
                self.tracked_orders[order_id]['status'] = 'FILLED'
                self.tracked_orders[order_id]['filled_at'] = datetime.datetime.now()
                self.tracked_orders[order_id]['fill_price'] = event.data.get('price')
                self.tracked_orders[order_id]['events'].append(('FILL', datetime.datetime.now(), event.data))
                event_logger.debug(f"FILL for order: {order_id} - Price: {event.data.get('price')}")
            else:
                event_logger.warning(f"FILL for unknown order: {order_id}")
        
        elif event_type == EventType.ORDER_STATE_CHANGE:
            order_id = event.data.get('order_id')
            if order_id in self.tracked_orders:
                self.tracked_orders[order_id]['status'] = event.data.get('status')
                self.tracked_orders[order_id]['events'].append(('STATE_CHANGE', datetime.datetime.now(), event.data))
                event_logger.debug(f"STATE CHANGE for order {order_id}: {event.data.get('status')}")
            else:
                event_logger.warning(f"STATE CHANGE for unknown order: {order_id}")
    
    def report(self):
        """Generate a report of all tracked events."""
        logger.info("=== Event System Debug Report ===")
        logger.info("Event counts by type:")
        for event_type, count in self.event_counts.items():
            if count > 0:
                logger.info(f"  {event_type}: {count}")
        
        logger.info("\nOrder lifecycle tracking:")
        complete_orders = 0
        incomplete_orders = 0
        
        for order_id, data in self.tracked_orders.items():
            if data['status'] == 'FILLED':
                complete_orders += 1
                creation_time = data.get('created_at')
                fill_time = data.get('filled_at')
                if creation_time and fill_time:
                    duration = (fill_time - creation_time).total_seconds()
                    logger.info(f"  Order {order_id} - COMPLETE - {data['symbol']} {data['direction']} {data['quantity']} @ {data['price']} -> {data['fill_price']} (Duration: {duration:.3f}s)")
            else:
                incomplete_orders += 1
                logger.info(f"  Order {order_id} - INCOMPLETE - Status: {data['status']} - {data['symbol']} {data['direction']} {data['quantity']} @ {data['price']}")
                # Print event history for incomplete orders
                logger.info(f"    Event history:")
                for event_type, timestamp, event_data in data['events']:
                    logger.info(f"      {timestamp.strftime('%H:%M:%S.%f')[:-3]} - {event_type}")
        
        logger.info(f"\nSummary: {complete_orders} complete orders, {incomplete_orders} incomplete orders")


class BrokerDebugWrapper:
    """Wrapper to add detailed logging to the SimulatedBroker."""
    
    def __init__(self, broker):
        self.broker = broker
        
        # Store original methods
        self.original_on_order = broker.on_order
        if hasattr(broker, 'process_order'):
            self.original_process_order = broker.process_order
        
        # Replace methods with debug versions
        broker.on_order = self._debug_on_order
        if hasattr(broker, 'process_order'):
            broker.process_order = self._debug_process_order
        
        # Check for other order handling methods
        if hasattr(broker, 'on_order_state_change'):
            self.original_on_order_state_change = broker.on_order_state_change
            broker.on_order_state_change = self._debug_on_order_state_change
    
    def _debug_on_order(self, order_event):
        """Debug wrapper for on_order method."""
        broker_logger.debug(f"BROKER on_order CALLED with order_id: {order_event.data.get('order_id')}")
        
        # Call original method
        result = self.original_on_order(order_event)
        
        broker_logger.debug(f"BROKER on_order COMPLETED for order_id: {order_event.data.get('order_id')}")
        return result
    
    def _debug_process_order(self, order):
        """Debug wrapper for process_order method."""
        broker_logger.debug(f"BROKER process_order CALLED for order_id: {order.order_id}, symbol: {order.symbol}, direction: {order.direction}, quantity: {order.quantity}, price: {order.price}")
        
        # Call original method
        result = self.original_process_order(order)
        
        broker_logger.debug(f"BROKER process_order COMPLETED for order_id: {order.order_id}")
        if hasattr(self.broker, 'last_fill_event'):
            broker_logger.debug(f"BROKER generated fill event: {self.broker.last_fill_event}")
        return result
    
    def _debug_on_order_state_change(self, event):
        """Debug wrapper for on_order_state_change method."""
        order_id = event.data.get('order_id')
        status = event.data.get('status')
        broker_logger.debug(f"BROKER on_order_state_change CALLED with order_id: {order_id}, status: {status}")
        
        # Call original method
        result = self.original_on_order_state_change(event)
        
        broker_logger.debug(f"BROKER on_order_state_change COMPLETED for order_id: {order_id}")
        return result


class RegistryDebugWrapper:
    """Wrapper to add detailed logging to the OrderRegistry."""
    
    def __init__(self, registry):
        self.registry = registry
        
        # Store original methods
        if hasattr(registry, 'update_order_status'):
            self.original_update_order_status = registry.update_order_status
            # Replace method with debug version
            registry.update_order_status = self._debug_update_order_status
        
        self.original_register_order = registry.register_order
        registry.register_order = self._debug_register_order
        
        self.original_on_order = registry.on_order
        registry.on_order = self._debug_on_order
        
        self.original_on_fill = registry.on_fill
        registry.on_fill = self._debug_on_fill
    
    def _debug_register_order(self, order):
        """Debug wrapper for register_order method."""
        registry_logger.debug(f"REGISTRY register_order CALLED for order_id: {order.order_id}")
        
        # Call original method
        result = self.original_register_order(order)
        
        registry_logger.debug(f"REGISTRY register_order COMPLETED with result: {result}")
        return result
    
    def _debug_update_order_status(self, order_id, new_status, **details):
        """Debug wrapper for update_order_status method."""
        registry_logger.debug(f"REGISTRY update_order_status CALLED for order_id: {order_id}, new_status: {new_status}")
        
        # Call original method
        result = self.original_update_order_status(order_id, new_status, **details)
        
        registry_logger.debug(f"REGISTRY update_order_status COMPLETED with result: {result}")
        return result
    
    def _debug_on_order(self, order_event):
        """Debug wrapper for on_order method."""
        registry_logger.debug(f"REGISTRY on_order CALLED with order_id: {order_event.data.get('order_id')}")
        
        # Call original method
        result = self.original_on_order(order_event)
        
        registry_logger.debug(f"REGISTRY on_order COMPLETED for order_id: {order_event.data.get('order_id')}")
        return result
    
    def _debug_on_fill(self, fill_event):
        """Debug wrapper for on_fill method."""
        registry_logger.debug(f"REGISTRY on_fill CALLED with order_id: {fill_event.data.get('order_id')}")
        
        # Call original method
        result = self.original_on_fill(fill_event)
        
        registry_logger.debug(f"REGISTRY on_fill COMPLETED for order_id: {fill_event.data.get('order_id')}")
        return result


def create_test_data(symbol, num_bars=100):
    """Create simple test data for debugging."""
    logger.info(f"Creating test data for {symbol}")
    
    # Create date range
    now = datetime.datetime.now()
    dates = [now - datetime.timedelta(minutes=i) for i in range(num_bars, 0, -1)]
    
    np.random.seed(42)  # For reproducibility
    
    # Generate simple price data
    base_price = 100.0
    price_data = []
    
    for i in range(num_bars):
        # Create a few clear crossover points
        if i % 20 == 0:  # Every 20 bars, create a potential signal
            # Add sine wave pattern for predictable crossovers
            sine_component = 5 * np.sin(i/10 * np.pi)
        else:
            sine_component = 0
            
        # Random walk with slight upward trend
        price = base_price + i * 0.01 + sine_component + np.random.normal(0, 0.1)
        price_data.append(price)
    
    # Create OHLCV data
    data = []
    for i, date in enumerate(dates):
        close = price_data[i]
        high = close * (1 + abs(np.random.normal(0, 0.005)))
        low = close * (1 - abs(np.random.normal(0, 0.005)))
        open_price = low + (high - low) * np.random.random()
        volume = int(np.random.exponential(10000))
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    # Create DataFrame
    return pd.DataFrame(data)


def debug_order_flow(test_data_symbol='DEBUG'):
    """Run a simplified version of the system to debug order flow."""
    logger.info("=== Starting Order Flow Debug Test ===")
    
    # Create test data
    df = create_test_data(test_data_symbol)
    
    # Create core components
    event_bus = EventBus()
    
    # Create order registry with debug wrapper
    order_registry = OrderRegistry(event_bus)
    registry_wrapper = RegistryDebugWrapper(order_registry)
    
    # Create portfolio manager
    portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
    
    # Create broker with debug wrapper
    broker = SimulatedBroker(event_bus, order_registry)
    broker_wrapper = BrokerDebugWrapper(broker)
    
    # Create order manager
    order_manager = OrderManager(event_bus, broker, order_registry)
    
    # Create event debugger to track all events
    event_debugger = EventDebugger(event_bus)
    
    # Register components with event bus - ensure correct registration order
    for event_type_name in dir(EventType):
        if not event_type_name.startswith('_'):
            try:
                event_type_value = getattr(EventType, event_type_name)
                if isinstance(event_type_value, str):  # Only register string event types
                    # Registry should receive events first
                    if hasattr(order_registry, f"on_{event_type_name.lower()}"):
                        handler = getattr(order_registry, f"on_{event_type_name.lower()}")
                        event_bus.register(event_type_value, handler)
                        logger.info(f"Registered registry handler for event type: {event_type_value}")
                    
                    # Order manager should receive events next
                    if hasattr(order_manager, f"on_{event_type_name.lower()}"):
                        handler = getattr(order_manager, f"on_{event_type_name.lower()}")
                        event_bus.register(event_type_value, handler)
                        logger.info(f"Registered order manager handler for event type: {event_type_value}")
                    
                    # Broker should receive events next
                    if hasattr(broker, f"on_{event_type_name.lower()}"):
                        handler = getattr(broker, f"on_{event_type_name.lower()}")
                        event_bus.register(event_type_value, handler)
                        logger.info(f"Registered broker handler for event type: {event_type_value}")
                    
                    # Portfolio should receive events last
                    if hasattr(portfolio, f"on_{event_type_name.lower()}"):
                        handler = getattr(portfolio, f"on_{event_type_name.lower()}")
                        event_bus.register(event_type_value, handler)
                        logger.info(f"Registered portfolio handler for event type: {event_type_value}")
            except (AttributeError, TypeError):
                pass
    
    # Special handling for order state change event if used in your system
    if hasattr(EventType, "ORDER_STATE_CHANGE") and hasattr(broker, "on_order_state_change"):
        event_bus.register(EventType.ORDER_STATE_CHANGE, broker.on_order_state_change)
        logger.info(f"Registered broker handler for ORDER_STATE_CHANGE event")
        
    logger.info("System components created and events registered")
    
    # Test 1: Create a few manual orders and track their lifecycle
    logger.info("\n=== Test 1: Manual Order Creation ===")
    
    # Create and emit a few signal events which should lead to orders
    for i in range(5):
        # Generate random BUY or SELL signal
        direction = 1 if np.random.random() > 0.5 else -1
        signal_type = "BUY" if direction > 0 else "SELL"
        
        # Get price from test data
        price_idx = min(i * 10, len(df) - 1)
        price = df.iloc[price_idx]['close']
        
        # Create signal event
        logger.info(f"Creating {signal_type} signal at price {price:.2f}")
        signal = create_signal_event(
            signal_value=direction,
            price=price,
            symbol=test_data_symbol,
            timestamp=df.iloc[price_idx]['timestamp']
        )
        
        # Instead of emitting signal, manually create order
        order_id = str(uuid.uuid4())
        order_event = create_order_event(
            symbol=test_data_symbol,
            order_type='MARKET',
            direction=signal_type,
            quantity=100,
            price=price,
            order_id=order_id
        )
        
        # Emit order event (will be captured by registry and broker)
        logger.info(f"Emitting order event with ID: {order_id}")
        event_bus.emit(order_event)
        
        # Pause slightly between orders
        time.sleep(0.1)
    
    # Generate report of all event activity
    event_debugger.report()
    
    # Verify portfolio state
    logger.info("\n=== Portfolio State After Test ===")
    logger.info(f"Cash: ${portfolio.cash:.2f}")
    logger.info(f"Positions: {portfolio.positions}")
    logger.info(f"Trades: {portfolio.trades}")
    
    # Examine registry state
    logger.info("\n=== Order Registry State After Test ===")
    logger.info(f"Total orders registered: {len(order_registry.orders)}")
    for order_id, order in order_registry.orders.items():
        logger.info(f"  Order {order_id}: Status={order.status}, Symbol={order.symbol}, Direction={order.direction}, Quantity={order.quantity}, Price={order.price}")
    
    # Check for any order state transitions
    logger.info("\n=== Order State Transitions ===")
    logger.info(f"Total state changes: {len(order_registry.state_changes)}")
    for order_id, transition, timestamp in order_registry.state_changes:
        logger.info(f"  {timestamp.strftime('%H:%M:%S.%f')[:-3]} - Order {order_id}: {transition}")
    
    return {
        'event_debugger': event_debugger,
        'order_registry': order_registry,
        'broker': broker,
        'portfolio': portfolio,
        'event_bus': event_bus
    }


def trace_order_from_signal(test_data_symbol='TRACE'):
    """Trace the complete lifecycle of an order from signal to fill."""
    logger.info("\n=== Detailed Order Lifecycle Tracing ===")
    
    # Create components
    event_bus = EventBus()
    
    # Extend the EventBus to trace all event emissions
    original_emit = event_bus.emit
    
    def traced_emit(event):
        logger.info(f"EVENT EMITTED: {event.type} - {event.data.get('order_id', 'N/A')}")
        return original_emit(event)
    
    event_bus.emit = traced_emit
    
    # Create components in proper order
    order_registry = OrderRegistry(event_bus)
    broker = SimulatedBroker(event_bus, order_registry)
    order_manager = OrderManager(event_bus, broker, order_registry)
    portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
    
    # Register event handlers in proper order
    # Order lifecycle: Signal → Order → Registry → Broker → Fill → Portfolio
    
    # 1. Signal → Order (usually handled by strategy)
    if hasattr(order_manager, "on_signal"):
        event_bus.register(EventType.SIGNAL, order_manager.on_signal)
    
    # 2. Order → Registry
    if hasattr(order_registry, "on_order"):
        event_bus.register(EventType.ORDER, order_registry.on_order)
    
    # 3. Registry → Order State Change
    if hasattr(EventType, "ORDER_STATE_CHANGE") and hasattr(broker, "on_order_state_change"):
        event_bus.register(EventType.ORDER_STATE_CHANGE, broker.on_order_state_change)
    
    # 4. Order → Manager (after registry)
    if hasattr(order_manager, "on_order"):
        event_bus.register(EventType.ORDER, order_manager.on_order)
    
    # 5. Order → Broker
    if hasattr(broker, "on_order"):
        event_bus.register(EventType.ORDER, broker.on_order)
    
    # 6. Fill → Registry
    if hasattr(order_registry, "on_fill"):
        event_bus.register(EventType.FILL, order_registry.on_fill)
    
    # 7. Fill → Portfolio (after registry)
    if hasattr(portfolio, "on_fill"):
        event_bus.register(EventType.FILL, portfolio.on_fill)
    
    # Create a sample signal
    price = 100.0
    
    logger.info(f"Step 1: Emitting BUY signal for {test_data_symbol} at {price}")
    signal = create_signal_event(
        signal_value=1,  # BUY
        price=price,
        symbol=test_data_symbol,
        timestamp=datetime.datetime.now()
    )
    
    # Emit the signal
    event_bus.emit(signal)
    
    # Check results
    logger.info("\nTracing Results:")
    logger.info(f"Orders in registry: {len(order_registry.orders)}")
    for order_id, order in order_registry.orders.items():
        logger.info(f"  Order {order_id}: Status={order.status}, Symbol={order.symbol}, Direction={order.direction}, Quantity={order.quantity}, Price={order.price}")
    
    logger.info(f"Trades in portfolio: {len(portfolio.trades)}")
    for trade in portfolio.trades:
        logger.info(f"  Trade: {trade}")
    
    return {
        'event_bus': event_bus,
        'order_registry': order_registry,
        'broker': broker,
        'order_manager': order_manager,
        'portfolio': portfolio
    }


if __name__ == "__main__":
    logger.info("Starting order flow debugging")
    
    # Run simple debug test
    results = debug_order_flow()
    
    # Run detailed trace
    trace_results = trace_order_from_signal()
    
    logger.info("Order flow debugging complete")
