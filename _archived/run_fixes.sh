#!/bin/bash
# Make the scripts executable
chmod +x run_all_fixes_and_optimize.py
chmod +x run_fixed_optimization.py
chmod +x fix_trade_recording.py

# Run the fix and optimize script
./run_all_fixes_and_optimize.py --config "$1" --verbose
