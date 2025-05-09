#!/bin/bash
# Comprehensive troubleshooting script for ADMF-Trader optimization

# Make all scripts executable
chmod +x *.py
chmod +x *.sh

echo "=============================================="
echo "ADMF-Trader Optimization Troubleshooting Tool"
echo "=============================================="
echo ""

# Step 1: Run debug script to examine strategy factory
echo "Step 1: Running debug script to examine strategy factory..."
echo "=============================================="
python debug_factory.py

echo ""
echo "=============================================="
echo "Step 2: Testing direct optimization approach..."
echo "=============================================="
python manual_optimize.py

echo ""
echo "=============================================="
echo "Step 3: Testing main optimization script with debug flags..."
echo "=============================================="
python optimize_strategy.py --config config/head_test.yaml --strategy simple_ma_crossover --param-file config/parameter_spaces/ma_crossover_params.yaml --skip-train-test --verbose

echo ""
echo "=============================================="
echo "Troubleshooting Complete"
echo "=============================================="

echo ""
echo "If all steps failed, try the following:"
echo "1. Check the strategy implementation files:"
echo "   find /Users/daws/ADMF-trader -name \"*.py\" -exec grep -l \"MovingAverageCrossover\" {} \\;"
echo ""
echo "2. Examine the container configuration:"
echo "   python -c \"from src.core.system_bootstrap import Bootstrap; b = Bootstrap(['config/head_test.yaml']); c, _ = b.setup(); print('Container objects:', [k for k in c._container.keys()])\""
echo ""
echo "3. Try the simple test script:"
echo "   python test_optimization.py"
