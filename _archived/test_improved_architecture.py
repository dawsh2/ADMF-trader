#!/usr/bin/env python3
"""
Test script for validating the improved architecture changes.
This script tests both the fixed validation script and the improved risk manager.
"""

import os
import sys
import logging
import subprocess
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"architecture_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def test_validation_script():
    """Test the fixed validation script."""
    logger.info("======== Testing Fixed Validation Script ========")
    
    # Run validation script with different parameters
    cmd = "python validate_ma_strategy_fixed.py --data-file ./data/MINI_1min.csv --symbol MINI --fast-window 5 --slow-window 15 --visualize"
    logger.info(f"Running: {cmd}")
    
    try:
        # Use subprocess to capture output
        result = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True)
        logger.info(f"Output: {result.stdout}")
        
        if result.returncode == 0:
            logger.info("Validation script test passed.")
        else:
            logger.error(f"Validation script test failed with error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error running validation script: {str(e)}")
        return False
    
    return True

def create_mock_log_file():
    """Create a mock log file for testing."""
    logger.info("Creating mock log file for validation testing")
    log_content = """
2024-03-26 13:35:00 - INFO - Trading decision: BUY 100 MINI @ 520.45, rule_id=MINI_BUY_OPEN_20240326133500, timestamp=2024-03-26 13:35:00, action=OPEN
2024-03-26 13:42:00 - INFO - Trading decision: SELL 100 MINI @ 520.85, rule_id=MINI_SELL_CLOSE_20240326134200, timestamp=2024-03-26 13:42:00, action=CLOSE
2024-03-26 13:42:00 - INFO - Trading decision: SELL 100 MINI @ 520.85, rule_id=MINI_SELL_OPEN_20240326134200, timestamp=2024-03-26 13:42:00, action=OPEN
2024-03-26 13:47:00 - INFO - Trading decision: BUY 100 MINI @ 521.25, rule_id=MINI_BUY_CLOSE_20240326134700, timestamp=2024-03-26 13:47:00, action=CLOSE
2024-03-26 13:47:00 - INFO - Trading decision: BUY 100 MINI @ 521.25, rule_id=MINI_BUY_OPEN_20240326134700, timestamp=2024-03-26 13:47:00, action=OPEN
2024-03-26 14:05:00 - INFO - Trading decision: SELL 100 MINI @ 520.15, rule_id=MINI_SELL_CLOSE_20240326140500, timestamp=2024-03-26 14:05:00, action=CLOSE
2024-03-26 14:05:00 - INFO - Trading decision: SELL 100 MINI @ 520.15, rule_id=MINI_SELL_OPEN_20240326140500, timestamp=2024-03-26 14:05:00, action=OPEN
    """
    
    # Write to file
    log_file = "improved_architecture_test.log"
    with open(log_file, 'w') as f:
        f.write(log_content)
    
    logger.info(f"Created mock log file: {log_file}")
    return log_file

