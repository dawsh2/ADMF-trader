#!/usr/bin/env python3
"""
Fix for MA Crossover Signal Grouping issue.

This script addresses the discrepancy between the MA Crossover implementation
and validation script regarding rule_id format and signal group deduplication.

Problem: System generates 54 trades while validation expects 18 trades (3:1 ratio).
Root Cause: rule_id format mismatch preventing proper deduplication.
Solution: Update rule_id format in strategy and ensure proper reset of processed_rule_ids.
"""

import os
import sys
import logging
from datetime import datetime
import shutil
import re

# Set up logging
log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler(f"ma_signal_grouping_fix_{log_timestamp}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ma_signal_grouping_fix")

def backup_file(file_path):
    """Create a backup of a file."""
    backup_path = f"{file_path}.bak"
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup of {file_path} to {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to backup {file_path}: {e}")
        return False

def fix_ma_crossover_strategy():
    """Fix rule_id format in MA Crossover strategy implementation."""
    strategy_file = "src/strategy/implementations/ma_crossover.py"
    
    # Backup the file
    if not backup_file(strategy_file):
        return False
    
    try:
        # Read the file
        with open(strategy_file, 'r') as f:
            content = f.read()
        
        # Check if we need to fix the rule_id format
        if "rule_id = f\"{self.name}_{group_id}\"" in content:
            logger.info("Found incorrect rule_id format, fixing...")
            
            # Replace the rule_id assignment with the correct format
            content = content.replace(
                "rule_id = f\"{self.name}_{group_id}\"",
                "direction_name = \"BUY\" if signal_value == 1 else \"SELL\"\n            rule_id = f\"{self.name}_{symbol}_{direction_name}_group_{group_id}\""
            )
            
            logger.info("Updated rule_id format in MA Crossover strategy")
        elif "direction_name = \"BUY\" if signal_value == 1 else \"SELL\"" in content:
            logger.info("rule_id format appears to be already fixed")
        else:
            logger.warning("Could not find expected rule_id format pattern in strategy file")
            
            # Advanced pattern matching to find and replace the rule_id line
            rule_id_pattern = re.compile(r'(rule_id\s*=\s*f["\'].*?["\'])')
            if rule_id_pattern.search(content):
                # Find the rule_id line and grab the indentation level
                old_line = rule_id_pattern.search(content).group(0)
                indentation = re.match(r'^(\s*)', old_line).group(1)
                
                # Create new lines with correct format
                new_lines = f"{indentation}direction_name = \"BUY\" if signal_value == 1 else \"SELL\"\n{indentation}rule_id = f\"{self.name}_{{symbol}}_{{direction_name}}_group_{{group_id}}\""
                
                # Replace the old line with new lines
                content = rule_id_pattern.sub(new_lines, content)
                logger.info(f"Applied regex-based rule_id format fix: {old_line} -> {new_lines}")
        
        # Write the updated content
        with open(strategy_file, 'w') as f:
            f.write(content)
        
        logger.info("MA Crossover strategy rule_id format fix applied")
        return True
    except Exception as e:
        logger.error(f"Error fixing MA Crossover strategy: {e}")
        return False

def fix_risk_manager_reset():
    """Fix risk manager to properly reset processed_rule_ids."""
    risk_manager_file = "src/risk/managers/simple.py"
    
    # Backup the file
    if not backup_file(risk_manager_file):
        return False
    
    try:
        # Read the file
        with open(risk_manager_file, 'r') as f:
            content = f.read()
        
        # Check if processed_rule_ids is properly cleared in reset method
        reset_method = re.search(r'def reset\(self\):(.*?)def', content, re.DOTALL)
        
        if reset_method:
            reset_body = reset_method.group(1)
            
            if "self.processed_rule_ids.clear()" in reset_body:
                logger.info("Risk manager already properly resets processed_rule_ids")
            else:
                # Add processed_rule_ids.clear() to reset method
                new_reset_body = reset_body.replace(
                    "super().reset()",
                    "super().reset()\n        # CRITICAL FIX: Ensure processed_rule_ids is emptied on reset\n        logger.info(f\"Clearing {len(self.processed_rule_ids)} processed rule IDs\")\n        self.processed_rule_ids.clear()"
                )
                content = content.replace(reset_body, new_reset_body)
                logger.info("Added code to clear processed_rule_ids in risk manager reset method")
        else:
            logger.error("Could not find reset method in risk manager")
            return False
        
        # Write the updated content
        with open(risk_manager_file, 'w') as f:
            f.write(content)
        
        logger.info("Risk manager reset method fix applied")
        return True
    except Exception as e:
        logger.error(f"Error fixing risk manager reset method: {e}")
        return False

def fix_risk_manager_on_signal():
    """Add more detailed logging to risk manager on_signal method for debugging."""
    risk_manager_file = "src/risk/managers/simple.py"
    
    # Skip backup as we already did it in the previous function
    
    try:
        # Read the file
        with open(risk_manager_file, 'r') as f:
            content = f.read()
        
        # Add more robust rule_id extraction and logging
        if "def on_signal(self, signal_event):" in content:
            # Check if extract rule_id and logging is already present
            if "Extracted rule_id from signal:" in content:
                logger.info("Risk manager already has enhanced rule_id extraction and logging")
            else:
                # Add rule_id extraction code
                on_signal_pattern = re.compile(r'def on_signal\(self, signal_event\):(.*?)try:', re.DOTALL)
                if on_signal_pattern.search(content):
                    on_signal_start = on_signal_pattern.search(content).group(1)
                    
                    # Extract indentation
                    indentation_match = re.search(r'(\s+)# ', on_signal_start)
                    if indentation_match:
                        indentation = indentation_match.group(1)
                    else:
                        indentation = "        "  # Default indentation
                    
                    # Create enhanced extraction and logging code
                    enhanced_code = f"{indentation}# 1. Extract rule_id from signal event\n"
                    enhanced_code += f"{indentation}rule_id = None\n"
                    enhanced_code += f"{indentation}if hasattr(signal_event, 'data') and isinstance(signal_event.data, dict):\n"
                    enhanced_code += f"{indentation}    rule_id = signal_event.data.get('rule_id')\n"
                    enhanced_code += f"{indentation}    \n"
                    enhanced_code += f"{indentation}    # Log what we found to help with debugging\n"
                    enhanced_code += f"{indentation}    logger.info(f\"Extracted rule_id from signal: {{rule_id}}\")\n"
                    enhanced_code += f"{indentation}\n"
                    enhanced_code += f"{indentation}# CRITICAL FIX: Do the rule_id check first, before any other check\n"
                    enhanced_code += f"{indentation}# 2. MOST IMPORTANT CHECK: If rule_id exists and was already processed, reject immediately\n"
                    enhanced_code += f"{indentation}if rule_id and rule_id in self.processed_rule_ids:\n"
                    enhanced_code += f"{indentation}    logger.info(f\"REJECTING: Signal with rule_id {{rule_id}} already processed\")\n"
                    enhanced_code += f"{indentation}    # Print all processed rule_ids for debugging\n"
                    enhanced_code += f"{indentation}    logger.info(f\"All processed rule_ids: {{sorted(list(self.processed_rule_ids))}}\")\n"
                    enhanced_code += f"{indentation}    # Mark event as consumed to prevent other handlers from processing it\n"
                    enhanced_code += f"{indentation}    signal_event.consumed = True\n"
                    enhanced_code += f"{indentation}    logger.info(f\"Signal with rule_id {{rule_id}} marked as consumed to stop propagation\")\n"
                    enhanced_code += f"{indentation}    # No need to process further\n"
                    enhanced_code += f"{indentation}    return None\n"
                    enhanced_code += f"{indentation}    \n"
                    enhanced_code += f"{indentation}# Debug log the rule_id more prominently \n"
                    enhanced_code += f"{indentation}if rule_id:\n"
                    enhanced_code += f"{indentation}    logger.info(f\"PROCESSING NEW SIGNAL with rule_id: {{rule_id}}\")\n"
                    enhanced_code += f"{indentation}    # Check if rule_id contains 'group' to verify correct format\n"
                    enhanced_code += f"{indentation}    if 'group' in rule_id:\n"
                    enhanced_code += f"{indentation}        logger.info(f\"CONFIRMED: Signal has proper group-based rule_id format\")\n"
                    enhanced_code += f"{indentation}    else:\n"
                    enhanced_code += f"{indentation}        logger.warning(f\"WARNING: Signal rule_id does not use group-based format: {{rule_id}}\")\n"
                    
                    # Replace the start of on_signal method with enhanced code
                    new_on_signal_start = on_signal_start.replace(
                        f"{indentation}# CRITICAL DEBUG: Log the incoming signal to help diagnose issues\n{indentation}logger.info(f\"Received signal event: {{signal_event.get_id() if hasattr(signal_event, 'get_id') else 'unknown'}}\")\n{indentation}\n{indentation}# Get unique ID for deduplication\n{indentation}signal_id = signal_event.get_id()\n{indentation}",
                        f"{indentation}# CRITICAL DEBUG: Log the incoming signal to help diagnose issues\n{indentation}logger.info(f\"Received signal event: {{signal_event.get_id() if hasattr(signal_event, 'get_id') else 'unknown'}}\")\n{indentation}\n{indentation}# Get unique ID for deduplication\n{indentation}signal_id = signal_event.get_id()\n{indentation}\n{enhanced_code}"
                    )
                    
                    content = content.replace(on_signal_start, new_on_signal_start)
                    logger.info("Added enhanced rule_id extraction and logging to risk manager")
        
        # Ensure rule_id is properly added to processed set
        if "# CRITICAL FIX: Add rule_id to processed set IMMEDIATELY" not in content:
            # Find the right location
            in_progress_pattern = re.compile(r'# Mark as in progress immediately\s+self\.events_in_progress\.add\(signal_id\)\s+')
            if in_progress_pattern.search(content):
                # Add rule_id processing right after marking as in progress
                content = in_progress_pattern.sub(
                    "# Mark as in progress immediately\n        self.events_in_progress.add(signal_id)\n        \n        # CRITICAL FIX: Add rule_id to processed set IMMEDIATELY to prevent race conditions\n        # This must happen before we do any processing that could generate events\n        if rule_id:\n            logger.info(f\"PROCESSING: Adding rule_id {rule_id} to processed set\")\n            self.processed_rule_ids.add(rule_id)\n        \n        ",
                    content
                )
                logger.info("Added immediate rule_id processing in on_signal method")
        
        # Write the updated content
        with open(risk_manager_file, 'w') as f:
            f.write(content)
        
        logger.info("Risk manager on_signal method fix applied")
        return True
    except Exception as e:
        logger.error(f"Error enhancing risk manager on_signal method: {e}")
        return False

def create_validation_script():
    """Create a validation script to verify the fix."""
    validation_script = "verify_signal_grouping_fix.sh"
    
    try:
        # Create validation script
        content = """#!/bin/bash
# Validation script for signal grouping fix

echo "====================================================="
echo "VALIDATING MA CROSSOVER SIGNAL GROUPING FIX"
echo "====================================================="

# Run the validation script to get expected signal count
echo "Running validation script to determine expected signal count..."
python ma_validation_fixed_groups.py > validation_output.log

# Extract expected signal group count
expected_count=$(grep "Signal direction changes:" validation_output.log | awk '{print $4}')
echo "Expected signal groups from validation: $expected_count"

# Run the fixed implementation
echo "Running fixed implementation..."
python run_fixed_ma_crossover_v2.py > fixed_output.log

# Extract actual trade count
actual_count=$(grep "Trades executed:" fixed_output.log | grep -oE '[0-9]+')
echo "Actual trades from implementation: $actual_count"

# Compare results
echo "====================================================="
echo "RESULTS"
echo "====================================================="
echo "Expected count: $expected_count"
echo "Actual count: $actual_count"

if [ "$expected_count" == "$actual_count" ]; then
    echo "✅ SUCCESS: Signal grouping fix verified! Counts match."
else
    echo "❌ FAILURE: Signal counts still do not match."
    echo "    Expected: $expected_count"
    echo "    Actual: $actual_count"
    echo ""
    echo "Examining logs for clues..."
    
    # Check rule_id formats
    echo ""
    echo "Validation rule_id format:"
    grep -o "rule_id = f\"[^\"]*\"" validation_output.log | head -1
    
    echo ""
    echo "Implementation rule_id format:"
    grep "RULE ID CREATED:" fixed_output.log | head -1
    
    # Check for rejected signals
    echo ""
    echo "Checking for rejected signals:"
    grep "REJECTING: Signal with rule_id" fixed_output.log | wc -l
fi

echo "====================================================="
echo "Detailed logs saved to:"
echo "- validation_output.log"
echo "- fixed_output.log"
echo "====================================================="
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
    """Apply all fixes for the MA Crossover Signal Grouping issue."""
    print("====================================================")
    print("MA CROSSOVER SIGNAL GROUPING FIX")
    print("====================================================")
    print("This script will apply the following fixes:")
    print("1. Update rule_id format in MA Crossover strategy")
    print("2. Ensure proper reset of processed_rule_ids")
    print("3. Add enhanced rule_id logging for debugging")
    print("====================================================")
    
    # Fix MA Crossover Strategy rule_id format
    print("\nFixing MA Crossover strategy rule_id format...")
    if fix_ma_crossover_strategy():
        print("✅ MA Crossover strategy fix applied successfully!")
    else:
        print("❌ Failed to fix MA Crossover strategy")
        return False
    
    # Fix Risk Manager reset method
    print("\nFixing Risk Manager reset method...")
    if fix_risk_manager_reset():
        print("✅ Risk Manager reset method fix applied successfully!")
    else:
        print("❌ Failed to fix Risk Manager reset method")
        return False
    
    # Enhance Risk Manager on_signal method
    print("\nEnhancing Risk Manager on_signal method...")
    if fix_risk_manager_on_signal():
        print("✅ Risk Manager on_signal enhancements applied successfully!")
    else:
        print("❌ Failed to enhance Risk Manager on_signal method")
        return False
    
    # Create validation script
    print("\nCreating validation script...")
    if create_validation_script():
        print("✅ Validation script created successfully!")
    else:
        print("❌ Failed to create validation script")
        return False
    
    # Print success message
    print("\n====================================================")
    print("MA CROSSOVER SIGNAL GROUPING FIX COMPLETED!")
    print("====================================================")
    print("To verify the fix, run:")
    print("  ./verify_signal_grouping_fix.sh")
    print("\nThe fix should reduce the number of trades from 54 to 18,")
    print("matching the validation expectation.")
    print("====================================================")
    
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
