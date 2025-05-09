#!/usr/bin/env python3
# chmod +x demo_safe_events.py  # Make this file executable
"""
Demo script showing how to use the enhanced event bus safety features.
This demonstrates configurable limits, event tracking, and timeout protection.
"""
import time
import logging
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from tests.adapters import EventBusAdapter
from tests.utils.event_tracker import EventMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("demo")

def run_demo():
    """Run a demonstration of the safe event bus features."""
    logger.info("Starting Safe Event Bus Demo")
    
    # Create event bus with enhanced safety
    event_bus = EventBus()
    EventBusAdapter.apply(
        event_bus,
        max_events=100,       # Limit to 100 events per type
        recursion_limit=5,    # Limit recursion depth to 5
        event_timeout=1.0     # Timeout after 1 second
    )
    
    # Define some event handlers
    def signal_handler(event):
        logger.info(f"Signal handler processing: {event.get_data()}")
        # Create an order event
        order_data = {
            "symbol": event.get_data().get("symbol", "UNKNOWN"),
            "quantity": 100,
            "price": 150.0,
            "direction": "BUY"
        }
        order_event = Event(EventType.ORDER, order_data)
        event_bus.emit(order_event)
        return event
    
    def order_handler(event):
        logger.info(f"Order handler processing: {event.get_data()}")
        # Create a fill event
        fill_data = {
            "symbol": event.get_data().get("symbol"),
            "quantity": event.get_data().get("quantity"),
            "price": event.get_data().get("price"),
            "direction": event.get_data().get("direction"),
            "commission": 1.50
        }
        fill_event = Event(EventType.FILL, fill_data)
        event_bus.emit(fill_event)
        return event
    
    def fill_handler(event):
        logger.info(f"Fill handler processing: {event.get_data()}")
        # Just log the fill
        return event
    
    def slow_handler(event):
        logger.info(f"Slow handler processing: {event.get_data()}")
        # Simulate slow processing
        logger.info("Slow handler sleeping for 2 seconds...")
        time.sleep(2.0)  # This should be caught by the timeout
        logger.info("Slow handler woke up!")  # This likely won't be reached
        return event
    
    def recursive_handler(event):
        logger.info(f"Recursive handler processing: {event.get_data()}")
        # Create an event of the same type - would cause infinite recursion without protection
        logger.info("Creating recursive event - should be caught by safety measures")
        event_bus.emit(event)
        return event
    
    # Register handlers
    event_bus.register(EventType.SIGNAL, signal_handler)
    event_bus.register(EventType.ORDER, order_handler)
    event_bus.register(EventType.FILL, fill_handler)
    event_bus.register(EventType.BAR, slow_handler)
    event_bus.register(EventType.SIGNAL, recursive_handler)
    
    # Start event monitoring
    with EventMonitor(event_bus) as monitor:
        # Test 1: Normal event chain
        logger.info("\n=== TEST 1: Normal Event Chain ===")
        signal_event = Event(EventType.SIGNAL, {"symbol": "AAPL"})
        event_bus.emit(signal_event)
        
        # Test 2: Slow handler with timeout
        logger.info("\n=== TEST 2: Slow Handler with Timeout ===")
        bar_event = Event(EventType.BAR, {"symbol": "MSFT", "close": 200.0})
        start = time.time()
        event_bus.emit(bar_event)
        duration = time.time() - start
        logger.info(f"Slow handler processed in {duration:.2f} seconds (should be ~1 second due to timeout)")
        
        # Test 3: Recursive events
        logger.info("\n=== TEST 3: Recursive Event Protection ===")
        signal_event_recursive = Event(EventType.SIGNAL, {"symbol": "GOOG", "quantity": 50})
        event_bus.emit(signal_event_recursive)
        
        # Print event statistics
        logger.info("\n=== Event Statistics ===")
        stats = event_bus.get_event_stats()
        logger.info(f"Total events processed: {stats['total_events']}")
        for event_type, count in stats.get('event_counts', {}).items():
            logger.info(f"  {event_type}: {count} events")
        
        # Print monitor summary
        logger.info("\n=== Event Monitor Summary ===")
        monitor.print_summary()

if __name__ == "__main__":
    run_demo()
