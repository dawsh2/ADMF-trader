#!/usr/bin/env python
"""
Extremely focused debug script for Event class issues.
"""

import sys
import os
import threading
import time
import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("Starting Event class debug...")

def run_with_timeout(func, timeout=1, *args, **kwargs):
    """Run a function with a very short timeout."""
    result = {"completed": False, "result": None, "error": None}
    completed = threading.Event()
    
    def run_func():
        try:
            result["result"] = func(*args, **kwargs)
            result["completed"] = True
            completed.set()
        except Exception as e:
            result["error"] = e
            completed.set()
    
    thread = threading.Thread(target=run_func)
    thread.daemon = True
    
    print(f"Starting function with {timeout}s timeout...")
    start_time = time.time()
    thread.start()
    
    if not completed.wait(timeout):
        elapsed = time.time() - start_time
        print(f"TIMEOUT after {elapsed:.2f}s")
        return f"TIMEOUT after {elapsed:.2f}s"
    
    elapsed = time.time() - start_time
    if result["error"]:
        print(f"ERROR after {elapsed:.2f}s: {result['error']}")
        return f"ERROR: {result['error']}"
    
    print(f"SUCCESS after {elapsed:.2f}s")
    return result["result"]

def test_import_event_type():
    """Test importing EventType only."""
    print("Testing import of EventType...")
    from src.core.events.event_types import EventType
    return "Success"

def test_import_event():
    """Test importing Event class."""
    print("Testing import of Event...")
    from src.core.events.event_types import Event
    return "Success"

def test_event_init():
    """Test creating an Event instance."""
    print("Testing Event initialization...")
    from src.core.events.event_types import Event, EventType
    event = Event(EventType.BAR, {"test": "data"})
    return event

def test_event_properties():
    """Test accessing Event properties."""
    print("Testing Event properties...")
    from src.core.events.event_types import Event, EventType
    event = Event(EventType.BAR, {"test": "data"})
    
    # Try accessing each property separately with a very short timeout
    for prop_name in ['event_type', 'data', 'timestamp', 'id', 'consumed']:
        print(f"Accessing property: {prop_name}")
        start = time.time()
        value = getattr(event, prop_name)
        elapsed = time.time() - start
        print(f"  - {prop_name} = {value} (accessed in {elapsed:.6f}s)")
    
    return "Success"

def test_event_methods():
    """Test calling Event methods."""
    print("Testing Event methods...")
    from src.core.events.event_types import Event, EventType
    event = Event(EventType.BAR, {"test": "data"})
    
    # Try each method separately
    methods = [
        ('get_type', []),
        ('get_timestamp', []),
        ('get_id', []),
        ('is_consumed', []),
        ('mark_consumed', [])
    ]
    
    for method_name, args in methods:
        if hasattr(event, method_name):
            print(f"Calling method: {method_name}")
            method = getattr(event, method_name)
            start = time.time()
            result = method(*args)
            elapsed = time.time() - start
            print(f"  - {method_name}() = {result} (executed in {elapsed:.6f}s)")
        else:
            print(f"  - {method_name}: Method not found")
    
    return "Success"

def test_event_with_timestamp():
    """Test Event with custom timestamp."""
    print("Testing Event with custom timestamp...")
    from src.core.events.event_types import Event, EventType
    timestamp = datetime.datetime(2024, 1, 1, 10, 0, 0)
    event = Event(EventType.BAR, {"test": "data"}, timestamp)
    return event

def run_all_tests():
    """Run all tests sequentially with timeouts."""
    tests = [
        ("Import EventType", test_import_event_type),
        ("Import Event", test_import_event),
        ("Event initialization", test_event_init),
        ("Event properties", test_event_properties),
        ("Event methods", test_event_methods),
        ("Event with timestamp", test_event_with_timestamp)
    ]
    
    results = {}
    for name, func in tests:
        print(f"\n{'=' * 50}")
        print(f"Running test: {name}")
        print(f"{'=' * 50}")
        
        result = run_with_timeout(func, 2)
        results[name] = "SUCCESS" if not isinstance(result, str) else result
    
    # Print summary
    print("\n\nTest Results Summary:")
    print("=" * 50)
    for name, result in results.items():
        status = "PASS" if result == "SUCCESS" else "FAIL"
        print(f"{name}: {status} - {result}")
    
    # Check if a specific test failed with a timeout
    if any("TIMEOUT" in str(result) for result in results.values()):
        print("\nTimeout detected! There may be an infinite loop or deadlock.")
    
    # Check which test failed first
    failed_tests = [(name, result) for name, result in results.items() 
                   if result != "SUCCESS"]
    if failed_tests:
        first_failure = failed_tests[0]
        print(f"\nFirst failure: {first_failure[0]} - {first_failure[1]}")

if __name__ == "__main__":
    run_all_tests()
