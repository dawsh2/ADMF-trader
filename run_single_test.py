#!/usr/bin/env python
"""
Script to run a single test file with debugging.
"""

import argparse
import subprocess
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Run a single test file with debugging")
    parser.add_argument('test_file', help='Path to the test file to run')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Increase verbosity')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.test_file):
        print(f"Error: Test file '{args.test_file}' not found")
        sys.exit(1)
    
    # Build command
    cmd = ["python", "-m", "pytest"]
    
    # Add debug flags
    if args.debug:
        cmd.extend(["-vv", "--showlocals", "--no-header"])
    
    # Add verbosity
    if args.verbose > 0:
        cmd.append("-" + "v" * args.verbose)
    
    # Add test file
    cmd.append(args.test_file)
    
    # Print command
    print(f"Running: {' '.join(cmd)}")
    
    # Run command
    result = subprocess.run(cmd)
    
    # Return exit code
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
