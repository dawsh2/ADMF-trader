"""
Portfolio management for tracking positions and equity.
"""
import pandas as pd
import datetime
import logging
import uuid
from typing import Dict, Any, List, Optional, Union

from src.core.events.event_types import EventType, Event
from src.core.events.event_utils import create_signal_event, EventTracker
from .position import Position

logger = logging.getLogger(__name__)

class PortfolioManager:
    """Portfolio for tracking positions and equity."""
    
    def __init__(self, event_bus=None, name=None, initial_cash=10000.0):
        """
        Initialize portfolio manager.
        
        Args:
            event_bus: Event bus for communication
            name: Portfolio name
            initial_cash: Initial cash balance
        """
        self._name = name or f"portfolio_{uuid.uuid4().hex[:8]}"
        self.event_bus = event_bus
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}  # symbol -> Position
        self.equity = initial_cash
        self.trades = []  # List of completed trades
        self.equity_curve = []  # List of equity points
        self.configured = False
        
        # Statistics tracking
        self.stats = {
            'trades_executed': 0,
            'long_trades': 0,
            'short_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'break_even_trades': 0,
            'total_pnl': 0.0,
            'total_commission': 0.0
        }
        
        # Event tracker for analysis
        self.event_tracker = EventTracker(f"{self._name}_tracker")
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.FILL, self.on_fill)
            self.event_bus.register(EventType.BAR, self.on_bar)
    
    def configure(self, config):
        """
        Configure the portfolio.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        # Extract parameters from config
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        self.initial_cash = config_dict.get('initial_cash', 10000.0)
        self.cash = self.initial_cash
        self.equity = self.initial_cash
        self._name = config_dict.get('name', self._name)
        
        self.configured = True
        logger.info(f"Configured portfolio {self._name} with initial cash: ${self.initial_cash:.2f}")
    
    def set_event_bus(self, event_bus):
        """
        Set the event bus.
        
        Args:
            event_bus: Event bus instance
        """
        self.event_bus = event_bus
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.FILL, self.on_fill)
            self.event_bus.register(EventType.BAR, self.on_bar)
    
    def on_fill(self, fill_event):
        """
        Handle fill events.
        
        Args:
            fill_event: Fill event to process
        """
        # Track the event
        self.event_tracker.track_event(fill_event)
        
        # Extract fill details
        symbol = fill_event.get_symbol()
        direction = fill_event.get_direction()
        quantity = fill_event.get_quantity()
        price = fill_event.get_price()
        commission = fill_event.get_commission()
        timestamp = fill_event.get_timestamp()
        
        # Convert to position update 
        quantity_change = quantity if direction == 'BUY' else -quantity
        
        # Get or create position
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        
        # Update position
        position = self.positions[symbol]
        pnl = position.update(quantity_change, price, timestamp)
        
        # Update cash
        trade_value = price * abs(quantity_change)
        self.cash -= trade_value if direction == 'BUY' else -trade_value
        self.cash -= commission  # Deduct commission
        
        # Update equity 
        self.update_equity()
        
        # Track trade for analysis
        trade = {
            'id': str(uuid.uuid4()),
            'timestamp': timestamp,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'pnl': pnl
        }
        self.trades.append(trade)
        
        # Update statistics
        self.stats['trades_executed'] += 1
        self.stats['total_commission'] += commission
        
        if direction == 'BUY':
            self.stats['long_trades'] += 1
        else:
            self.stats['short_trades'] += 1
            
        if pnl > 0:
            self.stats['winning_trades'] += 1
        elif pnl < 0:
            self.stats['losing_trades'] += 1
        else:
            self.stats['break_even_trades'] += 1
            
        self.stats['total_pnl'] += pnl
        
        # Log the fill
        logger.info(f"Fill: {direction} {quantity} {symbol} @ {price:.2f}, PnL: {pnl:.2f}")
        
        # Emit portfolio update event if event bus is available
        if self.event_bus:
            # Create a portfolio event
            portfolio_event = Event(
                EventType.PORTFOLIO, 
                {
                    'portfolio_id': self._name,
                    'cash': self.cash,
                    'equity': self.equity,
                    'trade': trade
                },
                timestamp
            )
            self.event_bus.emit(portfolio_event)
    
    def on_bar(self, bar_event):
        """
        Handle bar events for mark-to-market.
        
        Args:
            bar_event: Bar event to process
        """
        symbol = bar_event.get_symbol()
        price = bar_event.get_close()
        timestamp = bar_event.get_timestamp()
        
        # Mark position to market if exists
        if symbol in self.positions:
            self.positions[symbol].mark_to_market(price, timestamp)
        
        # Update equity
        self.update_equity()
        
        # Record equity point
        equity_point = {
            'timestamp': timestamp,
            'equity': self.equity,
            'cash': self.cash,
            'positions_value': self.equity - self.cash
        }
        self.equity_curve.append(equity_point)
    
    def update_equity(self):
        """
        Update portfolio equity.
        
        Returns:
            float: Current equity value
        """
        # Sum up all position values
        position_value = sum(pos.quantity * pos.current_price for pos in self.positions.values())
        self.equity = self.cash + position_value
        
        return self.equity
    
    def get_position(self, symbol):
        """
        Get position by symbol.
        
        Args:
            symbol: Position symbol
            
        Returns:
            Position object or None
        """
        return self.positions.get(symbol)
    
    def get_positions_summary(self):
        """
        Get summary of all positions.
        
        Returns:
            List of position dictionaries
        """
        return [pos.to_dict() for pos in self.positions.values()]
    
    def get_portfolio_summary(self):
        """
        Get portfolio summary.
        
        Returns:
            Dict with portfolio summary
        """
        position_value = sum(pos.quantity * pos.current_price for pos in self.positions.values())
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl() for pos in self.positions.values())
        
        return {
            'cash': self.cash,
            'equity': self.equity,
            'position_value': position_value,
            'positions': len(self.positions),
            'long_positions': sum(1 for pos in self.positions.values() if pos.quantity > 0),
            'short_positions': sum(1 for pos in self.positions.values() if pos.quantity < 0),
            'realized_pnl': total_realized_pnl,
            'unrealized_pnl': total_unrealized_pnl,
            'total_pnl': total_realized_pnl + total_unrealized_pnl,
            'total_commission': self.stats['total_commission'],
            'trades_executed': self.stats['trades_executed']
        }
    
    def get_equity_curve_df(self):
        """
        Get equity curve as DataFrame.
        
        Returns:
            DataFrame with equity curve
        """
        if not self.equity_curve:
            return pd.DataFrame()
            
        df = pd.DataFrame(self.equity_curve)
        
        if not df.empty:
            df.set_index('timestamp', inplace=True)
            
        return df
    
    def get_recent_trades(self, n=None):
        """
        Get recent trades.
        
        Args:
            n: Number of trades to return (None for all)
            
        Returns:
            List of trade dictionaries
        """
        if n is None:
            return list(self.trades)
        return list(self.trades[-n:])
    
    def get_trades_as_df(self):
        """
        Get trades as DataFrame.
        
        Returns:
            DataFrame with trade data
        """
        if not self.trades:
            return pd.DataFrame()
            
        df = pd.DataFrame(self.trades)
        
        if not df.empty and 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
            
        return df
    
    def get_stats(self):
        """
        Get portfolio statistics.
        
        Returns:
            Dict with statistics
        """
        # Calculate additional statistics
        win_rate = 0.0
        if self.stats['trades_executed'] > 0:
            win_rate = self.stats['winning_trades'] / self.stats['trades_executed']
            
        avg_win = 0.0
        winning_trades = [trade['pnl'] for trade in self.trades if trade['pnl'] > 0]
        if winning_trades:
            avg_win = sum(winning_trades) / len(winning_trades)
            
        avg_loss = 0.0
        losing_trades = [trade['pnl'] for trade in self.trades if trade['pnl'] < 0]
        if losing_trades:
            avg_loss = sum(losing_trades) / len(losing_trades)
            
        # Update and return stats
        self.stats.update({
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win) / abs(avg_loss) if avg_loss != 0 else float('inf')
        })
        
        return dict(self.stats)
    
    def reset(self):
        """Reset portfolio to initial state."""
        self.cash = self.initial_cash
        self.positions = {}
        self.equity = self.initial_cash
        self.trades = []
        self.equity_curve = []
        
        # Reset statistics
        self.stats = {
            'trades_executed': 0,
            'long_trades': 0,
            'short_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'break_even_trades': 0,
            'total_pnl': 0.0,
            'total_commission': 0.0
        }
        
        # Reset event tracker
        self.event_tracker.reset()
        
        logger.info(f"Reset portfolio {self._name} to initial state with cash: ${self.initial_cash:.2f}")
    
    def to_dict(self):
        """
        Convert portfolio to dictionary.
        
        Returns:
            Dict representation of portfolio
        """
        return {
            'name': self._name,
            'cash': self.cash,
            'equity': self.equity,
            'initial_cash': self.initial_cash,
            'positions': {symbol: pos.to_dict() for symbol, pos in self.positions.items()},
            'stats': self.get_stats(),
            'configured': self.configured
        }
    
    @property
    def name(self):
        """Get portfolio name."""
        return self._name
