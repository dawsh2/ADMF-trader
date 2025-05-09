#!/usr/bin/env python
"""
Fix strategy symbols directly
"""

import os
import sys
import logging
import traceback

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_strategy_symbols.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fix_symbols')

def ensure_strategy_has_symbols():
    """Ensure all strategy implementations have default symbols"""
    logger.info("Ensuring all strategy implementations have default symbols")
    
    # Paths to check
    strategy_paths = [
        "src/strategy/implementations/ma_crossover.py",
        "src/strategy/implementations/backup/ma_crossover.py",
        "src/strategy/implementations/backup/ma_crossover_fixed.py"
    ]
    
    for path in strategy_paths:
        if os.path.exists(path):
            fix_strategy_file(path)
        else:
            logger.warning(f"Strategy file not found: {path}")
            
    logger.info("Strategy symbol fixes applied")

def fix_strategy_file(path):
    """Fix a specific strategy file"""
    logger.info(f"Fixing strategy symbols in {path}")
    
    try:
        with open(path, 'r') as f:
            content = f.read()
        
        # Make a backup
        with open(f"{path}.bak.symbols", 'w') as f:
            f.write(content)
            
        # Check if symbols are initialized properly
        if "self.symbols = []" in content or "self.symbols = self.parameters.get('symbols', [])" in content:
            # Add default symbol
            modified_content = content.replace(
                "self.symbols = []", 
                "self.symbols = ['HEAD']  # Default symbol"
            )
            modified_content = modified_content.replace(
                "self.symbols = self.parameters.get('symbols', [])", 
                "self.symbols = self.parameters.get('symbols', ['HEAD'])  # Default symbol"
            )
            
            # Write back the modified content
            with open(path, 'w') as f:
                f.write(modified_content)
                
            logger.info(f"Added default symbol to {path}")
        else:
            # Add a direct init for symbols property
            # Find the __init__ method
            if "def __init__" in content:
                # Insert after the super().__init__ call
                if "super().__init__" in content:
                    modified_content = content.replace(
                        "super().__init__(event_bus, data_handler, name or self.name, parameters)",
                        "super().__init__(event_bus, data_handler, name or self.name, parameters)\n        # Ensure we have default symbols\n        if not hasattr(self, 'symbols') or not self.symbols:\n            self.symbols = ['HEAD']\n        logger.info(f\"Strategy symbols: {self.symbols}\")"
                    )
                else:
                    # Add at the end of __init__
                    modified_content = content.replace(
                        "logger.info(f\"MA Crossover strategy initialized with fast_window={self.fast_window}, \"",
                        "# Ensure we have default symbols\n        if not hasattr(self, 'symbols') or not self.symbols:\n            self.symbols = ['HEAD']\n        logger.info(f\"Strategy symbols: {self.symbols}\")\n\n        logger.info(f\"MA Crossover strategy initialized with fast_window={self.fast_window}, \""
                    )
                
                # Write back the modified content
                with open(path, 'w') as f:
                    f.write(modified_content)
                    
                logger.info(f"Added symbols initialization to {path}")
            else:
                logger.warning(f"Could not find __init__ method in {path}")
    
    except Exception as e:
        logger.error(f"Error fixing {path}: {e}")
        logger.error(traceback.format_exc())

def force_strategy_direct_fix():
    """Force a direct fix by modifying the strategy file used in the error"""
    target_path = "src/strategy/implementations/backup/ma_crossover_fixed.py"
    
    logger.info(f"Applying direct fix to {target_path}")
    
    try:
        if os.path.exists(target_path):
            with open(target_path, 'r') as f:
                content = f.read()
            
            # Make a backup
            with open(f"{target_path}.bak.direct", 'w') as f:
                f.write(content)
            
            # Add a direct symbols initialization right after class definition
            modified_content = content.replace(
                "class MACrossoverStrategy(Strategy):",
                "class MACrossoverStrategy(Strategy):\n    # Add default symbols\n    symbols = ['HEAD']"
            )
            
            # Also modify the __init__ method to set symbols
            modified_content = modified_content.replace(
                "def __init__(self, event_bus, data_handler, name=None, parameters=None):",
                "def __init__(self, event_bus, data_handler, name=None, parameters=None):\n        # Add debug print\n        import logging\n        logger = logging.getLogger(__name__)\n        logger.info(\"Initializing MACrossoverStrategy with default symbols\")"
            )
            
            modified_content = modified_content.replace(
                "super().__init__(event_bus, data_handler, name or self.name, parameters)",
                "super().__init__(event_bus, data_handler, name or self.name, parameters)\n        # Force symbols to be set\n        self.symbols = parameters.get('symbols', ['HEAD'])\n        logger.info(f\"Strategy symbols forced to: {self.symbols}\")"
            )
            
            # Write back the modified content
            with open(target_path, 'w') as f:
                f.write(modified_content)
                
            logger.info(f"Applied direct symbols fix to {target_path}")
        else:
            logger.warning(f"Target file not found: {target_path}")
    
    except Exception as e:
        logger.error(f"Error applying direct fix: {e}")
        logger.error(traceback.format_exc())

def main():
    """Run all symbol fixes"""
    logger.info("Running all strategy symbol fixes")
    
    # Apply general fixes
    ensure_strategy_has_symbols()
    
    # Apply direct fix to the specific file showing in the error
    force_strategy_direct_fix()
    
    logger.info("All symbol fixes applied - now run the optimization again")
    logger.info("python run_final_fixed_optimization.py")

if __name__ == "__main__":
    main()
