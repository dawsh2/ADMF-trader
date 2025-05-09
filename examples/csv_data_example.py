"""
Example script demonstrating the use of the CSV data handler.
"""

import os
import logging
import sys
from datetime import datetime, timedelta

# Add the project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.csv_data_handler import CSVDataHandler
from src.core.event_system.event_bus import EventBus
from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class BarPrinter:
    """Simple subscriber that prints bar events."""
    
    def __init__(self, event_bus):
        """Initialize and subscribe to bar events."""
        self.event_bus = event_bus
        self.event_bus.subscribe(EventType.BAR, self.on_bar)
        
    def on_bar(self, event):
        """Handle bar events."""
        bar_data = event.data
        logger.info(f"Received bar: {bar_data['symbol']} - {bar_data['timestamp']} - "
                   f"O: {bar_data['open']:.2f}, H: {bar_data['high']:.2f}, "
                   f"L: {bar_data['low']:.2f}, C: {bar_data['close']:.2f}, "
                   f"V: {bar_data['volume']}")

def main():
    """Run the CSV data handler example."""
    # Create the event bus
    event_bus = EventBus()
    
    # Create the data handler
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    data_handler = CSVDataHandler(
        name='csv_handler',
        data_dir=data_dir,
        date_format='%Y-%m-%d %H:%M:%S'
    )
    
    # Set the event bus
    data_handler.event_bus = event_bus
    
    # Create a subscriber
    bar_printer = BarPrinter(event_bus)
    
    # Load data
    symbols = ['SPY']
    start_date = datetime.now() - timedelta(days=30)  # Last 30 days
    success = data_handler.load_data(
        symbols=symbols,
        start_date=start_date,
        timeframe='1min'
    )
    
    if not success:
        logger.error("Failed to load data")
        return
    
    # Print some statistics
    for symbol in symbols:
        bars = data_handler.get_all_bars(symbol)
        if bars:
            logger.info(f"Loaded {len(bars)} bars for {symbol}")
            logger.info(f"Date range: {bars[0].timestamp} to {bars[-1].timestamp}")
        else:
            logger.warning(f"No bars loaded for {symbol}")
    
    # Process some bars
    logger.info("Starting bar updates")
    for _ in range(10):  # Process first 10 bars
        data_handler.update_bars()
    
    # Split the data
    train_data, test_data = data_handler.split_data(train_ratio=0.8)
    
    for symbol in symbols:
        logger.info(f"Train data for {symbol}: {len(train_data[symbol])} bars")
        logger.info(f"Test data for {symbol}: {len(test_data[symbol])} bars")
    
    # Reset the data handler
    logger.info("Resetting data handler")
    data_handler.reset()
    
    # Process some more bars
    logger.info("Continuing with bar updates after reset")
    for _ in range(5):  # Process first 5 bars after reset
        data_handler.update_bars()

if __name__ == "__main__":
    main()