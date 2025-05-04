#!/usr/bin/env python
"""
Integration test to verify all components work together with our fixes.
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# Set up path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the fixed components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import Event, EventType, BarEvent
from src.core.events.event_utils import create_signal_event, create_order_event
from src.strategy.implementations.ma_crossover import MACrossoverStrategy
from src.risk.portfolio.portfolio import PortfolioManager
from src.execution.broker.broker_simulator import SimulatedBroker
from src.risk.managers.simple import SimpleRiskManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_complete_event_flow():
    """Test the complete event flow from strategy signal to order to fill to portfolio update."""
    # Create event bus
    event_bus = EventBus()
    
    # Create portfolio
    portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
    
    # Create broker
    broker = SimulatedBroker(event_bus)
    broker.commission = 0.001  # 0.1% commission
    broker.slippage = 0.001  # 0.1% slippage
    
    # Create risk manager
    risk_manager = SimpleRiskManager(event_bus, portfolio)
    risk_manager.position_size = 100
    risk_manager.max_position_pct = 0.1
    
    # Create strategy
    parameters = {
        'fast_window': 3,
        'slow_window': 5,
        'price_key': 'close',
        'symbols': ['TEST']
    }
    strategy = MACrossoverStrategy(event_bus, None, parameters=parameters)
    
    # Create event trackers
    signals = []
    orders = []
    fills = []
    
    def track_signal(event):
        if event.get_type() == EventType.SIGNAL:
            signals.append(event)
            
    def track_order(event):
        if event.get_type() == EventType.ORDER:
            orders.append(event)
            
    def track_fill(event):
        if event.get_type() == EventType.FILL:
            fills.append(event)
    
    # Register trackers
    event_bus.register(EventType.SIGNAL, track_signal)
    event_bus.register(EventType.ORDER, track_order)
    event_bus.register(EventType.FILL, track_fill)
    
    # Generate a series of bars
    base_time = datetime.now()
    
    # Uptrend to generate a buy signal
    prices = [10, 10, 12, 15, 18, 22, 25, 30]
    
    logger.info("Sending bar events with uptrend...")
    for i, price in enumerate(prices):
        bar = BarEvent(
            symbol='TEST',
            timestamp=base_time + timedelta(minutes=i),
            open_price=price - 0.5,
            high_price=price + 1,
            low_price=price - 1,
            close_price=price,
            volume=1000
        )
        event_bus.emit(bar)
    
    # Check if events were processed correctly for uptrend
    logger.info(f"Generated {len(signals)} signals")
    logger.info(f"Generated {len(orders)} orders")
    logger.info(f"Generated {len(fills)} fills")
    
    buy_signals = [s for s in signals if s.data.get('signal_value') == 1]
    assert len(buy_signals) > 0, "No buy signals generated"
    
    buy_orders = [o for o in orders if o.data.get('direction') == 'BUY']
    assert len(buy_orders) > 0, "No buy orders generated"
    
    buy_fills = [f for f in fills if f.data.get('direction') == 'BUY']
    assert len(buy_fills) > 0, "No buy fills generated"
    
    # Check portfolio has position
    assert 'TEST' in portfolio.positions, "No position created in portfolio"
    assert portfolio.positions['TEST'].quantity > 0, "Position quantity not positive"
    
    # Record initial position quantity
    initial_quantity = portfolio.positions['TEST'].quantity
    logger.info(f"Position quantity after uptrend: {initial_quantity}")
    
    # Downtrend to generate a sell signal
    prices = [30, 28, 25, 20, 15, 10]
    
    logger.info("Sending bar events with downtrend...")
    initial_signal_count = len(signals)
    initial_order_count = len(orders)
    initial_fill_count = len(fills)
    
    for i, price in enumerate(prices):
        bar = BarEvent(
            symbol='TEST',
            timestamp=base_time + timedelta(minutes=i+len(prices)),
            open_price=price - 0.5,
            high_price=price + 1,
            low_price=price - 1,
            close_price=price,
            volume=1000
        )
        event_bus.emit(bar)
    
    # Check if events were processed correctly for downtrend
    logger.info(f"Generated {len(signals) - initial_signal_count} additional signals")
    logger.info(f"Generated {len(orders) - initial_order_count} additional orders")
    logger.info(f"Generated {len(fills) - initial_fill_count} additional fills")
    
    sell_signals = [s for s in signals if s.data.get('signal_value') == -1]
    assert len(sell_signals) > 0, "No sell signals generated"
    
    sell_orders = [o for o in orders if o.data.get('direction') == 'SELL']
    assert len(sell_orders) > 0, "No sell orders generated"
    
    sell_fills = [f for f in fills if f.data.get('direction') == 'SELL']
    assert len(sell_fills) > 0, "No sell fills generated"
    
    # Check portfolio position was reduced
    assert portfolio.positions['TEST'].quantity < initial_quantity, "Position not reduced after sell signals"
    logger.info(f"Final position quantity: {portfolio.positions['TEST'].quantity}")
    
    # Check trades were recorded
    assert len(portfolio.trades) > 0, "No trades recorded in portfolio"
    logger.info(f"Total trades recorded: {len(portfolio.trades)}")
    
    # Check equity was updated
    assert portfolio.equity != portfolio.initial_cash, "Equity wasn't updated"
    logger.info(f"Final equity: {portfolio.equity:.2f}")
    
    logger.info("✅ Complete event flow integration test passed")

def main():
    """Run integration tests."""
    logger.info("Running integration test...")
    
    test_complete_event_flow()
    
    logger.info("All integration tests passed! ✅")
    return 0

if __name__ == "__main__":
    sys.exit(main())
