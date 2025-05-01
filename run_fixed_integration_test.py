#!/usr/bin/env python
"""
Script to run the fixed integration test.
"""

import subprocess
import sys

def main():
    # Run the fixed integration test
    cmd = ["python", "-m", "pytest", "tests/integration/fixed_test_strategy_risk_order_flow.py", "-v"]
    print(f"Running: {' '.join(cmd)}")
    
    # Run with a timeout to avoid hanging indefinitely
    try:
        result = subprocess.run(cmd, timeout=30)
        return result.returncode
    except subprocess.TimeoutExpired:
        print("\nTest timed out after 30 seconds!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
