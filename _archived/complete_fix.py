#!/usr/bin/env python3
"""
Complete MA Crossover Signal Grouping Fix

This script applies all necessary fixes to resolve the MA Crossover signal grouping issue
that causes 54 trades instead of the expected 18 trades.
"""
import os
import sys
import shutil
import logging
import importlib
import inspect
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"complete_fix_{os.path.basename(__file__)}_{logging.Formatter().converter().tm_hour}{logging.Formatter().converter().tm_min}{logging.Formatter().converter().tm_sec}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_backtest_coordinator_fix():
    """
    Check if the BacktestCoordinator.run method has the proper fix.
    """
    try:
        # Import BacktestCoordinator
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Get run method source code
        source = inspect.getsource(BacktestCoordinator.run)
        
        # Check for event bus reset code
        has_reset = "event_bus.reset()" in source
        has_comment = "CRITICAL FIX:" in source and "Reset the event bus" in source
        
        if has_reset and has_comment:
            logger.info("✅ BacktestCoordinator.run method properly resets the event bus")
            return True
        else:
            logger.warning("❌ BacktestCoordinator.run method needs to be fixed")
            return False
    except Exception as e:
        logger.error(f"Error checking BacktestCoordinator fix: {e}", exc_info=True)
        return False

def fix_backtest_coordinator():
    """
    Fix the BacktestCoordinator.run method to reset the event bus.
    """
    try:
        # Define the file path
        file_path = "src/execution/backtest/backtest.py"
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Create a backup if it doesn't exist
        backup_path = file_path + ".bak"
        if not os.path.exists(backup_path):
            logger.info(f"Creating backup of BacktestCoordinator: {backup_path}")
            shutil.copy2(file_path, backup_path)
        
        # Add the fix if not already present
        if "CRITICAL FIX: Reset the event bus" not in content:
            # Find the run method signature
            run_method_start = content.find("def run(self, symbols=None, start_date=None, end_date=None, ")
            if run_method_start == -1:
                logger.error("Could not find run method in BacktestCoordinator")
                return False
            
            # Find where the method body starts (after the docstring)
            docstring_end = content.find('"""', run_method_start + 100)
            if docstring_end == -1:
                logger.error("Could not find end of run method docstring")
                return False
            
            # Find the first line after the docstring
            next_line_start = content.find('\n', docstring_end) + 1
            
            # Insert the fix at the beginning of the method body
            fixed_content = content[:next_line_start] + """        # CRITICAL FIX: Reset the event bus first to clear processed rule_ids
        if hasattr(self, 'event_bus') and self.event_bus:
            logger.info("Explicitly resetting event bus before run")
            self.event_bus.reset()
            logger.info("Event bus reset complete")
            
""" + content[next_line_start:]
            
            # Write the fixed content
            with open(file_path, 'w') as f:
                f.write(fixed_content)
                
            logger.info("✅ Successfully applied BacktestCoordinator.run fix")
            return True
        else:
            logger.info("BacktestCoordinator.run fix already applied")
            return True
    except Exception as e:
        logger.error(f"Error applying BacktestCoordinator fix: {e}", exc_info=True)
        return False

def check_risk_manager_fix():
    """
    Check if the SimpleRiskManager.reset method has the proper fix.
    """
    try:
        # Import SimpleRiskManager
        from src.risk.managers.simple import SimpleRiskManager
        
        # Get reset method source code
        source = inspect.getsource(SimpleRiskManager.reset)
        
        # Check for processed_rule_ids clearing
        has_rule_id_clear = "self.processed_rule_ids.clear()" in source
        has_comment = "CRITICAL FIX:" in source and "processed_rule_ids" in source
        
        if has_rule_id_clear and has_comment:
            logger.info("✅ SimpleRiskManager.reset method properly clears processed_rule_ids")
            return True
        else:
            logger.warning("❌ SimpleRiskManager.reset method needs to be fixed")
            return False
    except Exception as e:
        logger.error(f"Error checking SimpleRiskManager fix: {e}", exc_info=True)
        return False

