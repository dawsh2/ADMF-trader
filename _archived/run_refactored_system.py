#!/usr/bin/env python
"""
Run the system with the refactored architecture.

This script:
1. Applies patches to enable the enhanced risk manager
2. Runs the system with our refactored_test.yaml configuration
"""
import os
import sys
import logging
import subprocess
from update_bootstrap import apply_patches

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('refactored_system.log')
    ]
)

logger = logging.getLogger('run_refactored')

def run_system():
    """Run the system with refactored architecture."""
    logger.info("=== Running System with Refactored Architecture ===")
    
    # Apply patches to the bootstrap
    logger.info("Applying patches for enhanced risk manager...")
    apply_patches()
    
    # Check if refactored_test.yaml exists
    config_path = "config/refactored_test.yaml"
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        return False
    
    # Create the command to run the main script
    cmd = [
        "python", 
        "main.py", 
        "--config", config_path,
        "--log-level", "INFO"
    ]
    
    # Run the command
    logger.info(f"Running command: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Stream output in real-time
        for stdout_line in process.stdout:
            print(stdout_line.strip())
        
        # Get the return code
        return_code = process.wait()
        
        if return_code == 0:
            logger.info("System ran successfully with refactored architecture")
            return True
        else:
            logger.error(f"System failed with return code {return_code}")
            return False
    
    except Exception as e:
        logger.error(f"Error running system: {e}")
        return False

if __name__ == "__main__":
    success = run_system()
    
    if success:
        print("\n=== Success! ===")
        print("The system ran successfully with the refactored architecture.")
        print("Check the results directory for detailed output.")
    else:
        print("\n=== Failed! ===")
        print("The system failed to run with the refactored architecture.")
        print("Check the logs for more information.")
    
    sys.exit(0 if success else 1)
