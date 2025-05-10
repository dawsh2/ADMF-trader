#!/usr/bin/env python
"""
Apply the train/test isolation fix and run a quick verification.

This script:
1. Installs the fixed versions of the optimizer and backtest coordinator
2. Runs a direct test to verify the fix works
3. Prints instructions on how to use the fix in the main code
"""

import os
import sys
import logging
import shutil
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fix_installation.log')
    ]
)
logger = logging.getLogger(__name__)

def install_fixes():
    """Install the fixed files to main locations."""
    # Files to replace with their fixed versions
    fix_files = [
        ('src/strategy/optimization/fixed_optimizer.py', 'src/strategy/optimization/fixed_optimizer.py.fix'),
        ('src/execution/backtest/optimizing_backtest.py', 'src/execution/backtest/optimizing_backtest.py.fix'),
        ('src/strategy/optimization/runner.py', 'src/strategy/optimization/runner.py.fix')
    ]
    
    # Create backups and install fixes
    for target, source in fix_files:
        # Check if fix file exists
        if not os.path.exists(source):
            logger.error(f"Fix file {source} not found")
            continue
            
        # Create backup if it doesn't exist
        backup = f"{target}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if os.path.exists(target) and not os.path.exists(backup):
            logger.info(f"Creating backup of {target} to {backup}")
            shutil.copy2(target, backup)
            
        # Copy fix to target
        logger.info(f"Installing fix from {source} to {target}")
        shutil.copy2(source, target)
        
    logger.info("All fixes installed")
    
    # Fix the ImportError in runner.py
    runner_path = 'src/strategy/optimization/runner.py'
    if os.path.exists(runner_path):
        # Read the file
        with open(runner_path, 'r') as f:
            content = f.read()
        
        # Check if we need to fix the import
        if 'from src.strategy.optimization.fixed_optimizer import StrategyOptimizer' in content:
            # Make a backup
            backup = f"{runner_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Creating backup of {runner_path} to {backup}")
            shutil.copy2(runner_path, backup)
            
            # Fix the import
            content = content.replace(
                'from src.strategy.optimization.fixed_optimizer import StrategyOptimizer', 
                'from src.strategy.optimization.fixed_optimizer import FixedOptimizer as StrategyOptimizer'
            )
            
            # Write the file back
            with open(runner_path, 'w') as f:
                f.write(content)
                
            logger.info(f"Fixed import in {runner_path}")
        else:
            logger.info(f"Import in {runner_path} already fixed or using different pattern")

def verify_fix_works():
    """Run a direct test to verify the fix works."""
    try:
        # Import the test function
        logger.info("Running direct test to verify fix...")
        from fix_strategy_state import run_direct_test
        
        # Run the test
        success = run_direct_test()
        
        if success:
            logger.info("Fix verification PASSED! Train/test isolation is working correctly.")
            return True
        else:
            logger.error("Fix verification FAILED! Train/test isolation is not working correctly.")
            return False
    except Exception as e:
        logger.error(f"Error running verification: {e}")
        return False

def main():
    """Main function to apply and verify the fix."""
    print("ADMF-Trader Train/Test Isolation Fix Installer")
    print("=============================================")
    print("This script will install the train/test isolation fix")
    print("and verify that it works correctly.")
    print()
    
    # Install the fixes
    print("Installing fixes...")
    install_fixes()
    
    # Verify the fix works
    print("\nVerifying fix...")
    if verify_fix_works():
        print("\n✅ FIX SUCCESSFULLY INSTALLED AND VERIFIED!")
        print("\nYou can now run optimizations with proper train/test isolation:")
        print("python main.py --config config/simple_ma_optimization.yaml --optimize --verbose --bars 200")
        return 0
    else:
        print("\n❌ FIX INSTALLATION COULD NOT BE VERIFIED!")
        print("Please check the logs for details on what went wrong.")
        return 1

if __name__ == "__main__":
    sys.exit(main())