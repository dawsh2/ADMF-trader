#!/usr/bin/env python
"""
Test the risk manager deduplication using the RuleIdFilter.
"""
import logging
import sys
from test_order_flow import test_create_order_direct, test_create_order_from_signal
from test_order_flow import test_create_sell_after_buy, test_order_registry_deduplication
from test_order_flow import create_test_components
from rule_id_filter import RuleIdFilter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('filtered_test.log', mode='w')
    ]
)
logger = logging.getLogger("FilteredTest")

def modified_test_risk_manager_deduplication():
    """Modified version of the risk manager deduplication test using the filter."""
    logger.info("=== Modified Test: Risk Manager Deduplication with Filter ===")
    
    # Create components
    components = create_test_components()
    event_bus = components['event_bus']
    
    # Install the filter - this is the key difference!
    rule_filter = RuleIdFilter(event_bus)
    logger.info(f"Installed RuleIdFilter: {rule_filter}")
    
    # Now run the original test - it should pass with the filter installed
    from test_order_flow import test_risk_manager_deduplication
    result = test_risk_manager_deduplication()
    return result

def run_all_tests():
    """Run all tests including the modified risk manager deduplication test."""
    logger.info("======= Starting Filtered Tests =======")
    
    tests = [
        test_create_order_direct,
        test_create_order_from_signal,
        test_create_sell_after_buy,
        test_order_registry_deduplication,
        modified_test_risk_manager_deduplication
    ]
    
    results = {}
    
    for test_func in tests:
        test_name = test_func.__name__
        logger.info(f"\nRunning test: {test_name}")
        
        try:
            result = test_func()
            results[test_name] = result
            logger.info(f"Test {test_name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            logger.error(f"Test {test_name} raised exception: {e}", exc_info=True)
            results[test_name] = False
    
    # Print summary
    logger.info("\n======= Test Results Summary =======")
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info(f"\nPassed: {passed}, Failed: {failed}, Total: {len(tests)}")
    
    return passed, failed, len(tests)

if __name__ == "__main__":
    passed, failed, total = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
