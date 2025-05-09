#!/bin/bash
# Script to run optimization tests with simplified parameters for troubleshooting

echo "Running basic optimization test (skipping train/test splitting)"
python optimize_strategy.py --config config/head_test.yaml --strategy simple_ma_crossover --param-file config/parameter_spaces/ma_crossover_params.yaml --skip-train-test --verbose

echo ""
echo "If the above test succeeds, you can try the full test with train/test splitting:"
echo "python optimize_strategy.py --config config/head_test.yaml --strategy simple_ma_crossover --param-file config/parameter_spaces/ma_crossover_params.yaml"

echo ""
echo "Or you can run the simple test script:"
echo "python test_optimization.py"
