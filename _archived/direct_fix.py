#!/usr/bin/env python3
"""
Direct fix for the MA Crossover Signal Grouping issue.

This script directly replaces the original strategy implementation with the fixed version.
"""
import os
import sys
import shutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def apply_direct_fix():
    """
    Apply a direct fix by replacing the MA Crossover implementation.
    """
    # Define paths
    original_file = "src/strategy/implementations/ma_crossover_original.py"
    current_file = "src/strategy/implementations/ma_crossover.py"
    backup_file = "src/strategy/implementations/ma_crossover.py.bak"
    fixed_file = "src/strategy/implementations/ma_crossover_fixed.py"
    
    logger.info("Applying direct fix for MA Crossover Signal Grouping issue")
    
    # 1. Create backup of current file if it doesn't exist
    if os.path.exists(current_file) and not os.path.exists(backup_file):
        logger.info(f"Creating backup of current implementation: {backup_file}")
        shutil.copy2(current_file, backup_file)
    
    # 2. If fixed file exists, replace current implementation
    if os.path.exists(fixed_file):
        logger.info(f"Replacing current implementation with fixed version")
        shutil.copy2(fixed_file, current_file)
        return True
    
    # 3. If fixed file doesn't exist but original file exists, 
    # we can create a fixed version by modifying the original
    elif os.path.exists(original_file):
        logger.info("Fixed implementation not found, creating from original")
        try:
            # Read original file
            with open(original_file, 'r') as f:
                content = f.read()
            
            # Replace with fixed implementation
            # This replaces the critical part where rule_id is generated
            content = content.replace(
                'rule_id=f"{self.name}_{self.signal_count}"',
                'rule_id=f"{self.name}_{symbol}_{direction_name}_group_{self.signal_count}"'
            )
            
            # Add tracking for signal directions
            content = content.replace(
                "# Internal state\n        self.data = {symbol: [] for symbol in self.symbols}\n        self.signal_count = 0",
                "# Internal state\n        self.data = {symbol: [] for symbol in self.symbols}\n        self.signal_count = 0\n        \n        # Signal direction tracking\n        self.signal_directions = {}  # symbol -> current signal direction (1, 0, -1)\n        self.signal_groups = {}      # symbol -> current group ID"
            )
            
            # Add signal direction reset in configure method
            content = content.replace(
                "# Reset data for all configured symbols\n        self.data = {symbol: [] for symbol in self.symbols}",
                "# Reset data for all configured symbols\n        self.data = {symbol: [] for symbol in self.symbols}\n        \n        # Reset signal tracking\n        self.signal_directions = {}\n        self.signal_groups = {}"
            )
            
            # Add signal direction reset in reset method
            content = content.replace(
                "# Reset strategy-specific state\n        self.data = {symbol: [] for symbol in self.symbols}\n        self.signal_count = 0",
                "# Reset strategy-specific state\n        self.data = {symbol: [] for symbol in self.symbols}\n        self.signal_count = 0\n        self.signal_directions = {}\n        self.signal_groups = {}"
            )
            
            # Update the main signal handling logic to use direction changes
            content = content.replace(
                "# Generate and emit signal event if we have a signal\n        if signal_value != 0:",
                """# Enhanced debugging for rule ID
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
            direction_name = "BUY" if signal_value == 1 else "SELL\""""
            )
            
            # Add handling for signals that don't represent direction changes
            content = content.replace(
                "            return signal\n        \n        return None",
                """            return signal
        
        # If we have a signal but no direction change, we're still in the same group
        elif signal_value != 0 and signal_value == current_direction:
            # Use existing group ID but don't emit a new signal
            logger.debug(f"Signal for {symbol}: {signal_value} - same direction, no new signal emitted")
        
        return None"""
            )
            
            # Update docstring to indicate fixed version
            content = content.replace(
                "Moving Average Crossover Strategy Implementation.",
                "Moving Average Crossover Strategy Implementation - Fixed Version.\n\nThis strategy generates buy signals when a fast moving average crosses above\na slow moving average, and sell signals when it crosses below.\n\nThe implementation groups signals by direction, maintaining a single rule_id\nfor each directional state (BUY/SELL) until the direction changes."
            )
            
            # Update class docstring
            content = content.replace(
                '"""Moving Average Crossover strategy implementation."""',
                '"""Moving Average Crossover strategy implementation with proper signal grouping."""'
            )
            
            # Write fixed content to current file
            with open(current_file, 'w') as f:
                f.write(content)
                
            logger.info(f"Successfully created fixed implementation at {current_file}")
            return True
                
        except Exception as e:
            logger.error(f"Error creating fixed implementation: {e}", exc_info=True)
            return False
    
    else:
        logger.error("Neither fixed nor original implementation found")
        return False

def main():
    """Main function."""
    success = apply_direct_fix()
    
    if success:
        print("=" * 60)
        print("MA CROSSOVER SIGNAL GROUPING FIX APPLIED")
        print("=" * 60)
        print("The direct fix has been successfully applied.")
        print("To test the fix, run the system with:")
        print("  python main.py --config config/mini_test.yaml")
        print("Expected result: 18 trades instead of 54")
        return 0
    else:
        print("=" * 60)
        print("ERROR: MA CROSSOVER SIGNAL GROUPING FIX FAILED")
        print("=" * 60)
        print("The fix could not be applied. See log for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
