#!/usr/bin/env python
"""
Simple fix for the format specifier error in reporter.py.

This script focuses only on the exact line causing the error by replacing the
string formatting operation with a safer alternative.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def simple_format_fix():
    """
    Apply a simple fix that targets just the specific line causing the error.
    
    Returns:
        bool: True if successful, False otherwise
    """
    reporter_path = os.path.join('src', 'strategy', 'optimization', 'reporter.py')
    backup_path = reporter_path + '.bak_simple'
    
    try:
        # Create a backup
        with open(reporter_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        logger.info(f"Created backup at {backup_path}")
        
        # Read the original file line by line
        with open(reporter_path, 'r') as f:
            lines = f.readlines()
        
        # Flag to track if we found the problematic lines
        found_train = False
        found_test = False
        
        # Find and fix the problematic code section
        for i, line in enumerate(lines):
            # Looking for the specific formatter lines
            if "train_value = f'{train_value:{format_str}}'" in line:
                indentation = line[:line.find('train_value')]
                lines[i] = f"{indentation}# Safe alternative to f-string formatting for train_value\n"
                lines[i] += f"{indentation}if isinstance(train_value, (int, float)):\n"
                lines[i] += f"{indentation}    try:\n"
                lines[i] += f"{indentation}        train_value = format(train_value, format_str)\n"
                lines[i] += f"{indentation}    except (ValueError, TypeError):\n"
                lines[i] += f"{indentation}        train_value = str(train_value)\n"
                lines[i] += f"{indentation}else:\n"
                lines[i] += f"{indentation}    train_value = str(train_value)\n"
                found_train = True
                logger.info(f"Fixed train_value formatting at line {i+1}")
            
            # Same for test_value
            elif "test_value = f'{test_value:{format_str}}'" in line:
                indentation = line[:line.find('test_value')]
                lines[i] = f"{indentation}# Safe alternative to f-string formatting for test_value\n"
                lines[i] += f"{indentation}if isinstance(test_value, (int, float)):\n"
                lines[i] += f"{indentation}    try:\n"
                lines[i] += f"{indentation}        test_value = format(test_value, format_str)\n"
                lines[i] += f"{indentation}    except (ValueError, TypeError):\n"
                lines[i] += f"{indentation}        test_value = str(test_value)\n"
                lines[i] += f"{indentation}else:\n"
                lines[i] += f"{indentation}    test_value = str(test_value)\n"
                found_test = True
                logger.info(f"Fixed test_value formatting at line {i+1}")
        
        if not (found_train and found_test):
            logger.warning("Could not find one or both of the problematic lines")
            return False
        
        # Write the modified content back to the file
        with open(reporter_path, 'w') as f:
            f.writelines(lines)
            
        logger.info(f"Applied simple format fix to {reporter_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error applying simple format fix: {e}")
        
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
    logger.info("Starting simple format fix")
    success = simple_format_fix()
    
    if success:
        logger.info("Successfully applied simple format fix")
        
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
            logger.info(f"Stdout: {result.stdout}")
            logger.error(f"Stderr: {result.stderr}")
            return 1
    else:
        logger.error("Failed to apply simple format fix")
        return 1

if __name__ == '__main__':
    sys.exit(main())
