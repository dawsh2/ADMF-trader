#!/usr/bin/env python
"""
Debug script focused on trade generation and tracking in the ADMF-Trader system.

This script diagnoses issues in the trade lifecycle:
1. From signals to orders
2. From orders to fills
3. From fills to trade open/close events
4. Portfolio trade tracking
5. Validation of trade data integrity

Run with: python debug_trade_tracking.py --config config/mini_test.yaml
"""
import os
import sys
import datetime
import logging
import uuid
import argparse
import pandas as pd
from collections import defaultdict

# Import from the main application
from src.core.system_bootstrap import Bootstrap
from src.core.events.event_types import EventType, Event
from src.core.events.event_bus import EventBus
from src.core.events.event_utils import create_signal_event, create_trade_open_event, create_trade_close_event
from src.risk.portfolio.portfolio import PortfolioManager
from src.analytics.performance.calculator import PerformanceCalculator
from src.analytics.reporting.report_generator import ReportGenerator

# Configure logging to file and console
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_file = f'trade_tracking_verification_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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

# Create a trade tracker to monitor the full trade lifecycle
class TradeLifecycleTracker:
    """Track the complete lifecycle of trades for debugging."""
    
    def __init__(self):
        """Initialize the trade tracker."""
        self.start_time = datetime.datetime.now()
        self.signals = []
        self.orders = []
        self.fills = []
        self.trade_opens = []
        self.trade_closes = []
        self.portfolio_updates = []
        
        # Tracking maps for relationships
        self.rule_id_to_signals = defaultdict(list)
        self.rule_id_to_orders = defaultdict(list)
        self.order_id_to_fills = defaultdict(list)
        self.transaction_id_to_trades = defaultdict(list)
        
        # Statistics
        self.stats = {
            'signals_generated': 0,
            'signals_with_rule_id': 0,
            'orders_created': 0,
            'orders_with_rule_id': 0,
            'fills_processed': 0,
            'trade_opens': 0,
            'trade_closes': 0,
            'portfolio_updates': 0
        }
    
    def track_event(self, event):
        """
        Track an event in the trade lifecycle.
        
        Args:
            event: Event to track
        """
        try:
            event_type = event.get_type()
            event_id = event.get_id() if hasattr(event, 'get_id') else str(uuid.uuid4())
            timestamp = event.get_timestamp() if hasattr(event, 'get_timestamp') else datetime.datetime.now()
            
            # Extract event data
            if not hasattr(event, 'data') or not isinstance(event.data, dict):
                logger.warning(f"Event {event_id} missing data dictionary")
                return
                
            data = event.data.copy()
            
            # Track based on event type
            if event_type == EventType.SIGNAL:
                self._track_signal(event_id, timestamp, data)
            elif event_type == EventType.ORDER:
                self._track_order(event_id, timestamp, data)
            elif event_type == EventType.FILL:
                self._track_fill(event_id, timestamp, data)
            elif event_type == EventType.TRADE_OPEN:
                self._track_trade_open(event_id, timestamp, data)
            elif event_type == EventType.TRADE_CLOSE:
                self._track_trade_close(event_id, timestamp, data)
            elif event_type == EventType.PORTFOLIO:
                self._track_portfolio_update(event_id, timestamp, data)
                
        except Exception as e:
            logger.error(f"Error tracking event: {e}", exc_info=True)
    
    def _track_signal(self, event_id, timestamp, data):
        """Track a signal event."""
        self.stats['signals_generated'] += 1
        
        # Extract key fields
        symbol = data.get('symbol', 'unknown')
        signal_value = data.get('signal_value', 0)
        price = data.get('price', 0.0)
        rule_id = data.get('rule_id')
        
        # Create signal record
        signal = {
            'id': event_id,
            'timestamp': timestamp,
            'symbol': symbol,
            'signal_value': signal_value,
            'price': price,
            'rule_id': rule_id
        }
        
        # Track rule_id relationship
        if rule_id:
            self.stats['signals_with_rule_id'] += 1
            self.rule_id_to_signals[rule_id].append(signal)
        
        # Store signal
        self.signals.append(signal)
        
    def _track_order(self, event_id, timestamp, data):
        """Track an order event."""
        self.stats['orders_created'] += 1
        
        # Extract key fields
        order_id = data.get('order_id', str(uuid.uuid4()))
        symbol = data.get('symbol', 'unknown')
        direction = data.get('direction', 'unknown')
        size = data.get('size', data.get('quantity', 0))
        price = data.get('price', 0.0)
        rule_id = data.get('rule_id')
        position_action = data.get('position_action')
        
        # Create order record
        order = {
            'id': event_id,
            'order_id': order_id,
            'timestamp': timestamp,
            'symbol': symbol,
            'direction': direction,
            'size': size,
            'price': price,
            'rule_id': rule_id,
            'position_action': position_action
        }
        
        # Track rule_id relationship
        if rule_id:
            self.stats['orders_with_rule_id'] += 1
            self.rule_id_to_orders[rule_id].append(order)
        
        # Store order
        self.orders.append(order)
        
    def _track_fill(self, event_id, timestamp, data):
        """Track a fill event."""
        self.stats['fills_processed'] += 1
        
        # Extract key fields
        order_id = data.get('order_id', 'unknown')
        symbol = data.get('symbol', 'unknown')
        direction = data.get('direction', 'unknown')
        size = data.get('size', data.get('quantity', 0))
        fill_price = data.get('fill_price', data.get('price', 0.0))
        commission = data.get('commission', 0.0)
        
        # Create fill record
        fill = {
            'id': event_id,
            'timestamp': timestamp,
            'order_id': order_id,
            'symbol': symbol,
            'direction': direction,
            'size': size,
            'fill_price': fill_price,
            'commission': commission
        }
        
        # Track order_id relationship
        self.order_id_to_fills[order_id].append(fill)
        
        # Store fill
        self.fills.append(fill)
        
    def _track_trade_open(self, event_id, timestamp, data):
        """Track a trade open event."""
        self.stats['trade_opens'] += 1
        
        # Extract key fields
        symbol = data.get('symbol', 'unknown')
        direction = data.get('direction', 'unknown')
        quantity = data.get('quantity', 0)
        price = data.get('price', 0.0)
        commission = data.get('commission', 0.0)
        rule_id = data.get('rule_id')
        order_id = data.get('order_id')
        transaction_id = data.get('transaction_id', str(uuid.uuid4()))
        
        # Create trade open record
        trade_open = {
            'id': event_id,
            'timestamp': timestamp,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'rule_id': rule_id,
            'order_id': order_id,
            'transaction_id': transaction_id
        }
        
        # Track transaction_id relationship
        self.transaction_id_to_trades[transaction_id].append(trade_open)
        
        # Store trade open
        self.trade_opens.append(trade_open)
        
    def _track_trade_close(self, event_id, timestamp, data):
        """Track a trade close event."""
        self.stats['trade_closes'] += 1
        
        # Extract key fields
        symbol = data.get('symbol', 'unknown')
        direction = data.get('direction', 'unknown')
        quantity = data.get('quantity', 0)
        entry_price = data.get('entry_price', 0.0)
        exit_price = data.get('exit_price', 0.0)
        pnl = data.get('pnl', 0.0)
        commission = data.get('commission', 0.0)
        rule_id = data.get('rule_id')
        order_id = data.get('order_id')
        transaction_id = data.get('transaction_id', str(uuid.uuid4()))
        
        # Create trade close record
        trade_close = {
            'id': event_id,
            'timestamp': timestamp,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'commission': commission,
            'rule_id': rule_id,
            'order_id': order_id,
            'transaction_id': transaction_id
        }
        
        # Track transaction_id relationship
        self.transaction_id_to_trades[transaction_id].append(trade_close)
        
        # Store trade close
        self.trade_closes.append(trade_close)
        
    def _track_portfolio_update(self, event_id, timestamp, data):
        """Track a portfolio update event."""
        self.stats['portfolio_updates'] += 1
        
        # Extract key fields
        portfolio_id = data.get('portfolio_id', 'unknown')
        cash = data.get('cash', 0.0)
        equity = data.get('equity', 0.0)
        trade = data.get('trade')
        trade_count = data.get('trade_count', 0)
        
        # Create portfolio update record
        portfolio_update = {
            'id': event_id,
            'timestamp': timestamp,
            'portfolio_id': portfolio_id,
            'cash': cash,
            'equity': equity,
            'trade': trade,
            'trade_count': trade_count
        }
        
        # Store portfolio update
        self.portfolio_updates.append(portfolio_update)
    
    def get_detailed_report(self):
        """Generate a detailed report on the trade lifecycle."""
        report = []
        report.append("====== TRADE LIFECYCLE TRACKING REPORT ======")
        report.append(f"Tracking started: {self.start_time}")
        report.append(f"Tracking duration: {(datetime.datetime.now() - self.start_time).total_seconds()} seconds")
        
        # Basic statistics
        report.append("\n=== BASIC STATISTICS ===")
        for stat, count in self.stats.items():
            report.append(f"{stat}: {count}")
        
        # Signal analysis
        report.append("\n=== SIGNAL ANALYSIS ===")
        report.append(f"Total signals: {len(self.signals)}")
        report.append(f"Signals with rule_id: {self.stats['signals_with_rule_id']}")
        
        # Rule ID analysis
        report.append("\n=== RULE ID ANALYSIS ===")
        report.append(f"Total unique rule IDs: {len(self.rule_id_to_signals)}")
        
        # Count signals per rule_id
        signals_per_rule = {rule_id: len(signals) for rule_id, signals in self.rule_id_to_signals.items()}
        if signals_per_rule:
            max_signals = max(signals_per_rule.items(), key=lambda x: x[1])
            min_signals = min(signals_per_rule.items(), key=lambda x: x[1])
            report.append(f"Max signals per rule: {max_signals[1]} (rule_id: {max_signals[0]})")
            report.append(f"Min signals per rule: {min_signals[1]} (rule_id: {min_signals[0]})")
        
        # Count orders per rule_id
        orders_per_rule = {rule_id: len(orders) for rule_id, orders in self.rule_id_to_orders.items()}
        if orders_per_rule:
            report.append("\nRule ID to Orders mapping:")
            for rule_id, count in orders_per_rule.items():
                report.append(f"  Rule ID: {rule_id} -> Orders: {count}")
        
        # Signal to order conversion
        report.append("\n=== SIGNAL TO ORDER CONVERSION ===")
        common_rule_ids = set(self.rule_id_to_signals.keys()) & set(self.rule_id_to_orders.keys())
        report.append(f"Rule IDs with both signals and orders: {len(common_rule_ids)}")
        
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
        
        # Order to fill conversion
        report.append("\n=== ORDER TO FILL CONVERSION ===")
        order_ids = {order['order_id'] for order in self.orders if 'order_id' in order}
        filled_order_ids = set(self.order_id_to_fills.keys())
        report.append(f"Total unique order IDs: {len(order_ids)}")
        report.append(f"Orders with fills: {len(filled_order_ids)}")
        
        missing_fills = order_ids - filled_order_ids
        if missing_fills:
            report.append(f"Orders without fills: {len(missing_fills)}")
            if len(missing_fills) <= 5:
                report.append(f"Missing fill order IDs: {missing_fills}")
        
        # Fill to trade open/close conversion
        report.append("\n=== FILL TO TRADE CONVERSION ===")
        report.append(f"Total fills: {len(self.fills)}")
        report.append(f"Trade opens: {len(self.trade_opens)}")
        report.append(f"Trade closes: {len(self.trade_closes)}")
        
        # Transaction ID analysis
        report.append("\n=== TRANSACTION ID ANALYSIS ===")
        report.append(f"Total unique transaction IDs: {len(self.transaction_id_to_trades)}")
        
        # Portfolio update analysis
        report.append("\n=== PORTFOLIO UPDATE ANALYSIS ===")
        report.append(f"Total portfolio updates: {len(self.portfolio_updates)}")
        
        # If we have portfolio updates, show trade tracking
        if self.portfolio_updates:
            trade_counts = [update.get('trade_count', 0) for update in self.portfolio_updates]
            if trade_counts:
                report.append(f"Final trade count in portfolio: {trade_counts[-1]}")
                
                # Verify if this matches our trade counts
                total_trades = len(self.trade_opens) + len(self.trade_closes)
                if total_trades != trade_counts[-1]:
                    report.append(f"WARNING: Mismatch between tracked trades ({total_trades}) and portfolio trades ({trade_counts[-1]})")
        
        return "\n".join(report)


