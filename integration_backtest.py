#!/usr/bin/env python
"""
Simple MA Crossover Backtest Script

This script runs a Moving Average Crossover strategy backtest using
the ADMF-Trader framework with proper dependency injection.
"""
import os
import logging
import datetime
import pandas as pd
import numpy as np
import yaml
from typing import Dict, List, Optional, Union, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backtest.log', mode='w')
    ]
)
logger = logging.getLogger("ADMF-Trader")

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
from src.execution.broker.broker_simulator import SimulatedBroker
from src.execution.backtest.backtest import BacktestCoordinator
from src.analytics.performance.calculator import PerformanceCalculator
from src.analytics.reporting.report_generator import ReportGenerator
from src.execution.order_manager import OrderManager

# Create Simple Config class
class SimpleConfig:
    """Simplified configuration for use in backtest."""
    
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

# Create test data directory
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

class SimpleMAStrategy:
    """Simple Moving Average Crossover Strategy."""
    
    def __init__(self, event_bus, data_handler, name=None, parameters=None):
        """Initialize the strategy."""
        self.event_bus = event_bus
        self.data_handler = data_handler
        self.name = name or "ma_crossover"
        self.parameters = parameters or {}
        
        # Default parameters
        self.fast_window = self.parameters.get('fast_window', 10)
        self.slow_window = self.parameters.get('slow_window', 30)
        self.symbols = self.parameters.get('symbols', [])
        
        # Internal state
        self.data = {symbol: [] for symbol in self.symbols}
        self.signal_count = 0
        self.configured = False
        
        logger.info(f"Strategy initialized with fast_window={self.fast_window}, slow_window={self.slow_window}")
        
        # Register for bar events
        if self.event_bus:
            self.event_bus.register(EventType.BAR, self.on_bar)
    
    def configure(self, config):
        """Configure the strategy with parameters."""
        if hasattr(config, 'as_dict'):
            self.parameters = config.as_dict()
        else:
            self.parameters = dict(config)
            
        # Update parameters
        self.fast_window = self.parameters.get('fast_window', 10)
        self.slow_window = self.parameters.get('slow_window', 30)
        self.symbols = self.parameters.get('symbols', [])
        
        # Initialize data storage for each symbol
        self.data = {symbol: [] for symbol in self.symbols}
        
        self.configured = True
        logger.info(f"Strategy configured with parameters: {self.parameters}")
    
    def on_bar(self, bar_event):
        """Handle bar events."""
        symbol = bar_event.get_symbol()
        if symbol not in self.symbols:
            return
        
        # Store bar data
        close_price = bar_event.get_close()
        timestamp = bar_event.get_timestamp()
        
        if symbol not in self.data:
            self.data[symbol] = []
            
        self.data[symbol].append({
            'timestamp': timestamp,
            'close': close_price
        })
        
        # Wait until we have enough data
        if len(self.data[symbol]) <= self.slow_window:
            return
        
        # Calculate moving averages
        closes = [bar['close'] for bar in self.data[symbol]]
        fast_ma = sum(closes[-self.fast_window:]) / self.fast_window
        slow_ma = sum(closes[-self.slow_window:]) / self.slow_window
        
        # Check for crossover
        prev_fast_ma = sum(closes[-(self.fast_window+1):-1]) / self.fast_window
        prev_slow_ma = sum(closes[-(self.slow_window+1):-1]) / self.slow_window
        
        # Generate signal on crossover
        from src.core.events.event_utils import create_signal_event
        
        if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
            # Buy signal
            self.signal_count += 1
            signal = create_signal_event(
                signal_value=1,  # Buy
                price=close_price,
                symbol=symbol,
                timestamp=timestamp
            )
            logger.info(f"BUY signal #{self.signal_count} for {symbol} at {close_price:.2f}")
            self.event_bus.emit(signal)
            
        elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
            # Sell signal
            self.signal_count += 1
            signal = create_signal_event(
                signal_value=-1,  # Sell
                price=close_price,
                symbol=symbol,
                timestamp=timestamp
            )
            logger.info(f"SELL signal #{self.signal_count} for {symbol} at {close_price:.2f}")
            self.event_bus.emit(signal)
    
    def reset(self):
        """Reset strategy state."""
        self.data = {symbol: [] for symbol in self.symbols}
        self.signal_count = 0

