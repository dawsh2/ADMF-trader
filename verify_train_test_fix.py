#!/usr/bin/env python
"""
Verify Train/Test Split Fix

This script runs a minimal optimization to verify that train and test 
datasets are properly isolated after our fixes.
"""

import os
import sys
import logging
import pandas as pd
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('train_test_verification.log')
    ]
)
logger = logging.getLogger('verify_fix')

def run_optimization():
    """Run a minimal optimization to verify train/test split isolation."""
    # Use the same command as before, but with verbose output and bars limit
    # python main.py --config config/simple_ma_optimization.yaml --optimize --verbose --bars 100
    
    cmd = "python main.py --config config/simple_ma_optimization.yaml --optimize --verbose --bars 500"
    
    # Run the command
    logger.info(f"Running optimization with command: {cmd}")
    
    import subprocess
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    
    # Log results
    logger.info(f"Command exit code: {result.returncode}")
    
    if result.stderr:
        logger.error(f"Standard error:\n{result.stderr}")
    
    # Check the output for evidence of distinct train/test splits
    lines = result.stdout.split('\n')
    
    # Look for the diagnostic markers we added
    train_diagnostics = []
    test_diagnostics = []
    data_issue_warnings = []

    for i, line in enumerate(lines):
        if "DIAGNOSTIC: Training with params" in line:
            train_diagnostics.append(line)
        elif "DIAGNOSTIC: Testing with params" in line:
            test_diagnostics.append(line)
        elif "CRITICAL DATA ISSUE: Train and test results are identical" in line:
            data_issue_warnings.append(line)

    # Check if we found diagnostic markers
    if not train_diagnostics and not test_diagnostics:
        logger.error("No diagnostic markers found in output - new diagnostics might not be working")

        # Fall back to looking for any evidence of train vs test
        for line in lines:
            if "TRAINING BACKTEST" in line:
                train_diagnostics.append(line)
            elif "TESTING BACKTEST" in line:
                test_diagnostics.append(line)

        if not train_diagnostics and not test_diagnostics:
            logger.error("No evidence of train/test separation found")
            return False
    
    # Check if we found both train and test diagnostics
    logger.info(f"Found {len(train_diagnostics)} train diagnostics")
    logger.info(f"Found {len(test_diagnostics)} test diagnostics")

    # If we found data issue warnings, there might still be a problem
    if data_issue_warnings:
        logger.error(f"CRITICAL ISSUE: Found {len(data_issue_warnings)} data issue warnings")
        logger.error("Train and test results appear to be identical, which indicates isolation failure")
        return False

    # Check that we found at least one of each
    if train_diagnostics and test_diagnostics:
        logger.info("SUCCESS: Both train and test datasets are being used")
    else:
        logger.warning("Partial success: Only one dataset type has diagnostics")
        if not train_diagnostics and not test_diagnostics:
            return False
    
    # Check for diverse results in the optimization
    has_diverse_scores = False
    sharpe_ratios = []
    
    for line in lines:
        if "Sharpe Ratio:" in line:
            try:
                sharpe = float(line.split("Sharpe Ratio:")[-1].strip())
                sharpe_ratios.append(sharpe)
            except:
                pass
    
    # Check for diversity in Sharpe ratios
    if len(sharpe_ratios) >= 2:
        min_sharpe = min(sharpe_ratios)
        max_sharpe = max(sharpe_ratios)
        sharpe_range = max_sharpe - min_sharpe
        
        logger.info(f"Sharpe ratio range: {min_sharpe:.4f} to {max_sharpe:.4f} (range: {sharpe_range:.4f})")
        
        # If range is significant, results are diverse
        if sharpe_range > 0.1:  # Arbitrary threshold
            logger.info("SUCCESS: Optimization shows diverse Sharpe ratios across parameters")
            has_diverse_scores = True
        else:
            logger.warning(f"POSSIBLE ISSUE: Sharpe ratios have small range ({sharpe_range:.4f})")
    else:
        logger.warning(f"Not enough Sharpe ratios to analyze ({len(sharpe_ratios)} found)")
    
    return len(train_fingerprints) > 0 and len(test_fingerprints) > 0 and has_diverse_scores

if __name__ == "__main__":
    logger.info("Starting verification of train/test split fix")
    success = run_optimization()
    
    if success:
        logger.info("VERIFICATION PASSED: Train/test split isolation appears to be working correctly")
        sys.exit(0)
    else:
        logger.error("VERIFICATION FAILED: Train/test split isolation may still have issues")
        sys.exit(1)