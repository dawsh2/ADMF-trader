#!/usr/bin/env python
"""
Comprehensive test runner for ADMF-Trader.
Includes all tests with proper PYTHONPATH setup and timeout protection.
"""

import os
import sys
import time
import argparse
import subprocess
import logging

def setup_logging():
    """Set up logging for the test runner."""
    # Create logs directory if needed
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure logging
    log_file = os.path.join(logs_dir, 'test_runner.log')
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('test_runner')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run ADMF-Trader tests")
    
    # Test selection
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--unit", action="store_true", help="Run unit tests only")
    test_group.add_argument("--integration", action="store_true", help="Run integration tests only")
    test_group.add_argument("--all", action="store_true", help="Run all tests (default)")
    
    # Module selection
    parser.add_argument("--module", help="Run tests for specific module")
    
    # Test file or directory
    parser.add_argument("--path", help="Path to specific test file or directory")
    
    # Debug and timeout options
    parser.add_argument("--debug", action="store_true", help="Run with debug output")
    parser.add_argument("--timeout", type=int, default=30, help="Test timeout in seconds")
    
    # Output options
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")
    
    return parser.parse_args()

def build_command(args):
    """Build the pytest command."""
    cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if args.verbose > 0:
        cmd.append("-" + "v" * args.verbose)
    elif args.quiet:
        cmd.append("-q")
    
    # Add debug flags
    if args.debug:
        cmd.extend(["-vv", "--showlocals"])
    
    # Add test selection
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    
    # Add module selection
    if args.module:
        if args.module in ["core", "data", "strategy", "risk", "execution", "analytics"]:
            cmd.extend(["-k", args.module])
        else:
            print(f"Warning: Unknown module '{args.module}'")
    
    # Add test file or directory
    if args.path:
        if os.path.exists(args.path):
            cmd.append(args.path)
        else:
            print(f"Warning: Path '{args.path}' does not exist")
            cmd.append("tests")
    else:
        cmd.append("tests")
    
    return cmd

def main():
    """Main function."""
    # Set up logging
    logger = setup_logging()
    logger.info("Starting ADMF-Trader test runner")
    
    # Parse arguments
    args = parse_args()
    
    # Set up environment with proper Python path
    env = os.environ.copy()
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Set PYTHONPATH to include project root
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{project_root}:{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = project_root
    
    logger.info(f"PYTHONPATH: {env['PYTHONPATH']}")
    
    # Build command
    cmd = build_command(args)
    logger.info(f"Command: {' '.join(cmd)}")
    
    # Run the tests with timeout
    start_time = time.time()
    try:
        result = subprocess.run(cmd, timeout=args.timeout, env=env)
        elapsed = time.time() - start_time
        logger.info(f"Tests completed in {elapsed:.2f}s with exit code {result.returncode}")
        return result.returncode
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        logger.error(f"Tests timed out after {elapsed:.2f}s")
        return 1
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
