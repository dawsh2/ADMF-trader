#!/usr/bin/env python
"""
Run script for testing the pure strategy with signal interpreter pattern.

This script runs a backtest using the new architecture that separates signal generation
from position management, providing a cleaner separation of concerns.
"""
import argparse
import logging
import sys
import os
from datetime import datetime

from src.core.system_bootstrap import Bootstrap
from src.core.events.event_types import EventType

def main():
    """Main entry point for running a backtest with the new architecture."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run a backtest with pure strategy + signal interpreter pattern')
    parser.add_argument('--config', type=str, default='config/pure_strategy_test.yaml',
                        help='Path to configuration file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--trace', action='store_true', help='Enable trace logging for events')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs('results', exist_ok=True)
    
    # Create timestamp for log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Set up logging level
    log_level = logging.DEBUG if args.debug else logging.INFO
    
    # Generate log file path based on config name
    config_base = os.path.splitext(os.path.basename(args.config))[0]
    results_dir = f"./results/{config_base}"
    os.makedirs(results_dir, exist_ok=True)
    log_file = f"{results_dir}/{config_base}.log"
    
    # Initialize the system
    print(f"Initializing system with configuration: {args.config}")
    
    # Bootstrap the system
    bootstrap = Bootstrap(
        config_files=[args.config],
        log_level=log_level,
        log_file=log_file,
        debug=args.debug
    )
    
    # Set up the system and get container/config
    container, config = bootstrap.setup()
    
    # Extract key components
    backtest = container.get('backtest')
    risk_manager = container.get('risk_manager')
    signal_interpreter = container.get('signal_interpreter')
    portfolio = container.get('portfolio')
    event_bus = container.get('event_bus')
    
    # Enable event tracing if requested
    if args.trace:
        from src.core.events.event_utils import EventTracker
        
        # Create event tracker that logs all events
        tracker = EventTracker("backtest_tracker", verbose=True)
        
        # Register with event bus for all event types
        for event_type in EventType:
            event_bus.register(event_type, tracker.track_event, priority=999)
        
        print(f"Event tracing enabled for all event types")
    
    # Print key component status
    print("System initialized:")
    print(f"  Strategy: {container.get('strategy').name if container.get('strategy') else 'None'}")
    print(f"  Signal Interpreter: {signal_interpreter.name if signal_interpreter else 'None'}")
    print(f"  Portfolio: {'Initialized' if portfolio else 'None'}")
    print(f"  Risk Manager: {'Initialized' if risk_manager else 'None'}")
    
    # Run backtest
    print("Running backtest...")
    backtest.run()
    
    # Show results
    result_path = backtest.get_results_path()
    print(f"\nResults saved to {result_path}")
    print("- equity_curve_file")
    print("- detailed_report_file")
    print("- trades_file")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
