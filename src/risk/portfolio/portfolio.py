

# src/portfolio/portfolio.py
from .position import Position
from core.events.event_types import EventType
import pandas as pd
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

@ObjectRegistry.register
class Position:
    """Class representing a position in a single instrument."""
    
    def __init__(self, symbol, quantity=0, cost_basis=0.0):
        """
        Initialize a position.
        
        Args:
            symbol: Position symbol
            quantity: Initial position quantity (positive for long, negative for short)
            cost_basis: Initial cost basis
        """
        self.symbol = symbol
        self.quantity = quantity
        self.cost_basis = cost_basis
        self.realized_pnl = 0.0
        self.market_value = 0.0
        self.current_price = cost_basis if cost_basis > 0 else 0.0
        
        # Track transactions for analysis
        self.transactions = []
        
        # Initialize internal tracking
        self._total_cost = abs(quantity) * cost_basis if quantity != 0 else 0.0
    
    def update(self, quantity_change, price, timestamp=None):
        """
        Update position with a new transaction.
        
        Args:
            quantity_change: Change in quantity (positive for buys, negative for sells)
            price: Transaction price
            timestamp: Optional transaction timestamp
            
        Returns:
            float: Realized P&L if any
        """
        timestamp = timestamp or datetime.now()
        
        # Record transaction
        transaction = {
            'timestamp': timestamp,
            'quantity': quantity_change,
            'price': price,
            'type': 'BUY' if quantity_change > 0 else 'SELL',
        }
        self.transactions.append(transaction)
        
        # Track realized P&L for position reduction
        realized_pnl = 0.0
        
        # Update position
        if self.quantity * quantity_change >= 0:
            # Adding to position or opening new position
            new_quantity = self.quantity + quantity_change
            new_cost = self._total_cost + (quantity_change * price)
            
            # Update position
            self.quantity = new_quantity
            self._total_cost = new_cost
            
            # Update cost basis if position exists
            if new_quantity != 0:
                self.cost_basis = new_cost / abs(new_quantity)
        else:
            # Reducing or closing position
            if abs(quantity_change) <= abs(self.quantity):
                # Partial reduction
                reduction_ratio = abs(quantity_change) / abs(self.quantity)
                reduced_cost = self._total_cost * reduction_ratio
                
                # Calculate realized P&L
                if self.quantity > 0:  # Long position
                    realized_pnl = abs(quantity_change) * (price - self.cost_basis)
                else:  # Short position
                    realized_pnl = abs(quantity_change) * (self.cost_basis - price)
                
                # Update position
                self.quantity += quantity_change
                self._total_cost -= reduced_cost
                # Cost basis remains the same
                
            else:
                # Position flip
                # First close existing position
                if self.quantity > 0:  # Long position
                    realized_pnl = self.quantity * (price - self.cost_basis)
                else:  # Short position
                    realized_pnl = abs(self.quantity) * (self.cost_basis - price)
                
                # Then open new position in opposite direction
                new_quantity = self.quantity + quantity_change  # Will be opposite sign
                self.quantity = new_quantity
                self._total_cost = abs(new_quantity) * price
                self.cost_basis = price
        
        # Update realized P&L
        self.realized_pnl += realized_pnl
        
        # Update current price and market value
        self.current_price = price
        self.market_value = self.current_price * self.quantity
        
        return realized_pnl
    
    def mark_to_market(self, price):
        """
        Mark position to market price.
        
        Args:
            price: Current market price
            
        Returns:
            float: Unrealized P&L
        """
        self.current_price = price
        self.market_value = price * self.quantity
        return self.unrealized_pnl()
    
    def unrealized_pnl(self):
        """
        Calculate unrealized P&L.
        
        Returns:
            float: Unrealized P&L
        """
        if self.quantity == 0:
            return 0.0
            
        if self.quantity > 0:  # Long position
            return self.quantity * (self.current_price - self.cost_basis)
        else:  # Short position
            return abs(self.quantity) * (self.cost_basis - self.current_price)
    
    def total_pnl(self):
        """
        Calculate total P&L (realized + unrealized).
        
        Returns:
            float: Total P&L
        """
        return self.realized_pnl + self.unrealized_pnl()
    
    def __str__(self):
        return (f"Position({self.symbol}, quantity={self.quantity}, "
                f"cost_basis={self.cost_basis:.2f}, realized_pnl={self.realized_pnl:.2f})")
    
    def to_dict(self):
        """
        Convert position to dictionary.
        
        Returns:
            dict: Position as dictionary
        """
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'cost_basis': self.cost_basis,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl(),
            'market_value': self.market_value,
            'current_price': self.current_price
        }    
    
    
    @classmethod
    def from_dict(cls, data):
        """Reconstruct from dictionary."""
        position = cls(data["symbol"])
        position.quantity = data["quantity"]
        position.cost_basis = data["cost_basis"]
        position.realized_pnl = data["realized_pnl"]
        return positio