def test_validation_with_log():
    """Test validation script with log comparison."""
    # Create mock log file
    log_file = create_mock_log_file()
    
    # Run validation with log comparison
    cmd = f"python validate_ma_strategy_fixed.py --data-file ./data/MINI_1min.csv --compare-log {log_file}"
    logger.info(f"Running comparison test: {cmd}")
    
    try:
        # Use subprocess to capture output
        result = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True)
        logger.info(f"Output: {result.stdout}")
        
        if result.returncode == 0:
            logger.info("Validation comparison test passed.")
            return True
        else:
            logger.error(f"Validation comparison test failed with error: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"Error running validation comparison: {str(e)}")
        return False

def test_risk_manager():
    """
    Create a simple test script for the risk manager and run it.
    This avoids issues with importing the actual classes in this test script.
    """
    logger.info("======== Testing Improved Risk Manager ========")
    
    # Create a temporary test file
    test_file = "test_risk_manager_temp.py"
    test_code = '''
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger()

# Create mock classes to test the risk manager
class MockEvent:
    def __init__(self, id, symbol, signal_value, price, timestamp=None):
        self._id = id
        self._symbol = symbol
        self._signal_value = signal_value
        self._price = price
        self._timestamp = timestamp or datetime.now()
        self._consumed = False
        self._type = "SIGNAL"  # Add event type
    
    def is_consumed(self):
        return self._consumed
    
    def mark_consumed(self):
        self._consumed = True
    
    def get_id(self):
        return self._id
    
    def get_symbol(self):
        return self._symbol
    
    def get_signal_value(self):
        return self._signal_value
    
    def get_price(self):
        return self._price
    
    def get_timestamp(self):
        return self._timestamp
    
    def get_type(self):
        return self._type  # Add method to get event type

# Mock EventTracker that doesn't track anything
class MockEventTracker:
    def __init__(self, name):
        self.name = name
    
    def track_event(self, event):
        pass  # Do nothing
    
    def reset(self):
        pass

class MockPosition:
    def __init__(self, quantity):
        self.quantity = quantity

class MockPortfolioManager:
    def __init__(self):
        self.positions = {}
        self.equity = 100000.0
    
    def get_position(self, symbol):
        if symbol in self.positions:
            return MockPosition(self.positions[symbol])
        return None
    
    def set_position(self, symbol, quantity):
        self.positions[symbol] = quantity

class MockEventBus:
    def __init__(self):
        self.events = []
    
    def emit(self, event):
        self.events.append(event)
        return True
    
    def register(self, event_type, handler):
        pass
    
    def unregister(self, event_type, handler):
        pass

# Simple class to test the risk manager
class TestRiskManager:
    def __init__(self):
        self.success = False
    
    def run_tests(self):
        try:
            # Import the risk manager
            from src.core.events.event_types import EventType
            from src.risk.managers.enhanced_risk_manager_improved import EnhancedRiskManager
            
            # Create mock objects
            portfolio_manager = MockPortfolioManager()
            event_bus = MockEventBus()
            
            # Create risk manager
            risk_manager = EnhancedRiskManager(event_bus, portfolio_manager, "test_risk_manager")
            
            # Replace event tracker with our mock version
            risk_manager.event_tracker = MockEventTracker("mock_tracker")
            
            # Configure risk manager
            risk_manager.configure({
                'position_sizing_method': 'fixed',
                'position_size': 100
            })
            
            # Test 1: Flat to Long
            portfolio_manager.set_position('MINI', 0)
            signal1 = MockEvent("signal1", "MINI", 1, 520.0)
            decisions1 = risk_manager.on_signal(signal1)
            
            if not decisions1 or len(decisions1) != 1:
                logger.error(f"Test 1 failed: Expected 1 decision, got {len(decisions1) if decisions1 else 0}")
                return False
                
            logger.info("Test 1 passed: Flat to Long transition generated 1 order (OPEN)")
            
            # Test 2: Long to Short
            portfolio_manager.set_position('MINI', 100)
            signal2 = MockEvent("signal2", "MINI", -1, 525.0)
            decisions2 = risk_manager.on_signal(signal2)
            
            if not decisions2 or len(decisions2) != 2:
                logger.error(f"Test 2 failed: Expected 2 decisions, got {len(decisions2) if decisions2 else 0}")
                return False
                
            logger.info("Test 2 passed: Long to Short transition generated 2 orders (CLOSE + OPEN)")
            
            # Test 3: Short to Flat
            portfolio_manager.set_position('MINI', -100)
            signal3 = MockEvent("signal3", "MINI", 0, 522.0)
            decisions3 = risk_manager.on_signal(signal3)
            
            if not decisions3 or len(decisions3) != 1:
                logger.error(f"Test 3 failed: Expected 1 decision, got {len(decisions3) if decisions3 else 0}")
                return False
                
            logger.info("Test 3 passed: Short to Flat transition generated 1 order (CLOSE)")
            
            # All tests passed
            logger.info("All risk manager tests passed!")
            return True
            
        except Exception as e:
            logger.error(f"Error testing risk manager: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

# Run the tests
if __name__ == "__main__":
    tester = TestRiskManager()
    success = tester.run_tests()
    sys.exit(0 if success else 1)
'''
    
    # Write test file
    with open(test_file, 'w') as f:
        f.write(test_code)
    
    # Run the test
    try:
        result = subprocess.run(f"python {test_file}", shell=True, check=False, capture_output=True, text=True)
        logger.info(f"Risk manager test output: {result.stdout}")
        
        if result.returncode == 0:
            logger.info("Risk manager tests passed.")
            # Clean up
            os.remove(test_file)
            return True
        else:
            logger.error(f"Risk manager tests failed with error: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"Error running risk manager tests: {str(e)}")
        return False
    finally:
        # Clean up in case of error
        if os.path.exists(test_file):
            os.remove(test_file)

def main():
    """Run all tests."""
    logger.info("========== ADMF-Trader Improved Architecture Test ==========")
    
    # Test validation script
    validation_result = test_validation_script()
    
    # Test validation with log
    log_validation_result = test_validation_with_log()
    
    # Test risk manager
    risk_manager_result = test_risk_manager()
    
    # Overall result
    if validation_result and log_validation_result and risk_manager_result:
        logger.info("✓ All tests passed successfully!")
        return 0
    else:
        logger.error("✗ Some tests failed. Check the logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
