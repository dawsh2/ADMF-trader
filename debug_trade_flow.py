#!/usr/bin/env python
"""
Debug script for tracing signals to trades
"""

import logging
import yaml
from src.core.events.event_bus import EventBus, EventType
from src.core.events.event_utils import create_signal_event
from src.strategy.implementations.ma_crossover import MACrossoverStrategy
from src.execution.order_manager import OrderManager
from src.execution.broker.simulated_broker import SimulatedBroker
from src.execution.portfolio import Portfolio
from src.execution.backtest.backtest_coordinator import BacktestCoordinator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("signal_to_trade_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('debug')

def debug_signal_flow():
    """Test the signal to trade flow with a minimal setup"""
    # Create event bus with debug logging
    event_bus = EventBus(name="debug_event_bus")
    
    # Add debug listener to log all signals
    def signal_listener(event):
        logger.info(f"SIGNAL EVENT DETECTED: {event}")
    event_bus.subscribe(EventType.SIGNAL, signal_listener)
    
    # Add debug listener for orders
    def order_listener(event):
        logger.info(f"ORDER EVENT DETECTED: {event}")
    event_bus.subscribe(EventType.ORDER, order_listener)
    
    # Add debug listener for trades
    def trade_listener(event):
        logger.info(f"TRADE EVENT DETECTED: {event}")
    event_bus.subscribe(EventType.TRADE, trade_listener)
    
    # Load configuration
    with open('config/ma_crossover_optimization.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create minimal backtest setup
    portfolio = Portfolio("portfolio", 100000.0)
    broker = SimulatedBroker("broker")
    order_manager = OrderManager("order_manager")
    
    # Initialize components with event bus
    portfolio.event_bus = event_bus
    broker.event_bus = event_bus
    order_manager.event_bus = event_bus
    
    # Create a minimal backtest coordinator
    backtest = BacktestCoordinator("backtest", config)
    
    # Initialize and run a minimal backtest
    backtest.initialize({
        'event_bus': event_bus,
        'portfolio': portfolio,
        'broker': broker,
        'order_manager': order_manager
    })
    
    # Send a test signal event
    test_signal = create_signal_event(
        signal_value=1,  # Buy
        price=520.0,
        symbol="HEAD",
        timestamp=None,  # Current time
        rule_id="test_signal"
    )
    
    logger.info(f"Publishing test signal: {test_signal}")
    event_bus.publish(test_signal)
    
    logger.info("If you see a SIGNAL EVENT but no ORDER or TRADE events, there's a problem in the signal->order->trade chain")

if __name__ == "__main__":
    debug_signal_flow()
