#!/usr/bin/env python
"""
Debug script focusing specifically on signal generation and order creation.

This script analyzes:
1. Signal generation from strategy
2. Rule ID assignment and deduplication
3. Signal to order conversion in risk manager
4. Order parameter validation

It adds enhanced logging to debug signal flow issues.
"""
import os
import sys
import datetime
import logging
import uuid
import argparse
import time
from collections import defaultdict

# Import from the main application
from src.core.system_bootstrap import Bootstrap
from src.core.events.event_types import EventType, Event
from src.core.events.event_utils import create_signal_event

# Configure logging to file and console
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_file = f'signal_debug_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Get root logger
logger = logging.getLogger()
logger.info(f"Logging to {log_file}")

class SignalOrderTracker:
    """Track signal generation and order creation"""
    
    def __init__(self):
        """Initialize signal-order tracker"""
        self.start_time = datetime.datetime.now()
        self.signals = []
        self.orders = []
        
        # Relationship tracking
        self.rule_id_to_signals = defaultdict(list)
        self.rule_id_to_orders = defaultdict(list)
        self.signal_to_order_map = {}  # signal_id -> order_ids
        
        # Statistics tracking
        self.stats = {
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'neutral_signals': 0,
            'signals_with_rule_id': 0,
            'total_orders': 0,
            'market_orders': 0,
            'limit_orders': 0,
            'buy_orders': 0,
            'sell_orders': 0,
            'orders_with_rule_id': 0,
            'order_intents': {
                'OPEN': 0,
                'CLOSE': 0,
                'None': 0
            }
        }
    
    def track_event(self, event):
        """
        Track event for signal-order analysis.
        
        Args:
            event: Event to track
        """
        try:
            event_type = event.get_type()
            event_id = event.get_id() if hasattr(event, 'get_id') else str(uuid.uuid4())
            timestamp = event.get_timestamp() if hasattr(event, 'get_timestamp') else datetime.datetime.now()
            
            # Process event data
            if not hasattr(event, 'data') or not isinstance(event.data, dict):
                logger.warning(f"Event {event_id} missing data dictionary")
                return
                
            data = event.data.copy()
            
            # Track signals and orders
            if event_type == EventType.SIGNAL:
                self._track_signal(event_id, timestamp, data)
            elif event_type == EventType.ORDER:
                self._track_order(event_id, timestamp, data)
                
        except Exception as e:
            logger.error(f"Error tracking event: {e}", exc_info=True)
    
    def _track_signal(self, event_id, timestamp, data):
        """Track a signal event"""
        self.stats['total_signals'] += 1
        
        # Extract key fields
        symbol = data.get('symbol', 'unknown')
        signal_value = data.get('signal_value', 0)
        price = data.get('price', 0.0)
        rule_id = data.get('rule_id')
        confidence = data.get('confidence', 1.0)
        
        # Track signal direction
        if signal_value > 0:
            self.stats['buy_signals'] += 1
        elif signal_value < 0:
            self.stats['sell_signals'] += 1
        else:
            self.stats['neutral_signals'] += 1
        
        # Create signal record
        signal = {
            'id': event_id,
            'timestamp': timestamp,
            'symbol': symbol,
            'signal_value': signal_value,
            'price': price,
            'rule_id': rule_id,
            'confidence': confidence,
            'elapsed': (timestamp - self.start_time).total_seconds()
        }
        
        # Log signal details at debug level
        logger.debug(f"Signal: {symbol} {signal_value} @ {price:.2f}, rule_id: {rule_id}")
        
        # Track rule_id relationship
        if rule_id:
            self.stats['signals_with_rule_id'] += 1
            self.rule_id_to_signals[rule_id].append(signal)
        
        # Store signal
        self.signals.append(signal)
    
    def _track_order(self, event_id, timestamp, data):
        """Track an order event"""
        self.stats['total_orders'] += 1
        
        # Extract key fields
        order_id = data.get('order_id', str(uuid.uuid4()))
        symbol = data.get('symbol', 'unknown')
        direction = data.get('direction', 'unknown')
        size = data.get('size', data.get('quantity', 0))
        order_type = data.get('order_type', 'MARKET')
        price = data.get('price', 0.0)
        rule_id = data.get('rule_id')
        position_action = data.get('position_action')
        
        # Track order attributes
        if direction == 'BUY':
            self.stats['buy_orders'] += 1
        elif direction == 'SELL':
            self.stats['sell_orders'] += 1
            
        if order_type == 'MARKET':
            self.stats['market_orders'] += 1
        elif order_type == 'LIMIT':
            self.stats['limit_orders'] += 1
            
        # Track position action (intent)
        intent_key = str(position_action) if position_action else 'None'
        self.stats['order_intents'][intent_key] = self.stats['order_intents'].get(intent_key, 0) + 1
        
        # Create order record
        order = {
            'id': event_id,
            'order_id': order_id,
            'timestamp': timestamp,
            'symbol': symbol,
            'direction': direction,
            'size': size,
            'order_type': order_type,
            'price': price,
            'rule_id': rule_id,
            'position_action': position_action,
            'elapsed': (timestamp - self.start_time).total_seconds()
        }
        
        # Log order details at debug level
        logger.debug(f"Order: {direction} {size} {symbol} @ {price:.2f}, rule_id: {rule_id}, intent: {position_action}")
        
        # Track rule_id relationship
        if rule_id:
            self.stats['orders_with_rule_id'] += 1
            self.rule_id_to_orders[rule_id].append(order)
            
            # Find corresponding signal for this rule_id
            matching_signals = self.rule_id_to_signals.get(rule_id, [])
            if matching_signals:
                # Map signal ID to this order ID
                for signal in matching_signals:
                    signal_id = signal['id']
                    if signal_id not in self.signal_to_order_map:
                        self.signal_to_order_map[signal_id] = []
                    self.signal_to_order_map[signal_id].append(order_id)
        
        # Store order
        self.orders.append(order)
    
    def get_report(self):
        """Generate detailed signal-order analysis report"""
        report = []
        report.append("====== SIGNAL-ORDER ANALYSIS REPORT ======")
        report.append(f"Analysis from: {self.start_time}")
        report.append(f"Duration: {(datetime.datetime.now() - self.start_time).total_seconds()} seconds")
        
        # Signal statistics
        report.append("\n=== SIGNAL STATISTICS ===")
        report.append(f"Total signals: {self.stats['total_signals']}")
        report.append(f"Buy signals: {self.stats['buy_signals']}")
        report.append(f"Sell signals: {self.stats['sell_signals']}")
        report.append(f"Neutral signals: {self.stats['neutral_signals']}")
        report.append(f"Signals with rule_id: {self.stats['signals_with_rule_id']}")
        
        # Order statistics
        report.append("\n=== ORDER STATISTICS ===")
        report.append(f"Total orders: {self.stats['total_orders']}")
        report.append(f"Buy orders: {self.stats['buy_orders']}")
        report.append(f"Sell orders: {self.stats['sell_orders']}")
        report.append(f"Market orders: {self.stats['market_orders']}")
        report.append(f"Limit orders: {self.stats['limit_orders']}")
        report.append(f"Orders with rule_id: {self.stats['orders_with_rule_id']}")
        
        # Order intent statistics
        report.append("\n=== ORDER INTENT STATISTICS ===")
        for intent, count in self.stats['order_intents'].items():
            report.append(f"{intent}: {count}")
        
        # Rule ID analysis
        report.append("\n=== RULE ID ANALYSIS ===")
        report.append(f"Unique rule IDs in signals: {len(self.rule_id_to_signals)}")
        report.append(f"Unique rule IDs in orders: {len(self.rule_id_to_orders)}")
        
        # Signal-to-order conversion
        common_rule_ids = set(self.rule_id_to_signals.keys()) & set(self.rule_id_to_orders.keys())
        report.append(f"\nRule IDs with both signals and orders: {len(common_rule_ids)}")
        
        missing_orders = set(self.rule_id_to_signals.keys()) - set(self.rule_id_to_orders.keys())
        if missing_orders:
            report.append(f"Rule IDs with signals but no orders: {len(missing_orders)}")
            if len(missing_orders) <= 5:
                report.append(f"Missing order rule IDs: {missing_orders}")
        
        missing_signals = set(self.rule_id_to_orders.keys()) - set(self.rule_id_to_signals.keys())
        if missing_signals:
            report.append(f"Rule IDs with orders but no signals: {len(missing_signals)}")
            if len(missing_signals) <= 5:
                report.append(f"Missing signal rule IDs: {missing_signals}")
        
        # Signal-to-order conversion rate
        signals_with_orders = len([s for s in self.signals if s['id'] in self.signal_to_order_map])
        if self.stats['total_signals'] > 0:
            conversion_rate = signals_with_orders / self.stats['total_signals']
            report.append(f"\nSignal-to-order conversion rate: {conversion_rate:.2%}")
            report.append(f"Signals with corresponding orders: {signals_with_orders} / {self.stats['total_signals']}")
        
        # Signal-order timing analysis
        if self.signal_to_order_map:
            latencies = []
            for signal_id, order_ids in self.signal_to_order_map.items():
                # Find the signal
                signal = next((s for s in self.signals if s['id'] == signal_id), None)
                if not signal:
                    continue
                    
                for order_id in order_ids:
                    # Find the order
                    order = next((o for o in self.orders if o['order_id'] == order_id), None)
                    if not order:
                        continue
                        
                    # Calculate latency
                    signal_time = signal.get('elapsed', 0)
                    order_time = order.get('elapsed', 0)
                    latency = order_time - signal_time
                    latencies.append(latency)
            
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                max_latency = max(latencies)
                min_latency = min(latencies)
                
                report.append("\n=== SIGNAL-ORDER TIMING ANALYSIS ===")
                report.append(f"Average signal-to-order latency: {avg_latency:.6f} seconds")
                report.append(f"Maximum latency: {max_latency:.6f} seconds")
                report.append(f"Minimum latency: {min_latency:.6f} seconds")
        
        # Sample data
        if self.signals:
            report.append("\n=== SAMPLE SIGNAL ===")
            sample_signal = self.signals[0]
            for key, value in sample_signal.items():
                report.append(f"{key}: {value}")
        
        if self.orders:
            report.append("\n=== SAMPLE ORDER ===")
            sample_order = self.orders[0]
            for key, value in sample_order.items():
                report.append(f"{key}: {value}")
        
        return "\n".join(report)


