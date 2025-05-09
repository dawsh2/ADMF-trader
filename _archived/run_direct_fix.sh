#!/bin/bash
# Make the scripts executable
chmod +x direct_optimizer_fix.py
chmod +x run_fixed_reporter.py

# Apply the direct fix
python direct_optimizer_fix.py

# Run the optimization with patched reporter
python run_fixed_reporter.py --config "$1" --verbose
