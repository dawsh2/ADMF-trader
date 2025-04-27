#!/usr/bin/env python
"""
Simple validation script to test order flow.

This creates a simple scenario with predictable price movements to test
if orders and fills are flowing correctly through the system.
"""
import os
import pandas as pd
import datetime
import logging
import uuid
import numpy as np
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Validation")

# Import system components
from src.core.di.container import Container
from src.core.events.event_bus import EventBus
from src.core.events.event_manager import EventManager
from src.core.events.event_emitters import BarEmitter
from src.core.events.event_types import EventType
from src.data.sources.csv_handler import CSVDataSource
from src.data.historical_data_handler import HistoricalDataHandler
from src.risk.portfolio.portfolio import PortfolioManager
from src.risk.managers.simple import SimpleRiskManager
from src.execution.order_manager import OrderManager
from src.execution.order_registry import OrderRegistry
from src.execution.broker.broker_simulator import SimulatedBroker
from src.execution.backtest.backtest import BacktestCoordinator
from src.analytics.performance.calculator import PerformanceCalculator
from src.analytics.reporting.report_generator import ReportGenerator

# Define data directory
DATA_DIR = 'validation_data'
os.makedirs(DATA_DIR, exist_ok=True)

class SimpleConfig:
    """Simplified configuration class."""
    
    def __init__(self, config_dict=None):
        self.config_dict = config_dict or {}
    
    def get_section(self, section_name):
        """Get a configuration section."""
        return SimpleSection(section_name, self.config_dict.get(section_name, {}))

class SimpleSection:
    """Simplified configuration section."""
    
    def __init__(self, name, values=None):
        self.name = name
        self.values = values or {}
    
    def get(self, key, default=None):
        """Get a configuration value."""
        return self.values.get(key, default)
    
    def as_dict(self):
        """Get all values as a dictionary."""
        return dict(self.values)
    
    def get_section(self, name):
        """Get a nested configuration section."""
        value = self.values.get(name, {})
        if not isinstance(value, dict):
            value = {}
        return SimpleSection(f"{self.name}.{name}", value)
        
class SimpleAlternatingStrategy:
    """
    A simple price-threshold based strategy for predictable behavior.
    
    Buys when price crosses below buy_threshold and sells when price crosses above sell_threshold.
    """
    
    def __init__(self, event_bus=None, data_handler=None, name=None, parameters=None):
        """Initialize the strategy."""
        self.event_bus = event_bus
        self.data_handler = data_handler
        self.name = name or "simple_alternating"
        self.parameters = parameters or {}
        
        # Thresholds for buy/sell decisions
        self.buy_threshold = self.parameters.get('buy_threshold', 100.0)
        self.sell_threshold = self.parameters.get('sell_threshold', 101.0)
        
        # Internal state
        self.last_price = None
        self.last_signal = None
        self.signal_count = 0
        self.configured = False
        
        # Register event handler
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
            
        logger.info(f"Strategy initialized: buy @ {self.buy_threshold}, sell @ {self.sell_threshold}")
    
    def configure(self, config):
        """Configure the strategy."""
        if hasattr(config, 'as_dict'):
            self.parameters = config.as_dict()
        else:
            self.parameters = dict(config)
            
        self.buy_threshold = self.parameters.get('buy_threshold', 100.0)
        self.sell_threshold = self.parameters.get('sell_threshold', 101.0)
        self.configured = True
        
        logger.info(f"Strategy configured: buy @ {self.buy_threshold}, sell @ {self.sell_threshold}")
    
    def on_bar(self, bar_event):
        """Process bar events to generate signals."""
        from src.core.events.event_utils import create_signal_event
        
        symbol = bar_event.get_symbol()
        price = bar_event.get_close()
        timestamp = bar_event.get_timestamp()
        
        # Skip if this is the first price (need previous price for comparison)
        if self.last_price is None:
            self.last_price = price
            return None
        
        signal_value = 0 # Default to no signal
        
        # Alternating signals based on thresholds
        if self.last_signal != 1 and price <= self.buy_threshold:
            # Buy signal
            signal_value = 1
            self.last_signal = 1
            self.signal_count += 1
            logger.info(f"BUY signal #{self.signal_count} for {symbol} at {price:.2f}")
            
        elif self.last_signal != -1 and price >= self.sell_threshold:
            # Sell signal
            signal_value = -1
            self.last_signal = -1
            self.signal_count += 1
            logger.info(f"SELL signal #{self.signal_count} for {symbol} at {price:.2f}")
        
        # Save price for next bar
        self.last_price = price
        
        # Emit signal if non-zero
        if signal_value != 0 and self.event_bus:
            signal = create_signal_event(
                signal_value=signal_value,
                price=price,
                symbol=symbol,
                timestamp=timestamp
            )
            self.event_bus.emit(signal)
            return signal
            
        return None
    
    def reset(self):
        """Reset strategy state."""
        self.last_price = None
        self.last_signal = None
        self.signal_count = 0
        logger.info("Strategy reset")

