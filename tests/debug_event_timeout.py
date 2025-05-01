"""
Debug script to identify where Event class is causing timeouts.
This script runs each step individually with timing to isolate the issue.
"""

import sys
import os
import time
import traceback

# Add project root to path so 'src' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def time_function(func, *args, **kwargs):
    """Run a function and time how long it takes."""
    start_time = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        print(f"SUCCESS: Function completed in {elapsed:.6f} seconds")
        return result, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"ERROR: Function failed after {elapsed:.6f} seconds")
        traceback.print_exc()
        return None, elapsed

def step1_import_event_type():
    """Step 1: Just import EventType."""
    from src.core.events.event_types import EventType
    return EventType

def step2_import_event():
    """Step 2: Import Event class."""
    from src.core.events.event_types import Event
    return Event

def step3_create_event(Event, EventType):
    """Step 3: Create a basic Event instance."""
    data = {'test': 'data'}
    event = Event(EventType.BAR, data)
    return event

def step4_access_attributes(event):
    """Step 4: Access Event attributes."""
    results = {}
    results['event_type'] = event.event_type
    results['data'] = event.data
    
    if hasattr(event, 'id'):
        results['id'] = event.id
    
    if hasattr(event, 'timestamp'):
        results['timestamp'] = event.timestamp
    
    return results

def step5_add_property(Event):
    """Step 5: Add type property."""
    # Add type property to bridge event_type to type
    if not hasattr(Event, 'type'):
        @property
        def type_property(self):
            """Bridge property to access event_type as type."""
            return self.event_type
        
        Event.type = type_property
        print("Added 'type' property to Event class")
    else:
        print("Event class already has 'type' property")
    
    return Event

def step6_test_property(event):
    """Step 6: Test the type property."""
    # Access through property
    return event.type

def main():
    """Run each step with timing to identify where the issue occurs."""
    print("STEP 1: Import EventType")
    EventType, elapsed1 = time_function(step1_import_event_type)
    
    print("\nSTEP 2: Import Event")
    Event, elapsed2 = time_function(step2_import_event)
    
    if Event is None:
        print("Could not import Event class, stopping test.")
        return
    
    print("\nSTEP 3: Create Event instance")
    event, elapsed3 = time_function(step3_create_event, Event, EventType)
    
    if event is None:
        print("Could not create Event instance, stopping test.")
        return
    
    print("\nSTEP 4: Access Event attributes")
    attrs, elapsed4 = time_function(step4_access_attributes, event)
    
    if attrs is None:
        print("Could not access Event attributes, stopping test.")
        return
    else:
        print(f"Event attributes: {attrs}")
    
    print("\nSTEP 5: Add type property to Event class")
    extended_Event, elapsed5 = time_function(step5_add_property, Event)
    
    if extended_Event is None:
        print("Could not extend Event class, stopping test.")
        return
    
    print("\nSTEP 6: Test type property")
    type_value, elapsed6 = time_function(step6_test_property, event)
    
    if type_value is not None:
        print(f"Type property value: {type_value}")
    
    print("\nAll steps completed!")
    print(f"Total time: {elapsed1 + elapsed2 + elapsed3 + elapsed4 + elapsed5 + elapsed6:.6f} seconds")

if __name__ == "__main__":
    print("Starting debug for Event class timeout issue...")
    main()
