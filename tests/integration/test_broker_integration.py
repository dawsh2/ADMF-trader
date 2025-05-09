"""
Integration tests for the broker module components.

This tests the integration of:
- SimulatedBroker with the event bus
- SimulatedBroker with MarketSimulator
- SimulatedBroker with PortfolioManager
"""
import pytest
import datetime
from collections import defaultdict

from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType
from src.core.event_system.event_bus import EventBus
from src.execution.broker.simulated_broker import SimulatedBroker
from src.execution.broker.market_simulator import MarketSimulator
from src.risk.portfolio.portfolio_manager import PortfolioManager


@pytest.fixture
def event_bus():
    """Create an event bus for testing."""
    return EventBus()


@pytest.fixture
def market_simulator(event_bus):
    """Create a market simulator for testing."""
    simulator = MarketSimulator()
    simulator.initialize({"event_bus": event_bus})
    return simulator


@pytest.fixture
def broker(event_bus, market_simulator):
    """Create a simulated broker for testing."""
    broker = SimulatedBroker()
    broker.initialize({
        "event_bus": event_bus,
        "market_simulator": market_simulator
    })
    return broker


@pytest.fixture
def portfolio(event_bus):
    """Create a portfolio manager for testing."""
    portfolio = PortfolioManager(initial_cash=100000.0)
    portfolio.set_event_bus(event_bus)
    return portfolio


@pytest.mark.integration
class TestBrokerIntegration:
    """Integration tests for the broker module."""
    
    def test_order_to_fill_flow(self, event_bus, broker, market_simulator, portfolio):
        """Test the flow from order to fill."""
        # Set up a test listener
        events_received = defaultdict(list)
        
        def event_listener(event):
            event_type = event.type if hasattr(event, 'type') else None
            events_received[event_type].append(event)
        
        # Register event listeners
        event_bus.subscribe(EventType.FILL, event_listener)
        event_bus.subscribe(EventType.PORTFOLIO_UPDATE, event_listener)
        
        # Set up test data - use a bar event to update both broker and market simulator
        bar_data = {
            'symbol': 'TEST',
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000,
            'timestamp': datetime.datetime.now()
        }
        bar_event = Event(EventType.BAR, bar_data)
        # Process the bar event to update prices in both components
        broker.on_bar(bar_event)
        market_simulator.on_bar(bar_event)
        
        # Create and publish an order event
        order_data = {
            'id': 'order_1',
            'symbol': 'TEST',
            'direction': 'BUY',
            'quantity': 100,
            'price': 100.0,
            'order_type': 'MARKET',
            'status': 'CREATED',
            'rule_id': 'rule_1',
            'timestamp': datetime.datetime.now()
        }
        order_event = Event(EventType.ORDER, order_data)
        event_bus.publish(order_event)
        
        # Check that a fill event was generated
        assert len(events_received[EventType.FILL]) > 0
        fill_event = events_received[EventType.FILL][0]
        assert fill_event.data['symbol'] == 'TEST'
        assert fill_event.data['direction'] == 'BUY'
        assert fill_event.data['quantity'] == 100
        
        # Check that the portfolio was updated
        assert len(events_received[EventType.PORTFOLIO_UPDATE]) > 0
        
        # Check the portfolio state
        test_position = portfolio.get_position('TEST')
        assert test_position is not None
        assert test_position.quantity == 100
        
    def test_broker_market_simulator_integration(self, event_bus, broker, market_simulator):
        """Test integration between broker and market simulator."""
        # Set up market simulator with price data
        bar_data = {
            'symbol': 'TEST',
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000,
            'timestamp': datetime.datetime.now()
        }
        bar_event = Event(EventType.BAR, bar_data)
        market_simulator.on_bar(bar_event)
        
        # Verify that market simulator has the price data
        assert 'TEST' in market_simulator.current_prices
        assert market_simulator.current_prices['TEST']['close'] == 100.5
        
        # Create a limit order that should fill
        order_data = {
            'id': 'order_1',
            'symbol': 'TEST',
            'direction': 'BUY',
            'quantity': 100,
            'price': 100.0,
            'order_type': 'LIMIT',
            'status': 'CREATED',
            'timestamp': datetime.datetime.now()
        }
        
        # Process the order using the market simulator for fill conditions
        can_fill, fill_price = market_simulator.check_fill_conditions(order_data)
        
        # Verify that the order can be filled
        assert can_fill is True
        assert 99.0 <= fill_price <= 100.0  # Should fill between low and limit price
        
    def test_full_system_integration(self, event_bus, broker, market_simulator, portfolio):
        """Test full system integration with bar events, orders, fills, and portfolio updates."""
        # Set up event counters
        events_received = defaultdict(list)
        
        def event_listener(event):
            event_type = event.type if hasattr(event, 'type') else None
            events_received[event_type].append(event)
        
        # Register event listeners for all event types
        for event_type in EventType:
            event_bus.subscribe(event_type, event_listener)
        
        # Generate a sequence of bar events
        for i in range(5):
            price = 100.0 + i
            bar_data = {
                'symbol': 'TEST',
                'open': price - 0.5,
                'high': price + 1.0,
                'low': price - 1.0,
                'close': price + 0.5,
                'volume': 1000,
                'timestamp': datetime.datetime.now() + datetime.timedelta(minutes=i)
            }
            bar_event = Event(EventType.BAR, bar_data)
            # Process directly to ensure both components get the data
            broker.on_bar(bar_event)
            market_simulator.on_bar(bar_event)
            # Also publish to the event bus for event logging purposes
            event_bus.publish(bar_event)
        
        # Verify bar events were processed
        assert len(events_received[EventType.BAR]) == 5
        assert 'TEST' in broker.latest_prices
        assert broker.latest_prices['TEST']['close'] == 104.5  # Last price
        
        # Create a buy order - set price lower than current price to ensure it fills
        buy_order_data = {
            'id': 'order_buy',
            'symbol': 'TEST',
            'direction': 'BUY',
            'quantity': 100,
            'price': 110.0,  # Price is high enough to fill against last price (104.5)
            'order_type': 'LIMIT',
            'status': 'CREATED',
            'rule_id': 'rule_1',
            'timestamp': datetime.datetime.now()
        }
        buy_order_event = Event(EventType.ORDER, buy_order_data)
        event_bus.publish(buy_order_event)
        
        # Verify buy order was filled
        fills = [e for e in events_received[EventType.FILL] if e.data['order_id'] == 'order_buy']
        assert len(fills) > 0
        
        # Create a sell order - set price lower than current price to ensure it fills
        sell_order_data = {
            'id': 'order_sell',
            'symbol': 'TEST',
            'direction': 'SELL',
            'quantity': 50,
            'price': 100.0,  # Price is low enough to fill against last price (104.5)
            'order_type': 'LIMIT',
            'status': 'CREATED',
            'rule_id': 'rule_2',
            'timestamp': datetime.datetime.now()
        }
        sell_order_event = Event(EventType.ORDER, sell_order_data)
        event_bus.publish(sell_order_event)
        
        # Verify sell order was filled
        fills = [e for e in events_received[EventType.FILL] if e.data['order_id'] == 'order_sell']
        assert len(fills) > 0
        
        # Check portfolio state
        test_position = portfolio.get_position('TEST')
        assert test_position is not None
        assert test_position.quantity == 50  # 100 bought - 50 sold
        
        # Verify portfolio updates were generated
        assert len(events_received[EventType.PORTFOLIO_UPDATE]) >= 2
        
        # Check broker statistics
        assert broker.stats['orders_filled'] == 2
        assert broker.stats['orders_rejected'] == 0