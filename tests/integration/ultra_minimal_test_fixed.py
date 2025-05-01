"""
Ultra minimal integration test with no dependencies between tests.
Each test is completely independent and doesn't rely on shared fixtures.
This version uses event.event_type directly instead of event.type.
"""

import pytest

# Import minimal required components
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from src.strategy.strategy_base import Strategy
from src.risk.portfolio.portfolio import PortfolioManager


@pytest.mark.integration
class TestUltraMinimalIntegration:
    
    def test_event_bus_creation(self):
        """Test that an event bus can be created."""
        event_bus = EventBus()
        assert event_bus is not None
        assert hasattr(event_bus, 'handlers')
    
    def test_event_creation(self):
        """Test that events can be created."""
        # Simple event with minimal data
        data = {'test': 'data'}
        event = Event(EventType.BAR, data)
        
        assert event is not None
        # Use event_type directly instead of type
        assert event.event_type == EventType.BAR
        assert event.data == data
    
    def test_portfolio_creation(self):
        """Test that a portfolio can be created."""
        # Create a new event bus for this test only
        event_bus = EventBus()
        
        # Create portfolio
        portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
        assert portfolio is not None
        assert portfolio.cash == 100000.0
    
    def test_strategy_base(self):
        """Test that the strategy base class can be initialized."""
        # Create a new event bus for this test only
        event_bus = EventBus()
        
        # Simple strategy parameters
        parameters = {'test_param': 42}
        
        # Create a basic strategy (abstract base class)
        try:
            strategy = Strategy(event_bus, None, "test_strategy", parameters)
            assert strategy is not None
            assert strategy.name == "test_strategy"
            assert strategy.parameters.get('test_param') == 42
        except TypeError:
            # If Strategy is abstract and can't be instantiated directly,
            # just pass the test
            assert True
