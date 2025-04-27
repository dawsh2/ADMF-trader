#!/usr/bin/env python
"""
ADMF-Trader Project Cleanup Script

This script cleans up the project directory by:
1. Moving data files to the data directory
2. Removing temporary and debug files
3. Removing obsolete run scripts now replaced by main.py
"""
import os
import shutil
import sys
from pathlib import Path


def main():
    """Clean up the project directory."""
    # Get the project root directory
    root_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Create an archive directory (just in case we need to recover files)
    archive_dir = root_dir / "_archived"
    os.makedirs(archive_dir, exist_ok=True)
    
    # Ensure the data directory exists
    data_dir = root_dir / "data"
    os.makedirs(data_dir, exist_ok=True)
    
    # Files to keep in the root directory
    files_to_keep = [
        "main.py",
        "README.md",
        "README_MAIN.md",
        "README_REGIME_ENSEMBLE.md",
        ".gitignore",  # Keep Git files
        "cleanup.py",  # This script
    ]
    
    # Directories to keep in the root directory
    dirs_to_keep = [
        ".git",
        "config",
        "data",
        "docs",
        "examples",
        "src",
        "test_data",
        "validation_data",
        "results",
        "_archived",
    ]
    
    # Data files to move to data directory
    data_files = [
        "SPY250506P00551000_1min.csv",
        "SPY250507C00551000_1min.csv",
        "SPY250508C00551000_1min.csv",
        "SPY_1min.csv",
    ]
    
    # Move data files
    print("Moving data files to data directory...")
    for filename in data_files:
        src_path = root_dir / filename
        if src_path.exists():
            dst_path = data_dir / filename
            try:
                shutil.move(src_path, dst_path)
                print(f"  Moved {filename} to data directory")
            except Exception as e:
                print(f"  Error moving {filename}: {e}")
    
    # Remove directories not in the keep list
    print("\nCleaning up directories...")
    for item in root_dir.iterdir():
        if item.is_dir() and item.name not in dirs_to_keep:
            try:
                if item.name == "__pycache__":
                    shutil.rmtree(item)
                    print(f"  Removed {item.name}/")
                else:
                    # Archive other directories
                    dst_path = archive_dir / item.name
                    shutil.move(item, dst_path)
                    print(f"  Archived {item.name}/ -> _archived/{item.name}/")
            except Exception as e:
                print(f"  Error processing directory {item.name}: {e}")
    
    # Remove files not in the keep list
    print("\nCleaning up files...")
    for item in root_dir.iterdir():
        if item.is_file() and item.name not in files_to_keep:
            # Special case for .DS_Store (macOS system file)
            if item.name == ".DS_Store":
                try:
                    os.remove(item)
                    print(f"  Removed {item.name}")
                except Exception as e:
                    print(f"  Error removing {item.name}: {e}")
            else:
                try:
                    # Archive the file
                    dst_path = archive_dir / item.name
                    shutil.move(item, dst_path)
                    print(f"  Archived {item.name} -> _archived/{item.name}")
                except Exception as e:
                    print(f"  Error archiving {item.name}: {e}")
    
    # Special case: also save a copy of generate_multi_regime_data.py for reference
    try:
        src_path = archive_dir / "generate_multi_regime_data.py"
        if src_path.exists():
            dst_path = root_dir / "examples" / "generate_multi_regime_data.py"
            shutil.copy2(src_path, dst_path)
            print("\nSaved a copy of generate_multi_regime_data.py to examples/ for reference")
    except Exception as e:
        print(f"Error saving reference copy: {e}")
    
    print("\nCleanup complete!")
    print(f"Archived files are available in {archive_dir} if needed.")
    print("\nThe project now has a cleaner structure with main.py as the unified entry point.")


if __name__ == "__main__":
    if input("This will reorganize your project files. Continue? (y/n): ").lower() == "y":
        main()
    else:
        print("Operation cancelled.")
        sys.exit(0)
