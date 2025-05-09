#!/bin/bash
# Make all scripts executable
chmod +x fix_rule_id.py
chmod +x direct_optimizer_fix.py
chmod +x run_complete_fix.py

# Run the complete fix script
python run_complete_fix.py --config "$1" --verbose