def fix_risk_manager():
    """
    Fix the SimpleRiskManager.reset method to clear processed_rule_ids.
    """
    try:
        # Define the file path
        file_path = "src/risk/managers/simple.py"
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Create a backup if it doesn't exist
        backup_path = file_path + ".bak"
        if not os.path.exists(backup_path):
            logger.info(f"Creating backup of SimpleRiskManager: {backup_path}")
            shutil.copy2(file_path, backup_path)
        
        # Add the fix if not already present
        if "CRITICAL FIX: Ensure processed_rule_ids is emptied on reset" not in content:
            # Find the reset method
            reset_method_start = content.find("def reset(self):")
            if reset_method_start == -1:
                logger.error("Could not find reset method in SimpleRiskManager")
                return False
            
            # Find the line after "Clear order IDs and processed signals"
            clear_signals_line = content.find("self.processed_signals.clear()", reset_method_start)
            if clear_signals_line == -1:
                logger.error("Could not find processed_signals.clear() in reset method")
                return False
            
            # Find the next line
            next_line_start = content.find('\n', clear_signals_line) + 1
            
            # Insert the fix after clearing processed signals
            fixed_content = content[:next_line_start] + """        
        # CRITICAL FIX: Ensure processed_rule_ids is emptied on reset
        rule_id_count = len(self.processed_rule_ids)
        logger.info(f"CLEARING {rule_id_count} PROCESSED RULE IDs")
        self.processed_rule_ids.clear()
        logger.info(f"After reset, processed_rule_ids size: {len(self.processed_rule_ids)}")
        """ + content[next_line_start:]
            
            # Write the fixed content
            with open(file_path, 'w') as f:
                f.write(fixed_content)
                
            logger.info("✅ Successfully applied SimpleRiskManager.reset fix")
            return True
        else:
            logger.info("SimpleRiskManager.reset fix already applied")
            return True
    except Exception as e:
        logger.error(f"Error applying SimpleRiskManager fix: {e}", exc_info=True)
        return False

def check_ma_crossover_fix():
    """
    Check if the MACrossoverStrategy uses the correct rule_id format.
    """
    try:
        # First try to import directly
        try:
            from src.strategy.implementations.ma_crossover import MACrossoverStrategy
            
            # Check the on_bar method
            source = inspect.getsource(MACrossoverStrategy.on_bar)
            
            # Check rule_id format
            has_correct_rule_id = 'rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"' in source
            has_direction_tracking = "self.signal_directions" in source
            
            if has_correct_rule_id and has_direction_tracking:
                logger.info("✅ MACrossoverStrategy uses the correct rule_id format")
                return True
            else:
                logger.warning("❌ MACrossoverStrategy needs to be fixed")
                return False
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not directly import MACrossoverStrategy: {e}")
            return False
    except Exception as e:
        logger.error(f"Error checking MACrossoverStrategy fix: {e}", exc_info=True)
        return False