def verify_portfolio_trades(portfolio, tracker):
    """
    Verify portfolio trade tracking against event tracking.
    
    Args:
        portfolio: Portfolio manager instance
        tracker: Trade lifecycle tracker
        
    Returns:
        str: Verification report
    """
    report = []
    report.append("====== PORTFOLIO TRADE VERIFICATION ======")
    
    # Get trades from portfolio
    portfolio_trades = portfolio.get_recent_trades()
    tracked_trade_opens = tracker.trade_opens
    tracked_trade_closes = tracker.trade_closes
    
    report.append(f"Portfolio trade count: {len(portfolio_trades)}")
    report.append(f"Tracked trade opens: {len(tracked_trade_opens)}")
    report.append(f"Tracked trade closes: {len(tracked_trade_closes)}")
    
    # Check for missing fields in portfolio trades
    if portfolio_trades:
        missing_fields = defaultdict(int)
        for trade in portfolio_trades:
            for field in ['symbol', 'direction', 'quantity', 'price', 'pnl']:
                if field not in trade:
                    missing_fields[field] += 1
        
        if missing_fields:
            report.append("\nMissing fields in portfolio trades:")
            for field, count in missing_fields.items():
                report.append(f"  {field}: {count} trades")
    
    # Calculate total P&L from portfolio trades
    if portfolio_trades:
        total_pnl = sum(trade.get('pnl', 0) for trade in portfolio_trades)
        report.append(f"\nTotal P&L from portfolio trades: {total_pnl:.2f}")
        
        # Count winning and losing trades
        winning_trades = sum(1 for trade in portfolio_trades if trade.get('pnl', 0) > 0)
        losing_trades = sum(1 for trade in portfolio_trades if trade.get('pnl', 0) < 0)
        even_trades = sum(1 for trade in portfolio_trades if trade.get('pnl', 0) == 0)
        
        report.append(f"Winning trades: {winning_trades}")
        report.append(f"Losing trades: {losing_trades}")
        report.append(f"Break-even trades: {even_trades}")
    
    # Check if trade opens and closes match the portfolio trades
    # This is a heuristic check since exact matching is complex
    total_tracked_trades = len(tracked_trade_opens) + len(tracked_trade_closes)
    if total_tracked_trades != len(portfolio_trades):
        report.append(f"\nWARNING: Mismatch between tracked trades ({total_tracked_trades}) and portfolio trades ({len(portfolio_trades)})")
        
        # Try to identify the missing trades
        if total_tracked_trades > len(portfolio_trades):
            report.append("Some tracked trades are not in the portfolio.")
        else:
            report.append("Some portfolio trades are not tracked in events.")
    
    # Add portfolio statistics
    report.append("\n=== PORTFOLIO STATISTICS ===")
    portfolio_stats = portfolio.get_stats()
    for stat, value in portfolio_stats.items():
        if isinstance(value, (int, float)):
            report.append(f"{stat}: {value}")
    
    return "\n".join(report)


