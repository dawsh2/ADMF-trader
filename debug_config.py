#!/usr/bin/env python
"""
Debug tool for testing different configurations to fix the trading system.
This script will modify configuration parameters and run backtests to find
a working combination.
"""
import os
import sys
import logging
import yaml
import subprocess
import datetime
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug_config.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("config_debug")

def load_yaml_config(config_path):
    """Load YAML configuration file."""
    logger.info(f"Loading configuration from: {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Successfully loaded configuration")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return None

def save_yaml_config(config, config_path):
    """Save YAML configuration to file."""
    logger.info(f"Saving configuration to: {config_path}")
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        logger.info(f"Successfully saved configuration")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False

def create_test_config(base_config, output_path, changes):
    """Create a test configuration by applying changes to base config."""
    logger.info(f"Creating test configuration with changes: {changes}")
    
    # Make a deep copy of the base config
    import copy
    test_config = copy.deepcopy(base_config)
    
    # Apply changes
    for path, value in changes.items():
        # Split path into components
        components = path.split('.')
        
        # Navigate to the correct location
        target = test_config
        for i, comp in enumerate(components[:-1]):
            if comp not in target:
                target[comp] = {}
            target = target[comp]
        
        # Set the value
        target[components[-1]] = value
    
    # Save to file
    save_yaml_config(test_config, output_path)
    return output_path

