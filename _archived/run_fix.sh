#!/bin/bash
# Run the optimization with position management fixes

# Change to the script directory
cd "$(dirname "$0")"

# Activate virtual environment if present
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Make the script executable
chmod +x run_fixed_optimization.py

# Run the optimization
echo "Running optimization with position management fixes..."
python run_fixed_optimization.py

echo "Done! Check the log file for detailed output."
