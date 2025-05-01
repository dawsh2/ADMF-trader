#!/usr/bin/env python3
"""
Fix for rule_id format discrepancy in MA Crossover strategy.

This script applies a targeted fix to ensure that the rule_id format in
the strategy implementation matches the format expected by the validation.
"""

import os
import sys
import re
import logging
from datetime import datetime
import shutil

# Set up logging
log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler(f"rule_id_format_fix_{log_timestamp}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("rule_id_format_fix")

def backup_file(file_path):
    """Create a backup of a file."""
    backup_path = f"{file_path}.bak.{log_timestamp}"
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup of {file_path} to {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to backup {file_path}: {e}")
        return False

def fix_strategy_rule_id_format():
    """Fix rule_id format in MA Crossover strategy."""
    strategy_file = "/Users/daws/ADMF-trader/src/strategy/implementations/ma_crossover.py"
    
    # Backup the file
    if not backup_file(strategy_file):
        return False
    
    try:
        # Read the file
        with open(strategy_file, 'r') as f:
            content = f.read()
        
        # Look for the rule_id creation code
        rule_id_pattern = re.compile(r'rule_id = (f".+?")')
        rule_id_match = rule_id_pattern.search(content)
        
        if rule_id_match:
            current_format = rule_id_match.group(1)
            logger.info(f"Current rule_id format: {current_format}")
            
            # Check if it's already in the correct format
            if "_{symbol}_" in current_format and "_group_" in current_format:
                logger.info("Rule ID format is already correct")
                return True
            
            # Fix the rule_id format to match validation
            new_format = 'f"{self.name}_{symbol}_{direction_name}_group_{group_id}"'
            content = rule_id_pattern.sub(f'rule_id = {new_format}', content)
            
            logger.info(f"New rule_id format: {new_format}")
            
            # Write the updated content
            with open(strategy_file, 'w') as f:
                f.write(content)
            
            logger.info("Updated rule_id format in strategy implementation")
            return True
        else:
            logger.error("Could not find rule_id creation in strategy file")
            return False
    except Exception as e:
        logger.error(f"Error fixing strategy rule_id format: {e}")
        return False

def fix_run_script():
    """Fix run script to work with new rule_id format."""
    run_script = "/Users/daws/ADMF-trader/run_fixed_ma_crossover_v2.py"
    
    # Backup the file
    if not backup_file(run_script):
        return False
    
    try:
        # Read the file
        with open(run_script, 'r') as f:
            content = f.read()
        
        # Add code to clear processed_rule_ids on reset
        reset_pattern = re.compile(r'def reset\(self\):(.*?)super\(\)\.reset\(\)', re.DOTALL)
        if reset_pattern.search(content):
            logger.info("Found reset method, ensuring processed_rule_ids are cleared")
            if "processed_rule_ids.clear()" not in content:
                content = content.replace(
                    "super().reset()",
                    "super().reset()\n        logger.info('Clearing processed rule IDs')\n        self.processed_rule_ids.clear()"
                )
                logger.info("Added code to clear processed_rule_ids on reset")
        
        # Write the updated content
        with open(run_script, 'w') as f:
            f.write(content)
        
        logger.info("Updated run script")
        return True
    except Exception as e:
        logger.error(f"Error fixing run script: {e}")
        return False

def fix_validation_script():
    """Ensure validation script's rule_id format matches implementation."""
    validation_script = "/Users/daws/ADMF-trader/ma_validation_fixed_groups.py"
    
    # Backup the file
    if not backup_file(validation_script):
        return False
    
    try:
        # Read the file
        with open(validation_script, 'r') as f:
            content = f.read()
        
        # Look for rule_id generation code
        rule_id_pattern = re.compile(r'rule_id = f"([^"]+)"')
        rule_id_match = rule_id_pattern.search(content)
        
        if rule_id_match:
            current_format = rule_id_match.group(1)
            logger.info(f"Current validation rule_id format: {current_format}")
            
            # Ensure symbol is correctly defined
            if "symbol = " not in content:
                content = content.replace(
                    "def main():",
                    "def main():\n    # Define symbol for rule_id\n    global symbol\n    symbol = \"MINI\"\n"
                )
                logger.info("Added symbol definition to validation script")
            
            # Check if rule_id format matches strategy
            if "ma_crossover_MINI_" in current_format and not "ma_crossover_{symbol}_" in current_format:
                # Fix rule_id format to use symbol variable
                content = content.replace(
                    'rule_id = f"ma_crossover_MINI_', 
                    'rule_id = f"ma_crossover_{symbol}_'
                )
                logger.info("Updated rule_id format in validation script to use symbol variable")
            
            # Write the updated content
            with open(validation_script, 'w') as f:
                f.write(content)
            
            logger.info("Updated validation script")
            return True
        else:
            logger.error("Could not find rule_id creation in validation script")
            return False
    except Exception as e:
        logger.error(f"Error fixing validation script: {e}")
        return False

def create_simple_validation_script():
    """Create a simple validation script to check signal counts."""
    validation_script = "/Users/daws/ADMF-trader/validate_rule_id_match.sh"
    
    try:
        # Create the script
        content = """#!/bin/bash
# Simple validation script to verify rule_id format match

echo "==============================================="
echo "VALIDATING RULE ID FORMAT MATCH"
echo "==============================================="

# Run rule_id format test
echo "Running rule_id format test..."
python test_rule_id_format.py

# Run validation and implementation
echo "Running validation..."
python ma_validation_fixed_groups.py > validation_output.log
echo "Running implementation..."
python run_fixed_ma_crossover_v2.py > implementation_output.log

# Check rule_id formats
echo "Checking rule_id formats..."
grep "rule_id" validation_output.log | head -n 5
grep "rule_id" implementation_output.log | head -n 5

# Compare signal counts
validation_count=$(grep "Signal direction changes:" validation_output.log | awk '{print $4}')
implementation_count=$(grep "Trades executed:" implementation_output.log | awk '{print $3}')

echo "==============================================="
echo "RESULTS"
echo "==============================================="
echo "Validation signal count: $validation_count"
echo "Implementation trade count: $implementation_count"

if [ "$validation_count" == "$implementation_count" ]; then
    echo "SUCCESS: Signal counts match!"
else
    echo "FAILURE: Signal counts do not match!"
fi
"""
        
        with open(validation_script, 'w') as f:
            f.write(content)
        
        # Make executable
        os.chmod(validation_script, 0o755)
        
        logger.info(f"Created validation script: {validation_script}")
        return True
    except Exception as e:
        logger.error(f"Error creating validation script: {e}")
        return False

def main():
    """Apply all rule_id format fixes."""
    logger.info("Starting rule_id format fix")
    
    # Fix MA Crossover strategy
    if not fix_strategy_rule_id_format():
        logger.error("Failed to fix strategy rule_id format")
        return False
    
    # Fix run script
    if not fix_run_script():
        logger.error("Failed to fix run script")
        return False
    
    # Fix validation script
    if not fix_validation_script():
        logger.error("Failed to fix validation script")
        return False
    
    # Create simple validation script
    if not create_simple_validation_script():
        logger.error("Failed to create validation script")
        return False
    
    logger.info("Rule ID format fix completed successfully")
    print("\nRule ID format fix complete. Run ./validate_rule_id_match.sh to verify.")
    
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
