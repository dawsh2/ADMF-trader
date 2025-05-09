#!/usr/bin/env python
"""
Run fix verification script and capture output.
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the fix verification script."""
    try:
        # Run the fix verification script
        result = subprocess.run(
            ["python", "fix_verification.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Print stdout and stderr
        if result.stdout:
            print("STDOUT:")
            for line in result.stdout.split('\n'):
                if 'Performance:' in line or 'parameter' in line or 'Score:' in line:
                    print(line)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Return exit code
        return result.returncode
    except Exception as e:
        logger.error(f"Error running fix verification: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
