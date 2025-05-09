#!/usr/bin/env python
"""
Run all debugging scripts to identify the source of the inconsistency.
"""

import os
import sys
import subprocess
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_script(script_path, description):
    """Run a Python script and log its output."""
    logger.info(f"Running {description}...")
    try:
        # Make script executable
        os.chmod(script_path, 0o755)
        
        # Run the script
        result = subprocess.run(
            ['python', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Log output
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.info(f"  {line}")
        
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if "WARNING" in line or "ERROR" in line:
                    logger.warning(f"  {line}")
                else:
                    logger.info(f"  {line}")
        
        if result.returncode != 0:
            logger.error(f"{description} failed with exit code {result.returncode}")
            return False
        
        logger.info(f"{description} completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error running {description}: {e}")
        return False

def main():
    """Run all debugging scripts."""
    # Define scripts to run
    scripts = [
        {"path": "debug_metrics.py", "description": "Metric Consistency Test"},
        {"path": "debug_simple_strategy.py", "description": "Simple Strategy Test"},
        {"path": "debug_ma_crossover.py", "description": "MA Crossover Strategy Test"}
    ]
    
    # Run each script
    results = []
    for script in scripts:
        result = run_script(script["path"], script["description"])
        results.append({"script": script["path"], "success": result})
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("DEBUGGING RESULTS SUMMARY")
    logger.info("=" * 80)
    
    all_successful = True
    for result in results:
        status = "Success" if result["success"] else "Failed"
        logger.info(f"{result['script']}: {status}")
        all_successful = all_successful and result["success"]
    
    if all_successful:
        logger.info("\nAll debugging scripts completed successfully.")
    else:
        logger.error("\nSome debugging scripts failed.")
    
    return 0 if all_successful else 1

if __name__ == "__main__":
    sys.exit(main())
