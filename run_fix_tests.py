#!/usr/bin/env python
"""
Run all deduplication fix tests.

This script runs all the tests to verify the signal deduplication fix:
1. Deduplication test - Testing all new components
2. Implementation test - Testing integration with existing system
"""
import os
import subprocess
import sys
import time

def run_test(test_file):
    """Run a test script and return result."""
    print(f"\n{'='*60}")
    print(f"Running test: {test_file}")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run([sys.executable, test_file], capture_output=False)
    end_time = time.time()
    
    elapsed = end_time - start_time
    success = result.returncode == 0
    
    print(f"\nTest {test_file} {'PASSED' if success else 'FAILED'} in {elapsed:.2f} seconds")
    return success

def run_all_tests():
    """Run all tests for the deduplication fix."""
    tests = [
        "deduplication_test.py",
        "implementation_test.py"
    ]
    
    results = {}
    
    for test_file in tests:
        results[test_file] = run_test(test_file)
    
    # Print summary
    print("\n")
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    
    for test_file, success in results.items():
        status = "PASSED" if success else "FAILED"
        print(f"{test_file}: {status}")
        if success:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(tests)}")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
