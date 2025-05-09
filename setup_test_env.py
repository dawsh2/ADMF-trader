#!/usr/bin/env python3
"""
Set up testing environment for ADMF-Trader.

This script installs all required dependencies and prepares the environment
for running tests without hanging issues.
"""
import os
import sys
import subprocess
import importlib
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("setup")

# Required packages for testing
REQUIRED_PACKAGES = [
    'pytest',
    'pytest-cov',
    'pytest-timeout',
    'pytest-xdist',  # For parallel testing
    'jsonschema',    # For config schema tests
]

def ensure_dependencies():
    """Check and install dependencies if needed."""
    missing = []
    
    print("Checking required dependencies...")
    for package in REQUIRED_PACKAGES:
        try:
            importlib.import_module(package.replace('-', '_'))
            print(f"✓ {package} is installed")
        except ImportError:
            missing.append(package)
            print(f"✗ {package} is missing")
    
    if missing:
        print(f"\nInstalling missing packages: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
            print("All dependencies installed successfully!")
        except Exception as e:
            print(f"Failed to install packages: {e}")
            print("Please install packages manually:")
            print(f"pip install {' '.join(missing)}")
            return False
    else:
        print("\nAll required dependencies are already installed!")
    
    return True

def main():
    """Main entry point."""
    print("\n===== ADMF-Trader Test Environment Setup =====\n")
    
    # Check Python version
    py_version = sys.version.split()[0]
    print(f"Python version: {py_version}")
    
    # Install dependencies
    if not ensure_dependencies():
        print("Failed to install required dependencies")
        return False
    
    # Find print statements that might be causing issues
    print("\nSearching for problematic print statements...")
    find_print_script = os.path.join(os.path.dirname(__file__), "find_print_statements.py")
    if os.path.exists(find_print_script):
        subprocess.run([sys.executable, find_print_script])
    
    print("\nEnvironment setup complete!")
    print("\nRecommended test commands:")
    print("1. Run debug integration test:")
    print("   python run_tests.py --debug-integration")
    print("\n2. Run all tests with safety measures:")
    print("   python run_tests.py")
    print("\n3. Run tests with coverage:")
    print("   python run_tests.py -v --with-coverage")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