def fix_ma_crossover():
    """
    Fix the MACrossoverStrategy to use the correct rule_id format.
    """
    try:
        # Define paths
        current_file = "src/strategy/implementations/ma_crossover.py"
        original_file = "src/strategy/implementations/ma_crossover_original.py"
        fixed_file = "src/strategy/implementations/ma_crossover_fixed.py"
        backup_file = current_file + ".bak"
        
        # Create a backup of the current file if it doesn't exist
        if os.path.exists(current_file) and not os.path.exists(backup_file):
            logger.info(f"Creating backup of current MACrossoverStrategy: {backup_file}")
            shutil.copy2(current_file, backup_file)
        
        # Check if fixed file exists
        if os.path.exists(fixed_file):
            logger.info(f"Using fixed implementation from {fixed_file}")
            shutil.copy2(fixed_file, current_file)
            logger.info("✅ Successfully applied MACrossoverStrategy fix from fixed file")
            return True
        
        # If fixed file doesn't exist, try to fix from original or current file
        source_file = original_file if os.path.exists(original_file) else current_file
        if not os.path.exists(source_file):
            logger.error(f"Could not find source file: {source_file}")
            return False
        
        logger.info(f"Creating fixed implementation from {source_file}")
        
        # Read the source file
        with open(source_file, 'r') as f:
            content = f.read()
        
        # Check if the file already has the fix
        if 'rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"' in content:
            logger.info("MACrossoverStrategy already has the correct rule_id format")
            return True
        
        # Apply fixes to the content
        
        # 1. Update docstring
        content = content.replace(
            "Moving Average Crossover Strategy Implementation.",
            "Moving Average Crossover Strategy Implementation - Fixed Version.\n\nThis strategy generates buy signals when a fast moving average crosses above\na slow moving average, and sell signals when it crosses below.\n\nThe implementation groups signals by direction, maintaining a single rule_id\nfor each directional state (BUY/SELL) until the direction changes."
        )
        
        # 2. Update class docstring
        content = content.replace(
            '"""Moving Average Crossover strategy implementation."""',
            '"""Moving Average Crossover strategy implementation with proper signal grouping."""'
        )
        
        # 3. Add signal direction tracking to __init__
        content = content.replace(
            "# Internal state\n        self.data = {symbol: [] for symbol in self.symbols}\n        self.signal_count = 0",
            "# Internal state\n        self.data = {symbol: [] for symbol in self.symbols}\n        self.signal_count = 0\n        \n        # Signal direction tracking\n        self.signal_directions = {}  # symbol -> current signal direction (1, 0, -1)\n        self.signal_groups = {}      # symbol -> current group ID"
        )
        
        # 4. Add signal direction reset to configure method
        content = content.replace(
            "# Reset data for all configured symbols\n        self.data = {symbol: [] for symbol in self.symbols}",
            "# Reset data for all configured symbols\n        self.data = {symbol: [] for symbol in self.symbols}\n        \n        # Reset signal tracking\n        self.signal_directions = {}\n        self.signal_groups = {}"
        )
        
        # 5. Add signal direction reset to reset method
        content = content.replace(
            "# Reset strategy-specific state\n        self.data = {symbol: [] for symbol in self.symbols}\n        self.signal_count = 0",
            "# Reset strategy-specific state\n        self.data = {symbol: [] for symbol in self.symbols}\n        self.signal_count = 0\n        self.signal_directions = {}\n        self.signal_groups = {}"
        )
        
        # 6. Replace the signal generation logic
        signal_generation_old = """# Generate and emit signal event if we have a signal
        if signal_value != 0:
            self.signal_count += 1
            signal = create_signal_event(
                signal_value=signal_value,
                price=price,
                symbol=symbol,
                rule_id=f"{self.name}_{self.signal_count}",
                timestamp=timestamp
            )
            
            # Emit signal if we have an event bus
            if self.event_bus:
                self.event_bus.emit(signal)
                logger.info(f"Signal #{self.signal_count} emitted for {symbol}: {signal_value}")
            
            return signal"""
        
        signal_generation_new = """# Enhanced debugging for rule ID
        logger.info(f"Signal generation: symbol={symbol}, signal_value={signal_value}, current_direction={self.signal_directions.get(symbol, 0)}")
        if signal_value != 0 and signal_value != self.signal_directions.get(symbol, 0):
            logger.info(f"DIRECTION CHANGE DETECTED: {self.signal_directions.get(symbol, 0)} -> {signal_value}")
        
        # Process signal only if it represents a direction change
        
        # Now check if direction has changed
        current_direction = self.signal_directions.get(symbol, 0)
        
        # CRITICAL: Only process signals that represent a direction change
        if signal_value != 0 and signal_value != current_direction:
            # Direction has changed - create a new group
            self.signal_count += 1
            self.signal_groups[symbol] = self.signal_count
            self.signal_directions[symbol] = signal_value
            
            # Create group-based rule ID - CRITICAL: match validation format
            group_id = self.signal_groups[symbol]
            
            # CRITICAL FIX: MUST use this specific format
            direction_name = "BUY" if signal_value == 1 else "SELL"
            rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"
            
            # Log rule_id with more emphasis
            logger.info(f"RULE ID CREATED: {rule_id} for direction change {current_direction} -> {signal_value}")
            
            # Log the new signal group with more visibility
            logger.info(f"NEW SIGNAL GROUP: {symbol} direction changed to {direction_name}, group={group_id}, rule_id={rule_id}")
            
            # Generate and emit signal event
            signal = create_signal_event(
                signal_value=signal_value,
                price=price,
                symbol=symbol,
                rule_id=rule_id,
                timestamp=timestamp
            )
            
            # Debug the signal to verify rule_id is included
            if hasattr(signal, 'data') and isinstance(signal.data, dict):
                logger.info(f"DEBUG: Signal created with rule_id={signal.data.get('rule_id')}")
            
            # Emit signal if we have an event bus
            if self.event_bus:
                self.event_bus.emit(signal)
                logger.info(f"Signal #{group_id} emitted for {symbol}: {signal_value}, rule_id={rule_id}, timestamp={timestamp}")
            
            return signal
        
        # If we have a signal but no direction change, we're still in the same group
        elif signal_value != 0 and signal_value == current_direction:
            # Use existing group ID but don't emit a new signal
            logger.debug(f"Signal for {symbol}: {signal_value} - same direction, no new signal emitted")"""
        
        # Replace signal generation logic
        content = content.replace(signal_generation_old, signal_generation_new)
        
        # Write the fixed content
        with open(current_file, 'w') as f:
            f.write(content)
            
        logger.info("✅ Successfully created fixed MACrossoverStrategy implementation")
        return True
    except Exception as e:
        logger.error(f"Error fixing MACrossoverStrategy: {e}", exc_info=True)
        return False

