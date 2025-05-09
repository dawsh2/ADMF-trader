#!/usr/bin/env python
"""
Script to fix the empty symbols issue in the backtest configuration.
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
logger = logging.getLogger('config_fix')

def create_backup(file_path):
    """Create a backup of a file."""
    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copyfile(file_path, backup_path)
    logger.info(f"Created backup at {backup_path}")
    return backup_path

def fix_config_file():
    """Fix the configuration file to properly load symbols."""
    config_file = 'config/optimization_test.yaml'
    
    if not os.path.exists(config_file):
        logger.error(f"Config file not found: {config_file}")
        return False
    
    # Create backup
    create_backup(config_file)
    
    try:
        # Load the config
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Get the configured symbols
        symbols = config.get('backtest', {}).get('symbols', [])
        if not symbols:
            logger.error("No symbols defined in backtest section")
            return False
        
        # Update the optimization test config to fix the empty symbols issue
        
        # 1. Make sure symbol list is in both backtest and strategies sections
        if 'strategies' in config:
            for strategy_name, strategy_config in config['strategies'].items():
                if 'symbols' not in strategy_config or not strategy_config['symbols']:
                    strategy_config['symbols'] = symbols
                    logger.info(f"Added symbols to strategy '{strategy_name}': {symbols}")
        
        # 2. Also add start_date and end_date to match the available data
        if 'backtest' in config:
            # Update date range to match HEAD_1min.csv data range
            config['backtest']['start_date'] = '2024-03-26'
            config['backtest']['end_date'] = '2024-03-28'
            logger.info(f"Updated date range to match available data: 2024-03-26 to 2024-03-28")
        
        # 3. Make sure optimization parameters include wider windows
        if 'optimization' in config and 'parameter_space' in config['optimization']:
            for strategy_name, params in config['optimization']['parameter_space'].items():
                if 'fast_window' in params:
                    params['fast_window']['min'] = 2
                    params['fast_window']['max'] = 20
                    params['fast_window']['step'] = 2
                if 'slow_window' in params:
                    params['slow_window']['min'] = 5
                    params['slow_window']['max'] = 50
                    params['slow_window']['step'] = 5
                logger.info(f"Updated parameter ranges for wider search")
        
        # 4. Make sure to use only close prices (per your request)
        if 'strategies' in config:
            for strategy_name, strategy_config in config['strategies'].items():
                strategy_config['price_key'] = 'close'
                logger.info(f"Set price_key to 'close' for strategy '{strategy_name}'")
        
        # Write the updated config
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Updated config saved to {config_file}")
        
        # Create a special test config for manual testing
        test_config_file = 'config/test_ma.yaml'
        
        # Update configuration for a simple test
        test_config = config.copy()
        test_config['strategies']['simple_ma_crossover'] = {
            'enabled': True,
            'symbols': symbols,
            'price_key': 'close',
            'fast_window': 2,  # Very small window for more signals
            'slow_window': 8   # Very small window for more signals
        }
        
        with open(test_config_file, 'w') as f:
            yaml.dump(test_config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Created test config with very short MA windows: {test_config_file}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error fixing config: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def run_test_backtest():
    """Run a test backtest with the fixed config."""
    logger.info("\nRunning test backtest with fixed configuration...")
    
    try:
        from src.core.system_bootstrap import Bootstrap
        
        # Initialize bootstrap
        bootstrap = Bootstrap(config_files=['config/test_ma.yaml'], log_level="INFO")
        container, config = bootstrap.setup()
        
        # Run backtest
        backtest = container.get('backtest')
        results = backtest.run()
        
        # Check results
        if results:
            trades = results.get('trades', [])
            metrics = results.get('metrics', {})
            logger.info(f"\nTrades generated: {len(trades)}")
            
            if trades:
                logger.info("\nSample trades:")
                for i, trade in enumerate(trades[:5]):  # Show first 5 trades
                    logger.info(f"  Trade {i}: {trade}")
                
                logger.info("\nPerformance metrics:")
                for k, v in metrics.items():
                    logger.info(f"  {k}: {v}")
                
                return True
            else:
                logger.warning("No trades were generated!")
                return False
        else:
            logger.error("Backtest did not produce any results")
            return False
    
    except Exception as e:
        logger.error(f"Error during test backtest: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("Starting config fix process...")
    
    if fix_config_file():
        logger.info("\nConfiguration fixed successfully.")
        logger.info("\nYou can now run the optimizer with the fixed config:")
        logger.info("python optimize_with_close_only.py --config config/optimization_test.yaml")
        
        # Optionally run a test backtest
        run_test = input("\nRun a test backtest with fixed config? (y/n): ").lower().strip() == 'y'
        if run_test:
            success = run_test_backtest()
            if success:
                logger.info("\nTest backtest completed successfully!")
            else:
                logger.warning("\nTest backtest did not generate trades.")
        
        sys.exit(0)
    else:
        logger.error("Failed to fix configuration.")
        sys.exit(1)