"""
Integration tests for the strategy -> risk -> order execution flow.
Tests the interaction between strategy, risk management, and order execution components.
"""

import pytest
from datetime import datetime
import pandas as pd
import numpy as np

from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from src.strategy.implementations.ma_crossover import MACrossoverStrategy
from src.risk.managers.simple import SimpleRiskManager
from src.risk.portfolio.portfolio import PortfolioManager
from src.execution.order_manager import OrderManager
from src.execution.broker.broker_simulator import SimulatedBroker


@pytest.mark.integration
class TestStrategyRiskOrderFlow:
    
    @pytest.fixture
    def setup_components(self):
        """Set up an integrated system of components."""
        # Create event bus
        event_bus = EventBus()
        
        # Create portfolio manager
        portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
        
        # Create risk manager
        risk_manager = SimpleRiskManager(event_bus, portfolio)
        risk_manager.position_size = 100
        risk_manager.max_position_pct = 0.1
        
        # Create broker simulator
        broker = SimulatedBroker(event_bus)
        broker.set_slippage(0.001)  # 0.1% slippage
        broker.set_commission(0.001)  # 0.1% commission
        
        # Create order manager
        order_manager = OrderManager(event_bus, broker)
        
        # Create strategy
        parameters = {
            'fast_window': 5,
            'slow_window': 15,
            'price_key': 'close',
            'symbols': ['TEST']
        }
        strategy = MACrossoverStrategy(event_bus, None, parameters=parameters)
        
        # Return all components
        return {
            'event_bus': event_bus,
            'portfolio': portfolio,
            'risk_manager': risk_manager,
            'broker': broker,
            'order_manager': order_manager,
            'strategy': strategy
        }
    
    @pytest.fixture
    def price_series(self):
        """Generate a price series that will trigger signals."""
        np.random.seed(42)
        
        # Create a series with clear trends to trigger signals
        prices = []
        
        # Start at 100 and trend up to 110
        prices += list(np.linspace(100, 110, 20) + np.random.normal(0, 0.2, 20))
        
        # Trend down to 95
        prices += list(np.linspace(110, 95, 20) + np.random.normal(0, 0.2, 20))
        
        # Trend up to 115
        prices += list(np.linspace(95, 115, 20) + np.random.normal(0, 0.2, 20))
        
        # Trend down to 105
        prices += list(np.linspace(115, 105, 20) + np.random.normal(0, 0.2, 20))
        
        return prices
    
    @pytest.fixture
    def bar_events(self, price_series):
        """Convert price series to bar events."""
        events = []
        start_date = datetime(2024, 1, 1, 9, 30)
        
        for i, price in enumerate(price_series):
            # Create bar event data
            event_data = {
                'symbol': 'TEST',
                'timestamp': (start_date + pd.Timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S'),
                'open': price - 0.1,
                'high': price + 0.2,
                'low': price - 0.2,
                'close': price,
                'volume': 1000 + np.random.randint(-200, 200)
            }
            
            # Create event
            event = Event(EventType.BAR, event_data)
            events.append(event)
        
        return events
    
    def test_end_to_end_flow(self, setup_components, bar_events):
        """Test the end-to-end flow from bar event to order execution."""
        components = setup_components
        event_bus = components['event_bus']
        portfolio = components['portfolio']
        strategy = components['strategy']
        
        # Track events for verification
        signal_events = []
        order_events = []
        fill_events = []
        
        # Register handlers to track events
        def signal_tracker(event):
            signal_events.append(event)
            return event
        
        def order_tracker(event):
            order_events.append(event)
            return event
        
        def fill_tracker(event):
            fill_events.append(event)
            return event
        
        event_bus.register(EventType.SIGNAL, signal_tracker)
        event_bus.register(EventType.ORDER, order_tracker)
        event_bus.register(EventType.FILL, fill_tracker)
        
        # Process bar events through the system
        for event in bar_events:
            event_bus.emit(event)
        
        # Verify signals were generated
        assert len(signal_events) > 0
        
        # Verify orders were created from signals
        assert len(order_events) > 0
        
        # Verify fills were generated from orders
        assert len(fill_events) > 0
        
        # Verify position changes in portfolio
        final_positions = portfolio.get_positions()
        assert len(final_positions) > 0
        
        # Verify equity changed due to trades
        equity_curve = portfolio.get_equity_curve()
        assert len(equity_curve) > 0
        
        # Verify beginning equity matches initial cash
        assert abs(equity_curve[0] - 100000.0) < 1e-10
        
        # Verify trades were recorded
        trades = portfolio.get_trades()
        assert len(trades) > 0
        
        # Verify each trade has correct data structure
        for trade in trades:
            assert 'symbol' in trade
            assert 'entry_time' in trade
            assert 'exit_time' in trade
            assert 'entry_price' in trade
            assert 'exit_price' in trade
            assert 'quantity' in trade
            assert 'pnl' in trade
        
        # Verify event flow matches expectations:
        # 1. Strategy generates signals after enough bars
        # 2. Risk manager converts signals to orders
        # 3. Broker fills orders
        # 4. Portfolio updates based on fills
        
        # Count number of buy/sell signals
        buy_signals = [s for s in signal_events if s.get_data().get('signal_value') == 1]
        sell_signals = [s for s in signal_events if s.get_data().get('signal_value') == -1]
        
        # Count number of buy/sell orders
        buy_orders = [o for o in order_events if o.get_data().get('direction') == 'BUY']
        sell_orders = [o for o in order_events if o.get_data().get('direction') == 'SELL']
        
        # Verify number of orders matches signals
        assert len(buy_orders) == len(buy_signals)
        assert len(sell_orders) == len(sell_signals)
    
    def test_portfolio_performance(self, setup_components, bar_events):
        """Test that the system produces reasonable portfolio performance."""
        components = setup_components
        event_bus = components['event_bus']
        portfolio = components['portfolio']
        
        # Process bar events
        for event in bar_events:
            event_bus.emit(event)
        
        # Verify equity curve
        equity_curve = portfolio.get_equity_curve()
        
        # Calculate returns
        returns = np.diff(equity_curve) / equity_curve[:-1]
        
        # Calculate metrics
        total_return = (equity_curve[-1] / equity_curve[0]) - 1
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
        
        # Basic sanity checks
        assert not np.isnan(total_return)
        assert not np.isnan(sharpe_ratio)
        
        # Log performance metrics
        print(f"Total Return: {total_return:.2%}")
        print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        
        # Verify trades were made
        trades = portfolio.get_trades()
        assert len(trades) > 0
        
        # Calculate win rate
        profitable_trades = [t for t in trades if t['pnl'] > 0]
        win_rate = len(profitable_trades) / len(trades)
        
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Number of Trades: {len(trades)}")
        
        # These metrics are for information only, not hard assertions
        # The strategy may not be profitable on all test data
    
    def test_event_ordering(self, setup_components, bar_events):
        """Test that events are processed in the correct order."""
        components = setup_components
        event_bus = components['event_bus']
        
        # Track event sequence
        event_sequence = []
        
        # Handler to record event sequence
        def sequence_tracker(event):
            event_sequence.append(event.get_type())
            return event
        
        # Register for all event types
        event_bus.register(EventType.BAR, sequence_tracker)
        event_bus.register(EventType.SIGNAL, sequence_tracker)
        event_bus.register(EventType.ORDER, sequence_tracker)
        event_bus.register(EventType.FILL, sequence_tracker)
        
        # Process a subset of bars to keep test manageable
        for event in bar_events[:50]:
            event_bus.emit(event)
        
        # Verify event sequence logic
        for i in range(len(event_sequence)):
            if event_sequence[i] == EventType.SIGNAL:
                # Find the preceding BAR event
                preceding_idx = next((j for j in range(i-1, -1, -1) if event_sequence[j] == EventType.BAR), None)
                assert preceding_idx is not None, "SIGNAL event without preceding BAR event"
            
            elif event_sequence[i] == EventType.ORDER:
                # Find the preceding SIGNAL event
                preceding_idx = next((j for j in range(i-1, -1, -1) if event_sequence[j] == EventType.SIGNAL), None)
                assert preceding_idx is not None, "ORDER event without preceding SIGNAL event"
            
            elif event_sequence[i] == EventType.FILL:
                # Find the preceding ORDER event
                preceding_idx = next((j for j in range(i-1, -1, -1) if event_sequence[j] == EventType.ORDER), None)
                assert preceding_idx is not None, "FILL event without preceding ORDER event"
