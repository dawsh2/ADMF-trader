#!/usr/bin/env python
"""
Run optimization after fixing the indentation error
"""

import os
import sys
import logging
import yaml
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fixed_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fixed_opt')

def create_fixed_config():
    """Create a fixed optimization config"""
    config_content = """# ma_crossover_optimization_fixed.yaml
# Fixed configuration for MA crossover optimization

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

data:
  source_type: csv
  sources:
    - symbol: HEAD
      file: data/HEAD_1min.csv
      date_column: timestamp
      price_column: Close
      date_format: "%Y-%m-%d %H:%M:%S"

optimization:
  objective: sharpe_ratio
  method: grid

# Reduced parameter space for faster testing
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
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Created fixed optimization config at {config_path}")
        return config_path
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        return None

def print_log_snippets(log_path, lines=20):
    """Print the last few lines of a log file"""
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r') as f:
                content = f.readlines()
            
            # Print the last few lines
            logger.info(f"Last {min(lines, len(content))} lines of {log_path}:")
            for line in content[-lines:]:
                logger.info(line.rstrip())
        except Exception as e:
            logger.error(f"Error reading log file {log_path}: {e}")
    else:
        logger.warning(f"Log file {log_path} does not exist")

def run_optimizer():
    """Run the optimization directly"""
    logger.info("Running optimization directly...")
    
    try:
        # Import required modules
        from src.strategy.optimization.optimizer import StrategyOptimizer
        
        # Create the optimizer
        config_path = create_fixed_config()
        optimizer = StrategyOptimizer(config_path)
        
        # Run the optimization
        logger.info("Starting optimization...")
        results = optimizer.optimize()
        
        # Check for trades
        all_results = results.get('all_results', [])
        
        trades_found = False
        for result in all_results:
            train_result = result.get('train_result', {})
            test_result = result.get('test_result', {})
            
            train_trades = train_result.get('trades', [])
            test_trades = test_result.get('trades', [])
            
            if train_trades or test_trades:
                trades_found = True
                logger.info(f"Found trades for parameters: {result.get('parameters')}")
                logger.info(f"Train trades: {len(train_trades)}, Test trades: {len(test_trades)}")
        
        if trades_found:
            logger.info("OPTIMIZATION SUCCESSFUL: Trades were generated!")
        else:
            logger.warning("OPTIMIZATION ISSUE: No trades were generated")
        
        return results
    
    except Exception as e:
        logger.error(f"Error running optimization: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def run_optimizer_subprocess():
    """Run the optimization as a subprocess"""
    logger.info("Running optimization as subprocess...")
    
    # Create the config file
    config_path = create_fixed_config()
    
    # Run the optimization command
    cmd = [
        sys.executable,
        "main.py",
        "optimize",
        "--config",
        config_path,
        "--verbose"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Command completed with return code {result.returncode}")
        logger.info(f"Output: {result.stdout}")
        
        # Check if any output mentions trades
        if "trades" in result.stdout.lower():
            # Look for lines with trade counts
            import re
            trade_counts = re.findall(r'trades.*?(\d+)', result.stdout.lower())
            if trade_counts:
                logger.info(f"Found trade counts in output: {trade_counts}")
                if any(int(count) > 0 for count in trade_counts):
                    logger.info("OPTIMIZATION SUCCESSFUL: Trades were generated!")
                else:
                    logger.warning("OPTIMIZATION ISSUE: Trade counts were all zero")
            else:
                logger.warning("OPTIMIZATION ISSUE: Could not determine trade counts")
        else:
            logger.warning("OPTIMIZATION ISSUE: No mention of trades in output")
        
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}")
        logger.error(f"Error: {e.stderr}")
        return False

def main():
    """Run the optimization directly or as subprocess"""
    logger.info("Running optimization after fixing indentation error...")
    
    # Try both methods
    logger.info("Method 1: Running as subprocess")
    if run_optimizer_subprocess():
        logger.info("Subprocess method succeeded")
    else:
        logger.warning("Subprocess method failed, trying direct method")
        
        logger.info("Method 2: Running directly")
        if run_optimizer():
            logger.info("Direct method succeeded")
        else:
            logger.warning("Both methods failed")
    
    # Check logs for any clues
    logger.info("Checking logs for clues...")
    print_log_snippets("optimization_detailed.log")
    print_log_snippets("fixed_optimization.log")
    
    logger.info("Optimization run completed")

if __name__ == "__main__":
    main()
