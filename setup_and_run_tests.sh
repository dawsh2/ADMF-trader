#!/bin/bash
# Setup and run the fixed tests

set -e  # Exit on error

echo "========== ADMF-Trader Test Setup and Run =========="
echo "Setting up environment and running tests with safety measures..."

# Make scripts executable
chmod +x run_fixed_tests.sh run_safe_tests.py find_fixed_event_print.py

# Also make this script executable for future use
chmod +x "$0"

# Ensure we're using the virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install required Python packages
echo "Installing required Python packages..."
pip install pytest pytest-cov pytest-timeout pytest-xdist

# Find debug prints that might be causing issues
echo "Scanning for debug print statements..."
python find_fixed_event_print.py

# Run safe tests
echo "Running tests with safety measures..."
./run_fixed_tests.sh tests/integration/test_safe_integration.py

echo "Test setup and run complete!"
