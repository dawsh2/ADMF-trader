#!/bin/bash
# Make the script executable
chmod +x run_simple_fix.py

# Run the simple fix with the specified config file
python run_simple_fix.py --config "$1" --verbose
