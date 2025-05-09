#!/bin/bash
# Simple script to run the fix verification

echo "Running fix verification..."
python fix_verification.py

# Check if the command succeeded
if [ $? -eq 0 ]; then
    echo "✅ Verification succeeded!"
else
    echo "❌ Verification failed!"
fi
