#!/usr/bin/env python
"""
Run all fixes including data handler fix and execute the optimization
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
        logging.FileHandler("final_fix_and_optimize.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('final_fix')

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
        if result.stdout:
            logger.info(f"Output (first 500 chars): {result.stdout[:500]}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}")
        if e.stderr:
            logger.error(f"Error (first 500 chars): {e.stderr[:500]}")
        return False

def create_simple_config():
    """Create a simple configuration for testing"""
    config_content = """# simple_ma_crossover.yaml
# Simple configuration for testing MA crossover strategy

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
"""
    
    config_path = "config/simple_ma_crossover.yaml"
    
    logger.info(f"Creating simple config: {config_path}")
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Created simple config at {config_path}")
        return config_path
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        return None

def build_event_bus_logger():
    """Create a helper module to log events"""
    logger_path = "src/util/event_logger.py"
    
    logger.info(f"Creating event logger: {logger_path}")
    
    try:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(logger_path), exist_ok=True)
        
        # Create the logger module
        with open(logger_path, 'w') as f:
            f.write("""\"\"\"
Event logger for debugging purposes.
\"\"\"

import logging
from src.core.events.event_types import EventType

logger = logging.getLogger(__name__)

class EventLogger:
    \"\"\"
    Event logger for debugging event flow.
    \"\"\"
    
    def __init__(self, event_bus, name="event_logger"):
        \"\"\"
        Initialize the event logger.
        
        Args:
            event_bus: Event bus to monitor
            name (str): Logger name
        \"\"\"
        self.event_bus = event_bus
        self.name = name
        self.signal_count = 0
        self.order_count = 0
        self.trade_count = 0
        self.bar_count = 0
        
        # Subscribe to events
        self._subscribe_to_events()
        
        logger.info(f"Event logger {name} initialized")
    
    def _subscribe_to_events(self):
        \"\"\"Subscribe to all event types\"\"\"
        if self.event_bus:
            if hasattr(self.event_bus, 'subscribe'):
                # Subscribe to all event types
                self.event_bus.subscribe(EventType.SIGNAL, self._on_signal)
                self.event_bus.subscribe(EventType.ORDER, self._on_order)
                self.event_bus.subscribe(EventType.TRADE, self._on_trade)
                self.event_bus.subscribe(EventType.BAR, self._on_bar)
                
                logger.info(f"Event logger {self.name} subscribed to events")
            else:
                logger.warning(f"Event bus does not have subscribe method")
        else:
            logger.warning(f"No event bus provided to event logger")
    
    def _on_signal(self, event):
        \"\"\"Log signal events\"\"\"
        self.signal_count += 1
        data = event.get_data()
        symbol = data.get('symbol')
        signal_value = data.get('signal_value')
        price = data.get('price')
        
        logger.info(f"SIGNAL #{self.signal_count}: symbol={symbol}, value={signal_value}, price={price}")
    
    def _on_order(self, event):
        \"\"\"Log order events\"\"\"
        self.order_count += 1
        data = event.get_data()
        symbol = data.get('symbol')
        direction = data.get('direction')
        quantity = data.get('quantity')
        order_type = data.get('type')
        price = data.get('price')
        
        logger.info(f"ORDER #{self.order_count}: symbol={symbol}, direction={direction}, quantity={quantity}, type={order_type}, price={price}")
    
    def _on_trade(self, event):
        \"\"\"Log trade events\"\"\"
        self.trade_count += 1
        data = event.get_data()
        symbol = data.get('symbol')
        direction = data.get('direction')
        quantity = data.get('quantity')
        price = data.get('price')
        
        logger.info(f"TRADE #{self.trade_count}: symbol={symbol}, direction={direction}, quantity={quantity}, price={price}")
    
    def _on_bar(self, event):
        \"\"\"Log bar events\"\"\"
        self.bar_count += 1
        if self.bar_count % 100 == 0:  # Only log every 100th bar to avoid excessive logging
            data = event.get_data()
            symbol = data.get('symbol')
            timestamp = data.get('timestamp')
            close = data.get('close')
            
            logger.info(f"BAR #{self.bar_count}: symbol={symbol}, timestamp={timestamp}, close={close}")
    
    def print_summary(self):
        \"\"\"Print a summary of event counts\"\"\"
        logger.info(f"EVENT SUMMARY for {self.name}:")
        logger.info(f"  Signals: {self.signal_count}")
        logger.info(f"  Orders: {self.order_count}")
        logger.info(f"  Trades: {self.trade_count}")
        logger.info(f"  Bars: {self.bar_count}")
        
        # Check for issues
        if self.signal_count > 0 and self.order_count == 0:
            logger.warning("ISSUE: Signals were generated but no orders - check risk manager")
        if self.order_count > 0 and self.trade_count == 0:
            logger.warning("ISSUE: Orders were generated but no trades - check broker")
        if self.bar_count == 0:
            logger.warning("ISSUE: No bars were processed - check data handler")


