#!/usr/bin/env python
"""
Test runner for event system tests.

This script runs the unit tests for the event system to verify 
the core functionality is working correctly.
"""

import unittest
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_runner')

def run_tests():
    """Run event system tests."""
    # Ensure the project root is in the Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    # Import the test module
    from tests.core.event_system.test_event_system import EventTests, EventBusTests
    
    # Create test suite
    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(EventTests))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(EventBusTests))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Report results
    logger.info(f"Tests run: {result.testsRun}")
    logger.info(f"Errors: {len(result.errors)}")
    logger.info(f"Failures: {len(result.failures)}")
    
    return len(result.errors) + len(result.failures) == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)