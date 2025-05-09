#!/usr/bin/env python
"""
Test isolator script with Python path fix that runs individual test methods in isolation
to identify which specific test is causing issues.
"""

import argparse
import importlib.util
import inspect
import sys
import time
import traceback
import threading
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_python_path():
    """Add project root to Python path."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    return project_root

def fix_event_class():
    """Fix Event class to have 'type' property."""
    try:
        from src.core.events.event_types import Event
        
        # Add type property if it doesn't exist
        if not hasattr(Event, 'type'):
            @property
            def type_property(self):
                """Bridge property to access event_type as type."""
                return self.event_type
            
            # Add the type property
            Event.type = type_property
            # The type property has been added
    except ImportError as e:
        logger.warning(f"Could not import Event class: {e}")
    except Exception as e:
        logger.warning(f"Error fixing Event class: {e}")

def import_module_from_path(file_path):
    """Import a module from a file path."""
    module_name = os.path.basename(file_path).replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def find_test_classes(module):
    """Find all test classes in a module."""
    test_classes = []
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and name.startswith('Test'):
            test_classes.append(obj)
    return test_classes

def find_test_methods(test_class):
    """Find all test methods in a class."""
    test_methods = []
    for name, method in inspect.getmembers(test_class, predicate=inspect.isfunction):
        if name.startswith('test_'):
            test_methods.append(name)
    return test_methods

def run_test_method_with_timeout(test_class, method_name, timeout_seconds=10):
    """Run a test method with timeout protection."""
    instance = test_class()
    method = getattr(instance, method_name)
    
    # Create event for signaling completion
    complete_event = threading.Event()
    exception = [None]  # List to store exception if one occurs
    result = [None]  # List to store result
    
    # Thread function to run the test
    def run_test():
        try:
            # Set up method if needed
            if hasattr(instance, 'setUp'):
                instance.setUp()
            
            # Run the test method
            result[0] = method()
            
            # Tear down if needed
            if hasattr(instance, 'tearDown'):
                instance.tearDown()
                
            # Signal completion
            complete_event.set()
        except Exception as e:
            # Store exception
            exception[0] = e
            traceback.print_exc()
            complete_event.set()
    
    # Create and start thread
    thread = threading.Thread(target=run_test, daemon=True)
    start_time = time.time()
    thread.start()
    
    # Wait for completion or timeout
    complete = complete_event.wait(timeout_seconds)
    elapsed = time.time() - start_time
    
    if complete:
        if exception[0] is None:
            return True, elapsed, "PASSED"
        else:
            return False, elapsed, f"FAILED: {str(exception[0])}"
    else:
        return False, elapsed, "TIMEOUT"

def main():
    # Setup Python path
    project_root = setup_python_path()
    logger.info(f"Added project root to Python path: {project_root}")
    
    # Fix Event class
    fix_event_class()
    
    parser = argparse.ArgumentParser(description="Run individual test methods in isolation")
    parser.add_argument("file", help="Path to test file")
    parser.add_argument("--list", action="store_true", help="List test methods only")
    parser.add_argument("--class", dest="class_name", help="Run only tests from this class")
    parser.add_argument("--method", help="Run only this method")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    try:
        # Import module
        logger.info(f"Importing test file: {args.file}")
        module = import_module_from_path(args.file)
        
        # Find test classes
        test_classes = find_test_classes(module)
        
        if args.class_name:
            # Filter to specified class
            test_classes = [cls for cls in test_classes if cls.__name__ == args.class_name]
            if not test_classes:
                logger.error(f"Class '{args.class_name}' not found in {args.file}")
                return 1
        
        if args.list:
            # List test methods only
            print(f"\nTest methods in {args.file}:")
            for cls in test_classes:
                print(f"\nClass: {cls.__name__}")
                methods = find_test_methods(cls)
                for method in methods:
                    print(f"  - {method}")
            return 0
        
        # Run tests
        results = []
        
        for cls in test_classes:
            logger.info(f"Running tests from class: {cls.__name__}")
            methods = find_test_methods(cls)
            
            if args.method:
                # Filter to specified method
                if args.method in methods:
                    methods = [args.method]
                else:
                    logger.warning(f"Method '{args.method}' not found in class {cls.__name__}")
                    continue
            
            for method in methods:
                print(f"  Running {method}...", end="", flush=True)
                success, elapsed, status = run_test_method_with_timeout(cls, method, args.timeout)
                print(f" {status} ({elapsed:.2f}s)")
                results.append((cls.__name__, method, success, elapsed, status))
        
        # Print summary
        print("\nTest Summary:")
        print("-" * 80)
        passed = sum(1 for _, _, success, _, _ in results if success)
        total = len(results)
        print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed < total:
            print("\nFailed tests:")
            for cls_name, method, success, elapsed, status in results:
                if not success:
                    print(f"  - {cls_name}.{method}: {status} ({elapsed:.2f}s)")
        
        return 0 if passed == total else 1
    
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
