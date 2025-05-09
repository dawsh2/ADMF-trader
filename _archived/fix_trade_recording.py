#!/usr/bin/env python
"""
Fix for trade recording issue in ADMF-trader.

This script patches the execution handler to ensure trades are properly
recorded and the rule_id is correctly passed through the event chain.
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
        logging.FileHandler("fix_trade_recording.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fix_trade_recording')

def backup_file(filepath):
    """Create a backup of the file before modifying it"""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.bak"
        shutil.copy2(filepath, backup_path)
        logger.info(f"Created backup at {backup_path}")
        return True
    return False

def find_execution_handler():
    """Find the execution handler file in the project"""
    # Start with the most likely locations
    potential_paths = [
        'src/execution/execution_handler.py',
        'src/execution/handler.py',
        'src/execution/execution.py',
        'src/execution/broker.py'
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # If not found, search for it
    logger.info("Searching for execution handler file...")
    for root, dirs, files in os.walk('src'):
        for file in files:
            if 'execution' in file.lower() and file.endswith('.py'):
                filepath = os.path.join(root, file)
                # Check if the file contains fill_order method
                with open(filepath, 'r') as f:
                    content = f.read()
                    if 'fill_order' in content:
                        return filepath
    
    return None

def find_signal_handler():
    """Find the signal handler file in the project"""
    # Start with the most likely locations
    potential_paths = [
        'src/event/signal_handler.py',
        'src/event/handler.py',
        'src/signals/handler.py',
        'src/event/adapters/signal_adapter.py'
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # If not found, search for it
    logger.info("Searching for signal handler file...")
    for root, dirs, files in os.walk('src'):
        for file in files:
            if ('signal' in file.lower() or 'event' in file.lower()) and file.endswith('.py'):
                filepath = os.path.join(root, file)
                # Check if the file contains create_order_from_signal method
                with open(filepath, 'r') as f:
                    content = f.read()
                    if 'create_order' in content and 'signal' in content.lower():
                        return filepath
    
    return None

def fix_execution_handler(filepath):
    """Fix the execution handler to ensure trades are recorded"""
    if not filepath or not os.path.exists(filepath):
        logger.error(f"Execution handler file not found at {filepath}")
        return False
    
    logger.info(f"Fixing execution handler at {filepath}")
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern to find fill_order method
    fill_order_pattern = r'def\s+fill_order\s*\(.*?\).*?:'
    
    if re.search(fill_order_pattern, content, re.DOTALL):
        # Check if the method is creating and recording trades
        if 'Trade(' in content and 'add_trade' in content:
            # Check if rule_id is being passed
            if 'rule_id' not in content or 'order.rule_id' not in content:
                # Add rule_id to Trade constructor
                new_content = content.replace(
                    'Trade(',
                    'Trade('
                )
                
                # Make sure order.rule_id is passed to Trade constructor
                trade_pattern = r'Trade\s*\((.*?)\)'
                trade_match = re.search(trade_pattern, content, re.DOTALL)
                
                if trade_match:
                    trade_args = trade_match.group(1)
                    if 'rule_id' not in trade_args:
                        if trade_args.endswith(')'):
                            # Remove closing parenthesis
                            new_trade_args = trade_args[:-1]
                            if new_trade_args.strip().endswith(','):
                                new_trade_args += ' rule_id=order.rule_id)'
                            else:
                                new_trade_args += ', rule_id=order.rule_id)'
                            new_content = content.replace(trade_args, new_trade_args)
                        else:
                            # Just add rule_id parameter
                            if trade_args.strip().endswith(','):
                                new_trade_args = f"{trade_args} rule_id=order.rule_id"
                            else:
                                new_trade_args = f"{trade_args}, rule_id=order.rule_id"
                            new_content = content.replace(trade_args, new_trade_args)
                    
                    # Make sure add_trade is called
                    if 'add_trade' not in content:
                        add_trade_code = """
        # Record the trade in portfolio
        self.portfolio.add_trade(trade)"""
                        
                        # Find a good place to insert
                        new_content = re.sub(
                            r'(Trade\(.*?\))',
                            r'\1' + add_trade_code,
                            new_content,
                            flags=re.DOTALL
                        )
                    
                    # Write back the fixes
                    with open(filepath, 'w') as f:
                        f.write(new_content)
                    
                    logger.info(f"Fixed trade recording in {filepath}")
                    return True
                else:
                    logger.warning(f"Could not find Trade constructor in {filepath}")
            else:
                logger.info(f"rule_id is already being passed to Trade in {filepath}")
        else:
            # We need to add code to create and record trades
            fill_order_match = re.search(fill_order_pattern, content, re.DOTALL)
            if fill_order_match:
                fill_order_start = fill_order_match.start()
                
                # Find the method body
                method_body_start = content.find(':', fill_order_start) + 1
                
                # Find indentation level
                next_line_start = content.find('\n', method_body_start) + 1
                if next_line_start < len(content):
                    # Count spaces at the beginning of the next line
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
    rule_id=order.rule_id if hasattr(order, 'rule_id') else None
)
self.portfolio.add_trade(trade)
"""
                    
                    # Find a good insertion point - before any return statements
                    method_end = content.find('\n\n', method_body_start)
                    if method_end == -1:
                        method_end = len(content)
                    
                    return_pos = content.find('return', method_body_start, method_end)
                    if return_pos != -1:
                        insertion_point = content.rfind('\n', method_body_start, return_pos) + 1
                    else:
                        insertion_point = method_end
                    
                    new_content = content[:insertion_point] + trade_code + content[insertion_point:]
                    
                    # Write back the fixes
                    with open(filepath, 'w') as f:
                        f.write(new_content)
                    
                    logger.info(f"Added trade recording code to {filepath}")
                    return True
                else:
                    logger.warning(f"Could not determine indentation in {filepath}")
            else:
                logger.warning(f"Could not find fill_order method in {filepath}")
    else:
        logger.warning(f"Could not find fill_order method in {filepath}")
    
    return False

