#!/usr/bin/env python3
"""
Verify that the portfolio is properly tracking and recording trades.

This diagnostic script checks if:
1. Trades are being opened/closed properly
2. Completed trades are being recorded
3. There are any issues with the statistics calculation
"""
import sys
import logging
import time
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("verify")

# Imports from the trading system
try:
    from src.risk.portfolio.portfolio import PortfolioManager
    from src.core.events.event_bus import EventBus
    from src.core.events.event_types import EventType, Event
    from src.core.events.event_utils import create_trade_open_event, create_trade_close_event
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

def create_test_events():
    """Create a series of test events to verify trade tracking."""
    events = []
    
    # Create a test symbol and timestamps
    symbol = "TEST"
    timestamp = datetime.datetime.now()
    
    # Create TRADE_OPEN event
    open_event = create_trade_open_event(
        symbol=symbol,
        direction="BUY",
        quantity=100,
        price=100.0,
        commission=1.0,
        timestamp=timestamp,
        rule_id="test_rule_1",
        order_id="test_order_1",
        transaction_id="test_transaction_1"
    )
    events.append(open_event)
    
    # Create TRADE_CLOSE event (5 minutes later)
    close_timestamp = timestamp + datetime.timedelta(minutes=5)
    close_event = create_trade_close_event(
        symbol=symbol,
        direction="SELL",
        quantity=100,
        entry_price=100.0,
        exit_price=101.0,
        entry_time=timestamp,
        exit_time=close_timestamp,
        pnl=100.0,  # $1 profit × 100 shares
        commission=1.0,
        rule_id="test_rule_2",
        order_id="test_order_2",
        transaction_id="test_transaction_2"
    )
    events.append(close_event)
    
    return events

def setup_test_portfolio():
    """Create and configure a test portfolio."""
    event_bus = EventBus()
    portfolio = PortfolioManager(event_bus, name="test_portfolio", initial_cash=100000.0)
    
    # Reset to ensure clean state
    portfolio.reset()
    
    return event_bus, portfolio

def run_trade_test():
    """Run a complete test of the portfolio trade tracking."""
    logger.info("Setting up test portfolio...")
    event_bus, portfolio = setup_test_portfolio()
    
    # Verify portfolio is initialized properly
    logger.info(f"Initial portfolio cash: {portfolio.cash}")
    logger.info(f"Initial portfolio equity: {portfolio.equity}")
    logger.info(f"Initial trade count: {len(portfolio.trades)}")
    
    # Create test events
    events = create_test_events()
    logger.info(f"Created {len(events)} test events")
    
    # Process events
    logger.info("Processing trade events...")
    for event in events:
        if event.get_type() == EventType.TRADE_OPEN:
            logger.info(f"Processing TRADE_OPEN for {event.data.get('symbol')}")
            portfolio.on_trade_open(event)
        elif event.get_type() == EventType.TRADE_CLOSE:
            logger.info(f"Processing TRADE_CLOSE for {event.data.get('symbol')}")
            portfolio.on_trade_close(event)
        
        # Sleep briefly to ensure event processing completes
        time.sleep(0.1)
    
    # Check results
    logger.info(f"Final trade count: {len(portfolio.trades)}")
    logger.info(f"Final portfolio cash: {portfolio.cash}")
    logger.info(f"Final portfolio equity: {portfolio.equity}")
    
    # Dump trade details
    if portfolio.trades:
        logger.info("Trade details:")
        for i, trade in enumerate(portfolio.trades):
            logger.info(f"Trade {i+1}:")
            for key, value in trade.items():
                logger.info(f"  {key}: {value}")
    else:
        logger.warning("No trades were recorded!")
    
    # Check portfolio stats
    stats = portfolio.get_stats()
    logger.info("Portfolio statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    # Get recent trades using the method that's used for reporting
    # Explicitly set filter_open=False to include OPEN trades
    recent_trades = portfolio.get_recent_trades(filter_open=False)
    logger.info(f"get_recent_trades() returned {len(recent_trades)} trades with filter_open=False")
    
    # Verify if trade filtering is working
    if recent_trades:
        logger.info("Recent trades verification:")
        logger.info(f"  First trade PnL: {recent_trades[0].get('pnl')}")
        
    # Check for trade status field
    if portfolio.trades:
        status_count = sum(1 for t in portfolio.trades if 'status' in t)
        logger.info(f"Trades with status field: {status_count} out of {len(portfolio.trades)}")
        
        # Count by status
        open_count = sum(1 for t in portfolio.trades if t.get('status') == 'OPEN')
        closed_count = sum(1 for t in portfolio.trades if t.get('status') == 'CLOSED')
        logger.info(f"  OPEN trades: {open_count}")
        logger.info(f"  CLOSED trades: {closed_count}")
    
    return portfolio.trades, recent_trades

def main():
    """Main function."""
    logger.info("Starting portfolio trade verification...")
    
    # Run the test
    all_trades, recent_trades = run_trade_test()
    
    # Print summary
    print("\n====== PORTFOLIO TRADE VERIFICATION SUMMARY ======")
    print(f"Total trades in portfolio: {len(all_trades)}")
    print(f"Trades returned by get_recent_trades(): {len(recent_trades)}")
    
    # Check for discrepancies
    if len(all_trades) != len(recent_trades):
        print(f"\nWARNING: Trade count mismatch - portfolio has {len(all_trades)} trades but get_recent_trades() returned {len(recent_trades)}!")
        print("This indicates a filtering issue in the get_recent_trades() method.")
        
        # Check filtration
        if len(all_trades) > 0 and len(recent_trades) == 0:
            print("\nPossible issues:")
            print("1. Trades may all have status='OPEN' and get_recent_trades() is filtering them out")
            print("2. Trades may have invalid PnL values")
            print("3. There may be a deduplication issue in get_recent_trades()")
    
    # Provide guidance
    if len(recent_trades) == 0:
        print("\nRECOMMENDATIONS:")
        print("1. Check src/risk/portfolio/portfolio.py - get_recent_trades() method")
        print("2. Verify that trades are being assigned status='CLOSED' when completed")
        print("3. Check if trades are being properly recorded with valid PnL values")
        print("4. Ensure the position_action field is being correctly set in orders")
    else:
        print("\nPORTFOLIO TRADE VERIFICATION PASSED!")
        print("The portfolio correctly processes and records trades.")
    
    print("\n=================================================")

if __name__ == "__main__":
    main()