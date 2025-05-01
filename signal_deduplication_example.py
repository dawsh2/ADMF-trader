#!/usr/bin/env python
"""
Example script showing how to use the signal deduplication solution in ADMF-Trader.

This script demonstrates:
1. Setting up the deduplication solution
2. Creating and emitting signals
3. Verifying deduplication works
"""
import logging
import datetime
import uuid
import time
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deduplication_example.log', mode='w')
    ]
)
logger = logging.getLogger("DeduplicationExample")

# Import required components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import Event, EventType
from src.core.bootstrap.deduplication_setup import setup_signal_deduplication

def create_signal_event(symbol, signal_value, price, rule_id=None):
    """
    Create a signal event for testing.
    
    Args:
        symbol: Instrument symbol
        signal_value: Signal value (positive for buy, negative for sell)
        price: Instrument price
        rule_id: Optional rule ID for deduplication
        
    Returns:
        Event: Signal event
    """
    timestamp = datetime.datetime.now()
    
    # Create signal data
    data = {
        'symbol': symbol,
        'signal_value': signal_value,
        'price': price,
    }
    
    # Add rule_id if provided
    if rule_id:
        data['rule_id'] = rule_id
    
    # Create and return event
    return Event(EventType.SIGNAL, data, timestamp)

def run_deduplication_demo():
    """
    Run a demonstration of the signal deduplication solution.
    """
    logger.info("=== Signal Deduplication Demo ===")
    
    # Create event bus
    event_bus = EventBus()
    
    # Set up signal deduplication
    logger.info("Setting up signal deduplication...")
    dedup_filter = setup_signal_deduplication(event_bus)
    if not dedup_filter:
        logger.error("Failed to set up deduplication")
        return False
    
    # Create counter to track signal processing
    signals_processed = 0
    
    # Create signal handler
    def signal_handler(event):
        nonlocal signals_processed
        signals_processed += 1
        symbol = event.data.get('symbol', 'UNKNOWN')
        signal_value = event.data.get('signal_value', 0)
        rule_id = event.data.get('rule_id', 'NONE')
        direction = "BUY" if signal_value > 0 else "SELL" if signal_value < 0 else "NEUTRAL"
        logger.info(f"Signal processed: {direction} {symbol}, rule_id={rule_id}")
    
    # Register signal handler
    event_bus.register(EventType.SIGNAL, signal_handler)
    
    # Create a unique rule_id
    rule_id = f"test_rule_{uuid.uuid4()}"
    logger.info(f"Generated rule_id: {rule_id}")
    
    # Create two identical signals with the same rule_id
    signal1 = create_signal_event("AAPL", 1.0, 185.50, rule_id)
    signal2 = create_signal_event("AAPL", 1.0, 185.75, rule_id)
    
    # Create a different signal with a different rule_id
    diff_rule_id = f"test_rule_{uuid.uuid4()}"
    signal3 = create_signal_event("MSFT", -1.0, 390.25, diff_rule_id)
    
    # Emit first signal
    logger.info(f"Emitting first signal with rule_id: {rule_id}")
    event_bus.emit(signal1)
    
    # Check signal processing
    logger.info(f"Signals processed after first signal: {signals_processed}")
    
    # Emit duplicate signal
    logger.info(f"Emitting duplicate signal with rule_id: {rule_id}")
    event_bus.emit(signal2)
    
    # Check signal processing - should not increase
    logger.info(f"Signals processed after duplicate signal: {signals_processed}")
    
    # Emit different signal
    logger.info(f"Emitting different signal with rule_id: {diff_rule_id}")
    event_bus.emit(signal3)
    
    # Check signal processing - should increase
    logger.info(f"Signals processed after different signal: {signals_processed}")
    
    # Verify deduplication worked correctly
    if signals_processed == 2:
        logger.info("✓ Deduplication succeeded - duplicate signal was blocked")
        success = True
    else:
        logger.error(f"✗ Deduplication failed - expected 2 signals, got {signals_processed}")
        success = False
    
    return success

if __name__ == "__main__":
    success = run_deduplication_demo()
    sys.exit(0 if success else 1)
