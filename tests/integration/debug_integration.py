"""
Debug script for integration tests to identify where tests get stuck.
"""

import os
import sys
import time
import traceback

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import test modules
from tests.integration.test_strategy_risk_order_flow import TestStrategyRiskOrderFlow

def debug_test_end_to_end_flow():
    """
    Debug the end_to_end_flow test to see where it gets stuck.
    Add print statements at key points to trace execution.
    """
    print("\n=== Starting debug of test_end_to_end_flow ===")
    test = TestStrategyRiskOrderFlow()
    
    try:
        print("Setting up components...")
        setup_components = test.setup_components()
        print("Components created successfully:")
        for name, component in setup_components.items():
            print(f"  - {name}: {type(component).__name__}")
        
        event_bus = setup_components['event_bus']
        portfolio = setup_components['portfolio']
        strategy = setup_components['strategy']
        
        print("\nSetting up event trackers...")
        signal_events = []
        order_events = []
        fill_events = []
        
        def signal_tracker(event):
            print(f"Signal event received: {event.get_data()}")
            signal_events.append(event)
            return event
        
        def order_tracker(event):
            print(f"Order event received: {event.get_data()}")
            order_events.append(event)
            return event
        
        def fill_tracker(event):
            print(f"Fill event received: {event.get_data()}")
            fill_events.append(event)
            return event
        
        print("Registering event handlers...")
        event_bus.register(event_bus.EventType.SIGNAL, signal_tracker)
        event_bus.register(event_bus.EventType.ORDER, order_tracker)
        event_bus.register(event_bus.EventType.FILL, fill_tracker)
        
        print("\nCreating bar events...")
        bar_events = test.bar_events(setup_components)
        print(f"Created {len(bar_events)} bar events")
        
        print("\nProcessing bar events...")
        for i, event in enumerate(bar_events[:10]):  # Only process first 10 for debugging
            print(f"Processing bar event {i+1}/10...")
            print(f"Event data: {event.get_data()}")
            event_bus.emit(event)
            print(f"Event {i+1} processed")
            
            # Print state after each event
            print(f"  Signal events: {len(signal_events)}")
            print(f"  Order events: {len(order_events)}")
            print(f"  Fill events: {len(fill_events)}")
        
        print("\nTest execution completed successfully")
        
    except Exception as e:
        print(f"\nError during test execution: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_test_end_to_end_flow()
