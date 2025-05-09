#!/bin/bash
# Run test script for trade tracking fix

echo "Running trade tracking test with mini_test.yaml..."
python3 test_trade_tracking.py --config config/mini_test.yaml --log-level INFO

if [ $? -eq 0 ]; then
    echo "Mini test passed successfully!"
else
    echo "Mini test failed!"
    exit 1
fi

echo ""
echo "Running trade tracking test with head_test.yaml..."
python3 test_trade_tracking.py --config config/head_test.yaml --log-level INFO

if [ $? -eq 0 ]; then
    echo "Head test passed successfully!"
else
    echo "Head test failed!"
    exit 1
fi

echo ""
echo "All tests passed! Trade tracking fix is working correctly."
exit 0
