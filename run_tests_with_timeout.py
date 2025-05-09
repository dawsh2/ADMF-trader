#!/usr/bin/env python
"""
Test runner script with timeout protection for ADMF-Trader.
"""

import argparse
import subprocess
import sys
import os
import importlib.util
import signal
import threading


def timeout_handler(process, timeout):
    """
    Handler function for test timeout.
    Terminates the process after the specified timeout.
    """
    def handler():
        print(f"\n\nTEST TIMEOUT: Test execution exceeded {timeout} seconds!")
        print("Terminating test process...")
        process.terminate()
        
        # If termination doesn't work, kill it
        time.sleep(2)
        if process.poll() is None:
            print("Process not responding to termination, killing it...")
            process.kill()
    
    timer = threading.Timer(timeout, handler)
    timer.daemon = True
    timer.start()
    return timer


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
    parser = argparse.ArgumentParser(description="Run tests for ADMF-Trader with timeout protection")
    
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
    
    # Development install
    parser.add_argument(
        "--install-dev", action="store_true",
        help="Install the package in development mode before running tests"
    )
    
    # Debug mode
    parser.add_argument(
        "--debug", action="store_true",
        help="Run tests in debug mode with more detailed output"
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
    
    # Debug mode
    if args.debug:
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
    print("ADMF-Trader Test Runner (with Timeout Protection)")
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
    
    # Debug mode
    if args.debug:
        print("Debug mode enabled (more verbose output)")
    
    # Timeout
    print(f"Timeout: {args.timeout} seconds")
    
    print("-" * 80)


def install_dev_mode():
    """Install the package in development mode."""
    print("Installing package in development mode...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                           capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Error installing in development mode:")
        print(result.stderr)
        return False
    
    print("Development install successful")
    return True


def check_test_adapters():
    """Check that test adapters are properly loaded."""
    print("Checking test adapters...")
    
    # List of adapter modules
    adapter_modules = [
        "tests.unit.core.test_event_types_adapter",
        "tests.unit.core.test_event_bus_adapter",
        "tests.unit.execution.broker_adapter",
        "tests.unit.strategy.strategy_adapter",
        "tests.integration.integration_adapters"
    ]
    
    missing_adapters = []
    for module_name in adapter_modules:
        try:
            module = importlib.import_module(module_name)
            print(f"  ✓ {module_name}")
        except ImportError as e:
            missing_adapters.append((module_name, str(e)))
            print(f"  ✗ {module_name} - {e}")
    
    if missing_adapters:
        print("\nWarning: Some test adapters could not be loaded:")
        for name, error in missing_adapters:
            print(f"  - {name}: {error}")
        print("\nThis may cause some tests to fail.")
    else:
        print("All test adapters loaded successfully.")
    
    print("-" * 80)
    return len(missing_adapters) == 0


def main():
    """Main function."""
    import time
    
    args = parse_args()
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Install in development mode if requested
    if args.install_dev:
        if not install_dev_mode():
            return 1
    
    # Print header
    print_header(args)
    
    # Check test adapters in debug mode
    if args.debug:
        check_test_adapters()
    
    # Build command
    cmd = build_command(args)
    if not args.no_header:
        print(f"Running: {' '.join(cmd)}")
        print("-" * 80)
    
    # Run command with timeout protection
    process = subprocess.Popen(cmd)
    
    # Set up timeout handler
    timer = timeout_handler(process, args.timeout)
    
    try:
        # Wait for process to complete
        return_code = process.wait()
        
        # Cancel timer if process completes normally
        timer.cancel()
        
        return return_code
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Terminating...")
        process.terminate()
        timer.cancel()
        return 1


if __name__ == "__main__":
    sys.exit(main())
