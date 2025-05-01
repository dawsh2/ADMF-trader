"""
Integration test for strategy to portfolio flow.
Tests the complete flow from strategy signal to order to fill to portfolio update.
"""

import sys
import os
import pytest
import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import Event, EventType
from src.core.events.event_utils import create_signal_event, create_order_event
from src.strategy.strategy_base import Strategy
from src.risk.portfolio.portfolio import PortfolioManager
from src.execution.broker.broker_simulator import SimulatedBroker

@pytest.mark.integration
class TestStrategyPortfolioFlow:
    """Test the complete flow from strategy to portfolio."""
    
    @pytest.fixture
    def setup_components(self):
        """Set up test components."""
        # Create event bus
        event_bus = EventBus()
        
        # Create components
        portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
        broker = SimulatedBroker(event_bus)
        
        # Create test strategy - we'll simulate strategy signals manually
        class TestStrategy(Strategy):
            def __init__(self, event_bus, data_handler=None):
                super().__init__(event_bus, data_handler, "test_strategy")
                self.signals_emitted = []
                
            def emit_signal(self, signal_value, price, symbol):
                signal = create_signal_event(signal_value, price, symbol)
                self.signals_emitted.append(signal)
                if self.event_bus:
                    self.event_bus.emit(signal)
                return signal
        
        strategy = TestStrategy(event_bus)
        
        # Create order handler - simulates role of risk manager
        order_handler_calls = []
        
        def order_handler(signal_event):
            # Create order from signal
            symbol = signal_event.data.get('symbol', 'UNKNOWN')
            price = signal_event.data.get('price', 0.0)
            signal_value = signal_event.data.get('signal_value', 0)
            
            # 1 for buy, -1 for sell
            direction = 'BUY' if signal_value > 0 else 'SELL'
            quantity = 100  # Fixed quantity for testing
            
            # Create and emit order
            order = create_order_event(direction, quantity, symbol, 'MARKET', price)
            order_handler_calls.append(order)
            
            if event_bus:
                event_bus.emit(order)
            
            return order
        
        # Register order handler for signals
        event_bus.register(EventType.SIGNAL, order_handler)
        
        # Return all components
        return {
            'event_bus': event_bus,
            'portfolio': portfolio,
            'broker': broker,
            'strategy': strategy,
            'order_handler_calls': order_handler_calls
        }
    
    def test_strategy_signal_to_order(self, setup_components):
        """Test strategy signal leads to order creation."""
        components = setup_components
        strategy = components['strategy']
        order_handler_calls = components['order_handler_calls']
        
        # Emit signal
        signal = strategy.emit_signal(1, 100.0, 'TEST')
        
        # Check order was created
        assert len(order_handler_calls) == 1
        order = order_handler_calls[0]
        assert order.get_type() == EventType.ORDER
        assert order.data.get('direction') == 'BUY'
        assert order.data.get('symbol') == 'TEST'
        assert order.data.get('quantity') == 100
    
    def test_order_to_fill(self, setup_components):
        """Test order leads to fill creation by broker."""
        components = setup_components
        broker = components['broker']
        
        # Create order
        order = create_order_event('BUY', 100, 'TEST', 'MARKET', 100.0)
        
        # Process order
        fill = broker.on_order(order)
        
        # Check fill was created
        assert fill is not None
        assert fill.get_type() == EventType.FILL
        assert fill.data.get('symbol') == 'TEST'
        assert fill.data.get('direction') == 'BUY'
        assert fill.data.get('size') == 100
        assert abs(fill.data.get('fill_price') - 100.0) < 0.01  # Allow for slippage
    
    def test_fill_to_portfolio(self, setup_components):
        """Test fill updates portfolio."""
        components = setup_components
        portfolio = components['portfolio']
        
        # Create fill event
        fill_data = {
            'symbol': 'TEST',
            'direction': 'BUY',
            'size': 100,
            'fill_price': 100.0,
            'commission': 0.0
        }
        fill_event = Event(EventType.FILL, fill_data)
        
        # Initial cash
        initial_cash = portfolio.cash
        
        # Process fill
        portfolio.on_fill(fill_event)
        
        # Check portfolio was updated
        assert 'TEST' in portfolio.positions
        assert portfolio.positions['TEST'].quantity == 100
        assert portfolio.positions['TEST'].cost_basis == 100.0
        assert portfolio.cash == initial_cash - 100 * 100.0
    
    def test_complete_flow(self, setup_components):
        """Test complete flow from signal to portfolio."""
        components = setup_components
        strategy = components['strategy']
        portfolio = components['portfolio']
        
        # Initial cash
        initial_cash = portfolio.cash
        
        # Emit signal
        signal = strategy.emit_signal(1, 100.0, 'TEST')
        
        # Check portfolio was updated via the event flow
        assert 'TEST' in portfolio.positions
        assert portfolio.positions['TEST'].quantity == 100
        assert portfolio.positions['TEST'].cost_basis > 0
        assert portfolio.cash < initial_cash
        
        # Test closing the position
        strategy.emit_signal(-1, 110.0, 'TEST')
        
        # Check position was closed
        assert portfolio.positions['TEST'].quantity == 0
        assert portfolio.positions['TEST'].realized_pnl > 0
        assert portfolio.cash > initial_cash - 100  # Should have made profit
    
    def test_multiple_positions(self, setup_components):
        """Test handling multiple positions."""
        components = setup_components
        strategy = components['strategy']
        portfolio = components['portfolio']
        
        # Emit signals for different symbols
        strategy.emit_signal(1, 100.0, 'TEST1')
        strategy.emit_signal(1, 200.0, 'TEST2')
        
        # Check portfolio has both positions
        assert 'TEST1' in portfolio.positions
        assert 'TEST2' in portfolio.positions
        assert portfolio.positions['TEST1'].quantity == 100
        assert portfolio.positions['TEST2'].quantity == 100
        
        # Close one position
        strategy.emit_signal(-1, 110.0, 'TEST1')
        
        # Check one position closed, one still open
        assert portfolio.positions['TEST1'].quantity == 0
        assert portfolio.positions['TEST2'].quantity == 100
    
    def test_bar_updates(self, setup_components):
        """Test bar events update portfolio mark-to-market."""
        components = setup_components
        strategy = components['strategy']
        portfolio = components['portfolio']
        event_bus = components['event_bus']
        
        # Open a position
        strategy.emit_signal(1, 100.0, 'TEST')
        
        # Create and emit a bar event
        bar_data = {
            'symbol': 'TEST',
            'open': 109.0,
            'high': 111.0,
            'low': 108.0,
            'close': 110.0,
            'volume': 1000
        }
        bar_event = Event(EventType.BAR, bar_data)
        event_bus.emit(bar_event)
        
        # Check position was marked to market
        assert portfolio.positions['TEST'].current_price == 110.0
        assert portfolio.positions['TEST'].unrealized_pnl() > 0
