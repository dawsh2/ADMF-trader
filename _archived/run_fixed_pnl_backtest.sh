#!/bin/bash
# Make scripts executable
chmod +x test_pnl_consistency.py
chmod +x run_all_fixes.py
# Script to run the PnL consistency test

# Set up Python environment (if needed)
# source venv/bin/activate

# Run the test
python test_pnl_consistency.py --config config/ma_crossover_optimization.yaml

# Check the exit code
if [ $? -eq 0 ]; then
    echo "Test completed successfully!"
else
    echo "Test failed. Check the logs for details."
fi
