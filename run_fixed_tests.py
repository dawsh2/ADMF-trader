#!/usr/bin/env python
"""
Test runner script with timeout protection for ADMF-Trader using fixed adapters.
"""

import argparse
import subprocess
import sys
import os
import importlib.util
import time


def check_dependencies():
    """Check if required dependencies are installed."""
    missing_deps = []
    
    # List of required dependencies for testing
    required_deps = [
        "pytest",
        "pytest_cov",
        "jsonschema",
        "pandas",
        "numpy"
    ]
    
    for dep in required_deps:
        if importlib.util.find_spec(dep) is None:
            missing_deps.append(dep.replace("_", "-"))
    
    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install the missing dependencies:")
        print(f"pip install {' '.join(missing_deps)}")
        print("\nOr install all test dependencies with:")
        print("pip install -r requirements-test.txt")
        return False
    
    return True


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run tests for ADMF-Trader with fixed adapters")
    
    # Test type selection
    parser.add_argument(
        "--unit", action="store_true",
        help="Run unit tests only"
    )
    parser.add_argument(
        "--integration", action="store_true",
        help="Run integration tests only"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all tests (default)"
    )
    
    # Module selection
    parser.add_argument(
        "--module", type=str, default=None,
        help="Run tests for a specific module (core, data, strategy, risk, execution, analytics)"
    )
    
    # Test file selection
    parser.add_argument(
        "--file", type=str, default=None,
        help="Run a specific test file"
    )
    
    # Coverage options
    parser.add_argument(
        "--no-coverage", action="store_true",
        help="Disable coverage reporting (enabled by default in pytest.ini)"
    )
    
    # Output options
    parser.add_argument(
        "--verbose", "-v", action="count", default=0,
        help="Increase verbosity (can be used multiple times)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Show minimal output"
    )
    
    # Other options
    parser.add_argument(
        "--xvs", action="store_true",
        help="Exit on first failure (short for --exitfirst)"
    )
    parser.add_argument(
        "--no-header", action="store_true",
        help="Don't show header"
    )
    
    # Timeout
    parser.add_argument(
        "--timeout", type=int, default=30,
        help="Timeout in seconds for test execution (default: 30)"
    )
    
    return parser.parse_args()


def build_command(args):
    """Build pytest command based on arguments."""
    cmd = ["python", "-m", "pytest"]
    
    # Debug mode - always show verbose output
    cmd.extend(["-vv", "--showlocals"])
    
    # Test selection
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    # Otherwise all tests are run
    
    # Module selection
    if args.module:
        valid_modules = ["core", "data", "strategy", "risk", "execution", "analytics"]
        if args.module not in valid_modules:
            print(f"Error: Invalid module '{args.module}'. Choose from: {', '.join(valid_modules)}")
            sys.exit(1)
        cmd.extend(["-m", args.module])
    
    # File selection
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: Test file '{args.file}' not found")
            sys.exit(1)
        cmd.append(args.file)
    else:
        cmd.append("tests")  # Default test directory
    
    # Disable coverage if requested (it's enabled by default in pytest.ini)
    if args.no_coverage:
        cmd.append("--no-cov")
    
    # Verbosity
    if args.verbose > 0:
        cmd.append("-" + "v" * args.verbose)
    
    if args.quiet:
        cmd.append("-q")
    
    # Other options
    if args.xvs:
        cmd.append("--exitfirst")
    
    return cmd


def print_header(args):
    """Print header with information about the test run."""
    if args.no_header:
        return
    
    print("=" * 80)
    print("ADMF-Trader Test Runner (with FIXED Adapters)")
    print("=" * 80)
    
    # Test type
    if args.unit:
        print("Running unit tests only")
    elif args.integration:
        print("Running integration tests only")
    else:
        print("Running all tests")
    
    # Module
    if args.module:
        print(f"Module: {args.module}")
    
    # File
    if args.file:
        print(f"File: {args.file}")
    
    # Coverage
    if args.no_coverage:
        print("Coverage reporting disabled")
    else:
        print("Coverage reporting enabled (configured in pytest.ini)")
    
    # Timeout
    print(f"Timeout: {args.timeout} seconds")
    
    print("-" * 80)


def check_and_apply_fixes():
    """Set up environment to use fixed adapters."""
    
    # Create temporary file to redirect imports
    initfile_path = "/Users/daws/ADMF-trader/tests/__init__.py"
    
    try:
        # Backup original file if it exists
        backup_path = None
        if os.path.exists(initfile_path):
            backup_path = initfile_path + ".bak"
            with open(initfile_path, 'r') as src:
                with open(backup_path, 'w') as dst:
                    dst.write(src.read())
        
        # Write new file that imports fixed adapters
        with open(initfile_path, 'w') as f:
            f.write("""# This file makes the tests directory a Python package

# Import fixed adapters
try:
    import tests.adapters_fixed
except ImportError as e:
    print(f"Warning: Failed to import fixed adapters: {e}")
""")
        
        print("Applied fixes to use fixed adapters!")
        return True
    
    except Exception as e:
        print(f"Error applying fixes: {e}")
        # Try to restore backup if it exists
        if backup_path and os.path.exists(backup_path):
            with open(backup_path, 'r') as src:
                with open(initfile_path, 'w') as dst:
                    dst.write(src.read())
        return False


def main():
    """Main function."""
    args = parse_args()
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Apply fixes to use fixed adapters
    if not check_and_apply_fixes():
        return 1
    
    # Print header
    print_header(args)
    
    # Build command
    cmd = build_command(args)
    if not args.no_header:
        print(f"Running: {' '.join(cmd)}")
        print("-" * 80)
    
    # Run command with timeout
    try:
        result = subprocess.run(cmd, timeout=args.timeout)
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"\nTests timed out after {args.timeout} seconds!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
