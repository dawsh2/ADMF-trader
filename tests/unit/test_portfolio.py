"""
Unit tests for the PortfolioManager class.
"""

import sys
import os
import pytest
import datetime
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import components to test
from src.risk.portfolio.portfolio import PortfolioManager
from src.risk.portfolio.position import Position
from src.core.events.event_types import Event, EventType
from src.core.events.event_bus import EventBus

class TestPortfolioManager:
    """Tests for the PortfolioManager class."""
    
    def test_portfolio_creation(self):
        """Test creating a PortfolioManager with basic attributes."""
        # Create portfolio
        portfolio = PortfolioManager(initial_cash=10000.0)
        
        # Test attributes
        assert portfolio.cash == 10000.0
        assert portfolio.initial_cash == 10000.0
        assert portfolio.equity == 10000.0
        assert portfolio.positions == {}
        assert portfolio.trades == []
        assert portfolio.equity_curve == []
    
    def test_portfolio_with_event_bus(self):
        """Test portfolio with event bus registration."""
        # Create event bus
        event_bus = EventBus()
        
        # Create portfolio with event bus
        portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
        
        # Test event bus was set
        assert portfolio.event_bus is event_bus
        
        # Check that portfolio has registered for events
        assert event_bus.has_handlers(EventType.FILL)
        assert event_bus.has_handlers(EventType.BAR)
    
    def test_portfolio_reset(self):
        """Test resetting a portfolio."""
        # Create portfolio
        portfolio = PortfolioManager(initial_cash=10000.0)
        
        # Create a position
        symbol = 'TEST'
        portfolio.positions[symbol] = Position(symbol, 100, 50.0)
        
        # Add a trade
        portfolio.trades.append({
            'symbol': symbol,
            'direction': 'BUY',
            'quantity': 100,
            'price': 50.0,
            'pnl': 0.0
        })
        
        # Change cash
        portfolio.cash = 5000.0
        
        # Reset portfolio
        portfolio.reset()
        
        # Test reset state
        assert portfolio.cash == 10000.0
        assert portfolio.equity == 10000.0
        assert portfolio.positions == {}
        assert portfolio.trades == []
        assert len(portfolio.equity_curve) == 1  # Should have one initial point
    
    def test_portfolio_configuration(self):
        """Test configuring a portfolio."""
        # Create portfolio
        portfolio = PortfolioManager(initial_cash=10000.0)
        
        # Create config
        config = {
            'initial_cash': 20000.0,
            'name': 'TestPortfolio'
        }
        
        # Configure portfolio
        portfolio.configure(config)
        
        # Test configured state
        assert portfolio.initial_cash == 20000.0
        assert portfolio.cash == 20000.0
        assert portfolio.equity == 20000.0
        assert portfolio.name == 'TestPortfolio'
        assert portfolio.configured
    
    def test_get_position(self):
        """Test getting a position by symbol."""
        # Create portfolio
        portfolio = PortfolioManager(initial_cash=10000.0)
        
        # Create a position
        symbol = 'TEST'
        portfolio.positions[symbol] = Position(symbol, 100, 50.0)
        
        # Test get_position
        position = portfolio.get_position(symbol)
        assert position is not None
        assert position.symbol == symbol
        assert position.quantity == 100
        
        # Test get_position for non-existent symbol
        position = portfolio.get_position('NONEXISTENT')
        assert position is None
    
    def test_on_fill_buy(self):
        """Test processing a buy fill event."""
        # Create portfolio with event bus
        event_bus = EventBus()
        portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
        
        # Create a fill event
        fill_data = {
            'symbol': 'TEST',
            'direction': 'BUY',
            'size': 100,
            'fill_price': 50.0,
            'commission': 5.0
        }
        fill_event = Event(EventType.FILL, fill_data)
        
        # Process the fill event
        portfolio.on_fill(fill_event)
        
        # Test portfolio state after fill
        assert portfolio.cash == 10000.0 - 100 * 50.0 - 5.0
        assert 'TEST' in portfolio.positions
        assert portfolio.positions['TEST'].quantity == 100
        assert portfolio.positions['TEST'].cost_basis == 50.0
    
    def test_on_fill_sell(self):
        """Test processing a sell fill event."""
        # Create portfolio with event bus
        event_bus = EventBus()
        portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
        
        # Create a position first
        symbol = 'TEST'
        portfolio.positions[symbol] = Position(symbol, 100, 50.0)
        portfolio.cash = 10000.0 - 100 * 50.0  # Adjust cash as if position was bought
        
        # Create a sell fill event
        fill_data = {
            'symbol': symbol,
            'direction': 'SELL',
            'size': 100,
            'fill_price': 60.0,
            'commission': 5.0
        }
        fill_event = Event(EventType.FILL, fill_data)
        
        # Process the fill event
        portfolio.on_fill(fill_event)
        
        # Test portfolio state after fill
        assert portfolio.cash == 10000.0 - 100 * 50.0 + 100 * 60.0 - 5.0
        assert symbol in portfolio.positions  # Position still exists but quantity is 0
        assert portfolio.positions[symbol].quantity == 0
        assert portfolio.positions[symbol].realized_pnl == 100 * (60.0 - 50.0)
        assert len(portfolio.trades) == 1  # Should have recorded a trade
    
    def test_on_bar(self):
        """Test processing a bar event for mark-to-market."""
        # Create portfolio with event bus
        event_bus = EventBus()
        portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
        
        # Create a position
        symbol = 'TEST'
        portfolio.positions[symbol] = Position(symbol, 100, 50.0)
        portfolio.cash = 10000.0 - 100 * 50.0  # Adjust cash as if position was bought
        
        # Make sure equity is updated
        portfolio.update_equity()
        
        # Create a bar event
        bar_data = {
            'symbol': symbol,
            'open': 59.0,
            'high': 61.0,
            'low': 58.0,
            'close': 60.0,
            'volume': 1000
        }
        bar_event = Event(EventType.BAR, bar_data)
        
        # Process the bar event
        portfolio.on_bar(bar_event)
        
        # Test portfolio state after bar
        assert portfolio.positions[symbol].current_price == 60.0
        assert portfolio.equity == portfolio.cash + portfolio.positions[symbol].quantity * 60.0
        assert len(portfolio.equity_curve) > 0
    
    def test_update_equity(self):
        """Test updating portfolio equity."""
        # Create portfolio
        portfolio = PortfolioManager(initial_cash=10000.0)
        
        # Create positions
        portfolio.positions['TEST1'] = Position('TEST1', 100, 50.0)
        portfolio.positions['TEST2'] = Position('TEST2', -50, 60.0)
        
        # Mark positions to market
        portfolio.positions['TEST1'].mark_to_market(55.0)
        portfolio.positions['TEST2'].mark_to_market(55.0)
        
        # Adjust cash
        portfolio.cash = 10000.0 - 100 * 50.0 + 50 * 60.0  # Buy TEST1, short TEST2
        
        # Update equity
        equity = portfolio.update_equity()
        
        # Test equity calculation
        expected_equity = portfolio.cash + 100 * 55.0 - 50 * 55.0
        assert equity == expected_equity
        assert portfolio.equity == expected_equity
    
    def test_get_portfolio_summary(self):
        """Test getting portfolio summary."""
        # Create portfolio
        portfolio = PortfolioManager(initial_cash=10000.0)
        
        # Create positions
        portfolio.positions['TEST1'] = Position('TEST1', 100, 50.0)
        portfolio.positions['TEST2'] = Position('TEST2', -50, 60.0)
        
        # Mark positions to market
        portfolio.positions['TEST1'].mark_to_market(55.0)
        portfolio.positions['TEST2'].mark_to_market(55.0)
        
        # Adjust cash
        portfolio.cash = 10000.0 - 100 * 50.0 + 50 * 60.0  # Buy TEST1, short TEST2
        
        # Update equity
        portfolio.update_equity()
        
        # Get summary
        summary = portfolio.get_portfolio_summary()
        
        # Test summary contents
        assert 'cash' in summary
        assert 'equity' in summary
        assert 'position_value' in summary
        assert 'positions' in summary
        assert 'long_positions' in summary
        assert 'short_positions' in summary
        assert 'realized_pnl' in summary
        assert 'unrealized_pnl' in summary
        assert 'total_pnl' in summary
        
        # Test counts
        assert summary['positions'] == 2
        assert summary['long_positions'] == 1
        assert summary['short_positions'] == 1
    
    def test_get_equity_curve_df(self):
        """Test getting equity curve as DataFrame."""
        # Create portfolio
        portfolio = PortfolioManager(initial_cash=10000.0)
        
        # Reset to create initial equity curve point
        portfolio.reset()
        
        # Add some equity curve points
        portfolio.equity_curve.append({
            'timestamp': datetime.datetime(2024, 1, 1, 10, 0, 0),
            'equity': 10100.0,
            'cash': 10100.0,
            'positions_value': 0.0
        })
        
        portfolio.equity_curve.append({
            'timestamp': datetime.datetime(2024, 1, 1, 11, 0, 0),
            'equity': 10200.0,
            'cash': 5200.0,
            'positions_value': 5000.0
        })
        
        # Get DataFrame
        df = portfolio.get_equity_curve_df()
        
        # Test DataFrame
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 3  # Initial point plus two added
        assert 'equity' in df.columns
        assert 'cash' in df.columns
        assert 'positions_value' in df.columns
    
    def test_get_recent_trades(self):
        """Test getting recent trades."""
        # Create portfolio
        portfolio = PortfolioManager(initial_cash=10000.0)
        
        # Add some trades
        trade1 = {
            'id': '1',
            'timestamp': datetime.datetime(2024, 1, 1, 10, 0, 0),
            'symbol': 'TEST1',
            'direction': 'BUY',
            'quantity': 100,
            'price': 50.0,
            'commission': 5.0,
            'pnl': 0.0
        }
        
        trade2 = {
            'id': '2',
            'timestamp': datetime.datetime(2024, 1, 1, 11, 0, 0),
            'symbol': 'TEST1',
            'direction': 'SELL',
            'quantity': 100,
            'price': 60.0,
            'commission': 5.0,
            'pnl': 1000.0
        }
        
        portfolio.trades.append(trade1)
        portfolio.trades.append(trade2)
        
        # Get all trades
        trades = portfolio.get_recent_trades()
        assert len(trades) == 2
        
        # Get limited trades
        trades = portfolio.get_recent_trades(1)
        assert len(trades) == 1
        assert trades[0]['id'] == '2'  # Should get most recent
