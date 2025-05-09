#!/usr/bin/env python
"""
Direct fix for the optimizer to handle None best_parameters.

This script specifically fixes the 'NoneType' object has no attribute 'items' error
in the reporter.py file.
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
        logging.FileHandler("direct_fix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('direct_fix')

def backup_file(filepath):
    """Create a backup of the file before modifying it"""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.bak"
        shutil.copy2(filepath, backup_path)
        logger.info(f"Created backup at {backup_path}")
        return True
    return False

def fix_reporter():
    """Fix the reporter.py file to handle None best_parameters"""
    reporter_path = os.path.join('src', 'strategy', 'optimization', 'reporter.py')
    
    if not os.path.exists(reporter_path):
        logger.error(f"Reporter file not found at {reporter_path}")
        return False
    
    logger.info(f"Fixing reporter at {reporter_path}")
    backup_file(reporter_path)
    
    with open(reporter_path, 'r') as f:
        content = f.read()
    
    # Look for best_parameters.items() and add a check for None
    best_params_pattern = r'(best_parameters\s*=\s*results\.get\([\'\"]best_parameters[\'\"]\s*,\s*\{\}\))\s*\n'
    
    if re.search(best_params_pattern, content):
        # Add check for None
        fixed_content = re.sub(
            best_params_pattern,
            r'\1\n        # Check if best_parameters is None\n        if best_parameters is None:\n            best_parameters = {}\n',
            content
        )
        
        # Write back the fixed content
        with open(reporter_path, 'w') as f:
            f.write(fixed_content)
        
        logger.info(f"Fixed best_parameters None check in {reporter_path}")
        return True
    else:
        # If the exact pattern doesn't match, try a more generic approach
        for_loop_pattern = r'for\s+param_name\s*,\s*param_value\s+in\s+best_parameters\.items\(\):'
        if re.search(for_loop_pattern, content):
            # Add check before the for loop
            fixed_content = re.sub(
                for_loop_pattern,
                r'# Check if best_parameters is None\n        if best_parameters is None:\n            best_parameters = {}\n        \n        for param_name, param_value in best_parameters.items():',
                content
            )
            
            # Write back the fixed content
            with open(reporter_path, 'w') as f:
                f.write(fixed_content)
            
            logger.info(f"Fixed best_parameters None check in {reporter_path}")
            return True
        else:
            logger.warning(f"Could not find best_parameters.items() in {reporter_path}")
            return False

def fix_objective_functions():
    """Fix objective functions to handle None results"""
    objective_path = os.path.join('src', 'strategy', 'optimization', 'objective_functions.py')
    
    if not os.path.exists(objective_path):
        logger.error(f"Objective functions file not found at {objective_path}")
        return False
    
    logger.info(f"Fixing objective functions at {objective_path}")
    backup_file(objective_path)
    
    with open(objective_path, 'r') as f:
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
        
        # Skip if function already handles None results
        if 'None' in function_body and 'is None' in function_body:
            continue
        
        # Find indentation level
        lines = function_body.split('\n')
        indentation = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#'):
                indentation = len(line) - len(line.lstrip())
                break
        
        # Add None check
        indent_str = ' ' * indentation
        none_check = f"\n{indent_str}if results is None:\n{indent_str}    return 0.0\n"
        
        # Add the check to the beginning of the function body
        modified_body = none_check + function_body
        
        # Replace the function body in the content
        new_content = new_content.replace(function_body, modified_body)
    
    if new_content != content:
        # Write back the fixes
        with open(objective_path, 'w') as f:
            f.write(new_content)
        
        logger.info(f"Fixed objective functions in {objective_path}")
        return True
    else:
        logger.info(f"No changes needed in objective functions in {objective_path}")
        return False

def main():
    """Main entry point for the script"""
    logger.info("Starting direct optimizer fix")
    
    # Fix the reporter
    reporter_fixed = fix_reporter()
    
    # Fix objective functions
    objective_fixed = fix_objective_functions()
    
    # Print summary
    logger.info("Fix summary:")
    logger.info(f"Reporter fix: {'Applied' if reporter_fixed else 'Not applied'}")
    logger.info(f"Objective functions fix: {'Applied' if objective_fixed else 'Not applied'}")
    
    if reporter_fixed or objective_fixed:
        logger.info("Some fixes were applied. Please test the system to verify the fixes.")
        return 0
    else:
        logger.warning("No fixes were applied. Either the system is already fixed or the files could not be found.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
