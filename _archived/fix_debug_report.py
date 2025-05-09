#!/usr/bin/env python
"""
Fix the debug report method in the backtest.py file to resolve all syntax errors.
"""
import os
import re
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fix_debug_report')

def fix_debug_report_method():
    """Replace the debug report method with a fixed version."""
    backtest_file = "src/execution/backtest/backtest.py"
    fixed_method_file = "src/execution/backtest/backtest_fixed.py"
    
    logger.info(f"Reading files: {backtest_file} and {fixed_method_file}")
    
    try:
        # Read the current backtest file
        with open(backtest_file, 'r') as f:
            content = f.read()
        
        # Read the fixed debug report method
        with open(fixed_method_file, 'r') as f:
            fixed_method = f.read()
        
        # Find the start of the debug report method
        debug_report_start = re.search(r'def _generate_debug_report\(self\):', content)
        if not debug_report_start:
            logger.error("Could not find the _generate_debug_report method in the backtest file")
            return False
        
        # Find where the method ends (the start of the next method)
        next_method = re.search(r'\n\s+def\s+\w+\(self', content[debug_report_start.start():])
        if next_method:
            debug_report_end = debug_report_start.start() + next_method.start()
        else:
            # If no next method, find the start of the next class
            next_class = re.search(r'\n\n# Factory for creating backtest coordinators', content[debug_report_start.start():])
            if next_class:
                debug_report_end = debug_report_start.start() + next_class.start()
            else:
                logger.error("Could not find the end of the _generate_debug_report method")
                return False
        
        # Replace the method
        new_content = content[:debug_report_start.start()] + fixed_method + content[debug_report_end:]
        
        # Write the fixed content back to the file
        logger.info("Writing fixed backtest file...")
        with open(backtest_file, 'w') as f:
            f.write(new_content)
        
        logger.info("Successfully fixed the _generate_debug_report method!")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing debug report method: {e}")
        return False

def main():
    """Main function."""
    print("Fixing the debug report method in backtest.py...")
    
    success = fix_debug_report_method()
    
    if success:
        print("\n✅ Successfully fixed the debug report method!")
        print("Now you can run 'python run_final_fix.py' to test the backtest.")
    else:
        print("\n❌ Failed to fix the debug report method.")
        print("Please check the logs for details.")

if __name__ == "__main__":
    main()
