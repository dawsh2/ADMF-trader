#!/bin/bash
# Run the minimal test to verify our fixes

echo "Running minimal test script..."
python minimal_test.py

if [ $? -eq 0 ]; then
    echo ""
    echo "============================"
    echo "✅ Minimal test passed! The core fixes have been successfully implemented."
    echo "============================"
    echo ""
    echo "You can now proceed with implementing the optimization module."
    echo "See FIXES_REPORT.md for details on all the fixes that were made."
    exit 0
else
    echo ""
    echo "============================"
    echo "❌ Minimal test failed. Check the output for details."
    echo "============================"
    exit 1
fi
