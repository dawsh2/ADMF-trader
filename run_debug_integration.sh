#!/bin/bash
# Run the fixed debug integration test

set -e  # Exit on error

echo "========== ADMF-Trader Debug Integration Test =========="

# Make scripts executable
chmod +x tests/integration/fixed_debug_integration.py

# Ensure we're using the virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run debug integration test
echo "Running debug integration test..."
python tests/integration/fixed_debug_integration.py

# Check exit code
if [ $? -eq 0 ]; then
    echo "Debug integration test passed!"
else
    echo "Debug integration test failed!"
    exit 1
fi

echo "Debug integration test complete!"
