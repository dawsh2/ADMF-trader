#!/bin/bash
# Make scripts executable so this can be run by double-clicking
# Run fixed tests with safety measures

set -e  # Exit on error

# Check for required Python packages
echo "Checking Python dependencies..."
required_packages=("pytest" "pytest-cov" "pytest-timeout" "pytest-xdist")
for package in "${required_packages[@]}"; do
    if ! python -c "import $(echo $package | tr '-' '_')" &>/dev/null; then
        echo "Installing missing package: $package"
        pip install "$package"
    fi
done
echo "All dependencies installed!"

# Set executable permissions
chmod +x run_safe_tests.py

# Set up environment
export PYTHONPATH="$PWD:$PYTHONPATH"

# Create logs directory if it doesn't exist
mkdir -p logs

# Run safe tests with color output
./run_safe_tests.py "$@" 2>&1 | tee logs/fixed_tests_$(date +%Y%m%d_%H%M%S).log

# Check exit code
STATUS=${PIPESTATUS[0]}
if [ $STATUS -eq 0 ]; then
    echo "All tests completed successfully!"
    exit 0
else
    echo "Tests failed with status $STATUS"
    exit $STATUS
fi
