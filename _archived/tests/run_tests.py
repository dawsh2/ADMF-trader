#!/usr/bin/env python3
"""
Run tests for ADMF-Trader with safety measures.

This script runs pytest with the adapters applied to prevent hanging tests.
"""
import os
import sys
import subprocess
import argparse
import logging
import importlib

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("test_runner")

def check_dependencies():
    """Check and install dependencies if needed."""
    required_packages = [
        'pytest', 
        'pytest-cov', 
        'pytest-timeout', 
        'jsonschema'  # Required for config schema tests
    ]
    missing = []

    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            logger.info(f"Found {package}")
        except ImportError:
            missing.append(package)
            logger.warning(f"Package {package} not found")

    if missing:
        logger.info(f"Installing missing packages: {missing}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
            logger.info("Packages installed successfully")
        except Exception as e:
            logger.error(f"Failed to install packages: {e}")
            logger.info("Please install packages manually:")
            logger.info(f"pip install {' '.join(missing)}")
            return False

    return True

def run_debug_integration():
    """Run the debug integration test."""
    logger.info("Running debug integration test...")
    
    integration_script = os.path.join('tests', 'integration', 'fixed_debug_integration.py')
    
    # Make sure the script exists
    if not os.path.exists(integration_script):
        logger.error(f"Integration script not found: {integration_script}")
        return False
    
    # Make script executable
    try:
        os.chmod(integration_script, 0o755)
    except Exception as e:
        logger.warning(f"Failed to make script executable: {e}")
    
    try:
        result = subprocess.run(
            [sys.executable, integration_script],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        print(result.stdout)
        
        if result.returncode == 0:
            logger.info("Debug integration test passed")
            return True
        else:
            logger.error(f"Debug integration test failed with exit code {result.returncode}")
            return False
    except Exception as e:
        logger.error(f"Error running debug integration test: {e}")
        return False

def run_tests(args):
    """Run tests with pytest."""
    logger.info(f"Running tests: {args.test_paths}")
    
    cmd = [
        sys.executable, "-m", "pytest"
    ]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage if requested
    if args.with_coverage:
        cmd.extend(["--cov=src", "--cov-report=term"])
    
    # Add timeout protection
    cmd.extend(["--timeout", str(args.timeout)])
    
    # Add test paths
    cmd.extend(args.test_paths)
    
    # Run pytest
    try:
        result = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        print(result.stdout)
        
        if result.returncode == 0:
            logger.info("Tests passed")
            return True
        else:
            logger.error(f"Tests failed with exit code {result.returncode}")
            return False
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run tests with safety measures")
    
    parser.add_argument(
        "test_paths",
        nargs="*",
        default=["tests"],
        help="Test paths to run (default: tests)"
    )
    
    parser.add_argument(
        "--debug-integration",
        action="store_true",
        help="Run debug integration test"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--with-coverage",
        action="store_true",
        help="Enable coverage reporting"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Test timeout in seconds (default: 60)"
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Missing required dependencies")
        return False
    
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Run debug integration test if requested
    if args.debug_integration:
        return run_debug_integration()
    
    # Run tests
    return run_tests(args)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
