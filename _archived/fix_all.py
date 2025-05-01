#!/usr/bin/env python3
"""
Quick fix for the MA Crossover Signal Grouping issue.

This script applies all the necessary changes to fix the issue where the MA Crossover
strategy generates 54 trades instead of the expected 18 trades. The fix includes updating
the rule_id format and ensuring proper reset of processed rule IDs.
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("fix_all")

def make_scripts_executable():
    """Make all scripts executable."""
    try:
        subprocess.run(['chmod', '+x', 'fix_signal_grouping.py'], check=True)
        subprocess.run(['chmod', '+x', 'verify_signal_grouping_fix.sh'], check=True)
        subprocess.run(['chmod', '+x', 'run_grouping_fix.sh'], check=True)
        subprocess.run(['chmod', '+x', 'fix.py'], check=True)
        subprocess.run(['chmod', '+x', 'run_and_validate.sh'], check=True)
        subprocess.run(['chmod', '+x', 'chmod_scripts.sh'], check=True)
        
        logger.info("Made all scripts executable")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to make scripts executable: {e}")
        return False

def apply_fix():
    """Apply the MA Crossover Signal Grouping fix."""
    try:
        logger.info("Applying the MA Crossover Signal Grouping fix...")
        
        # Run the fix script
        result = subprocess.run(['python', 'fix.py'], check=True, capture_output=True, text=True)
        
        # Log the output
        for line in result.stdout.splitlines():
            logger.info(line)
            
        logger.info("Fix applied successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to apply fix: {e}")
        if e.stdout:
            for line in e.stdout.splitlines():
                logger.error(line)
        if e.stderr:
            for line in e.stderr.splitlines():
                logger.error(line)
        return False

def validate_fix():
    """Validate the MA Crossover Signal Grouping fix."""
    try:
        logger.info("Validating the fix...")
        
        # Run the validation script
        result = subprocess.run(['bash', 'verify_signal_grouping_fix.sh'], check=True, capture_output=True, text=True)
        
        # Log the output
        for line in result.stdout.splitlines():
            logger.info(line)
            
        # Check if the validation was successful
        if "SUCCESS: Signal grouping fix verified! Counts match." in result.stdout:
            logger.info("Validation successful: Fix has been properly applied")
            return True
        else:
            logger.warning("Validation failed: Fix may not have been properly applied")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to validate fix: {e}")
        if e.stdout:
            for line in e.stdout.splitlines():
                logger.error(line)
        if e.stderr:
            for line in e.stderr.splitlines():
                logger.error(line)
        return False

def main():
    """Main function."""
    logger.info("Starting MA Crossover Signal Grouping fix...")
    
    # Step 1: Make scripts executable
    if not make_scripts_executable():
        logger.error("Failed to make scripts executable, exiting")
        return False
    
    # Step 2: Apply the fix
    if not apply_fix():
        logger.error("Failed to apply the fix, exiting")
        return False
    
    # Step 3: Validate the fix
    if not validate_fix():
        logger.warning("Fix validation failed, please check the logs for details")
        # Continue even if validation failed, so the user can see the results
    
    logger.info("MA Crossover Signal Grouping fix completed")
    logger.info("For detailed information, see the DEDUPLICATION_FIX.md file")
    
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
