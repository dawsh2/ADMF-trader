#!/usr/bin/env python
"""
Fix script to use ma_crossover instead of simple_ma_crossover.
"""
import os
import sys
import yaml
import logging
import shutil
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('strategy_name_fix')

def create_backup(file_path):
    """Create a backup of a file."""
    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copyfile(file_path, backup_path)
    logger.info(f"Created backup at {backup_path}")
    return backup_path

def fix_strategy_name():
    """Fix the strategy name mismatch in configuration files."""
    config_files = [
        'config/optimization_test.yaml',
        'config/test_ma.yaml'
    ]
    
    fixed_files = []
    
    for config_file in config_files:
        if not os.path.exists(config_file):
            logger.warning(f"Config file not found: {config_file}")
            continue
        
        # Create backup
        create_backup(config_file)
        
        try:
            # Load the config
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check if we need to modify the strategy name
            backtest_strategy = config.get('backtest', {}).get('strategy', '')
            
            if backtest_strategy == 'simple_ma_crossover':
                # Update to use ma_crossover
                config['backtest']['strategy'] = 'ma_crossover'
                logger.info(f"Updated backtest strategy from 'simple_ma_crossover' to 'ma_crossover'")
                
                # Copy settings from simple_ma_crossover to ma_crossover
                if 'strategies' in config and 'simple_ma_crossover' in config['strategies']:
                    simple_ma_config = config['strategies'].pop('simple_ma_crossover')
                    config['strategies']['ma_crossover'] = simple_ma_config
                    logger.info(f"Copied strategy settings from 'simple_ma_crossover' to 'ma_crossover'")
                
                # Update parameter space if it exists
                if 'optimization' in config and 'parameter_space' in config['optimization']:
                    if 'simple_ma_crossover' in config['optimization']['parameter_space']:
                        simple_ma_params = config['optimization']['parameter_space'].pop('simple_ma_crossover')
                        config['optimization']['parameter_space']['ma_crossover'] = simple_ma_params
                        logger.info(f"Updated parameter space from 'simple_ma_crossover' to 'ma_crossover'")
                
                # Write the updated config
                with open(config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                
                logger.info(f"Updated config saved to {config_file}")
                fixed_files.append(config_file)
            
        except Exception as e:
            logger.error(f"Error fixing config {config_file}: {str(e)}")
    
    # Create a simple test script for the fixed config
    create_test_script()
    
    return fixed_files

def create_test_script():
    """Create a simple script to test the fixed configuration."""
    test_script = """#!/usr/bin/env python
# test_ma_crossover.py - Test script for MA Crossover strategy
import logging
from src.core.system_bootstrap import Bootstrap

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_ma_crossover():
    print("Testing MA Crossover strategy with fixed configuration...")
    
    # Initialize bootstrap with the fixed config
    bootstrap = Bootstrap(config_files=['config/test_ma.yaml'], log_level="INFO")
    container, config = bootstrap.setup()
    
    # Get the strategy
    strategy = container.get('strategy')
    print(f"Strategy name: {strategy.name}")
    print(f"Fast window: {strategy.fast_window}")
    print(f"Slow window: {strategy.slow_window}")
    print(f"Symbols: {strategy.symbols}")
    
    # Run backtest
    backtest = container.get('backtest')
    results = backtest.run()
    
    # Check results
    trades = results.get('trades', []) if results else []
    print(f"Trades generated: {len(trades)}")
    
    if trades:
        print("First few trades:")
        for i, trade in enumerate(trades[:3]):
            print(f"  Trade {i+1}: {trade['symbol']} {trade['direction']} @ {trade['price']}")
    
    return len(trades) > 0

if __name__ == "__main__":
    success = test_ma_crossover()
    print(f"Test {'succeeded' if success else 'failed'} (trades were {'generated' if success else 'not generated'})")
"""
    
    # Write the test script
    test_script_path = 'test_ma_crossover.py'
    with open(test_script_path, 'w') as f:
        f.write(test_script)
    
    # Make it executable
    os.chmod(test_script_path, 0o755)
    logger.info(f"Created test script at {test_script_path}")
    
    return test_script_path

if __name__ == "__main__":
    logger.info("Starting strategy name fix process...")
    
    fixed_files = fix_strategy_name()
    
    if fixed_files:
        logger.info("\nFixed strategy name in the following files:")
        for file in fixed_files:
            logger.info(f"- {file}")
        
        logger.info("\nRun the test script to verify the fix:")
        logger.info("./test_ma_crossover.py")
        
        logger.info("\nOr run the optimizer with the fixed config:")
        logger.info("python optimize_with_close_only.py --config config/optimization_test.yaml")
        
        sys.exit(0)
    else:
        logger.error("No files were fixed")
        sys.exit(1)