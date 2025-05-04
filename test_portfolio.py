#!/usr/bin/env python
"""
Test the portfolio manager to verify our fixes.
"""

import os
import sys
import logging
from datetime import datetime

# Set up path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the fixed portfolio manager
from src.core.events.event_bus import EventBus
from src.core.events.event_types import Event, EventType
from src.risk.portfolio.portfolio import PortfolioManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_portfolio_creation():
    """Test portfolio creation and basic properties."""
    portfolio = PortfolioManager(name="test_portfolio", initial_cash=10000.0)
    
    assert portfolio.name == "test_portfolio"
    assert portfolio.cash == 10000.0
    assert portfolio.equity == 10000.0
    assert len(portfolio.positions) == 0
    logger.info("✅ Portfolio creation test passed")

def test_portfolio_with_event_bus():
    """Test portfolio with event bus integration."""
    event_bus = EventBus()
    portfolio = PortfolioManager(event_bus, name="test_portfolio", initial_cash=10000.0)
    
    assert portfolio.event_bus is event_bus
    assert event_bus.has_handlers(EventType.FILL)
    assert event_bus.has_handlers(EventType.BAR)
    logger.info("✅ Portfolio with event bus test passed")

def test_get_positions():
    """Test the get_positions method."""
    portfolio = PortfolioManager(name="test_portfolio", initial_cash=10000.0)
    
    # Portfolio starts with no positions
    positions = portfolio.get_positions()
    assert isinstance(positions, dict)
    assert len(positions) == 0
    
    # Create a fill event to add a position
    fill_data = {
        'symbol': 'TEST',
        'direction': 'BUY',
        'size': 100,
        'fill_price': 100.0,
        'commission': 0.0
    }
    fill_event = Event(EventType.FILL, fill_data)
    
    # Process the fill
    portfolio.on_fill(fill_event)
    
    # Check that the position was added
    positions = portfolio.get_positions()
    assert len(positions) == 1
    assert 'TEST' in positions
    assert positions['TEST'].quantity == 100
    logger.info("✅ Get positions test passed")

def test_get_equity_curve():
    """Test the get_equity_curve method."""
    portfolio = PortfolioManager(name="test_portfolio", initial_cash=10000.0)
    
    # Get equity curve
    equity_curve = portfolio.get_equity_curve()
    assert isinstance(equity_curve, list)
    assert len(equity_curve) >= 1  # Should have at least one point from initialization
    
    # Get equity curve dataframe
    df = portfolio.get_equity_curve_df()
    assert 'equity' in df.columns
    assert 'cash' in df.columns
    logger.info("✅ Get equity curve test passed")

def test_portfolio_fill_handling():
    """Test fill event handling in portfolio."""
    portfolio = PortfolioManager(name="test_portfolio", initial_cash=10000.0)
    
    # Initial cash
    initial_cash = portfolio.cash
    
    # Create a buy fill
    buy_fill = {
        'symbol': 'TEST',
        'direction': 'BUY',
        'size': 100,
        'fill_price': 50.0,
        'commission': 5.0
    }
    buy_event = Event(EventType.FILL, buy_fill)
    
    # Process the buy fill
    portfolio.on_fill(buy_event)
    
    # Check portfolio state after buy
    assert 'TEST' in portfolio.positions
    assert portfolio.positions['TEST'].quantity == 100
    assert portfolio.cash == initial_cash - (100 * 50.0) - 5.0
    
    # Create a sell fill
    sell_fill = {
        'symbol': 'TEST',
        'direction': 'SELL',
        'size': 100,
        'fill_price': 60.0,
        'commission': 5.0
    }
    sell_event = Event(EventType.FILL, sell_fill)
    
    # Process the sell fill
    portfolio.on_fill(sell_event)
    
    # Check portfolio state after sell
    assert portfolio.positions['TEST'].quantity == 0
    assert portfolio.cash > initial_cash  # Should have made profit
    assert len(portfolio.trades) == 2
    logger.info("✅ Portfolio fill handling test passed")

def main():
    """Run portfolio tests."""
    logger.info("Running portfolio tests...")
    
    test_portfolio_creation()
    test_portfolio_with_event_bus()
    test_get_positions()
    test_get_equity_curve()
    test_portfolio_fill_handling()
    
    logger.info("All portfolio tests passed! ✅")
    return 0

if __name__ == "__main__":
    sys.exit(main())
