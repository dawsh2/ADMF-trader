#!/usr/bin/env python
"""
Script to debug test methods individually with timeout protection.
"""

import sys
import os
import time
import importlib.util
import inspect
import threading
import traceback

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the test class
def import_test_class(file_path, class_name):
    """Import test class from file path."""
    print(f"Importing test class {class_name} from {file_path}")
    
    try:
        # Get module name from file path
        module_name = os.path.basename(file_path).replace('.py', '')
        
        # Create spec
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Get test class
        if hasattr(module, class_name):
            return getattr(module, class_name)
        else:
            print(f"Class {class_name} not found in module")
            return None
    except Exception as e:
        print(f"Error importing test class: {e}")
        traceback.print_exc()
        return None

def run_test_method_with_timeout(instance, method_name, timeout=5):
    """Run a test method with timeout protection."""
    print(f"Running test method: {method_name}")
    
    # Get method
    method = getattr(instance, method_name)
    
    # Result flags
    result = {"success": False, "error": None}
    completed = threading.Event()
    
    # Thread function
    def run_test():
        try:
            # Run test method
            method()
            result["success"] = True
            completed.set()
        except Exception as e:
            result["error"] = e
            traceback.print_exc()
            completed.set()
    
    # Create and start thread
    thread = threading.Thread(target=run_test)
    thread.daemon = True
    thread.start()
    
    # Wait for completion or timeout
    start_time = time.time()
    completed.wait(timeout)
    elapsed = time.time() - start_time
    
    if completed.is_set():
        if result["success"]:
            print(f"PASSED: {method_name} - Completed in {elapsed:.2f}s")
            return True
        else:
            print(f"FAILED: {method_name} - Error: {result['error']} - Completed in {elapsed:.2f}s")
            return False
    else:
        print(f"TIMEOUT: {method_name} - Test did not complete in {timeout}s")
        return False

def main():
    """Main function."""
    # File path and class name
    file_path = "tests/integration/minimal_test_fixed.py"
    class_name = "TestMinimalIntegration"
    
    # Import test class
    test_class = import_test_class(file_path, class_name)
    if not test_class:
        return 1
    
    # Create instance
    instance = test_class()
    
    # Get test methods
    test_methods = []
    for name, method in inspect.getmembers(test_class, predicate=inspect.isfunction):
        if name.startswith("test_"):
            test_methods.append(name)
    
    print(f"Found {len(test_methods)} test methods: {', '.join(test_methods)}")
    
    # Run each test method with timeout
    results = {}
    for method_name in test_methods:
        print(f"\n{'=' * 50}")
        print(f"Testing: {method_name}")
        print(f"{'=' * 50}")
        
        # Create fresh instance for each test
        instance = test_class()
        
        # Run test with timeout
        success = run_test_method_with_timeout(instance, method_name, timeout=10)
        results[method_name] = success
    
    # Print summary
    print(f"\n{'=' * 50}")
    print("Test Summary:")
    print(f"{'=' * 50}")
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed < total:
        print("\nFailed tests:")
        for method_name, success in results.items():
            if not success:
                print(f"  - {method_name}")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
