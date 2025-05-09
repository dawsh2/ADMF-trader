#!/usr/bin/env python
"""
Verify that the fix was properly applied to reporter.py.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_reporter_fix():
    """
    Check if the fix was properly applied to reporter.py.
    
    Returns:
        bool: True if the fix is present, False otherwise
    """
    reporter_path = os.path.join('src', 'strategy', 'optimization', 'reporter.py')
    
    try:
        # Check if the file exists
        if not os.path.exists(reporter_path):
            logger.error(f"File not found: {reporter_path}")
            return False
            
        # Read the file
        with open(reporter_path, 'r') as f:
            content = f.read()
        
        # Check if our fix is present
        train_fix_present = "isinstance(train_value, (int, float))" in content
        test_fix_present = "isinstance(test_value, (int, float))" in content
        
        logger.info(f"Train value type check: {'✅ Present' if train_fix_present else '❌ Missing'}")
        logger.info(f"Test value type check: {'✅ Present' if test_fix_present else '❌ Missing'}")
        
        return train_fix_present and test_fix_present
        
    except Exception as e:
        logger.error(f"Error verifying fix: {e}")
        return False

if __name__ == '__main__':
    fix_verified = verify_reporter_fix()
    if fix_verified:
        logger.info("✅ Fix successfully verified!")
        sys.exit(0)
    else:
        logger.error("❌ Fix verification failed!")
        sys.exit(1)
