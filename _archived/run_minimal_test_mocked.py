#!/usr/bin/env python
"""
Script to run the minimal integration test with mocked Event class.
"""

import subprocess
import sys
import os

def main():
    # Add project root to PYTHONPATH for the subprocess
    env = os.environ.copy()
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Set PYTHONPATH environment variable
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{project_root}:{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = project_root
    
    # Run the mock minimal test
    cmd = ["python", "-m", "pytest", "tests/integration/minimal_test_mocked.py", "-v"]
    print(f"Running: {' '.join(cmd)}")
    print(f"PYTHONPATH set to: {env['PYTHONPATH']}")
    
    # Run with a timeout
    try:
        result = subprocess.run(cmd, timeout=30, env=env)
        return result.returncode
    except subprocess.TimeoutExpired:
        print("\nTest timed out after 30 seconds!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
