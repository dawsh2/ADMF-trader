#!/usr/bin/env python
"""
Run a backtest with optimized parameters to generate trades.
"""
import os
import sys
import logging
import yaml
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fixed_backtest')

def create_optimized_config():
    """Create an optimized configuration for successful backtesting."""
    logger.info("Creating optimized configuration...")
    
    config = {
        'backtest': {
            'initial_capital': 100000.0,
            'symbols': ['SPY'],
            'timeframe': "1min",
            'start_date': "2024-01-01",
            'end_date': "2024-12-31"
        },
        'data': {
            'source_type': "csv",
            'custom_data': {
                'file': "HEAD_1min.csv",
                'symbol_column': None
            }
        },
        'strategy': {
            'type': "ma_crossover",
            'parameters': {
                'fast_window': 2,  # Very small for more signals
                'slow_window': 5,  # Very small for more signals
                'price_key': "close"
            }
        },
        'risk_manager': {
            'position_size': 500,
            'max_position_pct': 1.0
        },
        'logging': {
            'level': "DEBUG",
            'components': [
                "strategy.implementations.ma_crossover",
                "execution.order_registry",
                "execution.order_manager",
                "execution.backtest.backtest",
                "risk.managers.simple"
            ]
        }
    }
    
    # Create directory if it doesn't exist
    os.makedirs("config", exist_ok=True)
    
    # Save config to file
    config_path = "config/optimized.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    logger.info(f"Saved optimized config to {config_path}")
    return config_path

def run_backtest(config_path):
    """Run the backtest with the given config."""
    logger.info(f"Running backtest with config: {config_path}")
    
    # Run the backtest
    result = subprocess.run(["python", "main.py", "--config", config_path], 
                          capture_output=True, text=True)
    
    # Print output
    logger.info("Backtest output:")
    print(result.stdout)
    
    if "Backtest did not produce any results: No trades were executed" in result.stdout:
        logger.warning("Backtest failed: No trades were executed")
        return False
    else:
        logger.info("Backtest succeeded!")
        return True

def main():
    """Main function to run the fixed backtest."""
    logger.info("Running fixed backtest")
    
    # Create optimized config
    config_path = create_optimized_config()
    
    # Add get_all_orders method to OrderRegistry if not already there
    registry_path = "src/execution/order_registry.py"
    if os.path.exists(registry_path):
        with open(registry_path, 'r') as f:
            content = f.read()
        
        if "def get_all_orders" not in content:
            logger.info("Adding get_all_orders method to OrderRegistry")
            with open(registry_path, 'a') as f:
                f.write("\n    def get_all_orders(self):\n")
                f.write("        \"\"\"\n")
                f.write("        Get all orders regardless of status.\n")
                f.write("        \n")
                f.write("        Returns:\n")
                f.write("            List of all orders\n")
                f.write("        \"\"\"\n")
                f.write("        return list(self.orders.values())\n")
    
    # Run the backtest
    success = run_backtest(config_path)
    
    if success:
        logger.info("Backtest completed successfully!")
        logger.info(f"You can use this config for future backtests: {config_path}")
    else:
        logger.warning("Backtest failed. Please check the logs for details.")

if __name__ == "__main__":
    main()