def fix_signal_handler(filepath):
    """Fix the signal handler to ensure rule_id is passed to orders"""
    if not filepath or not os.path.exists(filepath):
        logger.error(f"Signal handler file not found at {filepath}")
        return False
    
    logger.info(f"Fixing signal handler at {filepath}")
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern to find create_order_from_signal method
    create_order_pattern = r'def\s+create_order.*?signal.*?:'
    
    if re.search(create_order_pattern, content, re.DOTALL):
        # Check if rule_id is being passed to Order constructor
        order_pattern = r'Order\s*\((.*?)\)'
        order_match = re.search(order_pattern, content, re.DOTALL)
        
        if order_match:
            order_args = order_match.group(1)
            if 'rule_id' not in order_args:
                # Add rule_id to Order constructor
                if order_args.endswith(')'):
                    # Remove closing parenthesis
                    new_order_args = order_args[:-1]
                    if new_order_args.strip().endswith(','):
                        new_order_args += ' rule_id=signal.rule_id if hasattr(signal, "rule_id") else (signal.strategy_id if hasattr(signal, "strategy_id") else None))'
                    else:
                        new_order_args += ', rule_id=signal.rule_id if hasattr(signal, "rule_id") else (signal.strategy_id if hasattr(signal, "strategy_id") else None))'
                    new_content = content.replace(order_args, new_order_args)
                else:
                    # Just add rule_id parameter
                    if order_args.strip().endswith(','):
                        new_order_args = f"{order_args} rule_id=signal.rule_id if hasattr(signal, 'rule_id') else (signal.strategy_id if hasattr(signal, 'strategy_id') else None)"
                    else:
                        new_order_args = f"{order_args}, rule_id=signal.rule_id if hasattr(signal, 'rule_id') else (signal.strategy_id if hasattr(signal, 'strategy_id') else None)"
                    new_content = content.replace(order_args, new_order_args)
                
                # Write back the fixes
                with open(filepath, 'w') as f:
                    f.write(new_content)
                
                logger.info(f"Fixed rule_id passing in {filepath}")
                return True
            else:
                logger.info(f"rule_id is already being passed to Order in {filepath}")
        else:
            logger.warning(f"Could not find Order constructor in {filepath}")
    else:
        logger.warning(f"Could not find create_order method in {filepath}")
    
    return False