class Portfolio:
    """Portfolio for tracking positions and equity."""
    
    def __init__(self, event_bus, initial_cash=10000.0):
        """
        Initialize portfolio.
        
        Args:
            event_bus: Event bus for communication
            initial_cash: Initial cash balance
        """
        self.event_bus = event_bus
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}  # symbol -> Position
        self.equity = initial_cash
        self.trades = []  # List of completed trades
        self.equity_curve = []  # List of equity points
        
        # Register for events
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
            config = config.as_dict()
            
        self.initial_cash = config.get('initial_cash', 10000.0)
        self.cash = self.initial_cash
        self.equity = self.initial_cash
    
    def on_fill(self, fill_event):
        """
        Handle fill events.
        
        Args:
            fill_event: Fill event to process
        """
        symbol = fill_event.get_symbol()
        direction = fill_event.get_direction()
        quantity = fill_event.get_quantity()
        price = fill_event.get_price()
        commission = fill_event.get_commission()
        
        # Convert to position update 
        quantity_change = quantity if direction == 'BUY' else -quantity
        
        # Get or create position
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        
        # Update position
        position = self.positions[symbol]
        pnl = position.update(quantity_change, price, fill_event.get_timestamp())
        
        # Update cash
        trade_value = price * abs(quantity_change)
        self.cash -= trade_value if direction == 'BUY' else -trade_value
        self.cash -= commission  # Deduct commission
        
        # Update equity 
        self.update_equity()
        
        # Record trade
        trade = {
            'timestamp': fill_event.get_timestamp(),
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'pnl': pnl
        }
        self.trades.append(trade)
        
        logger.info(f"Fill: {direction} {quantity} {symbol} @ {price:.2f}, PnL: {pnl:.2f}")
    
    def on_bar(self, bar_event):
        """
        Handle bar events for mark-to-market.
        
        Args:
            bar_event: Bar event to process
        """
        symbol = bar_event.get_symbol()
        price = bar_event.get_close()
        
        # Mark position to market if exists
        if symbol in self.positions:
            self.positions[symbol].mark_to_market(price)
        
        # Update equity
        self.update_equity()
        
        # Record equity point
        equity_point = {
            'timestamp': bar_event.get_timestamp(),
            'equity': self.equity
        }
        self.equity_curve.append(equity_point)
    
    def update_equity(self):
        """Update portfolio equity."""
        # Sum up all position values
        position_value = sum(pos.market_value for pos in self.positions.values())
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
        return {
            'cash': self.cash,
            'equity': self.equity,
            'positions': len(self.positions),
            'realized_pnl': sum(pos.realized_pnl for pos in self.positions.values()),
            'unrealized_pnl': sum(pos.unrealized_pnl() for pos in self.positions.values())
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
    
    def reset(self):
        """Reset portfolio to initial state."""
        self.cash = self.initial_cash
        self.positions = {}
        self.equity = self.initial_cash
        self.trades = []
        self.equity_curve = []    
