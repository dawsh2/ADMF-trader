#!/usr/bin/env python
"""
Debug script to identify why no trades are being generated
"""
import os
import logging
import argparse

from src.core.events.event_types import EventType
from src.core.system_bootstrap import Bootstrap

def set_up_debug_hooks(container):
    """Set up event hooks to debug the event flow."""
    event_bus = container.get("event_bus")
    
    # Track events by type
    event_counts = {
        "BAR": 0,
        "SIGNAL": 0,
        "ORDER": 0,
        "FILL": 0,
        "TRADE_OPEN": 0,
        "TRADE_CLOSE": 0
    }
    
    def debug_handler(event_type_name):
        def handler(event):
            event_counts[event_type_name] += 1
            if event_counts[event_type_name] <= 5:  # Only log first few events
                print(f"DEBUG: Received {event_type_name} event: {event.get_id() if hasattr(event, 'get_id') else 'unknown'}")
                if hasattr(event, 'data'):
                    print(f"   Data: {event.data}")
        return handler
    
    # Register handlers for each event type
    event_bus.register(EventType.BAR, debug_handler("BAR"), priority=999)
    event_bus.register(EventType.SIGNAL, debug_handler("SIGNAL"), priority=999)
    event_bus.register(EventType.ORDER, debug_handler("ORDER"), priority=999)
    event_bus.register(EventType.FILL, debug_handler("FILL"), priority=999)
    
    # Check if the new event types exist
    if hasattr(EventType, "TRADE_OPEN"):
        event_bus.register(EventType.TRADE_OPEN, debug_handler("TRADE_OPEN"), priority=999)
    if hasattr(EventType, "TRADE_CLOSE"):
        event_bus.register(EventType.TRADE_CLOSE, debug_handler("TRADE_CLOSE"), priority=999)
    
    return event_counts

def debug_chain(container):
    """Debug the component chain to ensure everything is properly connected."""
    # Check if data handler has symbols
    data_handler = container.get("data_handler")
    if hasattr(data_handler, "symbols"):
        print(f"DEBUG: Data handler symbols: {data_handler.symbols}")
    else:
        print("DEBUG: Data handler doesn't have symbols attribute!")
    
    # Check if strategy is properly configured
    strategy = container.get("strategy")
    if hasattr(strategy, "symbols"):
        print(f"DEBUG: Strategy symbols: {strategy.symbols}")
    else:
        print("DEBUG: Strategy doesn't have symbols attribute!")
    
    # Check risk manager
    risk_manager = container.get("risk_manager")
    if hasattr(risk_manager, "position_size"):
        print(f"DEBUG: Risk manager position size: {risk_manager.position_size}")
    else:
        print("DEBUG: Risk manager doesn't have position_size attribute!")
    
    # Check portfolio
    portfolio = container.get("portfolio")
    if hasattr(portfolio, "initial_cash"):
        print(f"DEBUG: Portfolio initial cash: {portfolio.initial_cash}")
    else:
        print("DEBUG: Portfolio doesn't have initial_cash attribute!")

def main():
    parser = argparse.ArgumentParser(description="Debug why no trades are being generated")
    parser.add_argument("--config", required=True, help="Configuration file path")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.verbose else logging.INFO
    log_file = "debug_trades.log"
    
    # Set up logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    print(f"Starting debug session with config: {args.config}")
    
    # Initialize the system
    bootstrap = Bootstrap(
        config_files=[args.config],
        log_level=log_level,
        log_file=log_file,
        debug=True
    )
    
    # Setup container with components
    container, config = bootstrap.setup()
    
    # Debug the component chain
    print("\n=== Component Chain Diagnostics ===")
    debug_chain(container)
    
    # Set up event hooks
    print("\n=== Setting Up Event Debuggers ===")
    event_counts = set_up_debug_hooks(container)
    
    # Get backtest coordinator
    backtest = container.get("backtest")
    
    # Run the backtest
    print("\n=== Running Backtest With Debugging ===")
    results = backtest.run()
    
    # Print event counts
    print("\n=== Event Counts ===")
    for event_type, count in event_counts.items():
        print(f"{event_type}: {count}")
    
    # Analyze any trade-related data
    print("\n=== Trade Analysis ===")
    portfolio = container.get("portfolio")
    if hasattr(portfolio, "trades"):
        print(f"Portfolio trades count: {len(portfolio.trades)}")
        if portfolio.trades:
            print("First trade:", portfolio.trades[0])
        else:
            print("No trades recorded in portfolio!")
    
    # Check risk manager state
    print("\n=== Risk Manager Analysis ===")
    risk_manager = container.get("risk_manager")
    if hasattr(risk_manager, "stats"):
        print(f"Risk manager stats: {risk_manager.stats}")
    else:
        print("Risk manager doesn't have stats attribute!")
    
    print("\nDebug session complete. Check debug_trades.log for detailed logs.")
    return True

if __name__ == "__main__":
    main()