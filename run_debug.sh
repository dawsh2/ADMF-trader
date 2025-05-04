#!/bin/bash
# Run the debug script to see detailed output

echo "Running MA strategy debug script..."
python debug_ma_strategy.py > ma_debug_output.txt 2>&1
DEBUG_RESULT=$?

echo "Debug script exited with code $DEBUG_RESULT"
echo "Debug output saved to ma_debug_output.txt"

# Show the beginning of the output
echo ""
echo "Beginning of debug output:"
echo "=========================="
head -n 30 ma_debug_output.txt

echo ""
echo "End of debug output snippet"
echo "=========================="
echo "To see full output, check ma_debug_output.txt"

# Run the main test script with the fixes
echo ""
echo "Running main test script..."
python test_the_fixes.py
TEST_RESULT=$?

echo "Test script exited with code $TEST_RESULT"

if [ $TEST_RESULT -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests still failed. Check the output for details."
fi

exit $TEST_RESULT
