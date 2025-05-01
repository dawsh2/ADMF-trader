"""
Unit tests for the Position class.
"""

import sys
import os
import pytest
import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import components to test
from src.risk.portfolio.position import Position

class TestPosition:
    """Tests for the Position class."""
    
    def test_position_creation(self):
        """Test creating a Position with basic attributes."""
        # Create position
        position = Position('TEST')
        
        # Test attributes
        assert position.symbol == 'TEST'
        assert position.quantity == 0
        assert position.cost_basis == 0.0
        assert position.realized_pnl == 0.0
        assert isinstance(position.id, str)
        assert isinstance(position.last_update, datetime.datetime)
    
    def test_position_with_initial_values(self):
        """Test creating a Position with initial values."""
        # Create position with initial values
        position = Position('TEST', 100, 50.0)
        
        # Test attributes
        assert position.symbol == 'TEST'
        assert position.quantity == 100
        assert position.cost_basis == 50.0
    
    def test_add_to_position(self):
        """Test adding to a position."""
        # Create position
        position = Position('TEST')
        
        # Add to position
        pnl = position.add_quantity(100, 50.0)
        
        # Test state after addition
        assert position.quantity == 100
        assert position.cost_basis == 50.0
        assert pnl == 0.0  # No PnL for first addition
        
        # Add more with same direction
        pnl = position.add_quantity(50, 60.0)
        
        # Test updated state
        assert position.quantity == 150
        assert position.cost_basis > 50.0  # Should increase due to higher price
        assert pnl == 0.0  # No PnL when adding in same direction
    
    def test_reduce_position(self):
        """Test reducing a position."""
        # Create position with initial values
        position = Position('TEST', 100, 50.0)
        
        # Reduce position
        pnl = position.reduce_quantity(40, 60.0)
        
        # Test reduced position
        assert position.quantity == 60
        assert position.cost_basis == 50.0  # Cost basis shouldn't change
        assert pnl > 0  # Should realize profit due to price increase
        assert pnl == 40 * (60.0 - 50.0)  # Realized PnL calculation
        
        # Further reduce to zero
        pnl = position.reduce_quantity(60, 60.0)
        
        # Test closed position
        assert position.quantity == 0
        assert position.realized_pnl > 0
        assert pnl == 60 * (60.0 - 50.0)  # Realized PnL calculation
    
    def test_position_flip(self):
        """Test flipping a position from long to short or vice versa."""
        # Create long position
        position = Position('TEST', 100, 50.0)
        
        # Flip to short (sell more than current long position)
        pnl = position.add_quantity(-150, 60.0)
        
        # Test flipped position
        assert position.quantity == -50
        assert position.cost_basis == 60.0  # New cost basis at flip price
        assert pnl > 0  # Should realize profit on closed portion
        assert pnl == 100 * (60.0 - 50.0)  # Realized PnL calculation
        
        # Flip back to long
        pnl = position.add_quantity(100, 40.0)
        
        # Test flipped position
        assert position.quantity == 50
        assert position.cost_basis == 40.0  # New cost basis at flip price
        assert pnl > 0  # Should realize profit on closed portion
        assert pnl == 50 * (60.0 - 40.0)  # Realized PnL calculation
    
    def test_mark_to_market(self):
        """Test marking a position to market."""
        # Create position with initial values
        position = Position('TEST', 100, 50.0)
        
        # Mark to market with higher price
        unrealized_pnl = position.mark_to_market(60.0)
        
        # Test unrealized PnL
        assert position.current_price == 60.0
        assert unrealized_pnl == 100 * (60.0 - 50.0)  # Unrealized PnL calculation
        assert position.unrealized_pnl() == unrealized_pnl
        
        # Mark to market with lower price
        unrealized_pnl = position.mark_to_market(40.0)
        
        # Test unrealized PnL
        assert position.current_price == 40.0
        assert unrealized_pnl == 100 * (40.0 - 50.0)  # Unrealized PnL calculation
        assert unrealized_pnl < 0  # Should be negative
        assert position.unrealized_pnl() == unrealized_pnl
    
    def test_total_pnl(self):
        """Test total PnL calculation."""
        # Create position
        position = Position('TEST')
        
        # Build position with realized PnL
        position.add_quantity(100, 50.0)
        position.reduce_quantity(50, 60.0)
        
        # Mark to market for unrealized PnL
        position.mark_to_market(55.0)
        
        # Calculate expected values
        realized_pnl = 50 * (60.0 - 50.0)  # From reduction
        unrealized_pnl = 50 * (55.0 - 50.0)  # From remaining position
        expected_total = realized_pnl + unrealized_pnl
        
        # Test total PnL
        assert position.realized_pnl == realized_pnl
        assert position.unrealized_pnl() == unrealized_pnl
        assert position.total_pnl() == expected_total
    
    def test_position_direction(self):
        """Test position direction methods."""
        # Create position
        position = Position('TEST')
        
        # Test flat position
        assert position.is_flat()
        assert not position.is_long()
        assert not position.is_short()
        assert position.position_direction() == "FLAT"
        
        # Test long position
        position.add_quantity(100, 50.0)
        assert not position.is_flat()
        assert position.is_long()
        assert not position.is_short()
        assert position.position_direction() == "LONG"
        
        # Test short position
        position = Position('TEST')
        position.add_quantity(-100, 50.0)
        assert not position.is_flat()
        assert not position.is_long()
        assert position.is_short()
        assert position.position_direction() == "SHORT"
    
    def test_position_serialization(self):
        """Test position to_dict and from_dict methods."""
        # Create position with some activity
        position = Position('TEST')
        position.add_quantity(100, 50.0)
        position.reduce_quantity(30, 60.0)
        position.mark_to_market(55.0)
        
        # Convert to dict
        position_dict = position.to_dict()
        
        # Test dict contents
        assert position_dict['symbol'] == 'TEST'
        assert position_dict['quantity'] == 70
        assert position_dict['cost_basis'] == 50.0
        assert position_dict['current_price'] == 55.0
        assert 'realized_pnl' in position_dict
        assert 'unrealized_pnl' in position_dict
        assert 'total_pnl' in position_dict
        
        # Test from_dict if method exists
        if hasattr(Position, 'from_dict'):
            new_position = Position.from_dict(position_dict)
            assert new_position.symbol == position.symbol
            assert new_position.quantity == position.quantity
            assert new_position.cost_basis == position.cost_basis
