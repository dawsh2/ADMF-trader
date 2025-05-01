#!/usr/bin/env python3
"""
Direct fix for the MA Crossover rule_id format issue.

This script directly modifies the MA Crossover strategy source file to ensure 
the rule_id format includes symbol and direction as required.
"""

import os
import sys
import re

def print_status(message):
    """Print a status message."""
    print(f"[DIRECT FIX] {message}")

def fix_rule_id_format():
    """Fix the rule_id format in the MA Crossover strategy source file."""
    file_path = "src/strategy/implementations/ma_crossover.py"
    
    # Check if file exists
    if not os.path.exists(file_path):
        print_status(f"Error: File {file_path} not found")
        return False
    
    # Create backup
    backup_path = f"{file_path}.bak"
    try:
        with open(file_path, 'r') as src_file:
            content = src_file.read()
            
        # Create backup
        with open(backup_path, 'w') as backup_file:
            backup_file.write(content)
        
        print_status(f"Created backup at {backup_path}")
    except Exception as e:
        print_status(f"Error creating backup: {e}")
        return False
    
    # Look for the rule_id assignment
    rule_id_pattern = re.compile(r'rule_id\s*=\s*f["\']([^"\']*)["\']')
    matches = rule_id_pattern.findall(content)
    
    if not matches:
        print_status("Could not find rule_id assignment in the file")
        return False
    
    print_status(f"Found rule_id format: f\"{matches[0]}\"")
    
    # Check if it already has the correct format
    rule_id_format = matches[0]
    has_symbol = "{symbol}" in rule_id_format
    has_direction = "direction_name" in rule_id_format or "BUY" in rule_id_format or "SELL" in rule_id_format
    has_group = "group" in rule_id_format
    
    format_correct = has_symbol and has_direction and has_group
    
    if format_correct:
        print_status("Rule ID format is already correct")
        print_status(f"Current format: f\"{rule_id_format}\"")
        return True
    
    # Apply the fix
    print_status("Applying fix to rule_id format...")
    
    # Look for the rule_id assignment line
    old_line_pattern = re.compile(r'(\s*)rule_id\s*=\s*f["\']([^"\']*)["\']')
    match = old_line_pattern.search(content)
    
    if not match:
        print_status("Could not locate the rule_id assignment line")
        return False
    
    indent = match.group(1)
    
    # Check if direction_name is already defined
    has_direction_name = "direction_name = " in content
    
    if has_direction_name:
        print_status("direction_name is already defined")
    else:
        print_status("Need to add direction_name definition")
        
        # Find the position to insert the direction_name code
        insert_position = match.start()
        
        # Create the direction_name line
        direction_name_line = f"{indent}direction_name = \"BUY\" if signal_value == 1 else \"SELL\"\n"
        
        # Insert the line
        content = content[:insert_position] + direction_name_line + content[insert_position:]
    
    # Now replace the rule_id assignment
    old_rule_id_line = match.group(0)
    new_rule_id_line = f"{indent}rule_id = f\"{{self.name}}_{{symbol}}_{{direction_name}}_group_{{group_id}}\""
    
    # Perform the replacement
    content = content.replace(old_rule_id_line, new_rule_id_line)
    
    # Write the modified content back to the file
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        print_status(f"Successfully updated {file_path}")
        print_status("New rule_id format: f\"{self.name}_{symbol}_{direction_name}_group_{group_id}\"")
        return True
    except Exception as e:
        print_status(f"Error writing to file: {e}")
        return False

def main():
    """Apply the direct fix and provide instructions."""
    print("\n=== DIRECT FIX FOR MA CROSSOVER RULE ID FORMAT ===\n")
    
    # Apply the fix
    success = fix_rule_id_format()
    
    if success:
        print("\n=== FIX APPLIED SUCCESSFULLY ===")
        print("The rule_id format in the MA Crossover strategy has been fixed.")
        print("Now run the following command to verify:")
        print("  python run_fixed_ma_crossover_v2.py")
    else:
        print("\n=== FIX FAILED ===")
        print("Could not apply the fix to the MA Crossover strategy.")
        print("You may need to manually edit the file:")
        print("  src/strategy/implementations/ma_crossover.py")
        print("And ensure the rule_id is created with:")
        print("  direction_name = \"BUY\" if signal_value == 1 else \"SELL\"")
        print("  rule_id = f\"{self.name}_{symbol}_{direction_name}_group_{group_id}\"")
    
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
