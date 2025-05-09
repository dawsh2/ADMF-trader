#!/usr/bin/env python
"""
Targeted fix for the format specifier issue in reporter.py.

This script applies a focused fix to address the specific formatting error
in the reporter.py file's HTML generation section.
"""

import os
import sys
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def apply_targeted_fix():
    """
    Apply a focused fix to address the specific formatting error.
    
    Returns:
        bool: True if successful, False otherwise
    """
    reporter_path = os.path.join('src', 'strategy', 'optimization', 'reporter.py')
    backup_path = reporter_path + '.bak'
    
    try:
        # Create a backup
        with open(reporter_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        logger.info(f"Created backup at {backup_path}")
        
        # Read the original file
        with open(reporter_path, 'r') as f:
            content = f.read()
        
        # Find the exact problematic section and fix it directly
        # This is specifically targeting line 441 where the error occurs
        problem_pattern = re.compile(r"(train_value = f'{train_value:{format_str}}')")
        
        if problem_pattern.search(content):
            # Replace with a try-except block for safety
            fix = """try:
                    if isinstance(train_value, (int, float)):
                        train_value = f'{train_value:{format_str}}'
                    else:
                        train_value = str(train_value)
                except (ValueError, TypeError):
                    train_value = str(train_value)"""
            
            # Apply the fix with proper indentation
            content = problem_pattern.sub(fix, content)
            logger.info("Applied fix to train_value formatting")
            
            # Do the same for test_value
            problem_pattern = re.compile(r"(test_value = f'{test_value:{format_str}}')")
            
            if problem_pattern.search(content):
                fix = """try:
                    if isinstance(test_value, (int, float)):
                        test_value = f'{test_value:{format_str}}'
                    else:
                        test_value = str(test_value)
                except (ValueError, TypeError):
                    test_value = str(test_value)"""
                
                content = problem_pattern.sub(fix, content)
                logger.info("Applied fix to test_value formatting")
        else:
            logger.warning("Could not find formatting pattern to fix")
            
        # Write the fixed content back to the file
        with open(reporter_path, 'w') as f:
            f.write(content)
            
        logger.info(f"Applied targeted fixes to {reporter_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error applying targeted fix: {e}")
        
        # Restore from backup if there was an error
        try:
            if os.path.exists(backup_path):
                with open(backup_path, 'r') as src, open(reporter_path, 'w') as dst:
                    dst.write(src.read())
                logger.info(f"Restored from backup {backup_path}")
        except Exception as restore_err:
            logger.error(f"Error restoring from backup: {restore_err}")
            
        return False

def main():
    """Main function."""
    logger.info("Starting targeted fix")
    success = apply_targeted_fix()
    
    if success:
        logger.info("Successfully applied targeted fix")
        
        # Run the verification script
        import subprocess
        logger.info("Running fix verification...")
        result = subprocess.run([sys.executable, 'fix_verification.py'], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Verification successful!")
            return 0
        else:
            logger.error("Verification failed after applying fix")
            logger.error(f"Error: {result.stderr}")
            return 1
    else:
        logger.error("Failed to apply targeted fix")
        return 1

if __name__ == '__main__':
    sys.exit(main())
