#!/usr/bin/env python
"""
Apply all fixes to the ADMF-Trader Optimization Framework.

This script applies all the necessary fixes to the optimization framework
and then runs the verification script to ensure everything is working.
"""

import os
import sys
import logging
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_script(script_path, description):
    """
    Run a Python script and log the output.
    
    Args:
        script_path: Path to the script to run
        description: Description of what the script does
        
    Returns:
        bool: True if the script succeeded, False otherwise
    """
    logger.info(f"Running {description}: {script_path}")
    
    try:
        result = subprocess.run([sys.executable, script_path], 
                               capture_output=True, text=True)
        
        # Log stdout
        if result.stdout:
            logger.info(f"{description} output:\n{result.stdout}")
            
        # Log stderr
        if result.stderr:
            logger.error(f"{description} errors:\n{result.stderr}")
            
        # Check if successful
        if result.returncode == 0:
            logger.info(f"{description} completed successfully")
            return True
        else:
            logger.error(f"{description} failed with return code {result.returncode}")
            return False
            
    except Exception as e:
        logger.error(f"Error running {description}: {e}")
        return False

def fix_format_issue_manually():
    """
    Apply the format specifier fix manually.
    
    Returns:
        bool: True if successful, False otherwise
    """
    reporter_path = os.path.join('src', 'strategy', 'optimization', 'reporter.py')
    
    try:
        # Read the file content
        with open(reporter_path, 'r') as f:
            content = f.readlines()
            
        # Find the relevant lines that need fixing
        for i, line in enumerate(content):
            if "train_value = f'{train_value:{format_str}}'" in line:
                # Look for the preceding line with the condition
                if "if train_value != 'N/A' and format_str:" in content[i-1]:
                    # Fix the condition line
                    content[i-1] = content[i-1].replace(
                        "if train_value != 'N/A' and format_str:", 
                        "if train_value != 'N/A' and format_str and isinstance(train_value, (int, float)):"
                    )
                    logger.info(f"Fixed train value condition at line {i}")
                    
            if "test_value = f'{test_value:{format_str}}'" in line:
                # Look for the preceding line with the condition
                if "if test_value != 'N/A' and format_str:" in content[i-1]:
                    # Fix the condition line
                    content[i-1] = content[i-1].replace(
                        "if test_value != 'N/A' and format_str:", 
                        "if test_value != 'N/A' and format_str and isinstance(test_value, (int, float)):"
                    )
                    logger.info(f"Fixed test value condition at line {i}")
        
        # Write back the fixed content
        with open(reporter_path, 'w') as f:
            f.writelines(content)
            
        logger.info(f"Manual fixes applied to {reporter_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error applying manual fixes: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting ADMF-Trader fixes application")
    
    # Try fixing with the fix_reporter.py script first
    if os.path.exists('fix_reporter.py'):
        logger.info("Applying reporter fix with fix_reporter.py")
        if not run_script('fix_reporter.py', "Reporter fix"):
            logger.warning("The reporter fix script failed, trying manual fix...")
            if not fix_format_issue_manually():
                logger.error("Manual fix also failed. Unable to proceed.")
                return 1
    else:
        logger.info("No fix_reporter.py found, applying manual fix only")
        if not fix_format_issue_manually():
            logger.error("Manual fix failed. Unable to proceed.")
            return 1
    
    # Run the verification script
    logger.info("Running fix verification...")
    if not run_script('fix_verification.py', "Fix verification"):
        logger.error("Fix verification failed.")
        return 1
    
    logger.info("All fixes applied and verified successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
