"""
Example script demonstrating the strategy framework.

This script shows how to:
1. Set up multiple strategies
2. Connect them to data sources
3. Process market data
4. Handle generated signals
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

# Add the project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.event_system.event_bus import EventBus
from src.core.event_system.event_types import EventType
from src.data.csv_data_handler import CSVDataHandler
from src.strategy.implementations.ma_crossover import MovingAverageCrossover
from src.strategy.implementations.multi_tf_ma_crossover import MultiTimeframeMACrossover
from src.data.data_types import Timeframe
from src.core.logging import configure_logging, get_logger, STRATEGY_PREFIX, DATA_PREFIX

# Get logger - will be configured based on command line arguments
logger = get_logger(__name__)

class SignalHandler:
    """Simple handler for signal events."""
    
    def __init__(self, name="SignalHandler"):
        """Initialize the signal handler."""
        self.name = name
        self.signals = []
    
    def on_signal(self, event):
        """
        Process a signal event.
        
        Args:
            event: Signal event
        """
        signal_data = event.data
        self.signals.append(signal_data)
        
        # Log the signal
        symbol = signal_data['symbol']
        direction = signal_data['direction']
        signal_type = signal_data['type']
        direction_str = "LONG" if direction > 0 else "SHORT" if direction < 0 else "FLAT"
        
        logger.info(f"Signal received: {signal_type} {direction_str} for {symbol}")
        logger.info(f"Signal metadata: {signal_data['metadata']}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Strategy Example")
    
    # Data options
    parser.add_argument('--symbol', default='SPY', help='Symbol to use')
    parser.add_argument('--timeframe', default='1min', help='Timeframe to use')
    parser.add_argument('--bars', type=int, default=500, help='Number of bars to process (0 for all)')
    parser.add_argument('--all-bars', action='store_true', help='Process all available bars')
    
    # Logging options
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--debug-strategy', action='store_true', help='Debug only strategy module')
    parser.add_argument('--debug-data', action='store_true', help='Debug only data module')
    parser.add_argument('--log-file', help='Write logs to file')
    parser.add_argument('--quiet', action='store_true', help='Suppress console output')
    
    return parser.parse_args()

def main():
    """Run the strategy example."""
    # Parse arguments
    args = parse_args()
    
    # Configure logging
    debug_modules = []
    if args.debug_strategy:
        debug_modules.append(STRATEGY_PREFIX)
    if args.debug_data:
        debug_modules.append(DATA_PREFIX)
        
    configure_logging(
        debug=args.debug or bool(debug_modules),  # Set debug mode if any module is debugged
        debug_modules=debug_modules,
        log_file=args.log_file,
        console=not args.quiet
    )
    
    # Create the event bus
    event_bus = EventBus()
    
    # Create the data handler
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    data_handler = CSVDataHandler(
        name='csv_handler',
        data_dir=data_dir,
        date_format='%Y-%m-%d %H:%M:%S'
    )
    
    # Set the event bus for the data handler
    data_handler.event_bus = event_bus
    
    # Create the strategies
    # 1. Simple MA Crossover
    ma_strategy = MovingAverageCrossover(
        name="ma_crossover",
        fast_period=5,
        slow_period=20
    )
    
    # 2. Multi-Timeframe MA Crossover
    multi_tf_strategy = MultiTimeframeMACrossover(
        name="multi_tf_ma_crossover",
        entry_tf=Timeframe.MINUTE_1,
        filter_tf=Timeframe.HOUR_1,
        fast_period=5,
        slow_period=20,
        filter_fast_period=3,
        filter_slow_period=10
    )
    
    # Set the event bus for the strategies
    ma_strategy.event_bus = event_bus
    multi_tf_strategy.event_bus = event_bus
    
    # Create the signal handler
    signal_handler = SignalHandler()
    
    # Subscribe to signal events
    event_bus.subscribe(EventType.SIGNAL, signal_handler.on_signal)
    
    # Subscribe strategies to BAR events
    event_bus.subscribe(EventType.BAR, ma_strategy.on_bar)
    event_bus.subscribe(EventType.BAR, multi_tf_strategy.on_bar)
    
    # Load data
    symbols = [args.symbol]
    # Load without date filtering to ensure we get data
    data_handler.load_data(
        symbols=symbols,
        timeframe=args.timeframe
    )
    
    # Add symbols to strategies
    ma_strategy.add_symbols(symbols)
    multi_tf_strategy.add_symbols(symbols)
    
    # Initialize strategies
    ma_strategy.initialize()
    multi_tf_strategy.initialize()
    
    # Process market data
    logger.info("Processing market data...")
    
    # Add more detailed logging
    logger.info(f"Data handler has loaded {len(data_handler.bars.get('SPY', []))} bars for SPY")
    
    # Process bars based on command-line argument
    total_bars = len(data_handler.bars.get('SPY', []))
    process_count = total_bars if args.all_bars or args.bars == 0 else min(args.bars, total_bars)
    
    logger.info(f"Processing {process_count} bars out of {total_bars} total bars")
    
    signal_count = 0
    crossover_count = 0
    
    for i in range(process_count):
        if i % 1000 == 0 and i > 0:
            logger.info(f"Processed {i} bars, found {crossover_count} crossovers resulting in {signal_count} signals")
        
        if args.debug:
            logger.debug(f"Processing bar {i}")
            
        # Track signals before update
        old_signal_count = len(signal_handler.signals)
        
        # Update bar
        data_handler.update_bars()
        
        # Check if any new signals were generated
        new_signal_count = len(signal_handler.signals)
        if new_signal_count > old_signal_count:
            new_signals = new_signal_count - old_signal_count
            signal_count += new_signals
            crossover_count += 1
            if args.verbose:
                logger.info(f"Bar {i}: Generated {new_signals} signals")
    
    # Log results
    logger.info(f"Processed {len(signal_handler.signals)} signals in total")
    if signal_handler.signals:
        logger.info(f"Last signal: {signal_handler.signals[-1]}")

if __name__ == "__main__":
    main()