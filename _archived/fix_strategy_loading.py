#!/usr/bin/env python3
"""
Final Fix for MA Crossover Signal Grouping

This script ensures the system uses the correct MA Crossover implementation with proper signal grouping.
"""

import os
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def rename_original_implementation():
    """
    Rename the ma_crossover_original.py to ensure it's not loaded by the discovery system.
    """
    original_path = "src/strategy/implementations/ma_crossover_original.py"
    backup_path = "src/strategy/implementations/ma_crossover_original.py.bak"
    
    try:
        # Check if the original file exists
        if os.path.exists(original_path):
            # Create a backup if it doesn't exist yet
            if not os.path.exists(backup_path):
                os.rename(original_path, backup_path)
                logger.info(f"Renamed {original_path} to {backup_path}")
            else:
                logger.info(f"Backup already exists at {backup_path}")
            
            return True
        else:
            logger.warning(f"Original file {original_path} not found")
            return False
    except Exception as e:
        logger.error(f"Error renaming original implementation: {e}", exc_info=True)
        return False

def verify_implementations():
    """
    Verify that only the fixed implementation is available.
    """
    fixed_path = "src/strategy/implementations/ma_crossover.py"
    original_path = "src/strategy/implementations/ma_crossover_original.py"
    
    # Check fixed implementation
    if os.path.exists(fixed_path):
        logger.info(f"Fixed implementation exists at {fixed_path}")
        fixed_exists = True
    else:
        logger.error(f"Fixed implementation not found at {fixed_path}")
        fixed_exists = False
    
    # Check original implementation
    if not os.path.exists(original_path):
        logger.info(f"Original implementation properly renamed/removed")
        original_removed = True
    else:
        logger.warning(f"Original implementation still exists at {original_path}")
        original_removed = False
    
    return fixed_exists and original_removed

def main():
    """Main function to apply the final fix."""
    logger.info("=" * 60)
    logger.info("APPLYING FINAL MA CROSSOVER SIGNAL GROUPING FIX")
    logger.info("=" * 60)
    
    # Step 1: Rename the original implementation
    renamed = rename_original_implementation()
    if not renamed:
        logger.warning("Could not rename original implementation")
    
    # Step 2: Verify implementations
    verified = verify_implementations()
    
    logger.info("=" * 60)
    if verified:
        logger.info("FIX SUCCESSFULLY APPLIED")
        logger.info("The system will now use the fixed MA Crossover implementation")
        logger.info("Expected result: 18 trades instead of 54")
    else:
        logger.error("FIX APPLICATION FAILED")
        logger.error("Manual intervention required to remove ma_crossover_original.py")
    logger.info("=" * 60)
    
    return 0 if verified else 1

if __name__ == "__main__":
    sys.exit(main())
