#!/usr/bin/env python
"""
Complete fix for the HTML report generation in reporter.py.

This script completely rewrites the metrics formatting section of the HTML
report generation to be much more robust and avoid any formatting issues.
"""

import os
import sys
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_html_report_generation():
    """
    Completely rewrite the metrics formatting section of the HTML report generation.
    
    Returns:
        bool: True if successful, False otherwise
    """
    reporter_path = os.path.join('src', 'strategy', 'optimization', 'reporter.py')
    backup_path = reporter_path + '.bak3'
    
    try:
        # Create a backup
        with open(reporter_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        logger.info(f"Created backup at {backup_path}")
        
        # Read the original file
        with open(reporter_path, 'r') as f:
            content = f.read()
        
        # Define the problematic section pattern
        section_pattern = r"""            # Define metrics to display
            metrics = \[.*?\]
            
            for label, key, format_str in metrics:
                train_value = train_results\.get\('statistics', \{\}\)\.get\(key, 'N/A'\)
                test_value = test_results\.get\('statistics', \{\}\)\.get\(key, 'N/A'\)
                
                if train_value != 'N/A'.*?train_value = f'{train_value:{format_str}}'.*?
                
                if test_value != 'N/A'.*?test_value = f'{test_value:{format_str}}'.*?
                
                html\.append\(f'<tr><td>{label}</td><td>{train_value}</td><td>{test_value}</td></tr>'\)"""
        
        # Replacement with much more robust code
        replacement = """            # Define metrics to display
            metrics = [
                ('Total Return (%)', 'return_pct', ':.2f'),
                ('Sharpe Ratio', 'sharpe_ratio', ':.2f'),
                ('Profit Factor', 'profit_factor', ':.2f'),
                ('Max Drawdown (%)', 'max_drawdown', ':.2f'),
                ('Win Rate', 'win_rate', ':.2f'),
                ('Trades Executed', 'trades_executed', '')
            ]
            
            for label, key, format_str in metrics:
                # Get values safely
                train_value = train_results.get('statistics', {}).get(key, 'N/A')
                test_value = test_results.get('statistics', {}).get(key, 'N/A')
                
                # Format train value safely
                formatted_train = train_value
                if train_value != 'N/A':
                    try:
                        if isinstance(train_value, (int, float)) and format_str:
                            formatted_train = f'{train_value:{format_str}}'
                        else:
                            formatted_train = str(train_value)
                    except (ValueError, TypeError):
                        formatted_train = str(train_value)
                
                # Format test value safely
                formatted_test = test_value
                if test_value != 'N/A':
                    try:
                        if isinstance(test_value, (int, float)) and format_str:
                            formatted_test = f'{test_value:{format_str}}'
                        else:
                            formatted_test = str(test_value)
                    except (ValueError, TypeError):
                        formatted_test = str(test_value)
                
                # Add row to HTML table
                html.append(f'<tr><td>{label}</td><td>{formatted_train}</td><td>{formatted_test}</td></tr>')\n"""
        
        # Replace the section using regex with re.DOTALL to match across newlines
        new_content = re.sub(section_pattern, replacement, content, flags=re.DOTALL)
        
        # Check if we actually made a replacement
        if new_content == content:
            logger.warning("Could not find the section to replace. Using more targeted approach.")
            
            # Try a more targeted approach to fix just the problematic lines
            content = content.replace(
                "train_value = f'{train_value:{format_str}}'",
                "try:\n                    if isinstance(train_value, (int, float)):\n                        train_value = f'{train_value:{format_str}}'\n                    else:\n                        train_value = str(train_value)\n                except (ValueError, TypeError):\n                    train_value = str(train_value)"
            )
            
            content = content.replace(
                "test_value = f'{test_value:{format_str}}'",
                "try:\n                    if isinstance(test_value, (int, float)):\n                        test_value = f'{test_value:{format_str}}'\n                    else:\n                        test_value = str(test_value)\n                except (ValueError, TypeError):\n                    test_value = str(test_value)"
            )
            
            logger.info("Applied targeted fixes to formatting lines")
            new_content = content
        else:
            logger.info("Successfully replaced the entire metrics section")
        
        # Write the modified content back to the file
        with open(reporter_path, 'w') as f:
            f.write(new_content)
            
        logger.info(f"Applied HTML report generation fix to {reporter_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing HTML report generation: {e}")
        
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
    logger.info("Starting HTML report generation fix")
    success = fix_html_report_generation()
    
    if success:
        logger.info("Successfully applied HTML report generation fix")
        
        # Run the verification script
        import subprocess
        logger.info("Running fix verification...")
        result = subprocess.run([sys.executable, 'fix_verification.py'], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Verification successful!")
            return 0
        else:
            logger.error("Verification failed after applying fix")
            logger.info(f"Stdout: {result.stdout}")
            logger.error(f"Stderr: {result.stderr}")
            return 1
    else:
        logger.error("Failed to apply HTML report generation fix")
        return 1

if __name__ == '__main__':
    sys.exit(main())