def attach_to_backtest(backtest_instance):
    \"\"\"
    Attach event logger to a backtest instance.
    
    Args:
        backtest_instance: Backtest coordinator instance
    
    Returns:
        EventLogger: The attached event logger
    \"\"\"
    # Get the event bus from the backtest
    event_bus = None
    if hasattr(backtest_instance, 'event_bus'):
        event_bus = backtest_instance.event_bus
    elif hasattr(backtest_instance, 'components') and isinstance(backtest_instance.components, dict):
        event_bus = backtest_instance.components.get('event_bus')
    
    if event_bus:
        # Create and return event logger
        return EventLogger(event_bus, f"backtest_logger_{id(backtest_instance)}")
    else:
        logger.warning(f"Could not find event bus in backtest instance")
        return None
""")
        
        logger.info(f"Created event logger at {logger_path}")
        
        # Create an initialization file for the util package
        init_path = "src/util/__init__.py"
        with open(init_path, 'w') as f:
            f.write('"""Utility package"""')
        
        logger.info(f"Created util package initialization file at {init_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating event logger: {e}")
        return False

def create_backtest_hooks():
    """Create hooks for the backtest to add logging"""
    hooks_path = "src/util/backtest_hooks.py"
    
    logger.info(f"Creating backtest hooks: {hooks_path}")
    
    try:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(hooks_path), exist_ok=True)
        
        # Create the hooks module
        with open(hooks_path, 'w') as f:
            f.write("""\"\"\"
Hooks for adding functionality to the backtest coordinator.
\"\"\"

import logging
from src.execution.backtest.backtest_coordinator import BacktestCoordinator
from src.util.event_logger import EventLogger

logger = logging.getLogger(__name__)

def install_hooks():
    \"\"\"Install hooks for debugging\"\"\"
    logger.info("Installing backtest hooks")
    
    # Store the original run method
    original_run = BacktestCoordinator.run
    
    # Create a new run method with debugging
    def debug_run(self, *args, **kwargs):
        logger.info(f"BACKTEST START: {self.name}")
        
        # Log components
        if hasattr(self, 'components'):
            logger.info(f"BACKTEST COMPONENTS:")
            for name, component in self.components.items():
                logger.info(f"  - {name}: {component.__class__.__name__}")
        
        # Check for symbols in data handler
        data_handler = None
        if hasattr(self, 'data_handler'):
            data_handler = self.data_handler
        elif hasattr(self, 'components') and 'data_handler' in self.components:
            data_handler = self.components['data_handler']
        
        if data_handler:
            logger.info(f"DATA HANDLER: {data_handler.__class__.__name__}")
            
            # Try to get symbols
            if hasattr(data_handler, 'get_symbols') and callable(data_handler.get_symbols):
                symbols = data_handler.get_symbols()
                logger.info(f"SYMBOLS: {symbols}")
            elif hasattr(data_handler, 'data') and isinstance(data_handler.data, dict):
                symbols = list(data_handler.data.keys())
                logger.info(f"SYMBOLS (from data keys): {symbols}")
            else:
                logger.warning("No symbols found in data handler")
        
        # Check for strategy
        strategy = None
        if hasattr(self, 'strategy'):
            strategy = self.strategy
        elif hasattr(self, 'components') and 'strategy' in self.components:
            strategy = self.components['strategy']
        elif hasattr(self, 'components') and 'strategy_adapter' in self.components:
            strategy_adapter = self.components['strategy_adapter']
            if hasattr(strategy_adapter, 'strategy'):
                strategy = strategy_adapter.strategy
        
        if strategy:
            logger.info(f"STRATEGY: {strategy.__class__.__name__}")
            
            # Check for symbols in strategy
            if hasattr(strategy, 'symbols'):
                logger.info(f"STRATEGY SYMBOLS: {strategy.symbols}")
            
            # Check for parameters
            if hasattr(strategy, 'parameters'):
                logger.info(f"STRATEGY PARAMETERS: {strategy.parameters}")
        
        # Attach event logger
        event_logger = EventLogger(self.event_bus, "backtest_event_logger")
        
        # Run the original method
        result = original_run(self, *args, **kwargs)
        
        # Print event summary
        if event_logger:
            event_logger.print_summary()
        
        logger.info(f"BACKTEST END: {self.name}")
        return result
    
    # Install the debug run method
    BacktestCoordinator.run = debug_run
    logger.info("Backtest hooks installed")
    
    return True
