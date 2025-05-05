#!/bin/bash
# Run trade tracking verification test

# Ensure we're in the project root directory
cd "$(dirname "$0")"

# Make the verification script executable
chmod +x verify_trade_tracking.py

# Run the verification script
echo "Running trade tracking verification test..."
python3 verify_trade_tracking.py config/mini_test.yaml

# Check exit code
if [ $? -eq 0 ]; then
  echo "Verification test completed successfully."
else
  echo "Verification test failed."
  exit 1
fi
