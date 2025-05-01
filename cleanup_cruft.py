#!/usr/bin/env python
"""
Cleanup script to remove unused/cruft files from the ADMF-trader system.
"""
import os
import shutil
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def remove_file(path):
    """Remove a file if it exists and log the action."""
    if os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"Removed file: {path}")
            return True
        except Exception as e:
            logger.error(f"Error removing file {path}: {e}")
            return False
    else:
        logger.warning(f"File not found, already removed: {path}")
        return True

def remove_directory(path):
    """Remove a directory if it exists and log the action."""
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            logger.info(f"Removed directory: {path}")
            return True
        except Exception as e:
            logger.error(f"Error removing directory {path}: {e}")
            return False
    else:
        logger.warning(f"Directory not found, already removed: {path}")
        return True

def clean_pycache(directory):
    """Clean __pycache__ directories in the given directory."""
    for root, dirs, files in os.walk(directory):
        for d in dirs:
            if d == "__pycache__":
                pycache_path = os.path.join(root, d)
                logger.info(f"Cleaning __pycache__ directory: {pycache_path}")
                try:
                    for f in os.listdir(pycache_path):
                        # Only remove specific cruft-related cache files
                        cruft_patterns = [
                            "direct_signal_processor",
                            "signal_deduplication_filter",
                            "signal_management_service",
                            "signal_preprocessor",
                            "event_bus_patch",
                            "deduplication_setup"
                        ]
                        if any(pattern in f for pattern in cruft_patterns):
                            file_path = os.path.join(pycache_path, f)
                            os.remove(file_path)
                            logger.info(f"Removed __pycache__ file: {file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning __pycache__ directory {pycache_path}: {e}")

def main():
    """Main function to clean up cruft files."""
    # Project root directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Files to remove (relative to project root)
    files_to_remove = [
        # Signal processing cruft
        "src/core/events/direct_signal_processor.py",
        "src/core/events/signal_deduplication_filter.py",
        "src/core/events/signal_management_service.py",
        "src/core/events/signal_preprocessor.py",
        "src/core/events/event_bus_patch.py",
        "src/core/bootstrap/deduplication_setup.py",
    ]
    
    logger.info("Starting cleanup process...")
    
    # Remove files
    for rel_path in files_to_remove:
        full_path = os.path.join(root_dir, rel_path)
        remove_file(full_path)
    
    # Clean __pycache__ directories
    clean_pycache(os.path.join(root_dir, "src"))
    
    logger.info("Cleanup complete. All cruft files removed.")
    
    # Provide guidance on what to do next
    print("\n" + "="*80)
    print("CLEANUP COMPLETE")
    print("="*80)
    print("The following cruft files have been removed:")
    for f in files_to_remove:
        print(f"  - {f}")
    print("\nYou should now be able to run the application without errors.")
    print("Try: python main.py --config config/mini_test.yaml")
    print("="*80)

if __name__ == "__main__":
    main()
