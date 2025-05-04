#!/usr/bin/env python3
"""
Test runner with safety measures to prevent hanging tests.

This script runs tests with additional safety measures including:
- Global timeout protection
- Event system safety enhancements
- Detailed logging
"""
import os
import sys
import time
import argparse
import logging
import threading
import subprocess
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_runner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_runner")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run tests with safety measures")
    
    parser.add_argument(
        "tests",
        nargs="*",
        default=["tests"],
        help="Test files or directories to run"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Global timeout per test in seconds"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level"
    )
    
    parser.add_argument(
        "--skip-slow",
        action="store_true",
        help="Skip tests marked as slow"
    )
    
    parser.add_argument(
        "--apply-adapters",
        action="store_true",
        default=True,
        help="Apply safety adapters to tests"
    )
    
    parser.add_argument(
        "--parallel",
        type=int,
        default=0,
        help="Number of parallel processes (0 = auto)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="test_results",
        help="Directory for test results"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run tests in debug mode with extra diagnostics"
    )
    
    parser.add_argument(
        "--retry-failed",
        type=int,
        default=0,
        help="Number of times to retry failed tests"
    )
    
    return parser.parse_args()

def check_adapters():
    """Check if safety adapters are available."""
    try:
        from tests.adapters import EventBusAdapter
        logger.info("Safety adapters found")
        return True
    except ImportError:
        logger.warning("Safety adapters not found - tests may hang")
        return False

def run_test_with_timeout(test_cmd, timeout):
    """Run a test command with timeout protection."""
    logger.info(f"Running command: {' '.join(test_cmd)}")
    
    proc = subprocess.Popen(
        test_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # Set up timeout
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    
    output = []
    try:
        # Capture output in real-time
        for line in proc.stdout:
            print(line, end='')
            output.append(line)
        
        proc.wait()
        success = proc.returncode == 0
    finally:
        timer.cancel()
        if proc.poll() is None:
            logger.error(f"Test timed out after {timeout} seconds")
            proc.kill()
            success = False
    
    return success, ''.join(output)

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    # Handle SIGINT (Ctrl+C)
    def handle_sigint(sig, frame):
        logger.info("Received interrupt signal, exiting...")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, handle_sigint)

def prepare_environment():
    """Prepare environment for running tests."""
    # Add project root to python path
    project_root = os.path.abspath(os.path.dirname(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(project_root, "test_results")
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Project root: {project_root}")
    logger.info(f"Output directory: {output_dir}")
    
    return project_root, output_dir

def build_pytest_command(args, test_path):
    """Build pytest command with safety measures."""
    cmd = [
        "python", "-m", "pytest",
        test_path,
        "--verbose",
        f"--log-cli-level={args.log_level}",
    ]
    
    # Add timeout protection
    cmd.extend(["--timeout", str(args.timeout)])
    
    # Add coverage reporting
    cmd.extend([
        "--cov=src",
        "--cov-report=term",
        f"--cov-report=html:{args.output_dir}/coverage_html"
    ])
    
    # Skip slow tests if requested
    if args.skip_slow:
        cmd.extend(["-m", "not slow"])
    
    # Add JUnit report for CI integration
    cmd.extend([
        f"--junitxml={args.output_dir}/junit.xml"
    ])
    
    # Add debug flags if needed
    if args.debug:
        cmd.extend(["-vvs"])
    
    return cmd

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = ['pytest', 'pytest-cov', 'pytest-timeout']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"Found {package}")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"Package {package} not found")
    
    if missing_packages:
        logger.error(f"Missing required packages: {missing_packages}")
        logger.info("Installing missing packages...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            logger.info("Packages installed successfully")
        except Exception as e:
            logger.error(f"Failed to install packages: {e}")
            return False
    
    return True

def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Set up signal handlers
    setup_signal_handlers()
    
    # Prepare environment
    project_root, output_dir = prepare_environment()
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Missing required dependencies. Please install pytest and related packages.")
        logger.info("Run: pip install pytest pytest-cov pytest-timeout pytest-xdist")
        return False
    
    # Check for safety adapters
    has_adapters = check_adapters()
    
    if args.apply_adapters and not has_adapters:
        logger.warning("Safety adapters requested but not found")
    
    # Run tests
    for test_path in args.tests:
        # Build test command
        test_cmd = build_pytest_command(args, test_path)
        
        # Add adapter option if available
        if args.apply_adapters and has_adapters:
            test_cmd.append("--apply-adapters")
        
        # Set parallelism if requested
        if args.parallel > 0:
            test_cmd.extend(["-n", str(args.parallel)])
        
        # Run the test with timeout
        success, output = run_test_with_timeout(test_cmd, args.timeout * 2)  # Double timeout for full run
        
        # Handle retry if needed
        retries = 0
        while not success and retries < args.retry_failed:
            logger.info(f"Test failed, retrying ({retries+1}/{args.retry_failed})...")
            retries += 1
            success, output = run_test_with_timeout(test_cmd, args.timeout * 2)
        
        # Log success/failure
        if success:
            logger.info(f"Test {test_path} passed")
        else:
            logger.error(f"Test {test_path} failed after {retries} retries")
    
    logger.info("All tests completed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running tests: {e}", exc_info=True)
        sys.exit(2)