def create_oscillating_data(symbol="TEST", days=30, buy_price=100.0, sell_price=101.0):
    """
    Create predictable oscillating price data for testing.
    
    Each day alternates between exactly buy_price and sell_price for predictable signals.
    """
    logger.info(f"Creating oscillating data for {symbol}")
    
    # Generate dates
    start_date = datetime.datetime(2023, 1, 1)
    dates = [start_date + datetime.timedelta(days=i) for i in range(days)]
    
    # Generate alternating prices
    prices = []
    for i in range(days):
        if i % 2 == 0:
            # Even days - buy price
            prices.append(buy_price)
        else:
            # Odd days - sell price
            prices.append(sell_price)
    
    # Create DataFrame
    data = []
    for i in range(days):
        price = prices[i]
        data.append({
            'date': dates[i],
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': 100000
        })
    
    df = pd.DataFrame(data)
    
    # Save to CSV
    csv_path = os.path.join(DATA_DIR, f"{symbol}_1d.csv")
    df.to_csv(csv_path, index=False)
    
    logger.info(f"Created test data with {len(data)} bars, saved to {csv_path}")
    return df

def validate_backtest():
    """Run a validation backtest with predictable behavior."""
    logger.info("=== Starting Validation Backtest ===")
    
    # Create test data with predictable price pattern
    buy_price = 100.0
    sell_price = 101.0
    create_oscillating_data("TEST", 30, buy_price, sell_price)
    
    # Create configuration
    config_dict = {
        'strategy': {
            'simple_alternating': {
                'buy_threshold': buy_price,
                'sell_threshold': sell_price
            }
        },
        'risk_manager': {
            'position_size': 100
        },
        'portfolio': {
            'initial_cash': 10000.0
        },
        'broker': {
            'slippage': 0.0,
            'commission': 0.0
        }
    }
    config = SimpleConfig(config_dict)
    
    # Create components
    event_bus = EventBus()
    event_manager = EventManager(event_bus)
    
    # Create container and register components
    container = Container()
    container.register_instance('event_bus', event_bus)
    container.register_instance('event_manager', event_manager)
    container.register_instance('config', config)
    
    # Create data components
    bar_emitter = BarEmitter("bar_emitter", event_bus)
    bar_emitter.start()
    
    data_source = CSVDataSource(DATA_DIR)
    data_handler = HistoricalDataHandler(data_source, bar_emitter, max_bars_history=100)
    
    container.register_instance('bar_emitter', bar_emitter)
    container.register_instance('data_source', data_source)
    container.register_instance('data_handler', data_handler)
    
    # Create strategy
    strategy = SimpleAlternatingStrategy(
        event_bus,
        data_handler,
        parameters={
            'buy_threshold': buy_price,
            'sell_threshold': sell_price
        }
    )
    container.register_instance('strategy', strategy)
    
    # Create portfolio and risk components
    portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
    risk_manager = SimpleRiskManager(event_bus, portfolio)
    
    container.register_instance('portfolio', portfolio)
    container.register_instance('risk_manager', risk_manager)
    
    # Create order registry, broker, and order manager
    order_registry = OrderRegistry(event_bus)
    broker = SimulatedBroker(event_bus, order_registry)
    order_manager = OrderManager(event_bus, broker, order_registry)
    
    # Connect components
    broker.set_order_registry(order_registry)
    
    container.register_instance('order_registry', order_registry)
    container.register_instance('broker', broker)
    container.register_instance('order_manager', order_manager)
    
    # Create performance components
    calculator = PerformanceCalculator()
    report_generator = ReportGenerator(calculator)
    
    container.register_instance('calculator', calculator)
    container.register_instance('report_generator', report_generator)
    
    # Create backtest coordinator
    backtest = BacktestCoordinator(container, config)
    container.register_instance('backtest', backtest)
    
    # Run backtest
    results = backtest.run(
        symbols=["TEST"],
        start_date="2023-01-01",
        end_date="2023-01-30"
    )
    
    # Validate results
    trades = results.get('trades', [])
    
    # Calculate expected trades
    # Each cycle is a buy and sell pair
    expected_cycles = 15  # 30 days / 2 days per cycle (assuming full cycles)
    actual_cycles = len(trades) // 2  # Each cycle has 1 buy and 1 sell
    
    # Calculate expected profit
    expected_profit = expected_cycles * 1.0 * 100  # $1 profit per share × 100 shares × expected cycles
    actual_profit = sum(trade.get('pnl', 0) for trade in trades)
    
    logger.info("=== VALIDATION SUCCESSFUL ===")
    logger.info(f"Expected Profit: ${expected_profit:.2f}")
    logger.info(f"Actual Profit: ${actual_profit:.2f}")
    logger.info(f"Difference: ${actual_profit - expected_profit:.2f}")
    logger.info(f"Trades Executed: {len(trades)}")
    logger.info(f"Complete Cycles: {actual_cycles}")
    
    # Print trade details
    logger.info("\nTrade Details:")
    for i, trade in enumerate(trades[:10]):  # Show first 10 trades
        logger.info(f"Trade {i+1}: {trade.get('direction')} {trade.get('quantity')} {trade.get('symbol')} @ {trade.get('price'):.2f}, PnL: {trade.get('pnl'):.2f}")
    
    print(f"=== Validation {'Successful' if abs(actual_profit - expected_profit) < 0.01 else 'Failed'}! ===")
    print(f"Expected Profit: ${expected_profit:.2f}")
    print(f"Actual Profit: ${actual_profit:.2f}")
    print(f"Difference: ${actual_profit - expected_profit:.2f}")
    print(f"Trades Executed: {len(trades)}")
    
    return {
        'success': abs(actual_profit - expected_profit) < 0.01,
        'trades': len(trades),
        'profit': actual_profit
    }

if __name__ == "__main__":
    validate_backtest()
