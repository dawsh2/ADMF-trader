#!/usr/bin/env python
"""
Script to run integration tests with additional debugging.
"""

import argparse
import subprocess
import sys
import os
import importlib
import traceback

def run_integration_test_manually():
    """Run the integration test directly in this process for better debugging."""
    try:
        print("Importing integration test module...")
        from tests.integration.test_strategy_risk_order_flow import TestStrategyRiskOrderFlow
        
        print("\nCreating test instance...")
        test = TestStrategyRiskOrderFlow()
        
        print("\nSetting up components...")
        setup_components = test.setup_components()
        print("Components set up successfully")
        
        print("\nCreating bar events...")
        bar_events = test.bar_events(setup_components)
        print(f"Created {len(bar_events)} bar events")
        
        print("\nTesting end_to_end_flow with first 5 events only...")
        event_bus = setup_components['event_bus']
        portfolio = setup_components['portfolio']
        strategy = setup_components['strategy']
        
        # Track events
        signal_events = []
        order_events = []
        fill_events = []
        
        def signal_tracker(event):
            print(f"Signal received: {event.get_data()}")
            signal_events.append(event)
            return event
        
        def order_tracker(event):
            print(f"Order received: {event.get_data()}")
            order_events.append(event)
            return event
        
        def fill_tracker(event):
            print(f"Fill received: {event.get_data()}")
            fill_events.append(event)
            return event
        
        print("Registering handlers...")
        event_type = importlib.import_module("src.core.events.event_types").EventType
        event_bus.register(event_type.SIGNAL, signal_tracker)
        event_bus.register(event_type.ORDER, order_tracker)
        event_bus.register(event_type.FILL, fill_tracker)
        
        print("\nProcessing events...")
        for i, event in enumerate(bar_events[:5]):
            print(f"\nEvent {i+1}/5: Processing bar event...")
            event_bus.emit(event)
            print(f"Event {i+1} processed")
            
        print("\nTest successful!")
        print(f"Signal events: {len(signal_events)}")
        print(f"Order events: {len(order_events)}")
        print(f"Fill events: {len(fill_events)}")
    
    except Exception as e:
        print(f"\nError during test execution: {e}")
        traceback.print_exc()
        return 1
    
    return 0

def main():
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument("--pytest", action="store_true", help="Use pytest instead of direct execution")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    if args.pytest:
        # Run with pytest
        cmd = ["python", "-m", "pytest", "tests/integration/test_strategy_risk_order_flow.py", "-v"]
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, timeout=args.timeout)
        return result.returncode
    else:
        # Run manually
        print("Running integration test directly for better debugging...")
        return run_integration_test_manually()

if __name__ == "__main__":
    sys.exit(main())
