#!/usr/bin/env python3
"""
Test script for HistoricalDataHandler.

This script tests the HistoricalDataHandler implementation to verify that
it properly implements the DataHandler interface and can load data.
"""

import logging
from src.data.historical_data_handler import HistoricalDataHandler
from src.core.event_system import EventBus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test the HistoricalDataHandler implementation."""
    logger.info("Testing HistoricalDataHandler implementation")
    
    # Create data configuration
    data_config = {
        'timeframe': '1MIN',
        'sources': [
            {
                'symbol': 'SPY',
                'file': './data/SPY_1min.csv',
                'date_format': '%Y-%m-%d %H:%M:%S'
            }
        ]
    }
    
    # Create event bus
    event_bus = EventBus()
    
    # Create data handler
    handler = HistoricalDataHandler('test_data_handler', data_config)
    
    # Initialize with context
    handler.initialize({'event_bus': event_bus})
    
    # Test load_data method
    logger.info("Testing load_data method")
    success = handler.load_data(['SPY'])
    logger.info(f"load_data result: {success}")
    
    # Test get_symbols method
    symbols = handler.get_symbols()
    logger.info(f"Loaded symbols: {symbols}")
    
    # Test get_latest_bar method
    logger.info("Testing get_latest_bar method")
    bar = handler.get_latest_bar('SPY')
    logger.info(f"Latest bar: {bar}")
    
    # Test update_bars method
    logger.info("Testing update_bars method")
    has_more = handler.update_bars()
    logger.info(f"update_bars result: {has_more}")
    
    # Test split_data method
    logger.info("Testing split_data method")
    train_data, test_data = handler.split_data(train_ratio=0.7)
    logger.info(f"Train data symbols: {list(train_data.keys())}")
    logger.info(f"Test data symbols: {list(test_data.keys())}")
    
    logger.info("HistoricalDataHandler tests completed")

if __name__ == "__main__":
    main()