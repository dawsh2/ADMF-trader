#!/usr/bin/env python
"""
Fix for the rule_id missing in orders and trades not being recorded.

This script fixes the issue where rule_id is not being properly passed from signals to orders,
and ensures that trades are created and recorded when orders are filled.
"""

import os
import sys
import logging
import shutil
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_rule_id.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fix_rule_id')

def backup_file(filepath):
    """Create a backup of the file before modifying it"""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.bak"
        shutil.copy2(filepath, backup_path)
        logger.info(f"Created backup at {backup_path}")
        return True
    return False

def find_file(pattern, search_path='src'):
    """Find a file matching the pattern"""
    for root, dirs, files in os.walk(search_path):
        for filename in files:
            if pattern in filename.lower() and filename.endswith('.py'):
                return os.path.join(root, filename)
    return None

def find_order_manager():
    """Find the order manager file"""
    # Common file paths
    potential_paths = [
        'src/execution/order_manager.py',
        'src/execution/broker/order_manager.py',
        'src/core/execution/order_manager.py',
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # Search for the file
    return find_file('order_manager')

def find_signal_handler():
    """Find the signal handler file"""
    # Common file paths
    potential_paths = [
        'src/execution/signal_handler.py',
        'src/event/signal_handler.py',
        'src/core/events/signal_handler.py',
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # Search for any file that might handle signals
    signal_file = find_file('signal')
    if signal_file:
        return signal_file
    
    return find_file('event')

def find_execution_handler():
    """Find the execution handler file"""
    # Common file paths
    potential_paths = [
        'src/execution/execution_handler.py',
        'src/execution/broker.py',
        'src/core/execution/broker.py',
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # Search for any file that might handle execution
    return find_file('execution')

def fix_order_manager(filepath):
    """Fix the order manager to properly handle rule_id"""
    if not filepath or not os.path.exists(filepath):
        logger.error(f"Order manager file not found at {filepath}")
        return False
    
    logger.info(f"Analyzing order manager at {filepath}")
    
    # Check if the file contains functions related to order creation
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Look for where orders are created from signals
    order_creation_pattern = r'def\s+.*?create_order.*?\(.*?\).*?:|def\s+.*?signal_to_order.*?\(.*?\).*?:'
    order_match = re.search(order_creation_pattern, content, re.DOTALL)
    
    if order_match:
        logger.info(f"Found order creation function in {filepath}")
        
        # Look for where the order is created from the signal
        order_constructor_pattern = r'[Oo]rder\s*\((.*?)\)'
        order_constructor_match = re.search(order_constructor_pattern, content, re.DOTALL)
        
        if order_constructor_match:
            # Check if rule_id is already being passed
            constructor_args = order_constructor_match.group(1)
            if 'rule_id' not in constructor_args and 'strategy_id' not in constructor_args:
                logger.info(f"Order constructor doesn't include rule_id: {constructor_args}")
                
                # Modify the constructor to include rule_id
                backup_file(filepath)
                
                # This is tricky because we need to identify exactly where to add the rule_id
                # Let's use a pattern that's likely to match order creation
                new_content = content
                
                # Check if signal attributes are accessed in the constructor area
                signal_access_pattern = r'(signal\.([a-zA-Z_][a-zA-Z0-9_]*))'
                signal_accesses = re.findall(signal_access_pattern, content)
                
                if signal_accesses:
                    # If signal attributes are accessed, there's likely a signal object
                    modified = False
                    
                    # Try to find the Order constructor near signal accesses
                    for signal_access, attr_name in signal_accesses:
                        if attr_name in ['symbol', 'quantity', 'direction', 'price']:
                            before_access = content.rfind('Order(', 0, content.find(signal_access))
                            after_access = content.find('Order(', content.find(signal_access))
                            
                            if before_access != -1 and before_access > content.rfind('\n', 0, before_access):
                                # Found Order constructor before the signal access
                                constructor_end = content.find(')', before_access)
                                if constructor_end != -1:
                                    if 'rule_id' not in content[before_access:constructor_end]:
                                        # Add rule_id to the constructor
                                        new_content = content[:constructor_end] + ', rule_id=signal.strategy_id if hasattr(signal, "strategy_id") else None' + content[constructor_end:]
                                        modified = True
                                        break
                            
                            if after_access != -1:
                                # Found Order constructor after the signal access
                                constructor_end = content.find(')', after_access)
                                if constructor_end != -1:
                                    if 'rule_id' not in content[after_access:constructor_end]:
                                        # Add rule_id to the constructor
                                        new_content = content[:constructor_end] + ', rule_id=signal.strategy_id if hasattr(signal, "strategy_id") else None' + content[constructor_end:]
                                        modified = True
                                        break
                    
                    if modified:
                        # Write the modified content
                        with open(filepath, 'w') as f:
                            f.write(new_content)
                        
                        logger.info(f"Fixed order manager at {filepath} to include rule_id")
                        return True
                    else:
                        logger.warning(f"Could not find where to add rule_id in {filepath}")
                else:
                    logger.warning(f"Could not find signal attributes in {filepath}")
            else:
                logger.info(f"Order constructor already includes rule_id/strategy_id")
        else:
            logger.warning(f"Could not find Order constructor in {filepath}")
    else:
        logger.warning(f"Could not find order creation function in {filepath}")
    
    # Add instrumentation to track rule_id
    backup_file(filepath)
    
    # Add debug logging to track the rule_id
    debug_logging = """
    # Debug logging for tracking rule_id
    if hasattr(signal, 'rule_id') and signal.rule_id:
        logger.debug(f"Signal has rule_id: {signal.rule_id}")
    elif hasattr(signal, 'strategy_id') and signal.strategy_id:
        logger.debug(f"Signal has strategy_id: {signal.strategy_id}")
    else:
        logger.debug("Signal has no rule_id or strategy_id")
    """
    
    # Find a good place to insert the debug logging
    function_pattern = r'(def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(.*?signal.*?\).*?:.*?\n)(\s+)'
    match = re.search(function_pattern, content, re.DOTALL)
    
    if match:
        indentation = match.group(2)
        insertion_point = match.end()
        
        # Format the debug logging with proper indentation
        formatted_logging = "\n".join([indentation + line for line in debug_logging.strip().split("\n")])
        
        # Insert the debug logging
        new_content = content[:insertion_point] + formatted_logging + content[insertion_point:]
        
        # Write the modified content
        with open(filepath, 'w') as f:
            f.write(new_content)
        
        logger.info(f"Added debug logging to {filepath}")
        return True
    
    return False

def fix_execution_handler(filepath):
    """Fix the execution handler to record trades"""
    if not filepath or not os.path.exists(filepath):
        logger.error(f"Execution handler file not found at {filepath}")
        return False
    
    logger.info(f"Analyzing execution handler at {filepath}")
    
    # Check if the file contains functions related to execution
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Look for fill_order method
    fill_order_pattern = r'def\s+fill_order\s*\(.*?\).*?:'
    fill_match = re.search(fill_order_pattern, content, re.DOTALL)
    
    if fill_match:
        logger.info(f"Found fill_order function in {filepath}")
        
        # Check if the method creates and records trades
        if 'Trade(' in content and 'add_trade' in content:
            logger.info("Execution handler already creates and records trades")
            
            # Check if rule_id is being passed
            trade_constructor_pattern = r'Trade\s*\((.*?)\)'
            trade_match = re.search(trade_constructor_pattern, content, re.DOTALL)
            
            if trade_match:
                constructor_args = trade_match.group(1)
                if 'rule_id' not in constructor_args:
                    logger.info(f"Trade constructor doesn't include rule_id: {constructor_args}")
                    
                    # Modify the constructor to include rule_id
                    backup_file(filepath)
                    
                    # Add rule_id to Trade constructor
                    new_content = re.sub(
                        trade_constructor_pattern,
                        r'Trade(\1, rule_id=order.rule_id if hasattr(order, "rule_id") else None)',
                        content,
                        flags=re.DOTALL
                    )
                    
                    # Write the modified content
                    with open(filepath, 'w') as f:
                        f.write(new_content)
                    
                    logger.info(f"Fixed execution handler at {filepath} to include rule_id in Trade")
                    return True
                else:
                    logger.info(f"Trade constructor already includes rule_id")
            else:
                logger.warning(f"Could not find Trade constructor in {filepath}")
        else:
            logger.info("Execution handler does not create or record trades")
            
            # Add code to create and record trades
            backup_file(filepath)
            
            # Find the end of the fill_order method
            fill_start = fill_match.start()
            method_body_start = content.find(':', fill_start) + 1
            
            # Find the end of the method
            next_def = content.find('\ndef ', method_body_start)
            if next_def == -1:
                next_def = len(content)
            
            # Find the indentation level
            next_line_start = content.find('\n', method_body_start) + 1
            if next_line_start < len(content):
                indentation = 0
                for char in content[next_line_start:]:
                    if char == ' ':
                        indentation += 1
                    else:
                        break
                
                # Create the code to insert
                trade_code = "\n" + " " * indentation + """
# Create and record trade
trade = Trade(
    order.symbol,
    order.quantity,
    price,
    timestamp,
    order.direction,
    rule_id=order.rule_id if hasattr(order, "rule_id") else None
)
self.portfolio.add_trade(trade)
"""
                
                # Find a good insertion point - before any return statements
                return_pos = content.find('return', method_body_start, next_def)
                if return_pos != -1:
                    insertion_point = content.rfind('\n', method_body_start, return_pos) + 1
                else:
                    insertion_point = next_def
                
                new_content = content[:insertion_point] + trade_code + content[insertion_point:]
                
                # Write the modified content
                with open(filepath, 'w') as f:
                    f.write(new_content)
                
                logger.info(f"Added trade creation code to {filepath}")
                return True
    else:
        logger.warning(f"Could not find fill_order method in {filepath}")
    
    return False

def fix_signal_handler(filepath):
    """Fix the signal handler to ensure rule_id is properly set"""
    if not filepath or not os.path.exists(filepath):
        logger.error(f"Signal handler file not found at {filepath}")
        return False
    
    logger.info(f"Analyzing signal handler at {filepath}")
    
    # Check if the file contains functions related to signal handling
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Look for create_signal or handle_signal methods
    signal_pattern = r'def\s+create_signal.*?\(.*?\).*?:|def\s+handle_signal.*?\(.*?\).*?:'
    signal_match = re.search(signal_pattern, content, re.DOTALL)
    
    if signal_match:
        logger.info(f"Found signal handling function in {filepath}")
        
        # Look for signal creation
        if 'rule_id' in content and ('signal_type' in content or 'strategy_id' in content):
            logger.info("Signal handler already handles rule_id/strategy_id")
        else:
            # Add instrumentation to log signal properties
            backup_file(filepath)
            
            # Add debug logging for signal properties
            debug_logging = """
    # Debug logging for signal properties
    logger.debug(f"Created signal with properties: {vars(signal)}")
    """
            
            # Find a good place to insert the debug logging
            function_end = content.find('\n', signal_match.end())
            if function_end != -1:
                # Find the first non-empty line after the function definition
                line_start = function_end + 1
                while line_start < len(content) and not content[line_start].strip():
                    line_start = content.find('\n', line_start) + 1
                
                # Find the indentation level
                indentation = 0
                for char in content[line_start:]:
                    if char == ' ':
                        indentation += 1
                    else:
                        break
                
                # Format the debug logging with proper indentation
                formatted_logging = "\n".join([' ' * indentation + line for line in debug_logging.strip().split("\n")])
                
                # Insert the debug logging near the end of the function
                next_def = content.find('\ndef ', signal_match.end())
                if next_def == -1:
                    next_def = len(content)
                
                # Find a return statement
                return_pos = content.rfind('return', signal_match.end(), next_def)
                
                if return_pos != -1:
                    # Insert before the return statement
                    insertion_point = content.rfind('\n', signal_match.end(), return_pos) + 1
                    
                    new_content = content[:insertion_point] + formatted_logging + content[insertion_point:]
                    
                    # Write the modified content
                    with open(filepath, 'w') as f:
                        f.write(new_content)
                    
                    logger.info(f"Added debug logging to {filepath}")
                    return True
                else:
                    logger.warning(f"Could not find return statement in {filepath}")
            else:
                logger.warning(f"Could not find end of function in {filepath}")
    else:
        logger.warning(f"Could not find signal handling function in {filepath}")
    
    return False

def main():
    """Main entry point for the script"""
    logger.info("Starting rule_id and trade recording fix")
    
    # Find the relevant files
    order_manager_path = find_order_manager()
    if order_manager_path:
        logger.info(f"Found order manager at {order_manager_path}")
    else:
        logger.warning("Could not find order manager file")
    
    execution_handler_path = find_execution_handler()
    if execution_handler_path:
        logger.info(f"Found execution handler at {execution_handler_path}")
    else:
        logger.warning("Could not find execution handler file")
    
    signal_handler_path = find_signal_handler()
    if signal_handler_path:
        logger.info(f"Found signal handler at {signal_handler_path}")
    else:
        logger.warning("Could not find signal handler file")
    
    # Fix the files
    order_manager_fixed = False
    if order_manager_path:
        order_manager_fixed = fix_order_manager(order_manager_path)
    
    execution_handler_fixed = False
    if execution_handler_path:
        execution_handler_fixed = fix_execution_handler(execution_handler_path)
    
    signal_handler_fixed = False
    if signal_handler_path:
        signal_handler_fixed = fix_signal_handler(signal_handler_path)
    
    # Print summary
    logger.info("Fix summary:")
    logger.info(f"Order manager fix: {'Applied' if order_manager_fixed else 'Not applied'}")
    logger.info(f"Execution handler fix: {'Applied' if execution_handler_fixed else 'Not applied'}")
    logger.info(f"Signal handler fix: {'Applied' if signal_handler_fixed else 'Not applied'}")
    
    if order_manager_fixed or execution_handler_fixed or signal_handler_fixed:
        logger.info("Some fixes were applied. Please test the system to verify the fixes.")
        return 0
    else:
        logger.warning("No fixes were applied. Either the system is already fixed or the files could not be found.")
        
        # Provide a manual fix guide
        logger.info("\nManual Fix Guide:")
        logger.info("1. Check your order manager to ensure rule_id is passed from signals to orders")
        logger.info("   Look for where orders are created from signals and make sure rule_id is included")
        
        logger.info("\n2. Check your execution handler to ensure trades are created and recorded")
        logger.info("   Look for the fill_order method and ensure it creates a Trade and calls add_trade")
        
        logger.info("\n3. Check your signal handler to ensure rule_id is properly set")
        logger.info("   Look for where signals are created and make sure rule_id/strategy_id is set")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
