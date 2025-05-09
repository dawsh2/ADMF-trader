#!/usr/bin/env python
"""
Logging demo to demonstrate module-specific debug levels.

This script shows how to:
1. Set up the logging system
2. Configure different log levels for different modules
3. Log at different levels
4. Direct output to console or file
"""

import os
import sys
import argparse

# Add the project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.logging import configure_logging, get_logger, STRATEGY_PREFIX, DATA_PREFIX

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Logging Demo")
    
    # Logging options
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging for all modules')
    parser.add_argument('--debug-strategy', action='store_true', help='Debug only strategy module')
    parser.add_argument('--debug-data', action='store_true', help='Debug only data module')
    parser.add_argument('--log-file', help='Write logs to file')
    parser.add_argument('--quiet', action='store_true', help='Suppress console output')
    
    return parser.parse_args()

def main():
    """Run the logging demo."""
    # Parse arguments
    args = parse_args()
    
    # Configure logging
    debug_modules = []
    if args.debug_strategy:
        debug_modules.append(STRATEGY_PREFIX)
    if args.debug_data:
        debug_modules.append(DATA_PREFIX)
        
    # Debug message about logging config
    print(f"Debug mode: {args.debug}")
    print(f"Debug modules: {debug_modules}")
    
    # Configure logging system
    configure_logging(
        debug=args.debug or bool(debug_modules),  # Set debug mode if any module is debugged
        debug_modules=debug_modules,
        log_file=args.log_file,
        console=not args.quiet
    )
    
    # Create different loggers
    main_logger = get_logger(__name__)
    strategy_logger = get_logger(f"{STRATEGY_PREFIX}.demo")
    data_logger = get_logger(f"{DATA_PREFIX}.demo")
    
    # Log at different levels from each logger
    main_logger.debug("MAIN DEBUG - Should only show in full debug mode")
    main_logger.info("MAIN INFO - Should show in verbose or debug mode")
    main_logger.warning("MAIN WARNING - Should always show")
    
    strategy_logger.debug("STRATEGY DEBUG - Should show when strategy debugging is enabled")
    strategy_logger.info("STRATEGY INFO - Should always show")
    
    data_logger.debug("DATA DEBUG - Should show when data debugging is enabled")
    data_logger.info("DATA INFO - Should always show")
    
    # Print final message about log file
    if args.log_file:
        print(f"Logs written to: {args.log_file}")

if __name__ == "__main__":
    main()