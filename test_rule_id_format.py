#!/usr/bin/env python3
"""
Simple test script to verify signal to order pipeline with correct rule_id format.
"""

import logging
import sys
import datetime
import uuid
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler(f"rule_id_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger
logger = logging.getLogger("rule_id_test")

def test_signal_creation():
    """Test signal creation with proper rule_id format."""
    
    # Create signal events with proper rule_id format
    signals = []
    for i in range(5):
        direction = "BUY" if i % 2 == 0 else "SELL"
        symbol = "MINI"
        
        # Create rule_id with proper format
        rule_id = f"ma_crossover_{symbol}_{direction}_group_{i+1}"
        
        # Create signal event
        signal = {
            "id": str(uuid.uuid4()),
            "symbol": symbol,
            "direction": direction,
            "signal_value": 1 if direction == "BUY" else -1,
            "price": 100.0 + i,
            "timestamp": datetime.datetime.now(),
            "rule_id": rule_id
        }
        
        signals.append(signal)
        logger.info(f"Created signal: {signal['direction']} {signal['symbol']} with rule_id={signal['rule_id']}")
    
    return signals

def process_signals(signals):
    """Process signals and create orders."""
    processed_rule_ids = set()
    orders = []
    
    for signal in signals:
        rule_id = signal.get("rule_id")
        
        # Check if rule_id already processed
        if rule_id in processed_rule_ids:
            logger.info(f"REJECTING: Signal with rule_id {rule_id} already processed")
            continue
        
        # Process signal
        logger.info(f"PROCESSING: Signal with rule_id {rule_id}")
        
        # Add rule_id to processed set
        processed_rule_ids.add(rule_id)
        
        # Create order
        order = {
            "id": str(uuid.uuid4()),
            "symbol": signal["symbol"],
            "direction": signal["direction"],
            "quantity": 10,
            "price": signal["price"],
            "timestamp": datetime.datetime.now(),
            "rule_id": rule_id
        }
        
        orders.append(order)
        logger.info(f"Created order: {order['direction']} {order['quantity']} {order['symbol']} @ {order['price']} with rule_id: {order['rule_id']}")
    
    return orders, processed_rule_ids

def duplicate_signals(signals):
    """Create duplicate signals to test deduplication."""
    duplicates = []
    
    for signal in signals:
        # Create duplicate with same rule_id but different ID
        duplicate = signal.copy()
        duplicate["id"] = str(uuid.uuid4())
        duplicate["timestamp"] = datetime.datetime.now()
        
        duplicates.append(duplicate)
        logger.info(f"Created duplicate signal with rule_id={duplicate['rule_id']}")
    
    return duplicates

def main():
    """Run the test."""
    logger.info("Starting rule_id format test")
    
    # Create signals
    signals = test_signal_creation()
    
    # Process signals
    orders, processed_rule_ids = process_signals(signals)
    
    # Create and process duplicate signals
    duplicates = duplicate_signals(signals)
    duplicate_orders, _ = process_signals(duplicates)
    
    # Verify results
    logger.info("\n=== TEST RESULTS ===")
    logger.info(f"Original signals: {len(signals)}")
    logger.info(f"Orders created: {len(orders)}")
    logger.info(f"Processed rule_ids: {len(processed_rule_ids)}")
    logger.info(f"Duplicate signals: {len(duplicates)}")
    logger.info(f"Orders from duplicates: {len(duplicate_orders)}")
    
    # Test success?
    if len(orders) == len(signals) and len(duplicate_orders) == 0:
        logger.info("TEST PASSED: All original signals created orders, all duplicates were rejected")
        print("TEST PASSED: Signal deduplication working correctly!")
    else:
        logger.error("TEST FAILED: Expected orders != actual orders or duplicates were not rejected")
        print("TEST FAILED: Signal deduplication not working correctly!")

if __name__ == "__main__":
    main()
