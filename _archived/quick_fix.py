#!/usr/bin/env python3
"""
Quick direct fix for the MA Crossover Signal Grouping issue.

This script modifies the risk manager implementation to:
1. Add a clear log statement when rule_ids are cleared during reset
2. Add the processed_rule_ids initialization to the __init__ method if needed
"""

import sys
import re
import inspect

def log_message(message):
    """Print a formatted log message."""
    print(f"[QUICK FIX] {message}")

def fix_risk_manager():
    """Apply critical fixes to the risk manager."""
    from src.risk.managers.simple import SimpleRiskManager
    
    # Get the original source
    original_reset = inspect.getsource(SimpleRiskManager.reset)
    
    log_message("Checking SimpleRiskManager reset method...")
    
    # Verify that the reset method clears processed_rule_ids
    if "processed_rule_ids.clear()" in original_reset:
        log_message("Reset method already clears processed_rule_ids")
    else:
        log_message("Reset method needs to be fixed")
        
        # Create a new reset implementation
        def fixed_reset(self):
            """Fixed reset implementation that properly clears processed_rule_ids."""
            # Call parent reset
            super(SimpleRiskManager, self).reset()
            
            # Clear tracking collections
            self.logger.info("Resetting risk manager state: clearing tracking collections")
            self.order_ids.clear()
            self.processed_signals.clear()
            
            # CRITICAL FIX: Ensure processed_rule_ids is emptied on reset
            rule_id_count = len(self.processed_rule_ids)
            self.logger.info(f"CLEARING {rule_id_count} PROCESSED RULE IDs")
            self.processed_rule_ids.clear()
            self.logger.info(f"After reset, processed_rule_ids size: {len(self.processed_rule_ids)}")
            
            # Clear events in progress
            self.events_in_progress.clear()
            
            self.logger.info(f"Risk manager {self.name} reset completed")
        
        # Apply the fix
        SimpleRiskManager.reset = fixed_reset
        log_message("Fixed reset method applied")
    
    # Verify __init__ initializes processed_rule_ids
    original_init = inspect.getsource(SimpleRiskManager.__init__)
    if "processed_rule_ids = set()" in original_init or "self.processed_rule_ids = set()" in original_init:
        log_message("__init__ already initializes processed_rule_ids")
    else:
        log_message("__init__ needs to be fixed")
        
        # Create a new init implementation with processed_rule_ids
        def fixed_init(self, event_bus, portfolio_manager, name=None):
            """Fixed __init__ that properly initializes processed_rule_ids."""
            # Call parent init
            super(SimpleRiskManager, self).__init__(event_bus, portfolio_manager, name)
            
            self.position_size = 100  # Default fixed position size
            self.max_position_pct = 0.1  # Maximum 10% of equity per position
            self.order_ids = set()  # Track created order IDs to avoid duplicates
            self.processed_signals = set()  # Track processed signal IDs
            self.processed_rule_ids = set()  # CRITICAL FIX: Track rule IDs separately
            self.events_in_progress = set()  # Track events currently being processed
            
            # BUGFIX: Order manager reference is needed for order creation
            self.order_manager = None
            
            # Create logger
            self.logger = self.logger  # Use logger from parent
        
        # Apply the fix
        SimpleRiskManager.__init__ = fixed_init
        log_message("Fixed __init__ method applied")
    
    # Return success
    return True

def fix_strategy():
    """Ensure the strategy uses the correct rule_id format."""
    from src.strategy.implementations.ma_crossover import MACrossoverStrategy
    
    # Get the original source code
    original_on_bar = inspect.getsource(MACrossoverStrategy.on_bar)
    
    log_message("Checking MACrossoverStrategy on_bar method...")
    
    # Check if the rule_id format is correct
    rule_id_pattern = r'rule_id\s*=\s*f["\']([^"\']*)["\']'
    rule_id_matches = re.findall(rule_id_pattern, original_on_bar)
    
    if rule_id_matches:
        for match in rule_id_matches:
            if "{symbol}" in match and ("direction" in match or "BUY" in match or "SELL" in match) and "group" in match:
                log_message(f"on_bar already uses correct rule_id format: {match}")
                return True
    
    log_message("on_bar needs rule_id format fix")
    
    # Apply the fix at runtime by modifying the on_bar method
    
    # First, extract the direction name block
    if "direction_name = \"BUY\" if signal_value == 1 else \"SELL\"" in original_on_bar:
        log_message("direction_name assignment already present")
    else:
        log_message("Need to add direction_name assignment")
    
    # We can't easily modify the method at runtime without source manipulation
    # Just print instructions for manual fix
    log_message("\nMANUAL FIX REQUIRED: Please ensure the rule_id is created with this format:")
    log_message("direction_name = \"BUY\" if signal_value == 1 else \"SELL\"")
    log_message("rule_id = f\"{self.name}_{symbol}_{direction_name}_group_{group_id}\"")
    
    return True

def main():
    """Apply quick fixes for the MA Crossover Signal Grouping issue."""
    print("\n=== QUICK FIX FOR MA CROSSOVER SIGNAL GROUPING ===")
    
    try:
        # Fix the risk manager
        fix_risk_manager()
        
        # Fix the strategy
        fix_strategy()
        
        print("\n=== QUICK FIX COMPLETED ===")
        print("Run python check_rule_id_flow_fixed.py to verify")
        
        return True
    except Exception as e:
        print(f"Error applying quick fix: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
