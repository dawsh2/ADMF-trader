"""
Position tracker for managing multiple positions.

This module provides classes for tracking and managing multiple positions across
different instruments.
"""
import datetime
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from collections import defaultdict

from .position import Position

logger = logging.getLogger(__name__)

class PositionTracker:
    """
    Class for tracking multiple positions across different instruments.
    
    Key features:
    - Track positions across multiple instruments
    - Update positions based on fills
    - Calculate aggregate position metrics
    - Support position queries and filtering
    - Track historical positions
    """
    
    def __init__(self, event_bus=None):
        """
        Initialize position tracker.
        
        Args:
            event_bus: Optional event bus for emitting position events
        """
        self.positions = {}  # symbol -> Position
        self.event_bus = event_bus
        self.position_history = {}  # symbol -> List[Dict]
        self.closed_positions = []  # List of closed positions
        
    def update_position(self, symbol: str, quantity_change: float, price: float, 
                       timestamp=None) -> Tuple[Position, float]:
        """
        Update a position with a transaction.
        
        Args:
            symbol: Instrument symbol
            quantity_change: Change in quantity (positive for buys, negative for sells)
            price: Transaction price
            timestamp: Optional transaction timestamp
            
        Returns:
            Tuple of (Position, realized_pnl)
        """
        timestamp = timestamp or datetime.datetime.now()
        
        # Get or create position
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
            logger.debug(f"Created new position for {symbol}")
        
        position = self.positions[symbol]
        
        # Update position
        realized_pnl = position.update(quantity_change, price, timestamp)
        
        # Record snapshot in position history
        if symbol not in self.position_history:
            self.position_history[symbol] = []
        
        self.position_history[symbol].append(position.to_dict())
        
        # If position was closed, move to closed positions list
        if position.quantity == 0 and realized_pnl != 0:
            self.closed_positions.append({
                'symbol': symbol,
                'exit_time': timestamp,
                'realized_pnl': realized_pnl,
                'direction': 'LONG' if quantity_change < 0 else 'SHORT',
                'exit_price': price,
                **position.to_dict()
            })
            logger.info(f"Closed position for {symbol} with P&L {realized_pnl:.2f}")
        
        return position, realized_pnl
    
    def mark_to_market(self, market_prices: Dict[str, float], timestamp=None) -> Dict[str, float]:
        """
        Mark all positions to market.
        
        Args:
            market_prices: Dictionary mapping symbols to prices
            timestamp: Optional timestamp for the mark
            
        Returns:
            Dict mapping symbols to unrealized P&L
        """
        timestamp = timestamp or datetime.datetime.now()
        unrealized_pnls = {}
        
        for symbol, position in self.positions.items():
            if symbol in market_prices:
                unrealized_pnl = position.mark_to_market(market_prices[symbol], timestamp)
                unrealized_pnls[symbol] = unrealized_pnl
        
        return unrealized_pnls
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for a specific symbol.
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Position if exists, None otherwise
        """
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """
        Get all active positions.
        
        Returns:
            Dict mapping symbols to Positions
        """
        return {symbol: position for symbol, position in self.positions.items() 
                if position.quantity != 0}
    
    def get_position_value(self, symbol: str, price: Optional[float] = None) -> float:
        """
        Get market value of a position.
        
        Args:
            symbol: Instrument symbol
            price: Optional price to use (uses current_price if None)
            
        Returns:
            float: Position market value
        """
        position = self.get_position(symbol)
        if position:
            return position.get_market_value(price)
        return 0.0
    
    def get_total_position_value(self) -> float:
        """
        Get total market value of all positions.
        
        Returns:
            float: Total position value
        """
        return sum(pos.get_market_value() for pos in self.positions.values())
    
    def get_total_exposure(self) -> float:
        """
        Get total market exposure (absolute sum).
        
        Returns:
            float: Total exposure
        """
        return sum(abs(pos.get_market_value()) for pos in self.positions.values())
    
    def get_net_exposure(self) -> float:
        """
        Get net market exposure (long - short).
        
        Returns:
            float: Net exposure
        """
        return sum(pos.get_market_value() for pos in self.positions.values())
    
    def get_exposure_by_direction(self) -> Dict[str, float]:
        """
        Get exposure broken down by direction.
        
        Returns:
            Dict with 'LONG' and 'SHORT' exposure
        """
        exposures = {'LONG': 0.0, 'SHORT': 0.0}
        
        for position in self.positions.values():
            market_value = position.get_market_value()
            if market_value > 0:
                exposures['LONG'] += market_value
            elif market_value < 0:
                exposures['SHORT'] += abs(market_value)
        
        return exposures
    
    def get_position_history(self, symbol: str) -> List[Dict]:
        """
        Get history for a specific position.
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            List of position snapshots
        """
        return self.position_history.get(symbol, [])
    
    def get_all_closed_positions(self) -> List[Dict]:
        """
        Get all closed positions.
        
        Returns:
            List of closed position records
        """
        return self.closed_positions
    
    def get_winning_positions(self) -> List[Dict]:
        """
        Get all winning closed positions.
        
        Returns:
            List of winning position records
        """
        return [pos for pos in self.closed_positions if pos['realized_pnl'] > 0]
    
    def get_losing_positions(self) -> List[Dict]:
        """
        Get all losing closed positions.
        
        Returns:
            List of losing position records
        """
        return [pos for pos in self.closed_positions if pos['realized_pnl'] < 0]
    
    def get_position_metrics(self) -> Dict[str, Any]:
        """
        Get position metrics.
        
        Returns:
            Dict with various position metrics
        """
        # Count positions by direction
        long_count = sum(1 for pos in self.positions.values() if pos.is_long())
        short_count = sum(1 for pos in self.positions.values() if pos.is_short())
        
        # Calculate P&L metrics
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl() for pos in self.positions.values())
        
        # Calculate exposure metrics
        exposures = self.get_exposure_by_direction()
        
        # Calculate win/loss metrics
        winning_positions = self.get_winning_positions()
        losing_positions = self.get_losing_positions()
        
        win_count = len(winning_positions)
        loss_count = len(losing_positions)
        win_rate = win_count / (win_count + loss_count) if (win_count + loss_count) > 0 else 0.0
        
        # Calculate average metrics
        avg_win = sum(pos['realized_pnl'] for pos in winning_positions) / win_count if win_count > 0 else 0.0
        avg_loss = sum(pos['realized_pnl'] for pos in losing_positions) / loss_count if loss_count > 0 else 0.0
        
        return {
            'total_positions': len(self.get_all_positions()),
            'long_positions': long_count,
            'short_positions': short_count,
            'total_realized_pnl': total_realized_pnl,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_pnl': total_realized_pnl + total_unrealized_pnl,
            'long_exposure': exposures['LONG'],
            'short_exposure': exposures['SHORT'],
            'net_exposure': exposures['LONG'] - exposures['SHORT'],
            'gross_exposure': exposures['LONG'] + exposures['SHORT'],
            'closed_positions': len(self.closed_positions),
            'winning_positions': win_count,
            'losing_positions': loss_count,
            'win_rate': win_rate,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'profit_factor': abs(sum(pos['realized_pnl'] for pos in winning_positions)) / 
                           abs(sum(pos['realized_pnl'] for pos in losing_positions)) 
                           if sum(pos['realized_pnl'] for pos in losing_positions) != 0 else float('inf')
        }
    
    def reset(self) -> None:
        """Reset all position tracking."""
        self.positions = {}
        self.position_history = {}
        self.closed_positions = []
        logger.info("Position tracker reset")