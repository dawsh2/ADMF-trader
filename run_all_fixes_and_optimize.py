#!/usr/bin/env python
"""
Run all fixes and then execute the optimization
"""

import os
import sys
import logging
import subprocess
import time

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_and_optimize.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('run_all')

def run_command(cmd, desc=None):
    """Run a command and log the output"""
    if desc:
        logger.info(f"Running: {cmd} - {desc}")
    else:
        logger.info(f"Running: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        logger.info(f"Command completed with return code {result.returncode}")
        logger.info(f"Output: {result.stdout[:500]}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}")
        logger.error(f"Error: {e.stderr}")
        return False

def create_super_charged_config():
    """Create a super-charged configuration with debugging additions"""
    config_content = """# ma_crossover_optimization_fixed.yaml
# Fixed configuration for MA crossover optimization with improved risk management

strategy:
  name: ma_crossover
  parameters:
    fast_window: 5
    slow_window: 20

risk:
  position_manager:
    config:
      fixed_quantity: 10
      max_positions: 1
      enforce_single_position: true
      position_sizing_method: fixed
      allow_multiple_entries: false

backtest:
  initial_capital: 100000.0
  symbols: ['HEAD']  # Trading the HEAD symbol
  timeframe: 1min    # Using 1-minute data
  debug: true        # Enable debugging
  verbose: true      # Enable verbose output

data:
  source_type: csv
  sources:
    - symbol: HEAD
      file: data/HEAD_1min.csv
      date_column: timestamp  # The file uses 'timestamp' as date column
      price_column: Close     # The file uses 'Close' with capital C
      date_format: "%Y-%m-%d %H:%M:%S"  # Format for datetime with both date and time
  debug: true        # Enable debugging for data handler

optimization:
  objective: sharpe_ratio
  method: grid
  verbose: true     # Enable verbose output

# Parameter space definition for optimization - reduced for faster testing
parameter_space:
  - name: fast_window
    type: integer
    min: 5
    max: 10
    step: 5
    description: "Fast moving average window"
  - name: slow_window
    type: integer
    min: 20
    max: 30
    step: 10
    description: "Slow moving average window"
  
initial_capital: 100000.0
"""
    
    config_path = "config/ma_crossover_optimization_fixed.yaml"
    
    logger.info(f"Creating super-charged config: {config_path}")
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Created super-charged config")
        return config_path
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        return None

def fix_position_manager():
    """Add order generation to position manager if not present"""
    position_manager_path = "src/risk/position_manager.py"
    
    logger.info(f"Checking position manager: {position_manager_path}")
    
    try:
        with open(position_manager_path, 'r') as f:
            content = f.read()
        
        # Check if order generation is present
        if 'EventType.ORDER' not in content:
            logger.info("Adding order generation to position manager")
            
            # Create backup
            with open(f"{position_manager_path}.bak", 'w') as f:
                f.write(content)
            
            # Add order generation
            modified_content = content.replace(
                """        # Publish the modified signal
        self.event_bus.publish(Event(
            EventType.SIGNAL,
            modified_signal_data
        ))""",
                """        # Generate order from signal
        order_data = {
            'symbol': symbol,
            'direction': direction,
            'quantity': adjusted_quantity,
            'price': signal_data.get('price', 0.0),
            'rule_id': rule_id,
            'timestamp': signal_data.get('timestamp')
        }
        
        # Log the order generation
        self.logger.info(f"Generating order from signal: {order_data}")
        
        # Publish order event
        self.event_bus.publish(Event(
            EventType.ORDER,
            order_data
        ))"""
            )
            
            # Write modified content
            with open(position_manager_path, 'w') as f:
                f.write(modified_content)
            
            logger.info("Added order generation to position manager")
            return True
        else:
            logger.info("Position manager already has order generation")
            return True
    except Exception as e:
        logger.error(f"Error fixing position manager: {e}")
        return False

def check_event_bus_integration():
    """Make sure event_bus is properly integrated in backtest coordinator"""
    backtest_coord_path = "src/execution/backtest/backtest_coordinator.py"
    
    logger.info(f"Checking backtest coordinator: {backtest_coord_path}")
    
    try:
        with open(backtest_coord_path, 'r') as f:
            content = f.read()
        
        # Check if the event bus is properly shared
        if "self.event_bus = EventBus" in content:
            logger.info("Backtest coordinator has event bus initialization")
        else:
            logger.info("Adding event bus debug to backtest coordinator")
            
            # Create backup
            with open(f"{backtest_coord_path}.bak", 'w') as f:
                f.write(content)
            
            # Add event bus debug
            modified_content = content.replace(
                "def initialize(self, context):",
                """def initialize(self, context):
        # Debug logging for initialization
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Initializing backtest coordinator with context: {context.keys()}")"""
            )
            
            # Write modified content
            with open(backtest_coord_path, 'w') as f:
                f.write(modified_content)
            
            logger.info("Added event bus debug to backtest coordinator")
        
        return True
    except Exception as e:
        logger.error(f"Error checking backtest coordinator: {e}")
        return False

def main():
    """Run all fixes and then optimize"""
    logger.info("Running all fixes and then optimization...")
    
    # Step 1: Fix import paths
    logger.info("Step 1: Fixing import paths...")
    if run_command([sys.executable, "fix_import_paths.py"], "Fixing import paths"):
        logger.info("Import paths fixed successfully")
    else:
        logger.warning("Import path fixes may have failed - continuing anyway")
    
    # Step 2: Fix risk manager
    logger.info("Step 2: Fixing risk manager...")
    if run_command([sys.executable, "fix_risk_manager.py"], "Fixing risk manager"):
        logger.info("Risk manager fixed successfully")
    else:
        logger.warning("Risk manager fixes may have failed - continuing anyway")
    
    # Step 3: Additional fixes
    logger.info("Step 3: Applying additional fixes...")
    
    # Fix position manager to generate orders
    fix_position_manager()
    
    # Check event bus integration
    check_event_bus_integration()
    
    # Create super-charged config
    config_path = create_super_charged_config()
    
    # Wait a moment for everything to settle
    logger.info("Waiting for 1 second before running optimization...")
    time.sleep(1)
    
    # Step 4: Run the optimization
    logger.info("Step 4: Running optimization...")
    
    # Run directly with the main.py script
    optimization_cmd = [
        sys.executable, 
        "main.py", 
        "optimize", 
        "--config", 
        config_path,
        "--verbose"
    ]
    
    if run_command(optimization_cmd, "Running optimization"):
        logger.info("Optimization completed successfully")
    else:
        logger.warning("Optimization may have failed - check logs")
    
    logger.info("All fixes and optimization completed")
    
    # Final message
    logger.info("\nDEBUG INSTRUCTIONS:")
    logger.info("1. Check 'fix_and_optimize.log' for detailed log messages")
    logger.info("2. Check 'optimization_results/' directory for optimization results")
    logger.info("3. If still no trades, run: python main.py optimize --config config/ma_crossover_optimization_fixed.yaml --verbose")

if __name__ == "__main__":
    main()
