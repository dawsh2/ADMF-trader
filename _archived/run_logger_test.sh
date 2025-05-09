#!/bin/bash
# Script to run the logger fix verification tests
# Make this script executable with: chmod +x run_logger_test.sh

echo "Running logger fix verification tests..."
python test_logger_fixes.py

# Check exit status
if [ $? -eq 0 ]; then
    echo "Test script completed successfully!"
else
    echo "Test script encountered errors. Please check the logs."
fi