def add_rule_id_group_hack(event_bus):
    """
    Hack to add rule_id with group to signals for deduplication.
    
    Args:
        event_bus: Event bus to register handler
    """
    def add_rule_id_to_signal(signal_event):
        # Skip if already has rule_id
        if hasattr(signal_event, 'data') and signal_event.data.get('rule_id'):
            return
            
        # Generate rule_id with group identifier for proper deduplication
        symbol = signal_event.data.get('symbol', 'unknown')
        signal_value = signal_event.data.get('signal_value', 0)
        timestamp = signal_event.get_timestamp()
        
        # Format timestamp to minute precision for grouping
        time_str = timestamp.strftime("%Y%m%d_%H%M")
        
        # Create group-based rule ID (based on symbol, direction, minute)
        direction = "BUY" if signal_value > 0 else "SELL"
        rule_id = f"group_{symbol}_{direction}_{time_str}"
        
        # Add rule_id to data
        signal_event.data['rule_id'] = rule_id
        logger.info(f"Added rule_id to signal: {rule_id}")
    
    # Register handler with high priority (1000) to run before risk manager
    event_bus.register(EventType.SIGNAL, add_rule_id_to_signal, priority=1000)
    logger.info("Registered rule_id group hack")


def run_signal_order_test():
    """Test signal-order conversion directly."""
    logger.info("Running direct signal-order test")
    
    # Import needed components
    from src.core.events.event_bus import EventBus
    from src.risk.portfolio.portfolio import PortfolioManager
    from src.risk.managers.simple import SimpleRiskManager
    from src.execution.order_manager import OrderManager
    
    # Create components manually
    event_bus = EventBus()
    logger.info("Created event bus")
    
    # Create portfolio
    portfolio = PortfolioManager(event_bus, name="test_portfolio", initial_cash=100000.0)
    logger.info("Created portfolio")
    
    # Create risk manager
    risk_manager = SimpleRiskManager(event_bus, portfolio)
    risk_manager.position_size = 100
    risk_manager.max_position_pct = 0.1
    logger.info("Created risk manager")
    
    # Create order manager
    order_manager = OrderManager(event_bus)
    logger.info("Created order manager")
    
    # Set references
    risk_manager.order_manager = order_manager
    logger.info("Set component references")
    
    # Create tracker
    tracker = SignalOrderTracker()
    
    # Register event handlers
    event_bus.register(EventType.SIGNAL, tracker.track_event, priority=999)
    event_bus.register(EventType.ORDER, tracker.track_event, priority=999)
    logger.info("Registered event handlers")
    
    # Create and emit test signals
    timestamp = datetime.datetime.now()
    
    # 1. Create a buy signal
    buy_signal = create_signal_event(
        signal_value=1,  # Buy
        price=100.0,
        symbol="SPY",
        rule_id="test_buy_signal",
        timestamp=timestamp
    )
    
    # Emit the signal
    logger.info("Emitting buy signal")
    event_bus.emit(buy_signal)
    
    # Wait for processing
    time.sleep(0.5)
    
    # Check if an order was created
    buy_orders = [o for o in tracker.orders if o['direction'] == 'BUY']
    logger.info(f"Buy orders created: {len(buy_orders)}")
    
    # 2. Create a sell signal
    sell_signal = create_signal_event(
        signal_value=-1,  # Sell
        price=102.0,
        symbol="SPY",
        rule_id="test_sell_signal",
        timestamp=timestamp + datetime.timedelta(seconds=1)
    )
    
    # Emit the signal
    logger.info("Emitting sell signal")
    event_bus.emit(sell_signal)
    
    # Wait for processing
    time.sleep(0.5)
    
    # Check stats
    sell_orders = [o for o in tracker.orders if o['direction'] == 'SELL']
    logger.info(f"Sell orders created: {len(sell_orders)}")
    
    # Generate report
    report = tracker.get_report()
    logger.info("\n" + report)
    
    return report


