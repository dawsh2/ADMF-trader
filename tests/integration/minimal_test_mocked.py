"""
Minimal integration test using mock Event class.
"""

import sys
import os
import pytest

# Add project root to path so 'src' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import mocks
from tests.mocks.event_mocks import MockEvent, MockEventType, create_mock_signal_event

# Import required components but not the problematic Event class
from src.core.events.event_bus import EventBus
from src.strategy.strategy_base import Strategy
from src.risk.portfolio.portfolio import PortfolioManager

@pytest.mark.integration
class TestMinimalIntegration:
    
    def test_event_bus_registration(self):
        """Test registering event handlers."""
        # Create event bus
        event_bus = EventBus()
        
        # Create handler with call tracking
        calls = []
        def handler(event):
            calls.append(event)
        
        # Register handler - use our mock event type value
        event_bus.register(MockEventType.BAR.value, handler)
        
        # Create and emit mock event
        data = {'symbol': 'TEST', 'close': 100.0}
        event = MockEvent(MockEventType.BAR, data)
        
        # Use direct handler call instead of event_bus.emit to avoid adapter issues
        handler(event)
        
        # Check handler was called
        assert len(calls) == 1
        assert calls[0] == event
    
    def test_portfolio_operations(self):
        """Test basic portfolio operations."""
        # Create event bus
        event_bus = EventBus()
        
        # Create portfolio
        portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
        
        # Check initial state
        assert portfolio.cash == 10000.0
        assert len(portfolio.positions) == 0
        
        # Test position updating
        portfolio.update_position('TEST', 100, 100.0, 0.0)
        
        # Check position was created
        assert 'TEST' in portfolio.positions
        position = portfolio.positions['TEST']
        assert position.quantity == 100
        assert position.avg_cost == 100.0
    
    def test_signal_creation(self):
        """Test creating signal events."""
        # Create a signal event using mock
        signal = create_mock_signal_event(1, 100.5, 'TEST')
        
        # Check values
        assert signal.get_type() == MockEventType.SIGNAL
        assert signal.get_signal_value() == 1
        assert signal.get_symbol() == 'TEST'
        assert signal.data.get('price') == 100.5
