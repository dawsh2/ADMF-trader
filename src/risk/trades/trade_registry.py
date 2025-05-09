"""
Centralized trade registry for managing trades across the system.
"""
import logging
import uuid
import datetime
from typing import Dict, List, Optional, Any, Set, Set

logger = logging.getLogger(__name__)

class TradeRegistry:
    """
    Centralized trade registry for tracking all trades across the system.
    
    This component provides a single source of truth for trade information,
    eliminating issues with multiple trade collections and reference problems.
    """
    
    def __init__(self, event_bus=None, name=None):
        """
        Initialize trade registry.
        
        Args:
            event_bus: Optional event bus for emitting trade events
            name: Optional name for this registry instance
        """
        self._name = name or f"trade_registry_{uuid.uuid4().hex[:8]}"
        self.event_bus = event_bus
        self.trades = []  # Central trade collection
        self.trade_ids = set()  # For fast deduplication
        self.transaction_ids = set()  # For transaction tracking
        
        # Statistics tracking
        self.stats = {
            'trades_added': 0,
            'trades_updated': 0,
            'duplicates_rejected': 0,
            'total_pnl': 0.0,
            'win_count': 0,
            'loss_count': 0,
            'break_even_count': 0
        }
        
        logger.info(f"Trade registry {self._name} initialized")
    
    def add_trade(self, trade_data, update_if_exists=True, allow_zero_pnl=True) -> bool:
        """
        Add a trade to the registry with strict validation and deduplication.
        
        Args:
            trade_data: Dictionary with trade information
            update_if_exists: Whether to update existing trade if ID exists
            allow_zero_pnl: Whether to allow trades with zero PnL
            
        Returns:
            bool: True if trade was added/updated, False otherwise
        """
        try:
            # Validate trade data
            if not isinstance(trade_data, dict):
                logger.warning(f"Invalid trade data type: {type(trade_data)}")
                return False
            
            # Ensure trade has an ID
            trade_id = trade_data.get('id')
            if not trade_id:
                trade_id = str(uuid.uuid4())
                trade_data['id'] = trade_id
                logger.debug(f"Added missing ID to trade: {trade_id}")
            
            # Check for duplicate trade ID
            if trade_id in self.trade_ids:
                # Skip if update not allowed
                if not update_if_exists:
                    self.stats['duplicates_rejected'] += 1
                    logger.debug(f"Skipping duplicate trade ID: {trade_id}")
                    return False
                
                # Update existing trade
                for i, existing_trade in enumerate(self.trades):
                    if existing_trade.get('id') == trade_id:
                        # Make a copy of the existing trade and update with new data
                        updated_trade = existing_trade.copy()
                        updated_trade.update(trade_data)
                        
                        # Check if status changed from OPEN to CLOSED
                        status_changed = (
                            existing_trade.get('status') == 'OPEN' and 
                            updated_trade.get('status') == 'CLOSED'
                        )
                        
                        # Update the trade in the list
                        self.trades[i] = updated_trade
                        
                        # Update stats if status changed
                        if status_changed:
                            # Update PnL stats
                            pnl = updated_trade.get('pnl', 0.0)
                            self._update_pnl_stats(pnl)
                        
                        self.stats['trades_updated'] += 1
                        logger.debug(f"Updated existing trade: {trade_id}")
                        return True
            
            # Check for transaction ID if present for additional deduplication
            transaction_id = trade_data.get('transaction_id')
            if transaction_id and transaction_id in self.transaction_ids:
                self.stats['duplicates_rejected'] += 1
                logger.debug(f"Skipping duplicate transaction ID: {transaction_id}")
                return False
                
            # Ensure required fields exist
            required_fields = ['symbol', 'direction', 'quantity', 'price']
            for field in required_fields:
                if field not in trade_data:
                    logger.warning(f"Trade {trade_id} missing required field: {field}")
                    # Add default values for required fields
                    if field == 'symbol':
                        trade_data[field] = 'UNKNOWN'
                    elif field == 'direction':
                        trade_data[field] = 'BUY'
                    elif field == 'quantity':
                        trade_data[field] = 1.0
                    elif field == 'price':
                        trade_data[field] = 0.0
            
            # Ensure timestamp exists
            if 'timestamp' not in trade_data:
                trade_data['timestamp'] = datetime.datetime.now()
                
            # Ensure PnL exists
            if 'pnl' not in trade_data:
                # Try to use realized_pnl if available
                if 'realized_pnl' in trade_data:
                    trade_data['pnl'] = trade_data['realized_pnl']
                else:
                    trade_data['pnl'] = 0.0
                    
            # Skip zero PnL trades if not allowed
            if not allow_zero_pnl and trade_data.get('pnl', 0.0) == 0.0:
                logger.debug(f"Skipping zero PnL trade: {trade_id}")
                return False
                    
            # Ensure quantity and price are floats
            try:
                trade_data['quantity'] = float(trade_data['quantity'])
                trade_data['price'] = float(trade_data['price'])
                trade_data['pnl'] = float(trade_data['pnl'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid numeric values in trade: {trade_id}")
                # Attempt to fix invalid values
                if not isinstance(trade_data.get('quantity'), (int, float)):
                    trade_data['quantity'] = 1.0
                if not isinstance(trade_data.get('price'), (int, float)):
                    trade_data['price'] = 0.0
                if not isinstance(trade_data.get('pnl'), (int, float)):
                    trade_data['pnl'] = 0.0
                    
            # Ensure status exists
            if 'status' not in trade_data:
                # Default to CLOSED unless PnL is exactly 0
                if trade_data.get('pnl', 0.0) == 0.0:
                    trade_data['status'] = 'OPEN'
                else:
                    trade_data['status'] = 'CLOSED'
            
            # Update stats based on PnL
            pnl = trade_data.get('pnl', 0.0)
            self._update_pnl_stats(pnl)
                    
            # Add to registry
            self.trades.append(trade_data)
            self.trade_ids.add(trade_id)
            
            # Track transaction ID if available
            if transaction_id:
                self.transaction_ids.add(transaction_id)
                
            # Update stats
            self.stats['trades_added'] += 1
            logger.debug(f"Added new trade: {trade_id} (symbol: {trade_data.get('symbol')}, pnl: {pnl:.2f})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding trade to registry: {e}", exc_info=True)
            return False
    
    def _update_pnl_stats(self, pnl: float) -> None:
        """
        Update PnL statistics based on a new trade.
        
        Args:
            pnl: PnL value to update stats with
        """
        self.stats['total_pnl'] += pnl
        
        if pnl > 0:
            self.stats['win_count'] += 1
        elif pnl < 0:
            self.stats['loss_count'] += 1
        else:
            self.stats['break_even_count'] += 1
    
    def get_trade(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a trade by ID.
        
        Args:
            trade_id: ID of the trade to get
            
        Returns:
            Dict or None: Trade data if found, None otherwise
        """
        for trade in self.trades:
            if trade.get('id') == trade_id:
                return trade.copy()  # Return a copy to prevent modification
        return None
    
    def get_trades(self, filter_open=True, n=None, symbol=None, direction=None) -> List[Dict[str, Any]]:
        """
        Get trades with optional filtering.
        
        Args:
            filter_open: Whether to filter out OPEN trades
            n: Maximum number of trades to return (most recent first)
            symbol: Optional symbol to filter by
            direction: Optional direction to filter by ('BUY' or 'SELL')
            
        Returns:
            List: Filtered trades
        """
        # Apply filters
        filtered_trades = []
        for trade in self.trades:
            # Skip OPEN trades if filtering
            if filter_open and trade.get('status') == 'OPEN':
                continue
                
            # Apply symbol filter if provided
            if symbol is not None and trade.get('symbol') != symbol:
                continue
                
            # Apply direction filter if provided
            if direction is not None and trade.get('direction') != direction:
                continue
                
            # Include trade
            filtered_trades.append(trade.copy())  # Copy to prevent modification
        
        # Sort by timestamp (newest first)
        filtered_trades.sort(key=lambda t: t.get('timestamp', datetime.datetime.min), reverse=True)
        
        # Limit number of trades if specified
        if n is not None and n > 0:
            return filtered_trades[:n]
            
        return filtered_trades
    
    def get_trade_count(self, include_open=False) -> int:
        """
        Get the total number of trades.
        
        Args:
            include_open: Whether to include OPEN trades in the count
            
        Returns:
            int: Number of trades
        """
        if include_open:
            return len(self.trades)
            
        # Count closed trades only
        return sum(1 for t in self.trades if t.get('status') != 'OPEN')
    
    def get_pnl_sum(self) -> float:
        """
        Get the sum of PnL for all trades.
        
        Returns:
            float: Sum of PnL
        """
        return sum(t.get('pnl', 0.0) for t in self.trades)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dict: Registry statistics
        """
        # Update current stats
        self.stats['trade_count'] = len(self.trades)
        self.stats['closed_trade_count'] = sum(1 for t in self.trades if t.get('status') != 'OPEN')
        self.stats['open_trade_count'] = sum(1 for t in self.trades if t.get('status') == 'OPEN')
        
        # Calculate win rate
        closed_count = self.stats['win_count'] + self.stats['loss_count'] + self.stats['break_even_count']
        win_rate = self.stats['win_count'] / closed_count if closed_count > 0 else 0.0
        self.stats['win_rate'] = win_rate
        
        return dict(self.stats)  # Return a copy to prevent modification
    
    def clear_trades(self) -> None:
        """Clear all trades from the registry."""
        pre_count = len(self.trades)
        self.trades.clear()
        self.trade_ids.clear()
        self.transaction_ids.clear()
        
        # Reset PnL stats
        self.stats['total_pnl'] = 0.0
        self.stats['win_count'] = 0
        self.stats['loss_count'] = 0
        self.stats['break_even_count'] = 0
        
        logger.info(f"Cleared {pre_count} trades from registry")
    
    def reset(self) -> None:
        """Reset the registry to initial state."""
        # Clear trades
        self.clear_trades()
        
        # Reset all stats
        self.stats = {
            'trades_added': 0,
            'trades_updated': 0,
            'duplicates_rejected': 0,
            'total_pnl': 0.0,
            'win_count': 0,
            'loss_count': 0,
            'break_even_count': 0
        }
        
        logger.info(f"Reset trade registry {self._name}")

    def set_event_bus(self, event_bus) -> None:
        """
        Set the event bus.
        
        Args:
            event_bus: Event bus to use
        """
        self.event_bus = event_bus
        logger.debug(f"Set event bus for trade registry {self._name}")