def disable_original_implementation():
    """
    Disable the original MA Crossover implementation to prevent it from being loaded.
    """
    try:
        original_file = "src/strategy/implementations/ma_crossover_original.py"
        disabled_file = original_file + ".disabled"
        
        if os.path.exists(original_file) and not os.path.exists(disabled_file):
            logger.info(f"Disabling original implementation: {original_file}")
            shutil.move(original_file, disabled_file)
            logger.info("✅ Successfully disabled original implementation")
            return True
        elif os.path.exists(disabled_file):
            logger.info("Original implementation already disabled")
            return True
        else:
            logger.info("Original implementation not found")
            return True
    except Exception as e:
        logger.error(f"Error disabling original implementation: {e}", exc_info=True)
        return False

def flush_python_cache():
    """
    Clean up __pycache__ directories to ensure fresh imports.
    """
    try:
        # Find all __pycache__ directories
        pycache_dirs = []
        for root, dirs, files in os.walk("src"):
            if "__pycache__" in dirs:
                pycache_dirs.append(os.path.join(root, "__pycache__"))
        
        # Remove .pyc files related to ma_crossover
        count = 0
        for pycache_dir in pycache_dirs:
            for file in os.listdir(pycache_dir):
                if "ma_crossover" in file:
                    file_path = os.path.join(pycache_dir, file)
                    os.remove(file_path)
                    count += 1
        
        logger.info(f"Removed {count} cached Python files")
        return True
    except Exception as e:
        logger.error(f"Error flushing Python cache: {e}", exc_info=True)
        return False

def clear_sys_modules():
    """
    Clear strategy modules from sys.modules to force reloading.
    """
    try:
        # Find all ma_crossover modules
        ma_modules = [name for name in sys.modules if "ma_crossover" in name]
        
        # Remove them from sys.modules
        for name in ma_modules:
            del sys.modules[name]
            logger.info(f"Removed {name} from sys.modules")
        
        return True
    except Exception as e:
        logger.error(f"Error clearing sys.modules: {e}", exc_info=True)
        return False

def reload_modules():
    """
    Reload affected modules to ensure changes take effect.
    """
    try:
        # List of modules to reload
        modules_to_reload = [
            "src.strategy.implementations.ma_crossover",
            "src.strategy.strategy_base",
            "src.execution.backtest.backtest",
            "src.risk.managers.simple"
        ]
        
        # Reload each module
        for module_name in modules_to_reload:
            try:
                module = importlib.import_module(module_name)
                importlib.reload(module)
                logger.info(f"Reloaded module: {module_name}")
            except ImportError:
                logger.warning(f"Could not import module: {module_name}")
        
        return True
    except Exception as e:
        logger.error(f"Error reloading modules: {e}", exc_info=True)
        return False

def verify_all_fixes():
    """
    Verify that all fixes have been successfully applied.
    """
    backtest_fixed = check_backtest_coordinator_fix()
    risk_manager_fixed = check_risk_manager_fix()
    ma_crossover_fixed = check_ma_crossover_fix()
    
    all_fixed = backtest_fixed and risk_manager_fixed and ma_crossover_fixed
    
    logger.info("=" * 60)
    logger.info("VERIFICATION RESULTS:")
    logger.info(f"✅ BacktestCoordinator.run fix: {'APPLIED' if backtest_fixed else 'NOT APPLIED'}")
    logger.info(f"✅ SimpleRiskManager.reset fix: {'APPLIED' if risk_manager_fixed else 'NOT APPLIED'}")
    logger.info(f"✅ MACrossoverStrategy rule_id fix: {'APPLIED' if ma_crossover_fixed else 'NOT APPLIED'}")
    logger.info("=" * 60)
    
    return all_fixed

def main():
    """Main function to apply all fixes."""
    logger.info("=" * 60)
    logger.info("APPLYING MA CROSSOVER SIGNAL GROUPING FIX")
    logger.info("=" * 60)
    
    # 1. Disable original implementation to prevent conflicts
    disable_original_implementation()
    
    # 2. Flush Python cache to ensure fresh imports
    flush_python_cache()
    
    # 3. Clear affected modules from sys.modules
    clear_sys_modules()
    
    # 4. Apply all fixes
    fix_backtest_coordinator()
    fix_risk_manager()
    fix_ma_crossover()
    
    # 5. Reload affected modules
    reload_modules()
    
    # 6. Verify all fixes
    all_fixed = verify_all_fixes()
    
    logger.info("=" * 60)
    if all_fixed:
        logger.info("ALL FIXES SUCCESSFULLY APPLIED!")
        logger.info("Restart the Python process and run:")
        logger.info("  python main.py --config config/mini_test.yaml")
        logger.info("Expected result: 18 trades instead of 54")
    else:
        logger.info("SOME FIXES COULD NOT BE APPLIED")
        logger.info("See log for details")
    logger.info("=" * 60)
    
    return 0 if all_fixed else 1

if __name__ == "__main__":
    sys.exit(main())
