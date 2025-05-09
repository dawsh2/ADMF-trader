"""
Command-line interface for ADMF-Trader.

This module handles command-line arguments and provides subcommands
for different modes of operation.
"""

import argparse
import logging
import sys
from typing import Dict, List, Optional, Any

from src.core.logging import configure_logging

def parse_args():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="ADMF-Trader - Algorithmic Trading System"
    )
    
    # Main arguments
    parser.add_argument(
        "-c", "--config", 
        help="Path to configuration file",
        required=True
    )
    
    # Mode selection - inferred from config, but can be overridden
    parser.add_argument(
        "--optimize",
        help="Run in optimization mode",
        action="store_true"
    )
    
    # Logging options
    parser.add_argument(
        "-v", "--verbose",
        help="Enable verbose output",
        action="store_true"
    )
    parser.add_argument(
        "--debug",
        help="Enable debug logging for all modules",
        action="store_true"
    )
    parser.add_argument(
        "--debug-module",
        help="Enable debug logging for specific modules (e.g., src.core.event_system)",
        action="append",
        dest="debug_modules"
    )
    parser.add_argument(
        "--log-file",
        help="Write logs to file",
        dest="log_file"
    )
    parser.add_argument(
        "--quiet",
        help="Suppress console output",
        action="store_true"
    )
    
    return parser.parse_args()

def setup_logging(args):
    """
    Set up logging based on command line arguments.
    
    Args:
        args: Parsed command line arguments
    """
    # Configure logging based on arguments
    configure_logging(
        debug=args.debug,
        debug_modules=args.debug_modules,
        log_file=args.log_file,
        console=not args.quiet
    )
    
    # If verbose, but not debug, set INFO level
    if args.verbose and not args.debug:
        logging.getLogger().setLevel(logging.INFO)

def main():
    """Main entry point for the application."""
    # Parse arguments
    args = parse_args()
    
    # Setup logging
    setup_logging(args)
    
    # Import here to avoid circular imports
    from src.core.system_init import bootstrap_system
    
    # Bootstrap the system
    try:
        system = bootstrap_system(args.config)
        
        # Run in appropriate mode
        if args.optimize:
            system.run_optimization()
        else:
            system.run()
            
        return 0
        
    except Exception as e:
        logging.error(f"Error running system: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())