def run_backtest(config_path):
    """Run backtest with the given configuration."""
    logger.info(f"Running backtest with configuration: {config_path}")
    
    cmd = ["python", "main.py", "--config", config_path]
    logger.info(f"Executing command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate()
        
        # Log output
        if stdout:
            logger.info(f"Command output:\n{stdout}")
        if stderr:
            logger.error(f"Command error output:\n{stderr}")
        
        # Check for success
        success = process.returncode == 0
        
        # Check for trades in output
        has_trades = "No trades were executed" not in stdout
        
        return {
            'success': success,
            'has_trades': has_trades,
            'returncode': process.returncode,
            'stdout': stdout,
            'stderr': stderr
        }
    
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return {
            'success': False,
            'has_trades': False,
            'error': str(e)
        }

def test_ma_combinations():
    """Test different MA window combinations."""
    logger.info("Testing different MA window combinations")
    
    # Load base config
    base_config_path = "config/head_test.yaml"
    base_config = load_yaml_config(base_config_path)
    if not base_config:
        return
    
    # Create test directory
    test_dir = Path("config/debug_tests")
    test_dir.mkdir(exist_ok=True)
    
    # Define MA combinations to test
    ma_combinations = [
        (3, 10),
        (5, 15),
        (2, 7),
        (8, 20),
        (10, 25),
        (15, 45),
        (2, 5),
        (4, 12)
    ]
    
    results = []
    
    for fast_window, slow_window in ma_combinations:
        # Create unique config name
        config_name = f"ma_{fast_window}_{slow_window}"
        test_config_path = test_dir / f"{config_name}.yaml"
        
        # Create changes
        changes = {
            'strategy.parameters.fast_window': fast_window,
            'strategy.parameters.slow_window': slow_window
        }
        
        # Create test config
        create_test_config(base_config, test_config_path, changes)
        
        # Run backtest
        logger.info(f"Testing MA windows: fast={fast_window}, slow={slow_window}")
        result = run_backtest(test_config_path)
        
        # Store result
        result['fast_window'] = fast_window
        result['slow_window'] = slow_window
        result['config_path'] = str(test_config_path)
        results.append(result)
        
        # Log result
        success_str = "SUCCESS" if result['has_trades'] else "FAILED"
        logger.info(f"MA windows {fast_window}/{slow_window}: {success_str}")
        
        # Brief pause to allow logs to flush
        time.sleep(0.5)
    
    # Analyze results
    successful_configs = [r for r in results if r['has_trades']]
    
    logger.info("\n===== RESULTS =====")
    logger.info(f"Tested {len(results)} configurations")
    logger.info(f"Successful configurations: {len(successful_configs)}")
    
    if successful_configs:
        logger.info("Successful MA window combinations:")
        for r in successful_configs:
            logger.info(f"  - Fast: {r['fast_window']}, Slow: {r['slow_window']}")
        
        # Find best configuration
        best_config = successful_configs[0]
        logger.info(f"Best configuration: fast={best_config['fast_window']}, slow={best_config['slow_window']}")
        logger.info(f"Config path: {best_config['config_path']}")
        
        return best_config
    else:
        logger.warning("No successful configurations found!")
        return None

def test_other_parameters():
    """Test variations of other parameters like position size and risk limits."""
    logger.info("Testing variations of position sizing and risk parameters")
    
    # Load base config
    base_config_path = "config/head_test.yaml"
    base_config = load_yaml_config(base_config_path)
    if not base_config:
        return
    
    # Create test directory
    test_dir = Path("config/debug_tests")
    test_dir.mkdir(exist_ok=True)
    
    # Define parameter variations to test
    param_variations = [
        {"risk.position_size": 50, "risk.max_position_pct": 0.05},
        {"risk.position_size": 200, "risk.max_position_pct": 0.2},
        {"risk.position_size": 100, "risk.max_position_pct": 0.5},
        {"risk.position_size": 500, "risk.max_position_pct": 1.0},
        {"strategy.parameters.price_key": "close"},
        {"strategy.parameters.price_key": "open"},
        {"backtest.initial_capital": 50000},
        {"backtest.initial_capital": 200000}
    ]
    
    results = []
    
    for i, param_set in enumerate(param_variations):
        # Create unique config name
        config_name = f"param_test_{i+1}"
        test_config_path = test_dir / f"{config_name}.yaml"
        
        # Create changes dictionary
        changes = {}
        for key, value in param_set.items():
            changes[key] = value
        
        # Create test config
        create_test_config(base_config, test_config_path, changes)
        
        # Run backtest
        logger.info(f"Testing parameters: {param_set}")
        result = run_backtest(test_config_path)
        
        # Store result
        result['parameters'] = param_set
        result['config_path'] = str(test_config_path)
        results.append(result)
        
        # Log result
        success_str = "SUCCESS" if result['has_trades'] else "FAILED"
        logger.info(f"Parameter set {i+1}: {success_str}")
        
        # Brief pause to allow logs to flush
        time.sleep(0.5)
    
    # Analyze results
    successful_configs = [r for r in results if r['has_trades']]
    
    logger.info("\n===== RESULTS =====")
    logger.info(f"Tested {len(results)} parameter variations")
    logger.info(f"Successful configurations: {len(successful_configs)}")
    
    if successful_configs:
        logger.info("Successful parameter combinations:")
        for r in successful_configs:
            logger.info(f"  - Parameters: {r['parameters']}")
        
        # Find best configuration
        best_config = successful_configs[0]
        logger.info(f"Best configuration: {best_config['parameters']}")
        logger.info(f"Config path: {best_config['config_path']}")
        
        return best_config
    else:
        logger.warning("No successful configurations found!")
        return None

def main():
    """Main entry point."""
    logger.info("Starting configuration debugger")
    
    # Test MA combinations
    logger.info("\n===== TESTING MA COMBINATIONS =====")
    ma_result = test_ma_combinations()
    
    # Test other parameters
    logger.info("\n===== TESTING OTHER PARAMETERS =====")
    param_result = test_other_parameters()
    
    # Final report
    logger.info("\n===== FINAL REPORT =====")
    
    if ma_result and ma_result['has_trades']:
        logger.info(f"Found working MA combination: fast={ma_result['fast_window']}, slow={ma_result['slow_window']}")
        logger.info(f"Config path: {ma_result['config_path']}")
    else:
        logger.warning("No working MA combinations found")
    
    if param_result and param_result['has_trades']:
        logger.info(f"Found working parameter combination: {param_result['parameters']}")
        logger.info(f"Config path: {param_result['config_path']}")
    else:
        logger.warning("No working parameter combinations found")
    
    logger.info("Configuration debugging completed")

if __name__ == "__main__":
    main()
