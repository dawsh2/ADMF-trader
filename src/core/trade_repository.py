"""
Centralized trade repository for consistent trade tracking.

This repository provides a single source of truth for all trades
in the system, replacing the fragmented trade tracking approach
that was causing reliability issues.
"""

class TradeRepository:
    """
    Central storage for all trades in the system.
    
    This class ensures trades are only stored once and provides
    a consistent interface for adding and retrieving trades.
    """
    
    def __init__(self):
        """Initialize the trade repository."""
        self.trades = []
        self.trade_ids = set()  # For fast deduplication
        self.open_trades = {}   # Map of symbol -> list of open trades
        self.closed_trades = {} # Map of symbol -> list of closed trades
        
        # Add tracking for total PnL
        self.total_realized_pnl = 0.0
        self.total_unrealized_pnl = 0.0
        
        # Create logger
        import logging
        self.logger = logging.getLogger(__name__)
        
    def add_trade(self, trade):
        """
        Add a trade to the repository if it doesn't already exist.
        
        Args:
            trade (dict): Trade information
            
        Returns:
            bool: True if the trade was added, False if it was a duplicate
        """
        # Ensure trade has an ID
        trade_id = trade.get('id')
        if not trade_id:
            raise ValueError("Trade must have an 'id' field")
        
        # Check for duplicates
        if trade_id in self.trade_ids:
            return False
        
        # Add to main trade list and ID set
        self.trades.append(trade)
        self.trade_ids.add(trade_id)
        
        # Categorize by open/closed status
        symbol = trade.get('symbol')
        if not symbol:
            raise ValueError("Trade must have a 'symbol' field")
            
        if trade.get('closed', False):
            if symbol not in self.closed_trades:
                self.closed_trades[symbol] = []
            self.closed_trades[symbol].append(trade)
        else:
            if symbol not in self.open_trades:
                self.open_trades[symbol] = []
            self.open_trades[symbol].append(trade)
            
        return True
    
    def update_trade(self, trade_id, updates):
        """
        Update an existing trade.
        
        Args:
            trade_id (str): ID of the trade to update
            updates (dict): Fields to update
            
        Returns:
            bool: True if the trade was updated, False if not found
        """
        # Find the trade
        for i, trade in enumerate(self.trades):
            if trade.get('id') == trade_id:
                # Update the trade
                self.trades[i].update(updates)
                
                # Handle status change (open -> closed)
                if updates.get('closed', False) and not trade.get('closed', False):
                    symbol = trade.get('symbol')
                    # Remove from open trades
                    if symbol in self.open_trades:
                        self.open_trades[symbol] = [
                            t for t in self.open_trades[symbol] 
                            if t.get('id') != trade_id
                        ]
                    # Add to closed trades
                    if symbol not in self.closed_trades:
                        self.closed_trades[symbol] = []
                    self.closed_trades[symbol].append(self.trades[i])
                
                return True
        
        return False
    
    def close_trade(self, trade_id, close_price, close_time, quantity=None):
        """
        Close an open trade.
        
        Args:
            trade_id (str): ID of the trade to close
            close_price (float): Price at which the trade is closed
            close_time (datetime): Time when the trade was closed
            quantity (float, optional): Quantity closed, defaults to full position
            
        Returns:
            dict: Updated trade or None if not found
        """
        for trade in self.trades:
            if trade.get('id') == trade_id and not trade.get('closed', False):
                # Determine quantity to close
                position_size = trade.get('quantity', 0)
                close_quantity = quantity if quantity is not None else position_size
                
                # Validate quantity
                if close_quantity > position_size:
                    raise ValueError(f"Close quantity {close_quantity} exceeds position size {position_size}")
                
                # Calculate PnL using consistent methodology
                entry_price = trade.get('entry_price', 0)
                direction = trade.get('direction', '')
                entry_value = entry_price * close_quantity
                exit_value = close_price * close_quantity
                
                # Use consistent calculation method - same as in portfolio & metrics
                if direction.lower() == 'long':
                    pnl = exit_value - entry_value  # For long positions: exit_value - entry_value
                elif direction.lower() == 'short':
                    pnl = entry_value - exit_value  # For short positions: entry_value - exit_value
                
                # Update trade
                updates = {
                    'closed': True,
                    'close_price': close_price,
                    'close_time': close_time,
                    'pnl': pnl,
                    'closed_quantity': close_quantity
                }
                
                # If partial close, don't mark the trade as fully closed
                if close_quantity < position_size:
                    updates['closed'] = False
                    updates['quantity'] = position_size - close_quantity
                
                # Apply updates
                self.update_trade(trade_id, updates)
                
                # Return the updated trade
                for updated_trade in self.trades:
                    if updated_trade.get('id') == trade_id:
                        return updated_trade
                
        return None
    
    def get_trades(self):
        """
        Get all trades.
        
        Returns:
            list: Copy of all trades
        """
        return self.trades.copy()
    
    def get_open_trades(self, symbol=None):
        """
        Get open trades, optionally filtered by symbol.
        
        Args:
            symbol (str, optional): Symbol to filter by
            
        Returns:
            list: Copy of open trades
        """
        if symbol:
            return self.open_trades.get(symbol, []).copy()
        
        # Return all open trades across all symbols
        all_open = []
        for trades in self.open_trades.values():
            all_open.extend(trades)
        return all_open
    
    def get_closed_trades(self, symbol=None):
        """
        Get closed trades, optionally filtered by symbol.
        
        Args:
            symbol (str, optional): Symbol to filter by
            
        Returns:
            list: Copy of closed trades
        """
        if symbol:
            return self.closed_trades.get(symbol, []).copy()
        
        # Return all closed trades across all symbols
        all_closed = []
        for trades in self.closed_trades.values():
            all_closed.extend(trades)
        return all_closed
    
    def reset(self):
        """Reset the repository to its initial state."""
        self.trades = []
        self.trade_ids.clear()
        self.open_trades.clear()
        self.closed_trades.clear()