def fix_event_class():
    """Fix the Event class to add consumption tracking"""
    # Find the Event class file
    event_file = None
    for root, dirs, files in os.walk('src'):
        for file in files:
            if 'event' in file.lower() and file.endswith('.py'):
                filepath = os.path.join(root, file)
                # Check if the file contains the Event class
                with open(filepath, 'r') as f:
                    content = f.read()
                    if 'class Event' in content:
                        event_file = filepath
                        break
        if event_file:
            break
    
    if not event_file:
        logger.error("Could not find Event class file")
        return False
    
    logger.info(f"Fixing Event class in {event_file}")
    backup_file(event_file)
    
    with open(event_file, 'r') as f:
        content = f.read()
    
    # Check if the Event class already has consumption tracking
    if 'is_consumed' not in content or '_consumed' not in content:
        # Add consumption tracking attributes and methods
        event_class_pattern = r'class\s+Event\s*(?:\(.*?\))?\s*:'
        event_match = re.search(event_class_pattern, content)
        
        if event_match:
            # Find the __init__ method
            init_pattern = r'def\s+__init__\s*\(.*?\).*?:'
            init_match = re.search(init_pattern, content, re.DOTALL)
            
            if init_match:
                # Find the end of the __init__ method
                init_start = init_match.start()
                next_method_match = re.search(r'def\s+', content[init_start + 1:], re.DOTALL)
                
                if next_method_match:
                    init_end = init_start + 1 + next_method_match.start()
                else:
                    # Find the end of the class
                    next_class_match = re.search(r'class\s+', content[init_start + 1:], re.DOTALL)
                    if next_class_match:
                        init_end = init_start + 1 + next_class_match.start()
                    else:
                        init_end = len(content)
                
                # Find the indentation level
                line_after_init = content.find('\n', init_match.end()) + 1
                indentation = 0
                for char in content[line_after_init:]:
                    if char == ' ':
                        indentation += 1
                    else:
                        break
                
                # Find where to insert the _consumed attribute
                # Look for the last line of the __init__ method
                lines = content[init_match.end():init_end].split('\n')
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip() and not lines[i].strip().startswith('#'):
                        # Insert after this line
                        indent_str = ' ' * indentation
                        consumed_line = f"\n{indent_str}self._consumed = False"
                        lines.insert(i + 1, consumed_line)
                        break
                
                new_init = content[init_match.start():init_match.end()] + '\n'.join(lines)
                
                # Add the consumption methods after the init method
                method_indent = ' ' * (indentation - 4)  # Methods are usually indented less than init body
                consumption_methods = f"""
{method_indent}def is_consumed(self):
{method_indent}    \"\"\"Check if the event has been consumed.\"\"\"
{method_indent}    return getattr(self, '_consumed', False)
{method_indent}    
{method_indent}def consume(self):
{method_indent}    \"\"\"Mark the event as consumed.\"\"\"
{method_indent}    self._consumed = True
{method_indent}    
{method_indent}def reset_consumed(self):
{method_indent}    \"\"\"Reset the event consumption status.\"\"\"
{method_indent}    self._consumed = False
{method_indent}    
{method_indent}def get_type(self):
{method_indent}    \"\"\"Get the event type.\"\"\"
{method_indent}    return self.type
"""
                
                # Combine everything
                new_content = content[:init_start] + new_init + consumption_methods + content[init_end:]
                
                # Write back the fixes
                with open(event_file, 'w') as f:
                    f.write(new_content)
                
                logger.info(f"Added consumption tracking to Event class in {event_file}")
                return True
            else:
                logger.warning(f"Could not find __init__ method in Event class in {event_file}")
        else:
            logger.warning(f"Could not find Event class in {event_file}")
    else:
        logger.info(f"Event class already has consumption tracking in {event_file}")
    
    return False

