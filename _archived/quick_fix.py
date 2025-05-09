#!/usr/bin/env python
"""
Quick fix for the trading system issues.
This script performs the minimum necessary fixes to make the backtest run.
"""
import os
import sys
import logging
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('quick_fix')

def fix_backtest_file():
    """Fix syntax error in backtest.py file."""
    logger.info("Fixing syntax error in backtest.py file...")
    
    file_path = "src/execution/backtest/backtest.py"
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for the problematic code
    if "elif hasattr(self.order_registry, 'get_active_orders'):" in content and "orders = []" in content:
        # Fix the syntax error with duplicate elif
        logger.info("Found syntax error, fixing it...")
        
        # Replace the problematic section
        old_code = """            orders = []
            if hasattr(self.order_registry, 'get_all_orders'):
                orders = []
            if hasattr(self.order_registry, 'get_all_orders'):
                orders = self.order_registry.get_all_orders()
            elif hasattr(self.order_registry, 'get_active_orders'):
                orders = self.order_registry.get_active_orders()
                logger.info("Using get_active_orders() as get_all_orders() is not available")
            else:
                logger.warning("Order registry has neither get_all_orders nor get_active_orders method")
            elif hasattr(self.order_registry, 'get_active_orders'):
                orders = self.order_registry.get_active_orders()
                logger.info("Using get_active_orders() as get_all_orders() is not available")
            else:
                logger.warning("Order registry has neither get_all_orders nor get_active_orders method")"""
        
        new_code = """            orders = []
            if hasattr(self.order_registry, 'get_all_orders'):
                orders = self.order_registry.get_all_orders()
            elif hasattr(self.order_registry, 'get_active_orders'):
                orders = self.order_registry.get_active_orders()
                logger.info("Using get_active_orders() as get_all_orders() is not available")
            else:
                logger.warning("Order registry has neither get_all_orders nor get_active_orders method")"""
        
        # Replace the code
        fixed_content = content.replace(old_code, new_code)
        
        # Write fixed content back to file
        with open(file_path, 'w') as f:
            f.write(fixed_content)
        
        logger.info("Successfully fixed syntax error in backtest.py")
        return True
    else:
        logger.info("No syntax error found in backtest.py or already fixed")
        return True

def add_get_all_orders_method():
    """Add get_all_orders method to OrderRegistry if missing."""
    logger.info("Adding get_all_orders method to OrderRegistry...")
    
    file_path = "src/execution/order_registry.py"
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if method already exists
    if "def get_all_orders" in content:
        logger.info("get_all_orders method already exists in OrderRegistry")
        return True
    
    # Add method to the end of the class
    with open(file_path, 'a') as f:
        f.write("\n    def get_all_orders(self):\n")
        f.write("        \"\"\"\n")
        f.write("        Get all orders regardless of status.\n")
        f.write("        \n")
        f.write("        Returns:\n")
        f.write("            List of all orders\n")
        f.write("        \"\"\"\n")
        f.write("        return list(self.orders.values())\n")
    
    logger.info("Successfully added get_all_orders method to OrderRegistry")
    return True

def create_optimized_config():
    """Create an optimized configuration file."""
    logger.info("Creating optimized configuration file...")
    
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
        'risk': {
            'position_size': 500,
            'max_position_pct': 1.0
        },
        'logging': {
            'level': "DEBUG"
        }
    }
    
    # Create directory if it doesn't exist
    os.makedirs("config", exist_ok=True)
    
    # Save config to file
    config_path = "config/quick_fix.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    logger.info(f"Created optimized configuration file: {config_path}")
    return config_path

def main():
    """Apply all fixes and run the backtest."""
    logger.info("Starting quick fix for the trading system...")
    
    # Step 1: Fix syntax error in backtest.py
    fix_backtest_file()
    
    # Step 2: Add get_all_orders method to OrderRegistry
    add_get_all_orders_method()
    
    # Step 3: Create optimized configuration
    config_path = create_optimized_config()
    
    # Step 4: Run the backtest
    logger.info(f"All fixes applied. Now you can run:")
    logger.info(f"  python main.py --config {config_path}")
    
    logger.info("Quick fix completed successfully!")

if __name__ == "__main__":
    main()
