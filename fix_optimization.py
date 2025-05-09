#!/usr/bin/env python
"""
Apply specific fixes to solve the "no trades" issue
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fix')

def patch_risk_manager():
    """Add debugging and fix potential issues in the risk manager"""
    risk_manager_path = "src/risk/position_manager.py"
    
    logger.info(f"Looking for risk manager at: {risk_manager_path}")
    if not os.path.exists(risk_manager_path):
        logger.error(f"Risk manager not found at: {risk_manager_path}")
        return False
    
    # Make a backup of the original file
    backup_path = f"{risk_manager_path}.bak"
    try:
        with open(risk_manager_path, 'r') as f:
            original_content = f.read()
        
        with open(backup_path, 'w') as f:
            f.write(original_content)
        
        logger.info(f"Backed up original risk manager to: {backup_path}")
    except Exception as e:
        logger.error(f"Failed to backup risk manager: {e}")
        return False
    
    # Add debug logging to the risk manager
    try:
        # Find the on_signal method
        if "def on_signal" in original_content:
            # Add debug logging to the on_signal method
            modified_content = original_content.replace(
                "def on_signal(self, signal_event):",
                """def on_signal(self, signal_event):
        # Debug logging for signal events
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"RISK MANAGER received signal: {signal_event}")"""
            )
            
            # Find where orders are generated and add more logging
            modified_content = modified_content.replace(
                "self.event_bus.publish(order_event)",
                """# Debug before publishing order
        logger.info(f"RISK MANAGER generating order: {order_event}")
        # Ensure the event bus is available
        if self.event_bus:
            self.event_bus.publish(order_event)
        else:
            logger.error("EVENT BUS IS NONE - Cannot publish order!")"""
            )
            
            # Patch enforce_single_position logic if it exists
            if "enforce_single_position" in modified_content:
                # Make sure single position enforcement does not block all trades
                modified_content = modified_content.replace(
                    "if self.enforce_single_position and len(self.positions) >= self.max_positions:",
                    """if self.enforce_single_position and len(self.positions) >= self.max_positions:
            # Debug log position enforcement
            logger.info(f"Position enforcement triggered. Current positions: {self.positions}")
            
            # Allow closing positions even when at max
            if signal_event.get_signal_value() < 0 and self.positions:
                logger.info("Allowing sell signal despite max positions")
                pass  # Continue processing for sell signals
            else:"""
                )
            
            # Write the modified file
            with open(risk_manager_path, 'w') as f:
                f.write(modified_content)
            
            logger.info("Added debug logging to risk manager")
            return True
        else:
            logger.error("Could not find on_signal method in risk manager")
            return False
    except Exception as e:
        logger.error(f"Failed to patch risk manager: {e}")
        
        # Restore backup
        with open(backup_path, 'r') as f:
            original_content = f.read()
        
        with open(risk_manager_path, 'w') as f:
            f.write(original_content)
        
        logger.info("Restored original risk manager from backup")
        return False

def patch_backtest_coordinator():
    """Add debugging and fix potential issues in the backtest coordinator"""
    backtest_path = "src/execution/backtest/backtest_coordinator.py"
    
    logger.info(f"Looking for backtest coordinator at: {backtest_path}")
    if not os.path.exists(backtest_path):
        logger.error(f"Backtest coordinator not found at: {backtest_path}")
        return False
    
    # Make a backup of the original file
    backup_path = f"{backtest_path}.bak"
    try:
        with open(backtest_path, 'r') as f:
            original_content = f.read()
        
        with open(backup_path, 'w') as f:
            f.write(original_content)
        
        logger.info(f"Backed up original backtest coordinator to: {backup_path}")
    except Exception as e:
        logger.error(f"Failed to backup backtest coordinator: {e}")
        return False
    
    # Add debug logging to the backtest coordinator
    try:
        # Find the run method
        if "def run(self" in original_content:
            # Add debug logging to the run method
            modified_content = original_content.replace(
                "def run(self",
                """def run(self"""
            )
            
            # Find where the backtest loop runs
            if "self.data_handler.update()" in modified_content:
                modified_content = modified_content.replace(
                    "while self.data_handler.update():",
                    """# Debug log before starting backtest loop
            logger.info("Starting backtest run loop")
            
            # Ensure the critical components are correctly set up
            if not hasattr(self, 'event_bus') or not self.event_bus:
                logger.error("EVENT BUS IS MISSING in backtest!")
                self.event_bus = self.components.get('event_bus')
                if self.event_bus:
                    logger.info(f"Recovered event bus from components: {self.event_bus}")
                else:
                    logger.critical("CANNOT RECOVER EVENT BUS - Backtest will fail!")
            
            iteration = 0
            while self.data_handler.update():
                iteration += 1
                if iteration % 100 == 0:
                    logger.info(f"Processed {iteration} iterations")"""
                )
            
            # Fix result extraction
            if "def get_results(self" in modified_content:
                modified_content = modified_content.replace(
                    "def get_results(self):",
                    """def get_results(self):
        # Debug log result extraction
        logger.info("Extracting backtest results")
        
        # Check for trade repository
        if not hasattr(self, 'trade_repository') or not self.trade_repository:
            logger.warning("No trade repository found!")
            
            # Try to recover from components
            self.trade_repository = self.components.get('trade_repository')
            if self.trade_repository:
                logger.info(f"Recovered trade repository from components")
            else:
                logger.critical("CANNOT RECOVER TRADE REPOSITORY - No trades will be reported!")
                return {
                    'trades': [],
                    'statistics': {
                        'return_pct': 0,
                        'sharpe_ratio': 0,
                        'profit_factor': 0,
                        'max_drawdown': 0,
                        'trades_executed': 0
                    },
                    'warning': 'No trade repository available'
                }"""
                )
            
            # Write the modified file
            with open(backtest_path, 'w') as f:
                f.write(modified_content)
            
            logger.info("Added debug logging to backtest coordinator")
            return True
        else:
            logger.error("Could not find run method in backtest coordinator")
            return False
    except Exception as e:
        logger.error(f"Failed to patch backtest coordinator: {e}")
        
        # Restore backup
        with open(backup_path, 'r') as f:
            original_content = f.read()
        
        with open(backtest_path, 'w') as f:
            f.write(original_content)
        
        logger.info("Restored original backtest coordinator from backup")
        return False

def fix_event_bus_singleton():
    """Create an enhanced version of the event bus that logs all events"""
    event_bus_path = "src/core/events/enhanced_event_bus.py"
    
    logger.info(f"Creating enhanced event bus at: {event_bus_path}")
    
    try:
        # Create a new enhanced event bus
        with open(event_bus_path, 'w') as f:
            f.write("""\"\"\"
Enhanced event bus with extensive logging for debugging.
\"\"\"

import logging
from src.core.events.event_bus import EventBus as OriginalEventBus, EventType

logger = logging.getLogger(__name__)

class EnhancedEventBus(OriginalEventBus):
    \"\"\"
    Enhanced event bus with logging for debugging.
    \"\"\"
    
    instance = None
    
    @classmethod
    def get_instance(cls, name="global"):
        \"\"\"
        Get a singleton instance of the event bus.
        \"\"\"
        if cls.instance is None:
            logger.info(f"Creating new EnhancedEventBus instance: {name}")
            cls.instance = cls(name)
        return cls.instance
    
    def __init__(self, name="enhanced"):
        \"\"\"
        Initialize the enhanced event bus.
        \"\"\"
        super().__init__(name)
        logger.info(f"Enhanced event bus initialized: {name}")
        
        # Add debug listeners for all event types
        for event_type in EventType:
            self.subscribe(event_type, self._debug_listener)
        
        logger.info("Added debug listeners for all event types")
    
    def _debug_listener(self, event):
        \"\"\"
        Debug listener for all events.
        \"\"\"
        logger.info(f"EVENT BUS {self.name} received event: {event}")
    
    def publish(self, event):
        \"\"\"
        Publish an event with debug logging.
        \"\"\"
        logger.info(f"EVENT BUS {self.name} publishing event: {event}")
        return super().publish(event)
    
    def subscribe(self, event_type, callback):
        \"\"\"
        Subscribe to an event type with debug logging.
        \"\"\"
        logger.info(f"EVENT BUS {self.name} subscription: {event_type} -> {callback.__name__}")
        return super().subscribe(event_type, callback)

# Patch the original EventBus to use EnhancedEventBus
def patch_event_bus():
    \"\"\"
    Patch the original EventBus to use EnhancedEventBus.
    \"\"\"
    from src.core.events import event_bus
    
    logger.info("Patching original EventBus to use EnhancedEventBus")
    
    # Save the original class
    original_event_bus = event_bus.EventBus
    
    # Set the enhanced class in its place
    event_bus.EventBus = EnhancedEventBus
    
    logger.info("EventBus patched successfully")
    
    return True
""")
        
        logger.info("Created enhanced event bus")
        return True
    except Exception as e:
        logger.error(f"Failed to create enhanced event bus: {e}")
        return False

def main():
    """Apply all fixes"""
    logger.info("Applying fixes...")
    
    # Create the enhanced event bus
    if fix_event_bus_singleton():
        logger.info("Enhanced event bus created")
    else:
        logger.error("Failed to create enhanced event bus")
    
    # Patch the risk manager
    if patch_risk_manager():
        logger.info("Risk manager patched")
    else:
        logger.error("Failed to patch risk manager")
    
    # Patch the backtest coordinator
    if patch_backtest_coordinator():
        logger.info("Backtest coordinator patched")
    else:
        logger.error("Failed to patch backtest coordinator")
    
    logger.info("All fixes applied")
    
    # Write a patch loading script
    load_patch_path = "load_patches.py"
    with open(load_patch_path, 'w') as f:
        f.write("""#!/usr/bin/env python
\"\"\"
Load all patches before running optimization
\"\"\"

import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("patches.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('patches')

def load_patches():
    \"\"\"Load all patches\"\"\"
    logger.info("Loading patches...")
    
    try:
        # Load the enhanced event bus
        from src.core.events.enhanced_event_bus import patch_event_bus
        
        # Apply the patch
        patch_event_bus()
        
        logger.info("All patches loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load patches: {e}")
        return False

if __name__ == "__main__":
    load_patches()
""")
    
    logger.info(f"Created patch loading script: {load_patch_path}")
    
    # Create a final run script
    run_fixed_path = "run_fixed_optimization.py"
    with open(run_fixed_path, 'w') as f:
        f.write("""#!/usr/bin/env python
\"\"\"
Run the fixed optimization
\"\"\"

import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fixed_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fixed')

# Load patches
try:
    from load_patches import load_patches
    
    if not load_patches():
        logger.error("Failed to load patches")
except Exception as e:
    logger.error(f"Failed to import patches: {e}")

# Import strategy optimizer
from src.strategy.optimization.optimizer import StrategyOptimizer

def main():
    \"\"\"Run the fixed optimization\"\"\"
    logger.info("Running fixed optimization...")
    
    config_path = "config/ma_crossover_optimization.yaml"
    
    # Create optimizer
    optimizer = StrategyOptimizer(config_path)
    
    # Run optimization
    results = optimizer.optimize()
    
    # Check if trades were generated
    for param_result in results.get('all_results', []):
        train_result = param_result.get('train_result', {})
        test_result = param_result.get('test_result', {})
        
        train_trades = train_result.get('trades', [])
        test_trades = test_result.get('trades', [])
        
        logger.info(f"Parameters: {param_result.get('parameters')}")
        logger.info(f"Train trades: {len(train_trades)}")
        logger.info(f"Test trades: {len(test_trades)}")
    
    logger.info("Fixed optimization completed")
    return results

if __name__ == "__main__":
    main()
""")
    
    logger.info(f"Created fixed optimization script: {run_fixed_path}")
    
    logger.info("All scripts created, now run:")
    logger.info("1. python run_all_debug.py  # Run all debug scripts")
    logger.info("2. python fix_optimization.py  # Apply fixes")
    logger.info("3. python run_fixed_optimization.py  # Run fixed optimization")

if __name__ == "__main__":
    main()
