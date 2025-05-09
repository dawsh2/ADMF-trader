#!/usr/bin/env python
"""
Run all fixes and execute the optimization
"""

import os
import sys
import logging
import subprocess
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("all_fixed.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('all_fixed')

def run_script(script_name, desc=None):
    """Run a Python script and log the output"""
    if desc:
        logger.info(f"Running {script_name}: {desc}")
    else:
        logger.info(f"Running {script_name}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"{script_name} completed with return code {result.returncode}")
        logger.info(f"Output (first 500 chars): {result.stdout[:500]}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"{script_name} failed with return code {e.returncode}")
        logger.error(f"Error (first 500 chars): {e.stderr[:500]}")
        return False

def create_ultra_simple_config():
    """Create a super simple config file that will work"""
    config_content = """# ultra_simple.yaml
# Ultra simple configuration for testing

strategy:
  name: ma_crossover
  parameters:
    fast_window: 5
    slow_window: 20
    symbols: ['HEAD']  # Explicitly set symbols

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

# Only one parameter combination
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
    
    config_path = "config/ultra_simple.yaml"
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Created ultra simple config at {config_path}")
        return config_path
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        return None

def run_main_optimize():
    """Run the main.py optimize command with the ultra simple config"""
    logger.info("Running main.py optimize with ultra simple config")
    
    # Create the config
    config_path = create_ultra_simple_config()
    
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
        
        # Save the full output to a file
        with open("optimization_output.txt", 'w') as f:
            f.write(result.stdout)
        
        logger.info(f"Full output saved to optimization_output.txt")
        
        # Display a summary
        if "trades" in result.stdout.lower():
            # Look for any mention of trades
            import re
            trade_counts = re.findall(r'trades.*?(\d+)', result.stdout.lower())
            
            if trade_counts:
                logger.info(f"Found trade counts in output: {trade_counts}")
                
                if any(int(count) > 0 for count in trade_counts if count.isdigit()):
                    logger.info("SUCCESS: Trades were generated!")
                    return True
            
            logger.warning("No trades were found in the output")
        else:
            logger.warning("No mention of trades in output")
        
        return False
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}")
        logger.error(f"Error: {e.stderr}")
        return False

def create_direct_test_script():
    """Create a script that directly tests the strategy with data"""
    script_content = """#!/usr/bin/env python
\"\"\"
Direct test of MA Crossover strategy without the optimization framework
\"\"\"

import os
import sys
import logging
import pandas as pd
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("direct_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('direct_test')

def test_strategy_directly():
    \"\"\"Test the MA Crossover strategy directly with data\"\"\"
    logger.info("Testing MA Crossover strategy directly")
    
    try:
        # Import strategy
        from src.strategy.implementations.backup.ma_crossover_fixed import MACrossoverStrategy
        from src.core.events.event_bus import EventBus
        from src.core.events.event_types import Event, EventType
        
        # Create mock components
        event_bus = EventBus("test")
        
        # Track signals
        signals = []
        
        def signal_handler(event):
            logger.info(f"Signal received: {event}")
            signals.append(event)
        
        # Subscribe to signals
        event_bus.subscribe(EventType.SIGNAL, signal_handler)
        
        # Create strategy with explicit symbols
        strategy = MACrossoverStrategy(
            event_bus=event_bus,
            data_handler=None,
            parameters={
                'fast_window': 5,
                'slow_window': 20,
                'symbols': ['HEAD']
            }
        )
        
        # Check if symbols are set
        if hasattr(strategy, 'symbols'):
            logger.info(f"Strategy symbols: {strategy.symbols}")
        else:
            logger.warning("Strategy has no symbols attribute")
            # Add symbols directly
            strategy.symbols = ['HEAD']
        
        # Load data
        data_path = "data/HEAD_1min.csv"
        try:
            df = pd.read_csv(data_path)
            logger.info(f"Loaded data with {len(df)} rows")
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create bar events
            class BarEvent:
                def __init__(self, symbol, timestamp, open_price, high, low, close, volume):
                    self.symbol = symbol
                    self.timestamp = timestamp
                    self.open = open_price
                    self.high = high
                    self.low = low
                    self.close = close
                    self.volume = volume
                
                def get_symbol(self):
                    return self.symbol
                
                def get_timestamp(self):
                    return self.timestamp
                
                def get_close(self):
                    return self.close
                
                def get_data(self):
                    return {
                        'symbol': self.symbol,
                        'timestamp': self.timestamp,
                        'open': self.open,
                        'high': self.high,
                        'low': self.low,
                        'close': self.close,
                        'volume': self.volume
                    }
            
            # Process each bar
            logger.info("Processing bars...")
            for i, row in df.iterrows():
                bar = BarEvent(
                    symbol='HEAD',
                    timestamp=row['timestamp'],
                    open_price=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=row['Volume']
                )
                
                # Create an event to pass to the strategy
                event = Event(EventType.BAR, bar.get_data())
                event.get_symbol = bar.get_symbol
                event.get_timestamp = bar.get_timestamp
                event.get_close = bar.get_close
                
                # Process the bar
                strategy.on_bar(event)
                
                # Print progress every 100 bars
                if i % 100 == 0:
                    logger.info(f"Processed {i} bars, generated {len(signals)} signals so far")
            
            # Check if any signals were generated
            logger.info(f"Processing complete. Generated {len(signals)} signals")
            
            for i, signal in enumerate(signals[:10]):
                logger.info(f"Signal {i+1}: {signal}")
            
            if len(signals) > 10:
                logger.info(f"... and {len(signals) - 10} more signals")
            
            return len(signals) > 0
                
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    except Exception as e:
        logger.error(f"Error in direct test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_strategy_directly()
    
    if success:
        logger.info("SUCCESS: Strategy generated signals directly!")
    else:
        logger.warning("FAILURE: Strategy did not generate signals directly")
"""
    
    script_path = "test_strategy_directly.py"
    
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        logger.info(f"Created direct test script at {script_path}")
        return script_path
    except Exception as e:
        logger.error(f"Error creating script: {e}")
        return None

def main():
    """Run all fixes and tests"""
    logger.info("Running all fixes and tests")
    
    # Step 1: Fix import paths
    logger.info("Step 1: Fix import paths")
    run_script("fix_import_paths.py", "Fixing import paths")
    
    # Step 2: Fix risk manager
    logger.info("Step 2: Fix risk manager")
    run_script("fix_risk_manager.py", "Fixing risk manager")
    
    # Step 3: Fix data handler
    logger.info("Step 3: Fix data handler")
    run_script("fix_data_handler.py", "Fixing data handler")
    
    # Step 4: Fix strategy symbols
    logger.info("Step 4: Fix strategy symbols")
    run_script("fix_strategy_symbols.py", "Fixing strategy symbols")
    
    # Create direct test script
    logger.info("Creating direct test script")
    create_direct_test_script()
    
    # Step 5: Test strategy directly
    logger.info("Step 5: Test strategy directly")
    run_script("test_strategy_directly.py", "Testing strategy directly")
    
    # Step 6: Run optimization
    logger.info("Step 6: Run optimization")
    success = run_main_optimize()
    
    if success:
        logger.info("SUCCESS: All fixes applied and optimization generated trades!")
    else:
        logger.warning("ISSUE: Optimization may still have issues - check the logs")
    
    logger.info("All tests completed - check the logs for details")

if __name__ == "__main__":
    main()