""")
        
        logger.info(f"Created backtest hooks at {hooks_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating backtest hooks: {e}")
        return False

def create_run_simple_backtest():
    """Create a script to run a simple backtest with all fixes"""
    script_path = "run_simple_backtest.py"
    
    logger.info(f"Creating simple backtest runner: {script_path}")
    
    try:
        with open(script_path, 'w') as f:
            f.write("""#!/usr/bin/env python
\"\"\"
Run a simple backtest with all fixes applied.
\"\"\"

import os
import sys
import logging
import importlib

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simple_backtest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('simple_backtest')

def run_backtest():
    \"\"\"Run a simple backtest with all fixes\"\"\"
    logger.info("Running simple backtest with all fixes...")
    
    # First, install hooks for debugging
    try:
        from src.util.backtest_hooks import install_hooks
        install_hooks()
        logger.info("Installed backtest hooks")
    except ImportError:
        logger.warning("Could not import backtest hooks - run fix_data_handler.py first")
    
    # Import required components
    from src.execution.backtest.backtest_coordinator import BacktestCoordinator
    import yaml
    
    # Load the configuration
    config_path = "config/simple_ma_crossover.yaml"
    logger.info(f"Loading configuration from {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return False
    
    # Create and run the backtest
    logger.info("Creating backtest coordinator")
    backtest = BacktestCoordinator('simple_backtest', config)
    
    # Initialize and run backtest
    logger.info("Initializing backtest")
    backtest.initialize()
    
    logger.info("Running backtest")
    backtest.run()
    
    # Get and print results
    results = backtest.get_results()
    
    # Check for trades
    trades = results.get('trades', [])
    logger.info(f"Backtest completed with {len(trades)} trades")
    
    # Print trade details if any
    if trades:
        logger.info("Trade details:")
        for i, trade in enumerate(trades[:5]):  # Print first 5 trades
            logger.info(f"  Trade {i+1}: {trade}")
        
        if len(trades) > 5:
            logger.info(f"  ... and {len(trades) - 5} more trades")
    else:
        logger.warning("No trades were generated!")
    
    # Print statistics
    stats = results.get('statistics', {})
    logger.info("Backtest statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    return len(trades) > 0

if __name__ == "__main__":
    success = run_backtest()
    
    if success:
        logger.info("SUCCESS: The backtest generated trades!")
    else:
        logger.warning("FAILURE: The backtest did not generate any trades.")
""")
        
        logger.info(f"Created simple backtest runner at {script_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating simple backtest runner: {e}")
        return False

def main():
    """Run all fixes and execute optimization"""
    logger.info("Running all fixes and optimization...")
    
    # Step 1: Fix import paths
    logger.info("Step 1: Fixing import paths...")
    run_command([sys.executable, "fix_import_paths.py"], "Fixing import paths")
    
    # Step 2: Fix risk manager
    logger.info("Step 2: Fixing risk manager...")
    run_command([sys.executable, "fix_risk_manager.py"], "Fixing risk manager")
    
    # Step 3: Fix data handler
    logger.info("Step 3: Fixing data handler...")
    run_command([sys.executable, "fix_data_handler.py"], "Fixing data handler")
    
    # Step 4: Create additional helper modules
    logger.info("Step 4: Creating helper modules...")
    
    # Create simple test config
    create_simple_config()
    
    # Create event logger
    build_event_bus_logger()
    
    # Create backtest hooks
    create_backtest_hooks()
    
    # Create simple backtest runner
    create_run_simple_backtest()
    
    # Wait a moment for everything to settle
    logger.info("Waiting for 1 second before running backtest...")
    time.sleep(1)
    
    # Step 5: Run the simple backtest
    logger.info("Step 5: Running simple backtest...")
    
    run_command([sys.executable, "run_simple_backtest.py"], "Running simple backtest")
    
    logger.info("All fixes and backtest completed")
    
    # Final message
    logger.info("\nDEBUG INSTRUCTIONS:")
    logger.info("1. Check 'simple_backtest.log' for detailed log messages")
    logger.info("2. If simple backtest worked, run the optimization:")
    logger.info("   python main.py optimize --config config/ma_crossover_optimization_fixed.yaml")

if __name__ == "__main__":
    main()
