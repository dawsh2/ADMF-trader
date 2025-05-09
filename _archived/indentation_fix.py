#!/usr/bin/env python
"""
Fix for the format specifier error in reporter.py with proper indentation.

This script focuses on the exact lines causing the error and ensures
proper indentation in the replacement code.
"""

import os
import sys
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_formatting_with_proper_indentation():
    """
    Fix the formatting issue with careful attention to indentation.
    
    Returns:
        bool: True if successful, False otherwise
    """
    reporter_path = os.path.join('src', 'strategy', 'optimization', 'reporter.py')
    backup_path = reporter_path + '.bak_indent'
    
    try:
        # Create a backup
        with open(reporter_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        logger.info(f"Created backup at {backup_path}")
        
        # Read the file content
        with open(reporter_path, 'r') as f:
            content = f.read()
        
        # Replace the formatting code using regular expressions to ensure proper indentation
        # First fix for train_value
        pattern_train = r"([ \t]+)if train_value != 'N/A' and format_str.*?:\s*\n([ \t]+)train_value = f'{train_value:{format_str}}'"
        replacement_train = r"\1if train_value != 'N/A' and format_str:\n\2    if isinstance(train_value, (int, float)):\n\2        try:\n\2            train_value = format(train_value, format_str)\n\2        except (ValueError, TypeError):\n\2            train_value = str(train_value)\n\2    else:\n\2        train_value = str(train_value)"
        
        content = re.sub(pattern_train, replacement_train, content, flags=re.DOTALL)
        
        # Second fix for test_value
        pattern_test = r"([ \t]+)if test_value != 'N/A' and format_str.*?:\s*\n([ \t]+)test_value = f'{test_value:{format_str}}'"
        replacement_test = r"\1if test_value != 'N/A' and format_str:\n\2    if isinstance(test_value, (int, float)):\n\2        try:\n\2            test_value = format(test_value, format_str)\n\2        except (ValueError, TypeError):\n\2            test_value = str(test_value)\n\2    else:\n\2        test_value = str(test_value)"
        
        content = re.sub(pattern_test, replacement_test, content, flags=re.DOTALL)
        
        # Write the modified content back
        with open(reporter_path, 'w') as f:
            f.write(content)
            
        logger.info(f"Applied formatting fix with proper indentation to {reporter_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error applying formatting fix: {e}")
        
        # Restore from backup if there was an error
        try:
            if os.path.exists(backup_path):
                with open(backup_path, 'r') as src, open(reporter_path, 'w') as dst:
                    dst.write(src.read())
                logger.info(f"Restored from backup {backup_path}")
        except Exception as restore_err:
            logger.