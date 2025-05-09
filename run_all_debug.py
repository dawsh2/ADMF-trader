#!/usr/bin/env python
"""
Run all debugging tools in sequence
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("run_all_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('run_all')

def run_script(script_name, desc=None):
    """Run a Python script and log the output"""
    if desc:
        logger.info(f"Running {script_name}: {desc}")
    else:
        logger.info(f"Running {script_name}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"{script_name} completed with return code {result.returncode}")
        logger.info(f"Output: {result.stdout[:500]}...")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"{script_name} failed with return code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        return False

def main():
    """Run all debug scripts in sequence"""
    # First, make our scripts executable
    scripts = [
        'debug_trade_flow.py',
        'patch_strategy_adapter.py',
        'run_debug_optimization.py'
    ]
    
    # Run the scripts in sequence
    run_script('debug_optimization.py', "Checking for data file and signals")
    run_script('debug_trade_flow.py', "Testing signal-to-trade flow")
    run_script('patch_strategy_adapter.py', "Patching strategy adapter with additional logging")
    
    # Final optimization run
    logger.info("Running full debug optimization")
    run_script('run_debug_optimization.py', "Running optimization with detailed logging")
    
    logger.info("All debug scripts completed")
    logger.info("Check the following log files for detailed information:")
    logger.info("- signal_to_trade_debug.log")
    logger.info("- strategy_adapter_debug.log")
    logger.info("- optimization_detailed.log")
    logger.info("- debug_signals.csv")

if __name__ == "__main__":
    main()
