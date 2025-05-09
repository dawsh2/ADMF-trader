#!/bin/bash
# Run all tests to verify our fixes

# Run the simple test first
echo "Running simple test..."
python run_simple_test.py
SIMPLE_RESULT=$?

if [ $SIMPLE_RESULT -ne 0 ]; then
    echo "Simple test failed with exit code $SIMPLE_RESULT"
    exit $SIMPLE_RESULT
fi

echo "Simple test passed!"
echo "Running full test..."

# Run the full test
python test_the_fixes.py
FULL_RESULT=$?

if [ $FULL_RESULT -ne 0 ]; then
    echo "Full test failed with exit code $FULL_RESULT"
    exit $FULL_RESULT
fi

echo "All tests passed! The fixes have been successfully implemented."
exit 0