def fix_signal_event_creation():
    """Fix signal event creation parameter mismatch"""
    # Find strategy files
    strategy_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if ('strategy' in file.lower() or 'rule' in file.lower()) and file.endswith('.py'):
                filepath = os.path.join(root, file)
                # Check if the file contains create_signal_event method calls
                with open(filepath, 'r') as f:
                    content = f.read()
                    if 'create_signal_event' in content:
                        strategy_files.append(filepath)
    
    if not strategy_files:
        logger.info("No strategy files with create_signal_event calls found")
        return False
    
    fixed_files = 0
    
    for filepath in strategy_files:
        logger.info(f"Checking strategy file at {filepath}")
        backup_file(filepath)
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Find all create_signal_event method calls
        signal_event_pattern = r'create_signal_event\s*\((.*?)\)'
        signal_matches = re.finditer(signal_event_pattern, content, re.DOTALL)
        
        new_content = content
        for match in signal_matches:
            signal_args = match.group(1)
            if 'signal_value' in signal_args:
                # Fix signal_value to signal_type
                fixed_args = signal_args.replace('signal_value=', 'signal_type=')
                
                # Convert numeric values to BUY/SELL strings
                fixed_args = re.sub(r'signal_type=\s*1', 'signal_type="BUY"', fixed_args)
                fixed_args = re.sub(r'signal_type=\s*-1', 'signal_type="SELL"', fixed_args)
                
                # Map rule_id to strategy_id if needed
                if 'rule_id=' in fixed_args and 'strategy_id=' not in fixed_args:
                    fixed_args = fixed_args.replace('rule_id=', 'strategy_id=')
                
                # Remove price parameter if it exists and is not used
                if 'price=' in fixed_args:
                    price_pattern = r',\s*price=[^,)]*'
                    fixed_args = re.sub(price_pattern, '', fixed_args)
                
                # Add strength parameter if it doesn't exist
                if 'strength=' not in fixed_args and 'signal_value=' in signal_args:
                    strength_code = ", strength=abs(signal_value)"
                    if fixed_args.endswith(')'):
                        fixed_args = fixed_args[:-1] + strength_code + ')'
                    else:
                        fixed_args += strength_code
                
                # Replace in the content
                new_content = new_content.replace(f"create_signal_event({signal_args})", f"create_signal_event({fixed_args})")
        
        if new_content != content:
            # Write back the fixes
            with open(filepath, 'w') as f:
                f.write(new_content)
            
            logger.info(f"Fixed signal event creation in {filepath}")
            fixed_files += 1
    
    logger.info(f"Fixed signal event creation in {fixed_files} files")
    return fixed_files > 0

