#!/usr/bin/env python
"""
Debug tool for analyzing the event system in the trading framework.
This script will monitor and log all events flowing through the system
to help diagnose issues with signal-to-order-to-fill flow.
"""
import os
import sys
import logging
import inspect
import datetime
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug_events.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("debug")

class EventDebugger:
    """Debug wrapper for event bus to trace all events."""
    
    def __init__(self, event_bus, log_dir="event_logs"):
        """Initialize the event debugger with an existing event bus."""
        self.event_bus = event_bus
        self.log_dir = log_dir
        self.handlers = {}
        self.event_counts = {}
        self.event_latencies = {}
        self.event_flow = []
        
        # Create log directory
        os.makedirs(log_dir, exist_ok=True)
        
        logger.info(f"Event debugger initialized for {self.event_bus}")
        
        # Hook into event bus
        self._hook_event_bus()
    
    def _hook_event_bus(self):
        """Hook into event bus to intercept all events."""
        logger.info("Hooking into event bus...")
        
        # Store original emit method
        if hasattr(self.event_bus, 'emit'):
            self.original_emit = self.event_bus.emit
            
            # Replace with our debug version
            def debug_emit(event):
                # Track event
                self._track_event('emit', event)
                
                # Call original
                return self.original_emit(event)
            
            # Replace the method
            self.event_bus.emit = debug_emit
            logger.info("Hooked into event bus emit method")
        else:
            logger.warning("Event bus does not have emit method!")
        
        # Also hook register if available
        if hasattr(self.event_bus, 'register'):
            self.original_register = self.event_bus.register
            
            # Replace with our debug version
            def debug_register(event_type, handler):
                # Track registration
                handler_name = self._get_handler_name(handler)
                logger.info(f"Registering handler {handler_name} for event type {event_type}")
                
                # Store in our tracking
                if event_type not in self.handlers:
                    self.handlers[event_type] = []
                self.handlers[event_type].append(handler_name)
                
                # Call original
                return self.original_register(event_type, handler)
            
            # Replace the method
            self.event_bus.register = debug_register
            logger.info("Hooked into event bus register method")
            
    def _get_handler_name(self, handler):
        """Get a meaningful name for a handler function."""
        if hasattr(handler, '__self__'):
            # Method of an object
            return f"{handler.__self__.__class__.__name__}.{handler.__name__}"
        elif hasattr(handler, '__name__'):
            # Function
            return handler.__name__
        else:
            # Lambda or other callable
            return str(handler)
    
    def _track_event(self, action, event):
        """Track an event being emitted or processed."""
        # Get event details
        event_type = event.get_type() if hasattr(event, 'get_type') else str(type(event))
        event_id = event.get_id() if hasattr(event, 'get_id') else id(event)
        timestamp = datetime.datetime.now()
        
        # Extract data if available
        event_data = None
        if hasattr(event, 'data'):
            event_data = event.data
        
        # Update counts
        if event_type not in self.event_counts:
            self.event_counts[event_type] = 0
        self.event_counts[event_type] += 1
        
        # Record in event flow
        flow_record = {
            'timestamp': timestamp,
            'action': action,
            'event_type': event_type,
            'event_id': event_id,
            'data': event_data
        }
        self.event_flow.append(flow_record)
        
        # Log to file
        event_log_file = os.path.join(self.log_dir, f"{event_type}.log")
        with open(event_log_file, 'a') as f:
            f.write(f"{timestamp} - {action} - {event_id}: {event_data}\n")
        
        # Log to console
        logger.debug(f"EVENT {action}: {event_type} ({event_id})")
        if event_data:
            logger.debug(f"Event data: {event_data}")
    
    def get_event_counts(self):
        """Get counts of all tracked events."""
        return dict(self.event_counts)
    
    def get_handler_map(self):
        """Get map of event types to handlers."""
        return dict(self.handlers)
    
    def get_event_flow(self, limit=None):
        """Get flow of events in chronological order."""
        if limit and limit > 0:
            return self.event_flow[-limit:]
        return list(self.event_flow)
    
    def analyze_event_flow(self):
        """Analyze event flow to detect issues."""
        results = {
            'total_events': len(self.event_flow),
            'event_counts': self.get_event_counts(),
            'issues': []
        }
        
        # Check for signal events that didn't lead to order events
        signal_events = [e for e in self.event_flow if e['event_type'] == 'SIGNAL']
        order_events = [e for e in self.event_flow if e['event_type'] == 'ORDER']
        
        if signal_events and not order_events:
            results['issues'].append({
                'type': 'no_orders_from_signals',
                'message': f"Found {len(signal_events)} signal events but no order events",
                'details': f"Check risk manager and order manager for issues"
            })
        
        # Check for order events that didn't lead to fill events
        fill_events = [e for e in self.event_flow if e['event_type'] == 'FILL']
        
        if order_events and not fill_events:
            results['issues'].append({
                'type': 'no_fills_from_orders',
                'message': f"Found {len(order_events)} order events but no fill events",
                'details': f"Check broker and execution system for issues"
            })
        
        return results

def inject_event_debugger(system_container):
    """Inject event debugger into an existing system."""
    logger.info("Injecting event debugger into system...")
    
    # Get event bus from container
    event_bus = None
    if hasattr(system_container, 'get'):
        try:
            event_bus = system_container.get('event_bus')
            logger.info(f"Found event bus: {event_bus}")
        except Exception as e:
            logger.error(f"Error getting event bus: {e}")
    
    if not event_bus:
        logger.error("Could not find event bus in system container")
        return None
    
    # Create debugger
    debugger = EventDebugger(event_bus)
    
    # Return for later access
    return debugger

def main():
    """Main entry point when run as a script."""
    logger.info("Starting event system debugger")
    
    # We need to import the system here to avoid circular imports
    try:
        from src.core.bootstrap import bootstrap_system
        from src.core.container import Container
        
        # Create container
        container = Container()
        
        # Bootstrap system
        bootstrap_system('config/head_test.yaml', container)
        
        # Inject debugger
        debugger = inject_event_debugger(container)
        
        # Run system
        if container.has('backtest_coordinator'):
            coordinator = container.get('backtest_coordinator')
            logger.info("Running backtest...")
            coordinator.run()
            
            # Analyze events
            if debugger:
                analysis = debugger.analyze_event_flow()
                logger.info(f"Event analysis: {analysis}")
                
                # Check for issues
                if analysis['issues']:
                    logger.warning(f"Found {len(analysis['issues'])} issues in event flow!")
                    for issue in analysis['issues']:
                        logger.warning(f"Issue: {issue['message']}")
                        logger.warning(f"Details: {issue['details']}")
        else:
            logger.error("Backtest coordinator not found in container")
    
    except Exception as e:
        logger.error(f"Error running event debugger: {e}", exc_info=True)
    
    logger.info("Event system debugger completed")

if __name__ == "__main__":
    main()
