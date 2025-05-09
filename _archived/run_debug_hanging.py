#!/usr/bin/env python
"""
Script to run the debug hanging test.
"""

import os
import sys
import subprocess

def main():
    """Run the debug hanging test."""
    print("Running debug hanging test...")
    
    # Set up environment with proper Python path
    env = os.environ.copy()
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Set PYTHONPATH to include project root
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{project_root}:{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = project_root
    
    print(f"PYTHONPATH: {env['PYTHONPATH']}")
    
    # Command to run the test
    cmd = ["python", "-m", "pytest", "tests/integration/test_debug_hanging.py", "-v"]
    print(f"Command: {' '.join(cmd)}")
    
    # Run with subprocess
    try:
        result = subprocess.run(cmd, env=env)
        print(f"Test completed with exit code {result.returncode}")
        return result.returncode
    except Exception as e:
        print(f"Error running test: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
