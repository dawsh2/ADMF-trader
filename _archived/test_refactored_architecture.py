#!/usr/bin/env python
"""
Demo script to test the refactored architecture.

This script uses real market data from MINI_1min.csv and demonstrates:
1. MA Crossover strategy generating signals based only on market analysis
2. Risk manager handling position tracking and trading decisions
3. The clean separation of concerns in the new architecture
"""
import logging
import datetime
import pandas as pd
import sys
import os
import matplotlib.pyplot as plt
import numpy as np
from decimal import Decimal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('refactoring_test.log')
    ]
)

logger = logging.getLogger('refactoring_test')

# Import necessary components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from src.strategy.implementations.ma_crossover_pure import SimpleMACrossoverStrategy
from src.risk.managers.enhanced_risk_manager import EnhancedRiskManager

# Create a mock bar event class for testing with real data
class BarEvent:
    def __init__(self, symbol, timestamp, open_price, high, low, close, volume):
        self.symbol = symbol
        self.timestamp = timestamp
        self.open_price = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
    
    def get_symbol(self):
        return self.symbol
    
    def get_timestamp(self):
        return self.timestamp
    
    def get_open(self):
        return self.open_price
    
    def get_high(self):
        return self.high
    
    def get_low(self):
        return self.low
    
    def get_close(self):
        return self.close
    
    def get_volume(self):
        return self.volume

# Create a mock portfolio manager
class MockPortfolioManager:
    def __init__(self):
        # Start with no positions
        self.positions = {}
        self.equity = 10000.0
    
    def get_position(self, symbol):
        if symbol not in self.positions:
            return None
        return self.positions[symbol]
    
    def update_position(self, symbol, quantity):
        if symbol not in self.positions:
            self.positions[symbol] = MockPosition(symbol, 0)
        self.positions[symbol].quantity = quantity
        logger.info(f"Updated position for {symbol}: quantity = {quantity}")
        
    @property
    def equity(self):
        return self._equity
    
    @equity.setter
    def equity(self, value):
        self._equity = value

# Create a mock position
class MockPosition:
    def __init__(self, symbol, quantity):
        self.symbol = symbol
        self.quantity = quantity

# Helper function to print the event details
def print_event(event):
    if event is None:
        return
    
    event_type = event.event_type.name if hasattr(event, 'event_type') else 'Unknown'
    data = event.data if hasattr(event, 'data') else {}
    
    logger.info(f"Event: {event_type}")
    for key, value in data.items():
        logger.info(f"  {key}: {value}")

# Function to process order events and update the portfolio
def process_order(event):
    symbol = event.data.get('symbol')
    direction = event.data.get('direction')
    quantity = event.data.get('quantity')
    
    # Convert direction to a sign
    sign = 1 if direction == 'BUY' else -1
    
    # Update the position
    position_quantity = sign * quantity
    portfolio_manager.update_position(symbol, position_quantity)
    
    logger.info(f"Processed order: {direction} {quantity} shares of {symbol}")

