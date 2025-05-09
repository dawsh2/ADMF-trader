#!/usr/bin/env python
"""
Run optimization after fixing all issues (including the syntax error)
"""

import os
import sys
import logging
import yaml
import subprocess
import time

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("final_fixed_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('final_fix')

def create_minimal_config():
    """Create a minimal config for testing"""
    config_content = """# minimal_ma_crossover.yaml
# Minimal configuration for testing MA crossover strategy

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
  symbols: ['HEAD']
  timeframe: 1min

data:
  source_type: csv
  sources:
    - symbol: HEAD
      file: data/HEAD_1min.csv
      date_column: timestamp
      price_column: Close
      date_format: "%Y-%m-%d %H:%M:%S"

# Only test one parameter combination to speed up testing
parameter_space:
  - name: fast_window
    type: integer
    min: 5
    max: 5
    step: 1
    description: "Fast moving average window"
  - name: slow_window
    type: integer
    min: 20
    max: 20
    step: 1
    description: "Slow moving average window"
"""
    
    config_path = "config/minimal_ma_crossover.yaml"
    
    logger.info(f"Creating minimal config at {config_path}")
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Created minimal config at {config_path}")
        return config_path
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        return None

def run_direct():
    """Run the optimizer directly"""
    logger.info("Running the optimizer directly...")
    
    try:
        # Import required modules
        from src.strategy.optimization.optimizer import StrategyOptimizer
        
        # Create the optimizer with minimal config
        config_path = create_minimal_config()
        optimizer = StrategyOptimizer(config_path)
        
        # Run the optimizer
        logger.info("Running optimization...")
        results = optimizer.optimize()
        
        # Check for trades
        if 'all_results' in results:
            for result in results['all_results']:
                train_result = result.get('train_result', {})
                test_result = result.get('test_result', {})
                
                train_trades = train_result.get('trades', [])
                test_trades = test_result.get('trades', [])
                
                logger.info(f"Parameters: {result.get('parameters')}")
                logger.info(f"Train trades: {len(train_trades)}")
                logger.info(f"Test trades: {len(test_trades)}")
                
                if train_trades or test_trades:
                    logger.info("SUCCESS: Trades were generated!")
                    for i, trade in enumerate(train_trades[:3]):
                        logger.info(f"Trade {i+1}: {trade}")
                    return True
        
        logger.warning("No trades were generated in the optimization")
        return False
    
    except Exception as e:
        logger.error(f"Error running optimizer directly: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def run_subprocess():
    """Run the optimizer as a subprocess"""
    logger.info("Running the optimizer as a subprocess...")
    
    # Create the minimal config
    config_path = create_minimal_config()
    
    # Build the command
    cmd = [
        sys.executable,
        "main.py",
        "optimize",
        "--config",
        config_path,
        "--verbose"
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Command completed with return code {result.returncode}")
        
        # Log the output in chunks to avoid truncation
        output = result.stdout
        chunk_size = 2000
        for i in range(0, len(output), chunk_size):
            logger.info(f"Output chunk {i//chunk_size + 1}: {output[i:i+chunk_size]}")
        
        # Check if optimization was successful
        if "Optimization completed" in output:
            logger.info("Optimization completed successfully")
            
            # Look for trade information
            import re
            trade_counts = re.findall(r'trades.*?(\d+)', output.lower())
            
            if trade_counts:
                logger.info(f"Found trade counts in output: {trade_counts}")
                
                if any(int(count) > 0 for count in trade_counts if count.isdigit()):
                    logger.info("SUCCESS: Trades were generated!")
                    return True
            
            logger.warning("No trades were found in the output")
        else:
            logger.warning("Optimization may not have completed successfully")
        
        return False
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}")
        
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        
        return False

def main():
    """Run both methods to test the optimization"""
    logger.info("Running final fixed optimization...")
    
    # Try both methods
    logger.info("Method 1: Running as subprocess")
    if run_subprocess():
        logger.info("Subprocess method succeeded!")
    else:
        logger.warning("Subprocess method failed, trying direct method")
        
        logger.info("Method 2: Running directly")
        if run_direct():
            logger.info("Direct method succeeded!")
        else:
            logger.warning("Both methods failed")
    
    logger.info("Optimization testing completed")

if __name__ == "__main__":
    main()
