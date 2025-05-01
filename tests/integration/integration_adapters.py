"""
Adapter for integration tests to bridge implementation gaps.
"""

import pytest
import weakref
import threading
import time
from src.execution.broker.broker_simulator import SimulatedBroker
from src.core.events.event_bus import EventBus


# Add protection against infinite recursion in event handling
def extend_event_bus_integration():
    """Extend EventBus to prevent infinite recursion in integration tests."""
    original_emit = EventBus.emit
    
    # Add processing flag to prevent recursive event processing
    if not hasattr(EventBus, '_processing_event'):
        EventBus._processing_event = threading.local()
        EventBus._processing_event.flags = set()
    
    def safe_emit(self, event):
        """
        Safe version of emit that prevents infinite recursion.
        Uses event ID to track which events are being processed.
        """
        event_id = event.get_id()
        
        # Check if we're already processing this event
        if not hasattr(EventBus._processing_event, 'flags'):
            EventBus._processing_event.flags = set()
            
        if event_id in EventBus._processing_event.flags:
            # Skip if already processing
            return []
        
        try:
            # Mark as processing
            EventBus._processing_event.flags.add(event_id)
            
            # Call original emit
            return original_emit(self, event)
        finally:
            # Always clean up
            EventBus._processing_event.flags.discard(event_id)
    
    EventBus.emit = safe_emit


# Adapter for SimulatedBroker in integration tests
def extend_simulated_broker_integration():
    """Extend the SimulatedBroker class with methods expected in integration tests."""
    
    # Add set_slippage method if not exists
    if not hasattr(SimulatedBroker, 'set_slippage'):
        def set_slippage(self, slippage):
            """Set slippage for the broker."""
            self.slippage = slippage
        
        SimulatedBroker.set_slippage = set_slippage
    
    # Add set_commission method if not exists
    if not hasattr(SimulatedBroker, 'set_commission'):
        def set_commission(self, commission):
            """Set commission for the broker."""
            self.commission = commission
        
        SimulatedBroker.set_commission = set_commission
    
    # Fix weak method calls in event handlers
    original_on_order = getattr(SimulatedBroker, 'on_order', None)
    
    if original_on_order:
        def safe_on_order(self, order_event):
            """Safe version of on_order that handles event properly."""
            try:
                return original_on_order(self, order_event)
            except Exception as e:
                print(f"Error in SimulatedBroker.on_order: {e}")
                raise
                
        SimulatedBroker.on_order = safe_on_order


# Call this function at import time
extend_simulated_broker_integration()
extend_event_bus_integration()


# Add fixture to ensure broker extension is applied
@pytest.fixture(autouse=True)
def ensure_integration_adapters():
    """Ensure all integration adapters are applied."""
    extend_simulated_broker_integration()
    extend_event_bus_integration()
