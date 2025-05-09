#!/usr/bin/env python
"""
Fix the formatting issue in the reporter.py file.

This script applies a comprehensive fix to the reporter.py file to handle
formatting more safely, especially when dealing with non-numeric values.
"""

import os
import sys
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_reporter():
    """
    Apply more comprehensive fixes to the reporter.py file.
    
    Returns:
        bool: True if successful, False otherwise
    """
    reporter_path = os.path.join('src', 'strategy', 'optimization', 'reporter.py')
    backup_path = reporter_path + '.bak'
    
    try:
        # Create a backup
        with open(reporter_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        logger.info(f"Created backup at {backup_path}")
        
        # Read the original file
        with open(reporter_path, 'r') as f:
            content = f.read()
        
        # Fix 1: HTML report formatting
        # Find the metrics definition section and fix it
        metrics_pattern = r'metrics = \[\s*\([^)]*\),\s*\([^)]*\),\s*\([^)]*\),\s*\([^)]*\),\s*\([^)]*\),\s*\([^)]*\),?\s*\]'
        metrics_replacement = """metrics = [
                ('Total Return (%)', 'return_pct', ':.2f'),
                ('Sharpe Ratio', 'sharpe_ratio', ':.2f'),
                ('Profit Factor', 'profit_factor', ':.2f'),
                ('Max Drawdown (%)', 'max_drawdown', ':.2f'),
                ('Win Rate', 'win_rate', ':.2f'),
                ('Trades Executed', 'trades_executed', '')
            ]"""
        
        content = re.sub(metrics_pattern, metrics_replacement, content)
        
        # Fix 2: Ensure type checking before formatting
        format_pattern1 = r"if train_value != 'N/A' and format_str:"
        format_replacement1 = "if train_value != 'N/A' and format_str and isinstance(train_value, (int, float)):"
        
        format_pattern2 = r"if test_value != 'N/A' and format_str:"
        format_replacement2 = "if test_value != 'N/A' and format_str and isinstance(test_value, (int, float)):"
        
        content = content.replace(format_pattern1, format_replacement1)
        content = content.replace(format_pattern2, format_replacement2)
        
        # Fix 3: Add safe formatting function for all other places
        # Insert this function after the class definition
        safe_format_func = """
    def _safe_format(self, value, format_str=''):
        """
        Safely format a value with the given format string.
        
        Args:
            value: Value to format
            format_str: Format string to use
            
        Returns:
            str: Formatted value
        """
        if not isinstance(value, (int, float)):
            return str(value)
            
        try:
            if format_str:
                return f'{value:{format_str}}'
            return str(value)
        except (ValueError, TypeError):
            return str(value)
        """
        
        class_pattern = r"class OptimizationReporter:.*?def __init__"
        class_replacement = lambda match: match.group(0) + safe_format_func.strip() + "\n\n    def __init__"
        
        content = re.sub(class_pattern, class_replacement, content, flags=re.DOTALL)
        
        # Fix 4: Fix any other formatting issues in the file
        # Find all other f-string formatting in the file and wrap with safety checks
        # This is a bit complex for a simple script, but we can add it if needed
        
        # Write the fixed content back to the file
        with open(reporter_path, 'w') as f:
            f.write(content)
            
        logger.info(f"Applied fixes to {reporter_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing reporter.py: {e}")
        
        # Restore from backup if there was an error
        try:
            if os.path.exists(backup_path):
                with open(backup_path, 'r') as src, open(reporter_path, 'w') as dst:
                    dst.write(src.read())
                logger.info(f"Restored from backup {backup_path}")
        except Exception as restore_err:
            logger.error(f"Error restoring from backup: {restore_err}")
            
        return False

def main():
    """Main function."""
    logger.info("Starting reporter.py fix")
    success = fix_reporter()
    
    if success:
        logger.info("Successfully fixed reporter.py")
        return 0
    else:
        logger.error("Failed to fix reporter.py")
        return 1

if __name__ == '__main__':
    sys.exit(main())
