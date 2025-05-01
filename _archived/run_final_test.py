#!/usr/bin/env python
"""
Final Test Script for ADMF-Trader - With Trade Tracking Diagnostics
"""
import os
import sys
import subprocess
import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_runner")

def run_backtest():
    """Run the backtest with the fixed code and additional diagnostics."""
    logger.info("Running backtest with fixed code...")
    
    # Create timestamped output directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"./results/mini_test/run_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Command to run
    cmd = ["python", "main.py", "--config", "config/mini_test.yaml"]
    
    # Run the command
    try:
        # Capture both stdout and stderr
        logger.info(f"Executing: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1  # Line buffered
        )
        
        # Collect output for logging
        stdout_lines = []
        stderr_lines = []
        
        # Process stdout
        for line in process.stdout:
            line = line.strip()
            stdout_lines.append(line)
            print(f"OUT: {line}")
            
        # Get return code
        return_code = process.wait()
        
        # Process stderr (if any)
        for line in process.stderr:
            line = line.strip()
            stderr_lines.append(line)
            print(f"ERR: {line}")
        
        # Write logs to file
        with open(f"{output_dir}/stdout.log", "w") as f:
            f.write("\n".join(stdout_lines))
            
        if stderr_lines:
            with open(f"{output_dir}/stderr.log", "w") as f:
                f.write("\n".join(stderr_lines))
        
        # Check for success
        if return_code != 0:
            logger.error(f"Backtest failed with return code {return_code}")
            return False
            
        # Look for trade count in output
        trade_count = None
        for line in stdout_lines:
            if "Trades executed:" in line:
                try:
                    trade_count = int(line.split("Trades executed:")[1].strip())
                    break
                except (ValueError, IndexError):
                    pass
        
        if trade_count is not None:
            logger.info(f"Backtest completed with {trade_count} trades executed")
        else:
            logger.warning("Could not determine trade count from output")
        
        return True
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        return False

def check_results():
    """Check the results of the backtest."""
    logger.info("Checking backtest results...")
    
    # Find the most recent backtest report
    results_dir = "./results/mini_test"
    report_files = [f for f in os.listdir(results_dir) if f.startswith("backtest_report_")]
    if not report_files:
        logger.error("No backtest reports found")
        return False
        
    # Sort by timestamp (newest first)
    report_files.sort(reverse=True)
    latest_report = os.path.join(results_dir, report_files[0])
    
    logger.info(f"Analyzing latest report: {latest_report}")
    
    # Check if the report contains trade data
    try:
        with open(latest_report, "r") as f:
            content = f.read()
            
        # Check for key metrics
        if "Trades executed: 0" in content:
            logger.error("Report shows 0 trades executed - fix failed")
            return False
            
        logger.info("Report shows trades were successfully recorded")
        return True
        
    except Exception as e:
        logger.error(f"Error checking results: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Starting test run...")
    
    success = run_backtest()
    if success:
        logger.info("Backtest completed successfully")
        results_ok = check_results()
        if results_ok:
            logger.info("TEST PASSED: Backtest recorded trades correctly")
            sys.exit(0)
        else:
            logger.error("TEST FAILED: Backtest did not record trades correctly")
            sys.exit(1)
    else:
        logger.error("TEST FAILED: Backtest did not complete successfully")
        sys.exit(1)