def main():
    """Run the signal-order debug script."""
    parser = argparse.ArgumentParser(description="Debug signal-order flow in ADMF-Trader")
    parser.add_argument("--config", default="config/mini_test.yaml", help="Configuration file path")
    parser.add_argument("--log-level", default="INFO", 
                      choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Logging level")
    parser.add_argument("--add-rule-id", action="store_true", 
                      help="Add rule_id to signals that don't have one")
    parser.add_argument("--direct-test", action="store_true",
                      help="Run direct signal-order test instead of backtest")
    args = parser.parse_args()
    
    # Set up logging
    logger.setLevel(getattr(logging, args.log_level))
    logger.info(f"Starting signal-order debug with config: {args.config}")
    
    # Check if we should run the direct test
    if args.direct_test:
        result = run_signal_order_test()
        
        # Save report to file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.getcwd(), "debug_output")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"direct_signal_order_test_{timestamp}.txt")
        
        with open(output_file, "w") as f:
            f.write(result)
            
        logger.info(f"Direct test report saved to {output_file}")
        return True
    
    # Create the tracker
    tracker = SignalOrderTracker()
    
    # Initialize the bootstrap
    bootstrap = Bootstrap(
        config_files=[args.config],
        log_level=getattr(logging, args.log_level),
        log_file="signal_debug.log"
    )
    
    # Setup container with components
    logger.info(f"Initializing system with configuration: {args.config}")
    container, config = bootstrap.setup()
    
    # Get event bus
    event_bus = container.get("event_bus")
    
    # Optionally add the rule_id group hack
    if args.add_rule_id:
        add_rule_id_group_hack(event_bus)
    
    # Register tracker for relevant event types
    event_types = [EventType.SIGNAL, EventType.ORDER]
    
    for event_type in event_types:
        event_bus.register(event_type, tracker.track_event, priority=999)
        logger.info(f"Registered tracker for {event_type.name} events")
    
    # Get backtest coordinator
    backtest = container.get("backtest")
    
    # Run the backtest
    logger.info("Running backtest with signal-order tracking...")
    results = backtest.run()
    
    # Generate report
    if results:
        detailed_report = tracker.get_report()
        print("\n" + detailed_report)
        
        # Save report to file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.getcwd(), "debug_output")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"signal_order_report_{timestamp}.txt")
        
        with open(output_file, "w") as f:
            f.write(detailed_report)
            
        print(f"\nDetailed signal-order report saved to {output_file}")
        
    else:
        logger.error("Backtest did not produce any results")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception("Signal-order debug failed with error")
        print(f"Error: {e}")
        sys.exit(1)