def fix_objective_functions():
    """Fix objective functions to handle None results"""
    # Find the objective_functions.py file
    objective_file = None
    for root, dirs, files in os.walk('src'):
        for file in files:
            if 'objective' in file.lower() and file.endswith('.py'):
                filepath = os.path.join(root, file)
                # Check if this is the right file
                with open(filepath, 'r') as f:
                    content = f.read()
                    if 'def sharpe_ratio' in content or 'OBJECTIVES' in content:
                        objective_file = filepath
                        break
        if objective_file:
            break
    
    if not objective_file:
        logger.error("Could not find objective_functions.py")
        return False
    
    logger.info(f"Fixing objective functions in {objective_file}")
    backup_file(objective_file)
    
    with open(objective_file, 'r') as f:
        content = f.read()
    
    # Find all objective functions
    function_pattern = r'def\s+([a-zA-Z0-9_]+).*?\(.*?results.*?\).*?:'
    function_matches = re.finditer(function_pattern, content, re.DOTALL)
    
    new_content = content
    for match in function_matches:
        function_name = match.group(1)
        function_start = match.start()
        
        # Find function body
        body_start = content.find(':', function_start) + 1
        
        # Find next function or end of file
        next_function = re.search(r'def\s+', content[body_start:], re.DOTALL)
        if next_function:
            body_end = body_start + next_function.start()
        else:
            body_end = len(content)
        
        function_body = content[body_start:body_end]
        
        # Check if the function already handles None results
        if 'None' not in function_body or 'is None' not in function_body:
            # Find indentation level
            lines = function_body.split('\n')
            indentation = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith('#'):
                    indentation = len(line) - len(line.lstrip())
                    break
            
            # Add None check
            indent_str = ' ' * indentation
            none_check = f"\n{indent_str}if results is None or not hasattr(results, 'get'):\n{indent_str}    return 0.0\n"
            
            # Add checks for specific metrics if they're used
            metrics_used = set()
            if 'return_pct' in function_body or 'returns' in function_body:
                metrics_used.add('returns')
            if 'sharpe_ratio' in function_body:
                metrics_used.add('sharpe_ratio')
            if 'profit_factor' in function_body:
                metrics_used.add('profit_factor')
            if 'max_drawdown' in function_body:
                metrics_used.add('max_drawdown')
            if 'win_rate' in function_body:
                metrics_used.add('win_rate')
            
            # Add additional checks for each metric used
            for metric in metrics_used:
                none_check += f"\n{indent_str}{metric} = results.get('{metric}', None)\n{indent_str}if {metric} is None or (isinstance({metric}, list) and len({metric}) == 0):\n{indent_str}    return 0.0\n"
            
            # Check for division by zero if it looks like division is happening
            if '/' in function_body and 'std' in function_body.lower():
                none_check += f"\n{indent_str}# Avoid division by zero\n{indent_str}std_dev = np.std(returns) if 'returns' in locals() else 0\n{indent_str}if std_dev == 0:\n{indent_str}    return 0.0\n"
            
            # Add the checks to the function body
            modified_body = none_check + function_body
            
            # Replace the function body in the content
            new_content = new_content.replace(function_body, modified_body)
    
    if new_content != content:
        # Write back the fixes
        with open(objective_file, 'w') as f:
            f.write(new_content)
        
        logger.info(f"Fixed objective functions in {objective_file}")
        return True
    else:
        logger.info(f"No changes needed in objective functions in {objective_file}")
        return False

def main():
    """Main entry point for the script"""
    logger.info("Starting trade recording fix")
    
    # Fix Event class to add consumption tracking
    event_fixed = fix_event_class()
    
    # Find and fix execution handler
    execution_handler_path = find_execution_handler()
    if execution_handler_path:
        execution_fixed = fix_execution_handler(execution_handler_path)
    else:
        logger.error("Could not find execution handler file")
        execution_fixed = False
    
    # Find and fix signal handler
    signal_handler_path = find_signal_handler()
    if signal_handler_path:
        signal_fixed = fix_signal_handler(signal_handler_path)
    else:
        logger.error("Could not find signal handler file")
        signal_fixed = False
    
    # Fix signal event creation
    signal_event_fixed = fix_signal_event_creation()
    
    # Fix objective functions
    objective_fixed = fix_objective_functions()
    
    # Print summary
    logger.info("Fix summary:")
    logger.info(f"Event class consumption tracking: {'Fixed' if event_fixed else 'Not fixed'}")
    logger.info(f"Execution handler: {'Fixed' if execution_fixed else 'Not fixed'}")
    logger.info(f"Signal handler: {'Fixed' if signal_fixed else 'Not fixed'}")
    logger.info(f"Signal event creation: {'Fixed' if signal_event_fixed else 'Not fixed'}")
    logger.info(f"Objective functions: {'Fixed' if objective_fixed else 'Not fixed'}")
    
    if event_fixed or execution_fixed or signal_fixed or signal_event_fixed or objective_fixed:
        logger.info("Some fixes were applied. Please test the system to verify the fixes.")
        return 0
    else:
        logger.warning("No fixes were applied. Either the system is already fixed or the files could not be found.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