def create_test_data(symbols, start_date, end_date):
    """Create test data with sine wave patterns to ensure MA crossovers."""
    logger.info(f"Creating test data for {symbols}")
    
    # Convert dates to datetime objects if needed
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    # Generate date range
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
    
    np.random.seed(42)  # For reproducibility
    
    for symbol in symbols:
        # Create price data with forced crossovers
        base_price = 100.0 if symbol == 'AAPL' else 200.0
        prices = []
        
        # Create a sine wave pattern for predictable crossovers
        for i in range(len(dates)):
            t = i / len(dates)
            # Multiple frequency components to create crossovers
            sine_component = 15 * np.sin(t * 20 * np.pi) + 7 * np.sin(t * 5 * np.pi)
            # Add slight trend and noise
            price = base_price + sine_component + i * 0.01 + np.random.normal(0, 0.5)
            prices.append(max(price, 1.0))  # Ensure positive prices
        
        # Generate OHLCV data
        data = []
        for i, date in enumerate(dates):
            close = prices[i]
            high = close * (1 + abs(np.random.normal(0, 0.01)))
            low = close * (1 - abs(np.random.normal(0, 0.01)))
            open_price = low + (high - low) * np.random.random()
            volume = int(np.random.exponential(100000))
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(data)
        filename = os.path.join(DATA_DIR, f"{symbol}_1d.csv")
        df.to_csv(filename, index=False)
        logger.info(f"Created test data for {symbol} with {len(data)} bars")
    
    return True

def create_config():
    """Create configuration for the backtest."""
    config_dict = {
        'backtest': {
            'initial_capital': 100000.0,
            'symbols': ['AAPL', 'MSFT'],
            'data_dir': DATA_DIR,
            'timeframe': '1d',
        },
        'strategy': {
            'ma_crossover': {
                'fast_window': 5,  # Use fast window for more signals in test
                'slow_window': 20,
                'symbols': ['AAPL', 'MSFT'],
            }
        },
        'risk_manager': {
            'position_size': 100,
            'max_position_pct': 0.1,  # Max 10% of equity per position
        },
        'broker': {
            'slippage': 0.001,  # 0.1% slippage
            'commission': 0.001,  # 0.1% commission
        }
    }
    
    # Save config to YAML file for reference
    with open('backtest_config.yaml', 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False)
    
    # Create SimpleConfig object
    return SimpleConfig(config_dict)

def setup_container(config):
    """Set up dependency injection container with components."""
    container = Container()
    
    # Register core components
    event_bus = EventBus()
    event_manager = EventManager(event_bus)
    
    container.register_instance('event_bus', event_bus)
    container.register_instance('event_manager', event_manager)
    container.register_instance('config', config)
    
    # Register event emitters
    bar_emitter = BarEmitter("bar_emitter", event_bus)
    bar_emitter.start()  # Explicitly start the emitter
    container.register_instance('bar_emitter', bar_emitter)
    
    # Register data components
    data_source = CSVDataSource(config.get_section('backtest').get('data_dir', DATA_DIR))
    container.register_instance('data_source', data_source)
    
    data_handler = HistoricalDataHandler(data_source, bar_emitter)
    container.register_instance('data_handler', data_handler)
    
    # Register portfolio and risk management
    portfolio = PortfolioManager(
        event_bus, 
        initial_cash=config.get_section('backtest').get('initial_capital', 100000.0)
    )
    container.register_instance('portfolio', portfolio)
    
    risk_manager = SimpleRiskManager(
        event_bus,
        portfolio,
        name="simple_risk_manager"
    )
    risk_manager.position_size = config.get_section('risk_manager').get('position_size', 100)
    risk_manager.max_position_pct = config.get_section('risk_manager').get('max_position_pct', 0.1)
    container.register_instance('risk_manager', risk_manager)
    
    # Register execution components - MODIFIED ORDER HERE
    # First create order manager with empty dependencies
    from src.execution.order_manager import OrderManager
    order_manager = OrderManager(None, None)
    container.register_instance('order_manager', order_manager)
    
    # Then create broker
    broker = SimulatedBroker(event_bus)
    broker.slippage = config.get_section('broker').get('slippage', 0.0)
    broker.commission = config.get_section('broker').get('commission', 0.0)
    container.register_instance('broker', broker)
    
    # Now connect order manager to event bus and broker
    order_manager.broker = broker
    order_manager.set_event_bus(event_bus)
    
    # Register analytics components
    calculator = PerformanceCalculator()
    container.register_instance('calculator', calculator)
    
    report_generator = ReportGenerator(calculator)
    container.register_instance('report_generator', report_generator)
    
    # Register strategy
    strategy_params = config.get_section('strategy').get_section('ma_crossover').as_dict()
    strategy = SimpleMAStrategy(event_bus, data_handler, name="ma_crossover", parameters=strategy_params)
    container.register_instance('strategy', strategy)
    
    # Register backtest coordinator
    backtest = BacktestCoordinator(container, config)
    container.register_instance('backtest', backtest)
    
    return container



