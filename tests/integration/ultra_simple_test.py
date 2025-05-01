"""
Ultra simple test file with no dependencies or events.
Each test is completely isolated and focused on a single component.
"""

import sys
import os
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import only what we need for each test
# DO NOT import Event class until needed

class TestUltraSimple:
    """Ultra simple test class with isolated tests."""
    
    def test_event_bus_only(self):
        """Test only EventBus without Event class."""
        # Import only what we need
        from src.core.events.event_bus import EventBus
        
        # Create event bus
        event_bus = EventBus()
        
        # Test basic attributes
        assert hasattr(event_bus, 'handlers')
        assert hasattr(event_bus, 'register')
        assert hasattr(event_bus, 'emit')
        
        # Simple handler registration
        handler_called = False
        
        def test_handler(event):
            nonlocal handler_called
            handler_called = True
        
        # Register for a simple integer event type
        event_bus.register(1, test_handler)
        
        # Create a dummy event (not using Event class)
        dummy_event = type('DummyEvent', (), {'type': 1})()
        
        # Emit the event
        event_bus.emit(dummy_event)
        
        # Check handler was called
        assert handler_called
    
    def test_position_only(self):
        """Test only Position class."""
        # Import only what we need
        from src.risk.portfolio.position import Position
        
        # Create position
        position = Position('TEST')
        
        # Test attributes
        assert position.symbol == 'TEST'
        assert position.quantity == 0
        assert position.cost_basis == 0.0
        
        # Test methods
        position.add_quantity(100, 100.0)
        assert position.quantity == 100
        assert position.cost_basis == 100.0
        
        # Test market value
        assert position.market_value(110.0) == 11000.0
    
    def test_portfolio_basic(self):
        """Test basic PortfolioManager without event bus."""
        # Import only what we need
        from src.risk.portfolio.portfolio import PortfolioManager
        
        # Create portfolio manager without event bus
        portfolio = PortfolioManager(event_bus=None, initial_cash=10000.0)
        
        # Test basic attributes
        assert portfolio.cash == 10000.0
        assert portfolio.positions == {}
        assert portfolio.equity == 10000.0
