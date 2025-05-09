#!/usr/bin/env python
"""
Apply all fixes and run optimization.

This script applies all the necessary fixes to the ADMF-trader system
and then runs the optimization with improved error handling.
"""

import os
import sys
import logging
import subprocess
import argparse
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_and_optimize.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fix_and_optimize')

def run_script(script_path, args=None):
    """Run a Python script with given arguments"""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        logger.info(f"Script executed successfully: {script_path}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Script failed: {script_path}")
        logger.error(f"Error: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False, e.stderr

def make_scripts_executable():
    """Make the scripts executable"""
    try:
        # Make fix_trade_recording.py executable
        os.chmod('fix_trade_recording.py', 0o755)
        # Make run_fixed_optimization.py executable
        os.chmod('run_fixed_optimization.py', 0o755)
        logger.info("Made scripts executable")
        return True
    except Exception as e:
        logger.error(f"Error making scripts executable: {e}")
        return False

def main():
    """Main entry point for applying fixes and running optimization"""
    parser = argparse.ArgumentParser(description='Apply all fixes and run optimization')
    parser.add_argument('--config', required=True, help='Path to the configuration file')
    parser.add_argument('--skip-fixes', action='store_true', help='Skip applying fixes and just run optimization')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Starting fix and optimize process")
    
    # Make scripts executable
    make_scripts_executable()
    
    # Step 1: Apply fixes unless skipped
    if not args.skip_fixes:
        logger.info("Applying fixes...")
        success, output = run_script('fix_trade_recording.py')
        if not success:
            logger.warning("Fix application may have issues, but continuing...")
    else:
        logger.info("Skipping fixes as requested")
    
    # Step 2: Run optimization with fixed modules
    logger.info("Running optimization with fixed modules...")
    optimize_args = ['--config', args.config]
    if args.verbose:
        optimize_args.append('--verbose')
    
    success, output = run_script('run_fixed_optimization.py', optimize_args)
    
    if success:
        logger.info("Optimization completed successfully")
        return 0
    else:
        logger.error("Optimization failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
