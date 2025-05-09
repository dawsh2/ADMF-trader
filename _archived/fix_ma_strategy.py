#!/usr/bin/env python
"""
Fix script to add rule_id to ma_crossover strategy signals.

This script adds proper rule_id formatting to signals from the MA Crossover strategy
to ensure deduplication works correctly. The rule_id is formatted as:
    "ma_crossover_{symbol}_{direction}_{timestamp}"

This creates a unique identifier for each crossover event that prevents duplicate
signals within the same minute timeframe.
"""
import os
import sys
import logging
import argparse
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ma_strategy_fix')

def backup_file(file_path):
    """Create a backup of the file."""
    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup at {backup_path}")
    return backup_path

def add_rule_id_to_signals():
    """Add rule_id to ma_crossover signals."""
    logger.info("Applying fix to MA Crossover strategy")
    
    # Define the file path
    file_path = os.path.join('src', 'strategy', 'implementations', 'ma_crossover.py')
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Create a backup
    backup_file(file_path)
    
    # Read the current implementation
    with open(file_path, 'r') as f:
        content = f.read()
        
    # Check if fix is already applied
    if 'rule_id=' in content and ('ma_crossover_' in content or 'f"ma_crossover_' in content):
        logger.info("Fix appears to be already applied (rule_id found in signal creation)")
        return True
    
    # Look for the signal creation part
    signal_creation = 'signal = create_signal_event('
    
    if signal_creation in content:
        # Find the block containing the signal creation
        lines = content.splitlines()
        
        # Find the line with signal creation
        signal_line_index = None
        for i, line in enumerate(lines):
            if signal_creation in line:
                signal_line_index = i
                break
        
        if signal_line_index is not None:
            # Find the closing parenthesis
            parenthesis_count = 0
            end_line_index = signal_line_index
            
            for i in range(signal_line_index, len(lines)):
                line = lines[i]
                parenthesis_count += line.count('(') - line.count(')')
                
                if parenthesis_count == 0:
                    end_line_index = i
                    break
            
            # Calculate the indentation
            indentation = len(lines[signal_line_index]) - len(lines[signal_line_index].lstrip())
            indent_str = ' ' * indentation
            
            # Add the rule_id parameter before the closing parenthesis
            if lines[end_line_index].strip().endswith(')'):
                # Add rule_id with appropriate indentation
                rule_id_line = indent_str + f"rule_id=f\"ma_crossover_{{symbol}}_{{signal_value}}_{{timestamp.strftime('%Y%m%d_%H%M')}}\","
                
                # Replace the closing line with the new parameters and closing parenthesis
                lines[end_line_index] = lines[end_line_index][:-1] + ",\n" + rule_id_line + "\n" + indent_str + ")"
                
                # Join the lines back together
                modified_content = '\n'.join(lines)
                
                # Write the modified content
                with open(file_path, 'w') as f:
                    f.write(modified_content)
                
                logger.info("Added rule_id to signal creation in MA Crossover strategy")
                return True
            
    logger.error("Could not find signal creation in the file")
    return False

def fix_risk_manager():
    """Fix the risk manager to properly close positions."""
    file_path = 'src/risk/managers/simple.py'
    
    if not os.path.exists(file_path):
        logger.error(f"Error: File not found at {file_path}")
        return False
        
    # Create a backup
    backup_file(file_path)
    
    with open(file_path, 'r') as f:
        content = f.read()
        
    # The issue is in the order creation sections where position_action isn't being properly set
    
    # Find the _process_processed_rule_ids method and add CRITICAL RESET line
    reset_method = "def reset(self):"
    clear_rule_ids = "self.processed_rule_ids.clear()"
    
    if reset_method in content and clear_rule_ids not in content:
        # Add explicit processed_rule_ids clear in reset method
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.strip() == reset_method:
                # Find the end of the method block (next line with same indentation)
                indent = len(line) - len(line.lstrip())
                j = i + 1
                while j < len(lines) and (len(lines[j]) - len(lines[j].lstrip()) > indent or lines[j].strip() == ''):
                    j += 1
                
                # Add the clear line before the end of the method
                lines.insert(j - 1, ' ' * (indent + 4) + "# CRITICAL FIX: Ensure processed_rule_ids is emptied on reset")
                lines.insert(j, ' ' * (indent + 4) + "self.processed_rule_ids.clear()")
                lines.insert(j + 1, ' ' * (indent + 4) + f"logger.info(\"Cleared processed rule IDs\")")
                
                # Join lines back together
                modified_content = '\n'.join(lines)
                
                # Write modified content
                with open(file_path, 'w') as f:
                    f.write(modified_content)
                
                logger.info("Added explicit rule_id clearing to risk manager reset method")
                return True
    
    # If we get here, either the file was already fixed or the method wasn't found
    if clear_rule_ids in content:
        logger.info("Risk manager already has rule_id clearing in reset method")
        return True
    
    logger.error("Could not find reset method in the risk manager")
    return False

def main():
    """Main entry point for the fix script."""
    parser = argparse.ArgumentParser(description="Fix MA Crossover strategy")
    parser.add_argument('--add-rule-id', action='store_true', help="Add rule_id to signals in MA Crossover strategy")
    parser.add_argument('--fix-risk-manager', action='store_true', help="Fix risk manager to properly handle rule IDs")
    parser.add_argument('--all', action='store_true', help="Apply all fixes")
    args = parser.parse_args()
    
    if not (args.add_rule_id or args.fix_risk_manager or args.all):
        logger.info("No action specified. Use --add-rule-id, --fix-risk-manager, or --all")
        parser.print_help()
        return 0
    
    success = True
    
    if args.add_rule_id or args.all:
        logger.info("Adding rule_id to MA Crossover strategy signals...")
        if not add_rule_id_to_signals():
            success = False
    
    if args.fix_risk_manager or args.all:
        logger.info("Fixing risk manager to properly handle rule IDs...")
        if not fix_risk_manager():
            success = False
    
    if success:
        logger.info("All requested fixes were applied successfully")
        logger.info("\nIMPORTANT: Run a backtest to see if your fixes resolved the issues.")
        logger.info("You should now see proper trade tracking in your backtest results.")
    else:
        logger.error("Some fixes were not successful. Please check the error messages above.")
        
    logger.info("If these fixes cause issues, you can restore from the backups created by this script.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())