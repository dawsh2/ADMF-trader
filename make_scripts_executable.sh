#!/bin/bash
# Make all scripts executable

echo "Making scripts executable..."

# Make debug and test scripts executable
chmod +x run_fixed_tests.sh run_safe_tests.py find_fixed_event_print.py setup_and_run_tests.sh run_debug_integration.sh

# Make debugging integration test executable
chmod +x tests/integration/fixed_debug_integration.py

# Make this script executable for future use
chmod +x "$0"

echo "All scripts made executable!"
