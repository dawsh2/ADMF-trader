#!/bin/bash
# Run the debug script to analyze position management

# Change to the script directory
cd "$(dirname "$0")"

# Activate virtual environment if present
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Make the debug script executable
chmod +x debug_positions.py

# Run the debug script
echo "Running debug script..."
python debug_positions.py --config config/ma_crossover_optimization.yaml

echo "Done! Check debug_positions.log for detailed output."
