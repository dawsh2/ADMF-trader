#!/usr/bin/env python
"""
Fix import paths for event_bus across the codebase
"""

import os
import sys
import logging
import re
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_imports.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fix_imports')

def fix_file_imports(file_path, backup=True):
    """Fix import paths in a single file"""
    logger.info(f"Fixing imports in {file_path}")
    
    try:
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Create backup if requested
        if backup:
            backup_path = f"{file_path}.bak.import"
            with open(backup_path, 'w') as f:
                f.write(content)
            logger.info(f"Created backup at {backup_path}")
        
        # Check if the file has incorrect imports
        has_incorrect_imports = False
        
        # Check for src.core.event_bus import pattern
        if re.search(r'from\s+src\.core\.event_bus\s+import', content) or re.search(r'import\s+src\.core\.event_bus', content):
            has_incorrect_imports = True
            logger.info(f"Found incorrect event_bus import in {file_path}")
        
        # If no incorrect imports, skip this file
        if not has_incorrect_imports:
            logger.info(f"No incorrect imports found in {file_path}")
            return False
        
        # Fix the imports
        # Replace src.core.event_bus with src.core.events.event_bus
        modified_content = re.sub(
            r'from\s+src\.core\.event_bus\s+import',
            'from src.core.events.event_bus import',
            content
        )
        modified_content = re.sub(
            r'import\s+src\.core\.event_bus',
            'import src.core.events.event_bus',
            modified_content
        )
        
        # Write the modified content back to the file
        with open(file_path, 'w') as f:
            f.write(modified_content)
        
        logger.info(f"Fixed imports in {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error fixing imports in {file_path}: {e}")
        return False

def find_strategy_files():
    """Find all strategy implementation files that might have incorrect imports"""
    strategy_paths = [
        "src/strategy/implementations",
        "src/strategy/implementations/backup"
    ]
    
    files_to_check = []
    
    for path in strategy_paths:
        if not os.path.exists(path):
            logger.warning(f"Path {path} does not exist")
            continue
        
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    files_to_check.append(os.path.join(root, file))
    
    logger.info(f"Found {len(files_to_check)} strategy files to check")
    return files_to_check

def fix_all_imports():
    """Fix imports in all relevant files"""
    logger.info("Finding files to fix...")
    
    # Find all strategy files
    files_to_check = find_strategy_files()
    
    # Fix imports in each file
    fixed_count = 0
    for file_path in files_to_check:
        if fix_file_imports(file_path):
            fixed_count += 1
    
    logger.info(f"Fixed imports in {fixed_count} files")
    return fixed_count > 0

def create_compatibility_modules():
    """Create compatibility modules to ensure old imports still work"""
    logger.info("Creating compatibility modules")
    
    # Ensure the src/core directory exists
    if not os.path.exists("src/core"):
        logger.error("src/core directory does not exist")
        return False
    
    # Create the event_bus.py compatibility module
    event_bus_path = "src/core/event_bus.py"
    with open(event_bus_path, 'w') as f:
        f.write("""\"\"\"
Compatibility module for event_bus imports.
This is a compatibility shim for code that imports from src.core.event_bus.
\"\"\"

import logging
logger = logging.getLogger(__name__)
logger.warning("Importing from src.core.event_bus is deprecated. Use src.core.events.event_bus instead.")

# Re-export from the correct module
from src.core.events.event_bus import *
""")
    
    logger.info(f"Created compatibility module: {event_bus_path}")
    return True

def main():
    """Fix import paths across the codebase"""
    logger.info("Starting import path fixes...")
    
    # Fix imports in all files
    if fix_all_imports():
        logger.info("Successfully fixed imports in strategy files")
    else:
        logger.warning("No imports were fixed in strategy files")
    
    # Create compatibility modules to ensure old imports still work
    if create_compatibility_modules():
        logger.info("Created compatibility modules")
    else:
        logger.error("Failed to create compatibility modules")
    
    logger.info("Import path fixes completed")
    
    # Instructions for running the optimization
    logger.info("\nNow you can try running optimization again with:")
    logger.info("python main.py optimize --config config/ma_crossover_optimization.yaml")

if __name__ == "__main__":
    main()
