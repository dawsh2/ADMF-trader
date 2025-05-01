"""
Minimal integration test that verifies components individually without complex event interactions.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta

from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from src.strategy.implementations.ma_crossover import MACrossoverStrategy
from src.risk.managers.simple import SimpleRiskManager
from src.risk.portfolio.portfolio import PortfolioManager
from src.execution.order_manager import OrderManager
from src.execution.broker.broker_simulator import SimulatedBroker


@pytest.mark.integration
class TestMinimalIntegration:
    
    def test_component_initialization(self):
        """Test that all components can be initialized without errors."""
        # Create event bus
        event_bus = EventBus()
        assert event_bus is not None
        
        # Create portfolio manager
        portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
        assert portfolio is not None
        assert portfolio.cash == 100000.0
        
        # Create risk manager
        risk_manager = SimpleRiskManager(event_bus, portfolio)
        assert risk_manager is not None
        
        # Create broker simulator
        broker = SimulatedBroker(event_bus)
        assert broker is not None
        
        # Set broker properties directly
        broker.slippage = 0.001
        broker.commission = 0.001
        
        # Create order manager
        order_manager = OrderManager(event_bus, broker)
        assert order_manager is not None
        
        # Create strategy
        parameters = {
            'fast_window': 5,
            'slow_window': 15,
            'price_key': 'close',
            'symbols': ['TEST']
        }
        strategy = MACrossoverStrategy(event_bus, None, parameters=parameters)
        assert strategy is not None
        assert strategy.fast_window == 5
        assert strategy.slow_window == 15
    
    def test_event_creation(self):
        """Test that events can be created without errors."""
        # Create a bar event
        bar_data = {
            'symbol': 'TEST',
            'timestamp': '2024-01-01 09:30:00',
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000
        }
        bar_event = Event(EventType.BAR, bar_data)
        assert bar_event is not None
        assert bar_event.type == EventType.BAR
        assert bar_event.data == bar_data
        
        # Test accessing event data via get methods if they exist
        if hasattr(bar_event, 'get_symbol'):
            assert bar_event.get_symbol() == 'TEST'
        
        if hasattr(bar_event, 'get_close'):
            assert bar_event.get_close() == 100.5
    
    def test_portfolio_operations(self):
        """Test basic portfolio operations without events."""
        # Create portfolio
        event_bus = EventBus()
        portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
        
        # Initial state
        assert portfolio.cash == 100000.0
        assert len(portfolio.get_positions()) == 0
        
        # Add a position directly if method exists
        if hasattr(portfolio, 'update_position'):
            portfolio.update_position('TEST', 100, 50.0, 5.0)
            positions = portfolio.get_positions()
            assert len(positions) == 1
            assert 'TEST' in positions
    
    def test_broker_simulation(self):
        """Test broker simulation without events."""
        # Create components
        event_bus = EventBus()
        broker = SimulatedBroker(event_bus)
        
        # Create a simple order event
        order_data = {
            'symbol': 'TEST',
            'order_id': '12345',
            'direction': 'BUY',
            'quantity': 100,
            'order_type': 'MARKET',
            'price': 50.0,
            'timestamp': '2024-01-01 09:30:00'
        }
        order_event = Event(EventType.ORDER, order_data)
        
        # Process the order directly if method exists
        if hasattr(broker, 'process_order'):
            fill_event = broker.process_order(order_event)
            assert fill_event is not None
            assert fill_event.type == EventType.FILL
            
            # Check fill data
            fill_data = fill_event.data
            assert fill_data.get('symbol') == 'TEST'
            assert fill_data.get('order_id') == '12345'
            assert fill_data.get('direction') == 'BUY'
            assert fill_data.get('quantity') == 100
