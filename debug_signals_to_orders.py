#!/usr/bin/env python
"""
Debug tool to trace the signal-to-order conversion process.
This script will simulate signals and check if they are properly converted to orders.
"""
import os
import sys
import logging
import datetime
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('signal_order_debug')

def main():
    """Main entry point."""
    logger.info("Signal-to-Order Debug Tool")
    
    try:
        # Import system components
        from src.core.bootstrap import bootstrap_system
        from src.core.container import Container
        from src.core.events.event_types import EventType
        from src.core.events.event_utils import create_signal_event
        
        # Create container and bootstrap the system
        container = Container()
        bootstrap_system('config/head_test.yaml', container)
        
        # Get required components
        event_bus = container.get('event_bus')
        risk_manager = container.get('risk_manager')
        order_registry = container.get('order_registry')
        order_manager = container.get('order_manager')
        
        # Enable verbose logging
        for component_name in ['src.risk.managers.simple', 'src.execution.order_registry', 
                              'src.execution.order_manager', 'src.core.events.event_bus']:
            logging.getLogger(component_name).setLevel(logging.DEBUG)
        
        logger.info("System components initialized")
        logger.info(f"Event bus: {event_bus}")
        logger.info(f"Risk manager: {risk_manager}")
        logger.info(f"Order registry: {order_registry}")
        logger.info(f"Order manager: {order_manager}")
        
        # Monitor events
        signal_events = []
        order_events = []
        
        def on_signal(event):
            logger.info(f"Signal received: {event.get_id()}")
            signal_events.append(event)
        
        def on_order(event):
            logger.info(f"Order created: {event.get_id()}")
            order_events.append(event)
        
        # Register event handlers
        event_bus.register(EventType.SIGNAL, on_signal)
        event_bus.register(EventType.ORDER, on_order)
        
        # Create test signals
        timestamp = datetime.datetime.now()
        
        # Buy signal
        logger.info("Creating and emitting BUY signal event")
        buy_signal = create_signal_event(
            signal_value=1,  # Buy
            price=100.0,
            symbol="SPY",
            rule_id="test_buy_signal",
            timestamp=timestamp
        )
        
        # Emit signal
        logger.info(f"Emitting buy signal: {buy_signal.get_id()}")
        event_bus.emit(buy_signal)
        
        # Wait briefly
        import time
        time.sleep(0.5)
        
        # Check results
        logger.info(f"Signal events received: {len(signal_events)}")
        logger.info(f"Order events created: {len(order_events)}")
        
        # Sell signal
        logger.info("Creating and emitting SELL signal event")
        sell_signal = create_signal_event(
            signal_value=-1,  # Sell
            price=105.0,
            symbol="SPY",
            rule_id="test_sell_signal",
            timestamp=timestamp
        )
        
        # Emit signal
        logger.info(f"Emitting sell signal: {sell_signal.get_id()}")
        event_bus.emit(sell_signal)
        
        # Wait briefly
        time.sleep(0.5)
        
        # Check final results
        logger.info(f"Final signal events received: {len(signal_events)}")
        logger.info(f"Final order events created: {len(order_events)}")
        
        # Check order registry
        active_orders = order_registry.get_active_orders()
        logger.info(f"Active orders in registry: {len(active_orders)}")
        for order in active_orders:
            logger.info(f"Order: {order}")
        
        # Check risk manager stats
        if hasattr(risk_manager, 'get_stats'):
            risk_stats = risk_manager.get_stats()
            logger.info(f"Risk manager stats: {risk_stats}")
        
        # Check event bus
        if hasattr(event_bus, 'get_stats'):
            event_stats = event_bus.get_stats()
            logger.info(f"Event bus stats: {event_stats}")
            
        if hasattr(event_bus, 'event_counts'):
            event_counts = event_bus.event_counts
            logger.info(f"Event counts: {event_counts}")
        
        # Check if order registry has order_ids attribute
        if hasattr(order_registry, 'orders'):
            logger.info(f"Order registry has {len(order_registry.orders)} orders")
            for order_id, order in order_registry.orders.items():
                logger.info(f"Order {order_id}: {order}")
    
    except Exception as e:
        logger.error(f"Error in signal-order debug: {e}", exc_info=True)

if __name__ == "__main__":
    main()
