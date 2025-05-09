#!/usr/bin/env python
"""
Debug script to track event flow in the ADMF-Trader system.

This script runs a simple backtest with enhanced logging to track:
1. Bar events generation
2. Signal generation
3. Order creation
4. Fill processing
5. Portfolio updates
6. Trade tracking

The script includes additional event listeners to monitor each step
of the process, with timestamps to identify bottlenecks.
"""
import os
import sys
import datetime
import logging
import uuid
import argparse
from collections import defaultdict

# Import from the main application
from src.core.system_bootstrap import Bootstrap
from src.core.events.event_types import EventType, Event

# Configure logging to file and console
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(f'event_flow_debug_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

# Get root logger
logger = logging.getLogger()

# Create a special event tracker to monitor all events
class EventTracker:
    """Track all events through the system for debugging."""
    
    def __init__(self):
        """Initialize the event tracker."""
        self.events = defaultdict(list)
        self.event_counts = defaultdict(int)
        self.rule_ids = set()
        self.order_ids = set()
        self.transaction_ids = set()
        self.signal_to_order_map = {}
        self.order_to_fill_map = {}
        self.rule_id_to_orders = defaultdict(list)
        self.start_time = datetime.datetime.now()
    
    def track_event(self, event):
        """
        Track an event.
        
        Args:
            event: Event to track
        """
        try:
            event_type = event.get_type()
            self.event_counts[event_type] += 1
            
            # Store basic event info
            event_data = {
                'id': event.get_id() if hasattr(event, 'get_id') else str(uuid.uuid4()),
                'timestamp': event.get_timestamp() if hasattr(event, 'get_timestamp') else datetime.datetime.now(),
                'elapsed': (datetime.datetime.now() - self.start_time).total_seconds(),
                'type': event_type.name
            }
            
            # Extract event-specific data
            if hasattr(event, 'data'):
                event_data['data'] = event.data.copy() if isinstance(event.data, dict) else {}
                
                # Track rule_ids from signals
                if event_type == EventType.SIGNAL and 'rule_id' in event.data:
                    rule_id = event.data['rule_id']
                    event_data['rule_id'] = rule_id
                    self.rule_ids.add(rule_id)
                    
                # Track order IDs
                if event_type == EventType.ORDER and 'order_id' in event.data:
                    order_id = event.data['order_id']
                    event_data['order_id'] = order_id
                    self.order_ids.add(order_id)
                    
                    # Track rule_id to order relationship
                    if 'rule_id' in event.data:
                        rule_id = event.data['rule_id']
                        self.rule_id_to_orders[rule_id].append(order_id)
                        
                # Track fill IDs
                if event_type == EventType.FILL and 'order_id' in event.data:
                    order_id = event.data['order_id']
                    event_data['order_id'] = order_id
                    
                # Track transaction IDs
                if 'transaction_id' in event.data:
                    transaction_id = event.data['transaction_id']
                    event_data['transaction_id'] = transaction_id
                    self.transaction_ids.add(transaction_id)
            
            # Store the event
            self.events[event_type].append(event_data)
            
        except Exception as e:
            logger.error(f"Error tracking event: {e}")
    
    def print_summary(self):
        """Print a summary of tracked events."""
        print("\n===== EVENT FLOW SUMMARY =====")
        print(f"Tracked from {self.start_time}")
        print(f"Total duration: {(datetime.datetime.now() - self.start_time).total_seconds()} seconds")
        
        print("\nEvent Counts:")
        for event_type, count in sorted(self.event_counts.items(), key=lambda x: x[0].name):
            print(f"  {event_type.name}: {count}")
        
        print(f"\nUnique tracking IDs:")
        print(f"  Rule IDs: {len(self.rule_ids)}")
        print(f"  Order IDs: {len(self.order_ids)}")
        print(f"  Transaction IDs: {len(self.transaction_ids)}")
        
        # For detailed debugging, print rule_id -> orders mapping
        if self.rule_id_to_orders:
            print("\nRule ID to Orders mapping:")
            for rule_id, orders in self.rule_id_to_orders.items():
                print(f"  Rule ID: {rule_id} -> Orders: {len(orders)}")
        
        print("\n===== SIGNAL FLOW ANALYSIS =====")
        signals = self.events.get(EventType.SIGNAL, [])
        print(f"Total signals: {len(signals)}")
        
        signals_with_rule_id = [s for s in signals if 'rule_id' in s.get('data', {})]
        print(f"Signals with rule_id: {len(signals_with_rule_id)}")
        
        if signals:
            # Sample the first few signals
            print("\nSample signals:")
            for i, signal in enumerate(signals[:3]):
                print(f"  Signal {i+1}:")
                print(f"    ID: {signal.get('id')}")
                print(f"    Timestamp: {signal.get('timestamp')}")
                print(f"    Data: {signal.get('data')}")
        
        print("\n===== ORDER FLOW ANALYSIS =====")
        orders = self.events.get(EventType.ORDER, [])
        print(f"Total orders: {len(orders)}")
        
        orders_with_rule_id = [o for o in orders if 'rule_id' in o.get('data', {})]
        print(f"Orders with rule_id: {len(orders_with_rule_id)}")
        
        if orders:
            # Sample the first few orders
            print("\nSample orders:")
            for i, order in enumerate(orders[:3]):
                print(f"  Order {i+1}:")
                print(f"    ID: {order.get('order_id', 'unknown')}")
                print(f"    Timestamp: {order.get('timestamp')}")
                print(f"    Rule ID: {order.get('data', {}).get('rule_id', 'None')}")
                print(f"    Symbol: {order.get('data', {}).get('symbol', 'unknown')}")
                print(f"    Direction: {order.get('data', {}).get('direction', 'unknown')}")
                print(f"    Size: {order.get('data', {}).get('size', 0)}")
        
        print("\n===== FILL ANALYSIS =====")
        fills = self.events.get(EventType.FILL, [])
        print(f"Total fills: {len(fills)}")
        if len(orders) > 0:
            print(f"Fill/Order ratio: {len(fills)/len(orders):.2f}")
        
        if fills:
            # Sample the first few fills
            print("\nSample fills:")
            for i, fill in enumerate(fills[:3]):
                print(f"  Fill {i+1}:")
                print(f"    Order ID: {fill.get('data', {}).get('order_id', 'unknown')}")
                print(f"    Timestamp: {fill.get('timestamp')}")
                print(f"    Symbol: {fill.get('data', {}).get('symbol', 'unknown')}")
                print(f"    Direction: {fill.get('data', {}).get('direction', 'unknown')}")
                print(f"    Size: {fill.get('data', {}).get('size', 0)}")
        
        print("\n===== EVENT TIMING ANALYSIS =====")
        all_timestamps = []
        for event_list in self.events.values():
            for event in event_list:
                if 'elapsed' in event:
                    all_timestamps.append((event['elapsed'], event['type']))
        
        all_timestamps.sort()
        if all_timestamps:
            print("Event timeline (first 20 events):")
            for i, (elapsed, event_type) in enumerate(all_timestamps[:20]):
                print(f"  {elapsed:.4f}s: {event_type}")
            
            # Find the longest gap
            gaps = [(all_timestamps[i+1][0] - all_timestamps[i][0], 
                    all_timestamps[i][1], all_timestamps[i+1][1]) 
                    for i in range(len(all_timestamps)-1)]
            if gaps:
                max_gap = max(gaps, key=lambda x: x[0])
                print(f"\nLongest gap: {max_gap[0]:.4f}s between {max_gap[1]} and {max_gap[2]}")
        
        print("\n===== COMPLETED =====")


def main():
    """Run the event flow debug script."""
    parser = argparse.ArgumentParser(description="Debug event flow in ADMF-Trader")
    parser.add_argument("--config", default="config/mini_test.yaml", help="Configuration file path")
    parser.add_argument("--log-level", default="INFO", 
                      choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Logging level")
    args = parser.parse_args()
    
    # Set up logging
    logger.setLevel(getattr(logging, args.log_level))
    logger.info(f"Starting event flow debug with config: {args.config}")
    
    # Create the tracker
    tracker = EventTracker()
    
    # Initialize the bootstrap
    bootstrap = Bootstrap(
        config_files=[args.config],
        log_level=getattr(logging, args.log_level),
        log_file="debug_event_flow.log"
    )
    
    # Setup container with components
    logger.info(f"Initializing system with configuration: {args.config}")
    container, config = bootstrap.setup()
    
    # Get event bus and register tracker for ALL event types
    event_bus = container.get("event_bus")
    
    # Register tracker for all event types
    event_types = [EventType.BAR, EventType.SIGNAL, EventType.ORDER, EventType.FILL, 
                  EventType.POSITION, EventType.PORTFOLIO, EventType.TRADE_OPEN, 
                  EventType.TRADE_CLOSE]
    
    for event_type in event_types:
        event_bus.register(event_type, tracker.track_event, priority=999)  # High priority to ensure it's called
        logger.info(f"Registered tracker for {event_type.name} events")
    
    # Get backtest coordinator
    backtest = container.get("backtest")
    
    # Run the backtest
    logger.info("Running backtest with event tracking...")
    results = backtest.run()
    
    # If verbose logging, show all events
    if args.log_level == "DEBUG":
        for event_type in event_types:
            events = tracker.events.get(event_type, [])
            logger.debug(f"{event_type.name} events: {len(events)}")
            for e in events[:5]:  # Show first 5 of each type
                logger.debug(f"  {e}")
    
    # Generate and save reports
    if results:
        report_generator = container.get("report_generator")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract configuration details
        config_section = config.get_section("backtest")
        strategy_name = config_section.get("strategy", "unknown")
        symbols = config_section.get("symbols", [])
        
        print("\n===== BACKTEST RESULTS =====")
        print(f"Strategy: {strategy_name}")
        print(f"Symbols: {symbols}")
        
        # Get performance metrics
        metrics = results.get("metrics", {})
        print("\nPerformance Metrics:")
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value}")
        
        # Get trade summary
        trades = results.get("trades", [])
        print(f"\nTrades: {len(trades)}")
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losing_trades = sum(1 for t in trades if t.get('pnl', 0) < 0)
        print(f"  Winning trades: {winning_trades}")
        print(f"  Losing trades: {losing_trades}")
        if trades:
            print(f"  Win rate: {winning_trades / len(trades):.2%}")
        
        # Print event tracker summary
        tracker.print_summary()
    else:
        logger.error("Backtest did not produce any results")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception("Event flow debug failed with error")
        print(f"Error: {e}")
        sys.exit(1)