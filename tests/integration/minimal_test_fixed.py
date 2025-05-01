"""
Minimal integration test with fixed method calls.
Uses the actual methods available in the PortfolioManager class.
"""

import sys
import os
import pytest

# Add project root to path so 'src' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import required components 
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from src.strategy.strategy_base import Strategy
from src.risk.portfolio.portfolio import PortfolioManager
from src.risk.portfolio.position import Position

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
        
        # Register handler
        event_bus.register(EventType.BAR, handler)
        
        # Create and emit event
        data = {'symbol': 'TEST', 'close': 100.0}
        event = Event(EventType.BAR, data)
        event_bus.emit(event)
        
        # Check handler was called
        assert len(calls) == 1
        assert calls[0] == event
    
    def test_portfolio_operations(self):
        """Test basic portfolio operations using the proper methods."""
        # Create event bus
        event_bus = EventBus()
        
        # Create portfolio
        portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
        
        # Check initial state
        assert portfolio.cash == 10000.0
        assert len(portfolio.positions) == 0
        
        # Create a position directly
        symbol = 'TEST'
        if symbol not in portfolio.positions:
            portfolio.positions[symbol] = Position(symbol)
        
        # Use the position to add quantity
        position = portfolio.positions[symbol]
        position.add_quantity(100, 100.0)  # Buy 100 shares at $100
        
        # Check position was created correctly
        assert position.quantity == 100
        assert position.cost_basis == 100.0
        
        # Verify portfolio has the position
        assert symbol in portfolio.positions
        assert portfolio.get_position(symbol) is not None
        assert portfolio.get_position(symbol).quantity == 100
    
    def test_position_methods(self):
        """Test Position class methods directly."""
        # Create a position
        position = Position('TEST', 0, 0.0)
        
        # Add to position
        pnl = position.add_quantity(100, 100.0)
        
        # Check position state
        assert position.quantity == 100
        assert position.cost_basis == 100.0
        assert pnl == 0.0  # No realized PnL for new position
        
        # Mark to market at higher price
        position.mark_to_market(110.0)
        
        # Check unrealized PnL
        assert position.unrealized_pnl() == 1000.0  # 100 shares * $10 gain
        
        # Reduce position
        pnl = position.reduce_quantity(50, 110.0)
        
        # Check position and PnL
        assert position.quantity == 50
        assert position.realized_pnl == 500.0  # 50 shares * $10 gain
        assert pnl == 500.0
    
    def test_fill_event_processing(self):
        """Test portfolio processing of fill events."""
        # Create event bus
        event_bus = EventBus()
        
        # Create portfolio
        portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
        
        # Create a fill event (buy 100 shares at $100)
        fill_data = {
            'symbol': 'TEST',
            'direction': 'BUY',
            'size': 100,
            'fill_price': 100.0,
            'commission': 0.0
        }
        fill_event = Event(EventType.FILL, fill_data)
        
        # Process the fill event
        portfolio.on_fill(fill_event)
        
        # Check portfolio state
        assert 'TEST' in portfolio.positions
        position = portfolio.get_position('TEST')
        assert position.quantity == 100
        assert position.cost_basis == 100.0
        assert portfolio.cash == 10000.0 - 100 * 100.0  # Initial cash - cost
