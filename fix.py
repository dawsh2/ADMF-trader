#!/usr/bin/env python3
"""
Quick fix script for MA Crossover Signal Grouping issue.

This script directly applies the required changes to fix the rule_id format
and reset functionality issues.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("quick_fix")

def fix_ma_crossover_rule_id():
    """Fix the rule_id format in MA Crossover strategy."""
    file_path = "src/strategy/implementations/ma_crossover.py"
    
    try:
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if fix is needed
        if "rule_id = f\"{self.name}_{group_id}\"" in content:
            # Apply the fix
            fixed_content = content.replace(
                "rule_id = f\"{self.name}_{group_id}\"",
                "direction_name = \"BUY\" if signal_value == 1 else \"SELL\"\n            rule_id = f\"{self.name}_{symbol}_{direction_name}_group_{group_id}\""
            )
            
            # Write the fixed content
            with open(file_path, 'w') as f:
                f.write(fixed_content)
                
            logger.info(f"✅ Fixed rule_id format in {file_path}")
            return True
        else:
            logger.info(f"ℹ️ No fix needed for rule_id format in {file_path}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to fix rule_id format in {file_path}: {e}")
        return False

def fix_risk_manager_reset():
    """Fix the reset method in SimpleRiskManager."""
    file_path = "src/risk/managers/simple.py"
    
    try:
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if fix is needed
        if "def reset(self):" in content and "self.processed_rule_ids.clear()" not in content:
            # Find the reset method
            reset_start = content.find("def reset(self):")
            if reset_start == -1:
                logger.warning(f"⚠️ Could not find reset method in {file_path}")
                return False
                
            # Find where to insert the fix
            super_reset = content.find("super().reset()", reset_start)
            if super_reset == -1:
                logger.warning(f"⚠️ Could not find super().reset() call in {file_path}")
                return False
                
            # Insert the fix after super().reset()
            fixed_content = content[:super_reset + len("super().reset()")] + "\n        logger.info(f\"Clearing {len(self.processed_rule_ids)} processed rule IDs\")\n        self.processed_rule_ids.clear()" + content[super_reset + len("super().reset()"):]
            
            # Write the fixed content
            with open(file_path, 'w') as f:
                f.write(fixed_content)
                
            logger.info(f"✅ Fixed reset method in {file_path}")
            return True
        else:
            logger.info(f"ℹ️ No fix needed for reset method in {file_path}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to fix reset method in {file_path}: {e}")
        return False

def main():
    """Apply the quick fix for MA Crossover Signal Grouping."""
    logger.info("🔧 Applying quick fix for MA Crossover Signal Grouping...")
    
    # Fix MA Crossover rule_id format
    if not fix_ma_crossover_rule_id():
        logger.error("❌ Failed to fix MA Crossover rule_id format")
        return False
        
    # Fix SimpleRiskManager reset method
    if not fix_risk_manager_reset():
        logger.error("❌ Failed to fix SimpleRiskManager reset method")
        return False
        
    logger.info("✅ Quick fix successfully applied!")
    logger.info("To verify, run: python run_fixed_ma_crossover_v2.py")
    
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