def main():
    """Run the trade tracking debug script."""
    parser = argparse.ArgumentParser(description="Debug trade tracking in ADMF-Trader")
    parser.add_argument("--config", default="config/mini_test.yaml", help="Configuration file path")
    parser.add_argument("--log-level", default="INFO", 
                      choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Logging level")
    args = parser.parse_args()
    
    # Set up logging
    logger.setLevel(getattr(logging, args.log_level))
    logger.info(f"Starting trade tracking debug with config: {args.config}")
    
    # Create the tracker
    tracker = TradeLifecycleTracker()
    
    # Initialize the bootstrap
    bootstrap = Bootstrap(
        config_files=[args.config],
        log_level=getattr(logging, args.log_level),
        log_file="trade_tracking_debug.log"
    )
    
    # Setup container with components
    logger.info(f"Initializing system with configuration: {args.config}")
    container, config = bootstrap.setup()
    
    # Get event bus and register tracker for trade lifecycle events
    event_bus = container.get("event_bus")
    
    # Register tracker for relevant event types
    event_types = [EventType.SIGNAL, EventType.ORDER, EventType.FILL, 
                  EventType.TRADE_OPEN, EventType.TRADE_CLOSE, EventType.PORTFOLIO]
    
    for event_type in event_types:
        event_bus.register(event_type, tracker.track_event, priority=999)  # High priority to ensure it's called
        logger.info(f"Registered tracker for {event_type.name} events")
    
    # Get backtest coordinator and portfolio
    backtest = container.get("backtest")
    portfolio = container.get("portfolio")
    
    # Run the backtest
    logger.info("Running backtest with trade tracking...")
    results = backtest.run()
    
    # Generate reports
    if results:
        # Get backtest metrics
        report_generator = container.get("report_generator")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Print backtest summary
        print("\n====== BACKTEST SUMMARY ======")
        metrics = results.get("metrics", {})
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                print(f"{key}: {value}")
        
        # Print trade lifecycle report
        detailed_report = tracker.get_detailed_report()
        print("\n" + detailed_report)
        
        # Verify portfolio trades
        if portfolio:
            verification_report = verify_portfolio_trades(portfolio, tracker)
            print("\n" + verification_report)
            
            # Write report to file
            output_dir = os.path.join(os.getcwd(), "debug_output")
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"trade_verification_report_{timestamp}.txt")
            
            with open(output_file, "w") as f:
                f.write(detailed_report)
                f.write("\n\n")
                f.write(verification_report)
                
            print(f"\nDetailed trade verification report saved to {output_file}")
        
    else:
        logger.error("Backtest did not produce any results")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception("Trade tracking debug failed with error")
        print(f"Error: {e}")
        sys.exit(1)