#!/bin/bash
# Simple script to run tests and capture output

# Set the output file
OUTPUT_FILE="test_results_$(date +%Y%m%d_%H%M%S).txt"

# Run the test
echo "Running tests..."
echo "Output will be saved to $OUTPUT_FILE"

# Run the test and capture output
python test_the_fixes.py > "$OUTPUT_FILE" 2>&1

# Get the exit code
EXIT_CODE=$?

# Print a summary based on exit code
if [ $EXIT_CODE -eq 0 ]; then
    echo "Tests PASSED!"
else
    echo "Tests FAILED with exit code $EXIT_CODE"
    echo "Check $OUTPUT_FILE for details"
fi

# Show the output
echo ""
echo "Test output:"
echo "============"
cat "$OUTPUT_FILE"

# Exit with the same code as the test
exit $EXIT_CODE