def run_backtest():
    """Run backtest using BacktestCoordinator."""
    logger.info("=== Starting ADMF-Trader Backtest ===")
    
    # Create test data
    symbols = ['AAPL', 'MSFT']
    start_date = '2023-01-01'
    end_date = '2023-02-28'  # Shorter period for faster testing
    
    create_test_data(symbols, start_date, end_date)
    
    # Create configuration
    config = create_config()
    
    # Set up container with all components
    container = setup_container(config)
    
    # Get backtest coordinator
    backtest = container.get('backtest')
    
    # Set up the backtest
    setup_success = backtest.setup()
    if not setup_success:
        logger.error("Failed to set up backtest")
        return False
    
    # Run the backtest
    results = backtest.run(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000.0,
        timeframe='1d'
    )
    
    # Process results
    if not results:
        logger.error("Backtest returned no results!")
        return {'success': False}
    
    # Get equity curve and trades
    equity_curve = results.get('equity_curve')
    trades = results.get('trades', [])
    
    logger.info(f"Executed {len(trades)} trades")
    
    # Show first few trades
    for i, trade in enumerate(trades[:5]):
        if i < len(trades):
            logger.info(f"Trade {i+1}: {trade['direction']} {trade['quantity']} {trade['symbol']} @ {trade['price']:.2f}, PnL: {trade['pnl']:.2f}")
    
    # Calculate metrics from equity curve
    metrics = results.get('metrics', {})
    if equity_curve is not None and not equity_curve.empty:
        start_equity = equity_curve['equity'].iloc[0]
        end_equity = equity_curve['equity'].iloc[-1]
        total_return = (end_equity / start_equity) - 1
        
        logger.info(f"Initial equity: ${start_equity:.2f}")
        logger.info(f"Final equity: ${end_equity:.2f}")
        logger.info(f"Total return: {total_return:.2%}")
        
        # Save equity curve
        equity_curve.to_csv("equity_curve.csv")
        logger.info("Saved equity curve to 'equity_curve.csv'")
        
        # Save detailed report
        detailed_report = results.get('detailed_report', '')
        if detailed_report:
            with open('backtest_report.txt', 'w') as f:
                f.write(detailed_report)
            logger.info("Saved detailed report to 'backtest_report.txt'")
    
    # Print metrics
    if metrics:
        logger.info("\nPerformance Metrics:")
        for metric, value in metrics.items():
            if isinstance(value, float):
                logger.info(f"  {metric}: {value:.4f}")
            else:
                logger.info(f"  {metric}: {value}")
    
    return {
        'success': True,
        'trades': len(trades),
        'return': total_return if 'total_return' in locals() else 0,
        'metrics': metrics
    }

if __name__ == "__main__":
    try:
        results = run_backtest()
        if results and results.get('success'):
            print("\n=== Backtest Completed Successfully! ===")
            print(f"Trades executed: {results.get('trades', 0)}")
            print(f"Total return: {results.get('return', 0):.2%}")
            
            # Print summary metrics
            print("\nKey Performance Metrics:")
            metrics = results.get('metrics', {})
            key_metrics = ['sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor']
            for metric in key_metrics:
                if metric in metrics:
                    print(f"  {metric}: {metrics[metric]:.4f}")
            
            print("\nDetailed results saved to backtest_report.txt")
            print("Equity curve saved to equity_curve.csv")
        else:
            print("\n=== Backtest Failed! ===")
            print("See logs for details.")
    except Exception as e:
        logger.error(f"Backtest failed with error: {e}", exc_info=True)
        print(f"Error: {e}")
