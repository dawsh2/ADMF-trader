#!/usr/bin/env python
"""
Direct fix for the reporter.py formatting issue.

This script directly replaces the problematic code in reporter.py
with a completely rewritten and safe implementation.
"""

import os
import sys
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def apply_direct_fix():
    """
    Apply a direct fix by completely replacing the problematic code section.
    
    Returns:
        bool: True if successful, False otherwise
    """
    reporter_path = os.path.join('src', 'strategy', 'optimization', 'reporter.py')
    backup_path = reporter_path + '.bak2'
    
    try:
        # Create a backup
        with open(reporter_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        logger.info(f"Created backup at {backup_path}")
        
        # Read the original file line by line
        with open(reporter_path, 'r') as f:
            lines = f.readlines()
        
        # Find and fix the problematic code section
        for i, line in enumerate(lines):
            # Looking for the specific formatter line
            if "train_value = f'{train_value:{format_str}}'" in line:
                indentation = line[:line.find('train_value')]
                lines[i] = f"{indentation}# Safely format train_value\n"
                lines[i] += f"{indentation}try:\n"
                lines[i] += f"{indentation}    if isinstance(train_value, (int, float)):\n"
                lines[i] += f"{indentation}        train_value = f'{{train_value:{format_str.strip()}}}'\n"
                lines[i] += f"{indentation}    else:\n"
                lines[i] += f"{indentation}        train_value = str(train_value)\n"
                lines[i] += f"{indentation}except (ValueError, TypeError):\n"
                lines[i] += f"{indentation}    train_value = str(train_value)\n"
                logger.info(f"Fixed train_value formatting at line {i+1}")
            
            # Same for test_value
            elif "test_value = f'{test_value:{format_str}}'" in line:
                indentation = line[:line.find('test_value')]
                lines[i] = f"{indentation}# Safely format test_value\n"
                lines[i] += f"{indentation}try:\n"
                lines[i] += f"{indentation}    if isinstance(test_value, (int, float)):\n"
                lines[i] += f"{indentation}        test_value = f'{{test_value:{format_str.strip()}}}'\n"
                lines[i] += f"{indentation}    else:\n"
                lines[i] += f"{indentation}        test_value = str(test_value)\n"
                lines[i] += f"{indentation}except (ValueError, TypeError):\n"
                lines[i] += f"{indentation}    test_value = str(test_value)\n"
                logger.info(f"Fixed test_value formatting at line {i+1}")
        
        # Write the modified content back to the file
        with open(reporter_path, 'w') as f:
            f.writelines(lines)
            
        logger.info(f"Applied direct fix to {reporter_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error applying direct fix: {e}")
        
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
    logger.info("Starting direct fix")
    success = apply_direct_fix()
    
    if success:
        logger.info("Successfully applied direct fix")
        
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
        logger.error("Failed to apply direct fix")
        return 1

if __name__ == '__main__':
    sys.exit(main())