# Load data from CSV file
def load_market_data(file_path):
    """Load market data from CSV file."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Check if required columns exist (case insensitive)
        column_mapping = {}
        csv_columns = [col.lower() for col in df.columns]
        
        # Check for required columns with case-insensitive matching
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for req_col in required_columns:
            found = False
            for actual_col in df.columns:
                if actual_col.lower() == req_col.lower():
                    column_mapping[req_col] = actual_col
                    found = True
                    break
            if not found:
                logger.error(f"Missing required column: {req_col}")
                return None
        
        # Create a copy with standardized column names
        standardized_df = pd.DataFrame()
        standardized_df['timestamp'] = pd.to_datetime(df[column_mapping['timestamp']])
        standardized_df['open'] = df[column_mapping['open']]
        standardized_df['high'] = df[column_mapping['high']]
        standardized_df['low'] = df[column_mapping['low']]
        standardized_df['close'] = df[column_mapping['close']]
        standardized_df['volume'] = df[column_mapping['volume']]
        
        # Extract symbol from filename
        symbol = os.path.basename(file_path).split('_')[0]
        
        logger.info(f"Loaded {len(standardized_df)} bars of data for {symbol}")
        return symbol, standardized_df
    
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return None

# Function to visualize the strategy results
def visualize_results(market_data, signals, positions):
    """Create visualization of market data, signals, and positions."""
    plt.figure(figsize=(12, 8))
    
    # Plot close prices
    plt.subplot(3, 1, 1)
    plt.plot(market_data['timestamp'], market_data['close'], label='Close Price')
    
    # Add fast and slow moving averages
    fast_window = 5
    slow_window = 15
    market_data['fast_ma'] = market_data['close'].rolling(window=fast_window).mean()
    market_data['slow_ma'] = market_data['close'].rolling(window=slow_window).mean()
    
    plt.plot(market_data['timestamp'], market_data['fast_ma'], label=f'Fast MA ({fast_window})')
    plt.plot(market_data['timestamp'], market_data['slow_ma'], label=f'Slow MA ({slow_window})')
    
    # Plot buy signals
    buy_signals = signals[signals['signal'] == 1]
    if not buy_signals.empty:
        plt.scatter(buy_signals['timestamp'], buy_signals['price'], 
                   marker='^', color='green', s=100, label='Buy Signal')
    
    # Plot sell signals
    sell_signals = signals[signals['signal'] == -1]
    if not sell_signals.empty:
        plt.scatter(sell_signals['timestamp'], sell_signals['price'], 
                   marker='v', color='red', s=100, label='Sell Signal')
    
    plt.title('Price and MA Crossover Signals')
    plt.legend()
    plt.grid(True)
    
    # Plot positions
    plt.subplot(3, 1, 2)
    plt.plot(positions['timestamp'], positions['quantity'], drawstyle='steps-post')
    plt.title('Position Size')
    plt.grid(True)
    
    # Plot equity curve (simplified)
    plt.subplot(3, 1, 3)
    plt.plot(market_data['timestamp'], market_data['close'] / market_data['close'].iloc[0] * 10000)
    plt.title('Price Performance (not P&L)')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('refactoring_test_results.png')
    logger.info("Created visualization: refactoring_test_results.png")

# Main demonstration function
def demonstrate_refactored_architecture():
    logger.info("=== Beginning Refactored Architecture Demonstration ===")
    
    # Create components
    event_bus = EventBus()
    
    # Load market data
    data_file = "data/MINI_1min.csv"
    data_result = load_market_data(data_file)
    
    if data_result is None:
        logger.error("Failed to load market data, aborting demonstration")
        return
    
    symbol, market_data = data_result
    
    # Create strategy - configure it for the symbol from data
    strategy = SimpleMACrossoverStrategy(event_bus, None, parameters={
        'symbols': [symbol],
        'fast_window': 5,  # Fast MA window
        'slow_window': 15  # Slow MA window
    })
    
    # Create risk manager with mock portfolio
    global portfolio_manager
    portfolio_manager = MockPortfolioManager()
    risk_manager = EnhancedRiskManager(event_bus, portfolio_manager)
    
    # Register event handlers
    event_bus.register(EventType.SIGNAL, print_event)
    event_bus.register(EventType.ORDER, print_event)
    event_bus.register(EventType.ORDER, process_order)
    
    logger.info("Components created and configured")
    logger.info(f"Using MA Crossover strategy with fast_window={strategy.fast_window}, slow_window={strategy.slow_window}")
    
    # Process each bar from the data
    logger.info("Beginning to process market data...")
    
    signal_count = 0
    order_count = 0
    
    # Create dataframes to store signals and positions for analysis
    signals_data = []
    positions_data = []
    
    # Process the first N bars for demonstration (otherwise too much output)
    max_bars = 300  # Increased for better visualization
    bar_count = min(len(market_data), max_bars)
    
    for i in range(bar_count):
        row = market_data.iloc[i]
        
        # Create bar event
        bar_event = BarEvent(
            symbol=symbol,
            timestamp=row['timestamp'],
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume']
        )
        
        # Process bar through strategy
        signal_event = strategy.on_bar(bar_event)
        
        # Count signals
        if signal_event:
            signal_count += 1
            # Emit signal to event bus (strategy should do this, but ensuring it happens)
            event_bus.emit(signal_event)
            
            # Record signal for analysis
            signals_data.append({
                'timestamp': signal_event.data['timestamp'],
                'price': signal_event.data['price'],
                'signal': signal_event.data['signal_value']
            })
        
        # Record position after each bar for analysis
        position_qty = 0
        if symbol in portfolio_manager.positions and portfolio_manager.positions[symbol]:
            position_qty = portfolio_manager.positions[symbol].quantity
            
        positions_data.append({
            'timestamp': row['timestamp'],
            'quantity': position_qty
        })
    
    # Print summary
    logger.info("=== Demonstration Complete ===")
    logger.info(f"Processed {bar_count} bars of market data")
    logger.info(f"Strategy generated {signal_count} signals")
    
    # Check final positions
    logger.info("Final positions:")
    for symbol, position in portfolio_manager.positions.items():
        logger.info(f"  {symbol}: {position.quantity} shares")
    
    logger.info("Check refactoring_test.log for detailed event logs")
    
    # Convert to dataframes for visualization
    signals_df = pd.DataFrame(signals_data) if signals_data else pd.DataFrame(columns=['timestamp', 'price', 'signal'])
    positions_df = pd.DataFrame(positions_data)
    
    # Visualize results if we have data
    if not signals_df.empty:
        visualize_results(market_data.iloc[:bar_count], signals_df, positions_df)

if __name__ == "__main__":
    demonstrate_refactored_architecture()
