#!/bin/bash
# Make this script executable with: chmod +x run_fixed_system.sh

# Run the fixed system test
echo "Running fixed optimization test..."
python run_fixed_system.py

# Check exit status
if [ $? -eq 0 ]; then
    echo "Test completed successfully!"
else
    echo "Test failed. Please check the logs for errors."
fi
