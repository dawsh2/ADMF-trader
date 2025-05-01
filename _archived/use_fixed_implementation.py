#!/usr/bin/env python3
"""
Apply the MA Crossover Fixed Implementation and Force Its Usage

This script ensures the system uses our fixed implementation with the correct rule_id format.
It directly modifies the import paths in the system bootstrap to use ma_crossover_fixed.py.
"""

import os
import sys
import logging
import importlib
import types
import inspect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("use_fixed_implementation")

def force_fixed_strategy_usage():
    """
    Force the system to use our fixed MA Crossover strategy implementation.
    This is done by directly modifying the module imports.
    """
    # First verify our fixed implementation exists
    fixed_path = "src/strategy/implementations/ma_crossover_fixed.py"
    if not os.path.exists(fixed_path):
        logger.error(f"Fixed implementation not found at {fixed_path}")
        return False
    
    # Now import and verify our fixed implementation
    try:
        # Import the fixed module
        sys.path.insert(0, os.getcwd())
        from src.strategy.implementations.ma_crossover_fixed import MACrossoverStrategy as FixedStrategy
        
        # Verify it has the correct format
        on_bar_source = inspect.getsource(FixedStrategy.on_bar)
        if "direction_name = \"BUY\" if signal_value == 1 else \"SELL\"" in on_bar_source and \
           "rule_id = f\"{self.name}_{symbol}_{direction_name}_group_{group_id}\"" in on_bar_source:
            logger.info("✅ Fixed implementation has correct rule_id format")
        else:
            logger.error("❌ Fixed implementation doesn't have correct rule_id format")
            return False
        
        # Now update the original implementation module
        import src.strategy.implementations.ma_crossover
        
        # Directly replace the class with our fixed version
        src.strategy.implementations.ma_crossover.MACrossoverStrategy = FixedStrategy
        logger.info("✅ Successfully replaced MACrossoverStrategy with fixed implementation")
        
        # Force reload of any modules that might have imported the original
        for module_name in list(sys.modules.keys()):
            if "ma_crossover" in module_name or "strategy" in module_name:
                if module_name != "src.strategy.implementations.ma_crossover_fixed":
                    try:
                        if module_name in sys.modules:
                            importlib.reload(sys.modules[module_name])
                            logger.info(f"Reloaded module: {module_name}")
                    except:
                        pass
        
        # Verify the replacement worked
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy
        on_bar_source_after = inspect.getsource(MACrossoverStrategy.on_bar)
        if "direction_name = \"BUY\" if signal_value == 1 else \"SELL\"" in on_bar_source_after and \
           "rule_id = f\"{self.name}_{symbol}_{direction_name}_group_{group_id}\"" in on_bar_source_after:
            logger.info("✅ Original implementation successfully updated with fixed version")
            return True
        else:
            logger.error("❌ Original implementation was not updated correctly")
            return False
        
    except Exception as e:
        logger.error(f"Error forcing fixed implementation: {e}")
        import traceback
        traceback.print_exc()
        return False

def ensure_event_bus_reset():
    """Add explicit reset to the BacktestCoordinator to ensure proper event bus reset."""
    try:
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Store the original run method
        original_run = BacktestCoordinator.run
        
        # Create a patched run method with explicit event bus reset
        def patched_run(self):
            """Patched run method with explicit event bus reset."""
            # Reset the event bus first to clear processed rule_ids
            if hasattr(self, 'event_bus') and self.event_bus:
                logger.info("Explicitly resetting event bus before run")
                self.event_bus.reset()
                logger.info("Event bus reset complete")
            
            # Call the original run method
            return original_run(self)
        
        # Apply the patch
        BacktestCoordinator