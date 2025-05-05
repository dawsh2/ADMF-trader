#!/usr/bin/env python
"""
A wrapper script to run the main module with reduced logging level.
"""
import os
import sys
import logging
import argparse

# Import the main function
from main import main

def run_with_reduced_logging():
    """Run main with reduced logging level."""
    parser = argparse.ArgumentParser(description="ADMF-Trader with Reduced Logging")
    
    # Add all the arguments from the main script
    parser.add_argument("--config", required=True, help="Configuration file path")
    parser.add_argument("--output-dir", default="./results", help="Results output directory")
    parser.add_argument("--data-dir", default="./data", help="Data directory")
    parser.add_argument("--log-level", default="WARNING", 
                      choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Logging level (defaults to WARNING for reduced output)")
    
    # Data generation options
    parser.add_argument("--generate-data", action="store_true", 
                      help="Generate synthetic data before running backtest")
    parser.add_argument("--data-type", default="multi_regime", 
                      choices=["multi_regime", "trend", "mean_reversion", "volatility", "random"],
                      help="Type of synthetic data to generate")
    parser.add_argument("--plot-data", action="store_true", 
                      help="Plot generated data")
    
    # Additional flags for this script
    parser.add_argument("--silence-modules", nargs="+", default=["matplotlib", "urllib3", "pandas"],
                      help="Modules to completely silence (set to CRITICAL)")
    
    args = parser.parse_args()
    
    # Set root logger to the specified level before anything else
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Silence noisy modules
    for module in args.silence_modules:
        logging.getLogger(module).setLevel(logging.CRITICAL)
    
    # These core modules should always be at least at WARNING level for important messages
    core_modules = [
        "src.core.events.event_bus",
        "src.execution.order_manager",
        "src.risk.managers.simple",
        "src.execution.broker.broker_simulator"
    ]
    
    for module in core_modules:
        # Don't raise the level if it's already lower (more verbose)
        current_level = logging.getLogger(module).level
        if current_level == 0 or current_level > logging.WARNING:
            logging.getLogger(module).setLevel(logging.WARNING)
    
    # Replace sys.argv with the parsed args to pass to main()
    sys.argv = [sys.argv[0]]
    for key, value in vars(args).items():
        if key not in ('silence_modules',):  # Skip our custom args
            if isinstance(value, bool):
                if value:
                    sys.argv.append(f"--{key.replace('_', '-')}")
            elif isinstance(value, list):
                if value:
                    sys.argv.append(f"--{key.replace('_', '-')}")
                    sys.argv.extend(value)
            elif value is not None:
                sys.argv.append(f"--{key.replace('_', '-')}")
                sys.argv.append(str(value))
    
    # Run the main function
    return main()

if __name__ == "__main__":
    try:
        success = run_with_reduced_logging()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)