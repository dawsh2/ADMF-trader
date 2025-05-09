#!/usr/bin/env python
"""
Script to fix the simple moving average strategy by using the correct price_key from config.
"""
import os
import sys
import yaml
import logging
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('simple_ma_strategy_fix')

def backup_file(file_path):
    """Create a backup of the file."""
    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup at {backup_path}")
    return backup_path

def fix_simple_ma_strategy():
    """Fix the SimpleMACrossover strategy to use the configured price_key."""
    logger.info("Applying fix to Simple MA Crossover strategy")
    
    # Define file path
    file_path = os.path.join('src', 'strategy', 'implementations', 'simple_ma_crossover.py')
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Create a backup
    backup_file(file_path)
    
    # Read the current implementation
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if the strategy uses price_key properly
    if "if self.price_key.lower() == 'open':" in content:
        logger.info("Fix appears to be already applied (price_key implementation found)")
        return True
    
    # Find the on_bar method
    on_bar_method = "def on_bar(self, bar_event):"
    
    if on_bar_method in content:
        lines = content.splitlines()
        
        # Find the line where the price is extracted
        price_extract_line = None
        for i, line in enumerate(lines):
            if "price = bar_event.get_close()" in line:
                price_extract_line = i
                break
        
        if price_extract_line is not None:
            # Get the indentation
            indentation = len(lines[price_extract_line]) - len(lines[price_extract_line].lstrip())
            indent_str = ' ' * indentation
            
            # Remove the existing price extraction
            lines.pop(price_extract_line)
            
            # Insert the new price extraction code
            new_price_code = [
                indent_str + "# Extract price data - using the configured price_key",
                indent_str + "if self.price_key.lower() == 'open':",
                indent_str + "    price = bar_event.get_open()",
                indent_str + "elif self.price_key.lower() == 'high':",
                indent_str + "    price = bar_event.get_high()",
                indent_str + "elif self.price_key.lower() == 'low':",
                indent_str + "    price = bar_event.get_low()",
                indent_str + "else:  # Default to close",
                indent_str + "    price = bar_event.get_close()"
            ]
            
            for j, code_line in enumerate(new_price_code):
                lines.insert(price_extract_line + j, code_line)
            
            # Join lines back together
            modified_content = '\n'.join(lines)
            
            # Write modified content
            with open(file_path, 'w') as f:
                f.write(modified_content)
            
            logger.info("Updated SimpleMACrossoverStrategy to use configured price_key")
            return True
        
        else:
            logger.error("Could not find price extraction in on_bar method")
            return False
    
    logger.error("Could not find on_bar method in the file")
    return False

def main():
    """Main entry point for the fix script."""
    logger.info("Starting Simple MA Crossover strategy fix")
    
    success = fix_simple_ma_strategy()
    
    if success:
        logger.info("Successfully fixed SimpleMACrossoverStrategy to use configured price_key")
        logger.info("\nIMPORTANT: Run your optimization again to see if it produces varying results:")
        logger.info("python run_quiet_optimization.py --config config/optimization_test.yaml")
    else:
        logger.error("Failed to fix SimpleMACrossoverStrategy")
        
    logger.info("If this fix causes issues, you can restore from the backup created by this script.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())