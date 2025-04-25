#!/usr/bin/env python
"""
Event Flow Debug Script

This script creates a simplified event flow to debug the signal → order → fill sequence.
It uses explicit event tracking and bypasses the backtest coordinator.
"""
import logging
import uuid
import datetime
import pandas as pd
import numpy as np

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_event_flow.log', mode='w')
    ]
)
logger = logging.getLogger("DebugFlow")

# Import core components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from src.core.events.event_utils import (
    create_signal_event, create_order_event, create_fill_event,
    EventTracker
)
from src.risk.portfolio.portfolio import PortfolioManager
from src.risk.managers.simple import SimpleRiskManager
from src.execution.broker.broker_simulator import SimulatedBroker
from src.execution.order_manager import OrderManager

# Custom event tracer to track all events in the system
class EventSystemTracer:
    """Add detailed tracing to event bus and track all events."""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.events = []
        self.event_counts = {
            "SIGNAL": 0,
            "ORDER": 0,
            "FILL": 0,
            "OTHER": 0
        }
        
        # Monkey patch event_bus.emit
        self.original_emit = event_bus.emit
        event_bus.emit = self.traced_emit
    
    def traced_emit(self, event):
        """Traced version of event_bus.emit."""
        # Log event
        event_type = event.get_type().name
        
        # Count by type
        if event_type == "SIGNAL":
            self.event_counts["SIGNAL"] += 1
            count = self.event_counts["SIGNAL"]
            logger.debug(f"EVENT_EMIT: SIGNAL #{count} for {event.data.get('symbol')} value={event.data.get('signal_value')}")
        elif event_type == "ORDER":
            self.event_counts["ORDER"] += 1
            count = self.event_counts["ORDER"]
            logger.debug(f"EVENT_EMIT: ORDER #{count} {event.data.get('direction')} {event.data.get('quantity')} {event.data.get('symbol')} @ {event.data.get('price')}")
        elif event_type == "FILL":
            self.event_counts["FILL"] += 1
            count = self.event_counts["FILL"]
            logger.debug(f"EVENT_EMIT: FILL #{count} {event.data.get('direction')} {event.data.get('quantity')} {event.data.get('symbol')} @ {event.data.get('price')}")
        else:
            self.event_counts["OTHER"] += 1
            count = self.event_counts["OTHER"]
            logger.debug(f"EVENT_EMIT: {event_type} #{count}")
        
        # Store event for later analysis
        self.events.append(event)
        
        # Call original emit
        return self.original_emit(event)
    
    def print_summary(self):
        """Print summary of events."""
        logger.info("=== Event Summary ===")
        logger.info(f"Total events: {len(self.events)}")
        for event_type, count in self.event_counts.items():
            logger.info(f"  {event_type}: {count}")

# Monkey patch handlers with tracing
def add_method_tracing(instance, method_name):
    """Add tracing to method."""
    original_method = getattr(instance, method_name)
    
    def traced_method(*args, **kwargs):
        logger.debug(f"CALL: {instance.__class__.__name__}.{method_name} START")
        result = original_method(*args, **kwargs)
        logger.debug(f"CALL: {instance.__class__.__name__}.{method_name} END")
        return result
    
    setattr(instance, method_name, traced_method)
    return instance

def run_debug_test():
    """Run simplified test with direct signal injection."""
    logger.info("=== Starting Event Flow Debug ===")
    
    # Create components
    event_bus = EventBus()
    event_tracer = EventSystemTracer(event_bus)
    event_tracker = EventTracker('event_tracker')
    
    # Create portfolio
    portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
    
    # Create broker
    broker = SimulatedBroker(event_bus)
    
    # Create order manager
    order_manager = OrderManager(event_bus, broker)
    
    # Create risk manager
    risk_manager = SimpleRiskManager(event_bus, portfolio)
    
    # Add trace logging to key methods
    add_method_tracing(risk_manager, 'on_signal')
    add_method_tracing(order_manager, 'on_order')
    add_method_tracing(broker, 'process_order')
    add_method_tracing(portfolio, 'on_fill')
    
    # Register event handlers
    event_bus.register(EventType.SIGNAL, risk_manager.on_signal)
    event_bus.register(EventType.ORDER, order_manager.on_order)  
    event_bus.register(EventType.ORDER, broker.on_order)
    event_bus.register(EventType.FILL, order_manager.on_fill)
    event_bus.register(EventType.FILL, portfolio.on_fill)
    
    # Register event tracker for all event types
    for event_type in EventType:
        event_bus.register(event_type, event_tracker.track_event)
    
    # Create a signal
    logger.info("Injecting first signal (BUY)")
    signal_event1 = create_signal_event(
        signal_value=1, # BUY
        price=100.0,
        symbol='AAPL',
        timestamp=datetime.datetime.now()
    )
    
    # Emit the signal
    event_bus.emit(signal_event1)
    
    # Wait a moment to ensure events are processed
    import time
    time.sleep(0.1)
    
    # Create another signal
    logger.info("Injecting second signal (SELL)")
    signal_event2 = create_signal_event(
        signal_value=-1, # SELL
        price=120.0,
        symbol='MSFT',
        timestamp=datetime.datetime.now()
    )
    
    # Emit the signal
    event_bus.emit(signal_event2)
    
    # Wait for events to be processed
    time.sleep(0.1)
    
    # Print event summary
    event_tracer.print_summary()
    
    # Print portfolio state
    logger.info(f"Portfolio cash: ${portfolio.cash:.2f}")
    logger.info(f"Portfolio equity: ${portfolio.equity:.2f}")
    
    # Print order manager state
    logger.info(f"Orders created: {len(order_manager.orders)}")
    logger.info(f"Active orders: {len(order_manager.active_orders)}")
    logger.info(f"Order history: {len(order_manager.order_history)}")
    
    # Print event tracker summary
    logger.info("Event counts by type:")
    for event_type in EventType:
        count = event_tracker.get_event_count(event_type)
        if count > 0:
            logger.info(f"  {event_type.name}: {count}")
    
    return {
        'events': event_tracer.events,
        'portfolio': portfolio,
        'order_manager': order_manager
    }

if __name__ == "__main__":
    logger.info("Debug script starting")
    try:
        results = run_debug_test()
        logger.info("Debug script completed successfully")
    except Exception as e:
        logger.error(f"Error in debug script: {e}", exc_info=True)
