"""
Position class for tracking positions in instruments.

This module provides classes for tracking and managing positions with accurate 
cost basis and P&L calculation.
"""
import datetime
import uuid
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

class Position:
    """
    Class representing a position in a single instrument.
    
    This class tracks a single position in an instrument with accurate cost basis and P&L calculation.
    It supports both long and short positions and handles position adjustments correctly.
    
    Key features:
    - Accurate cost basis tracking for both long and short positions
    - Proper handling of position increases and decreases
    - Realized and unrealized P&L tracking
    - Position history recording
    """
    
    def __init__(self, symbol: str, quantity: float = 0, cost_basis: float = 0.0):
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
        self.id = str(uuid.uuid4())
        self.last_update = datetime.datetime.now()
        self.entry_time = self.last_update if quantity != 0 else None
        
        # Add average_price property for compatibility with portfolio manager
        self.average_price = cost_basis
        
        # Track transactions for analysis
        self.transactions = []
        
        # Initialize internal tracking
        self._total_cost = abs(quantity) * cost_basis if quantity != 0 else 0.0
        
    def add_quantity(self, quantity: float, price: float, timestamp=None) -> float:
        """
        Add to position quantity (can be positive or negative).
        
        Args:
            quantity: Quantity to add (positive for buys, negative for sells/shorts)
            price: Price per unit
            timestamp: Optional transaction timestamp
            
        Returns:
            float: Realized P&L if any
        """
        return self.update(quantity, price, timestamp)
    
    def reduce_quantity(self, quantity: float, price: float, timestamp=None) -> float:
        """
        Reduce position quantity (always positive amount).
        
        Args:
            quantity: Quantity to reduce (always positive)
            price: Price per unit
            timestamp: Optional transaction timestamp
            
        Returns:
            float: Realized P&L
        """
        # Ensure quantity is positive
        quantity = abs(quantity)
        
        # Determine direction based on current position
        direction = -1 if self.quantity > 0 else 1
        
        # Calculate quantity change
        quantity_change = quantity * direction
        
        return self.update(quantity_change, price, timestamp)

    def update(self, quantity_change: float, price: float, timestamp=None) -> float:
        """
        Update position with a new transaction.

        Args:
            quantity_change: Change in quantity (positive for buys, negative for sells)
            price: Transaction price
            timestamp: Optional transaction timestamp

        Returns:
            float: Realized P&L if any
        """
        timestamp = timestamp or datetime.datetime.now()
        self.last_update = timestamp
        
        # Set entry time if this is opening a position
        if self.quantity == 0 and quantity_change != 0:
            self.entry_time = timestamp

        # Record transaction
        transaction = {
            'timestamp': timestamp,
            'quantity': quantity_change,
            'price': price,
            'type': 'BUY' if quantity_change > 0 else 'SELL',
        }
        self.transactions.append(transaction)

        # Debug logging
        logger.debug(f"Position update for {self.symbol}: current={self.quantity}, change={quantity_change}, cost_basis={self.cost_basis}")

        # Initialize realized P&L
        realized_pnl = 0.0

        # Handle three main cases
        if self.quantity == 0:
            # Case 1: Opening new position
            self.quantity = quantity_change
            self._total_cost = abs(quantity_change) * price
            self.cost_basis = price
            self.average_price = price  # Keep average_price in sync
            logger.debug(f"Opening new position: quantity={self.quantity}, cost_basis={self.cost_basis}")

        elif self.quantity * quantity_change > 0:
            # Case 2: Adding to position (same direction)
            old_quantity = self.quantity
            self.quantity += quantity_change
            self._total_cost += abs(quantity_change) * price
            if abs(self.quantity) > 0:
                self.cost_basis = self._total_cost / abs(self.quantity)
                self.average_price = self.cost_basis  # Keep average_price in sync
            logger.debug(f"Adding to position: new quantity={self.quantity}, new cost_basis={self.cost_basis}")

        else:
            # Case 3: Reducing or flipping position

            # Step 1: Calculate the portion being closed and the P&L on that portion
            close_quantity = min(abs(quantity_change), abs(self.quantity))
            close_direction = -1 if self.quantity > 0 else 1

            # Calculate P&L on the closed portion with high precision
            if self.quantity > 0:  # Long position being reduced
                # Use full decimal precision for price differences
                price_diff = price - self.cost_basis
                # Only consider truly zero if difference is extremely small
                if abs(price_diff) < 1e-10:
                    realized_pnl = 0.0
                    logger.debug(f"Price difference too small ({price_diff}), treating as zero PnL")
                else:
                    realized_pnl = close_quantity * price_diff
            else:  # Short position being reduced
                price_diff = self.cost_basis - price
                # Only consider truly zero if difference is extremely small
                if abs(price_diff) < 1e-10:
                    realized_pnl = 0.0
                    logger.debug(f"Price difference too small ({price_diff}), treating as zero PnL")
                else:
                    realized_pnl = close_quantity * price_diff

            logger.debug(f"Closing portion: quantity={close_quantity}, pnl={realized_pnl}")

            # Step 2: Update position
            remaining_quantity = self.quantity + quantity_change

            if remaining_quantity == 0:
                # Fully closed position
                self.quantity = 0
                self._total_cost = 0
                # Reset entry time since position is closed
                self.entry_time = None
                logger.debug(f"Position fully closed, pnl={realized_pnl}")
            elif remaining_quantity * self.quantity > 0:
                # Partially closed position
                reduction_ratio = close_quantity / abs(self.quantity)
                self._total_cost *= (1 - reduction_ratio)
                self.quantity = remaining_quantity
                logger.debug(f"Position partially closed: new quantity={self.quantity}, cost={self._total_cost}")
            else:
                # Position flipped to opposite direction
                flip_quantity = abs(quantity_change) - abs(self.quantity)
                self.quantity = remaining_quantity
                self._total_cost = flip_quantity * price
                self.cost_basis = price
                self.average_price = price  # Keep average_price in sync
                # Reset entry time since this is effectively a new position
                self.entry_time = timestamp
                logger.debug(f"Position flipped: new quantity={self.quantity}, new cost_basis={self.cost_basis}")

        # Update realized P&L
        self.realized_pnl += realized_pnl

        # Update current price and market value
        self.current_price = price
        self.market_value = self.current_price * self.quantity

        logger.debug(f"Update complete: quantity={self.quantity}, cost_basis={self.cost_basis}, realized_pnl={realized_pnl}")

        return realized_pnl
    
    def mark_to_market(self, price: float, timestamp=None) -> float:
        """
        Mark position to market price.
        
        Args:
            price: Current market price
            timestamp: Optional timestamp for the mark
            
        Returns:
            float: Unrealized P&L
        """
        self.current_price = price
        self.market_value = price * self.quantity
        
        if timestamp:
            self.last_update = timestamp
            
        return self.unrealized_pnl()
    
    def unrealized_pnl(self) -> float:
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
    
    def total_pnl(self) -> float:
        """
        Calculate total P&L (realized + unrealized).
        
        Returns:
            float: Total P&L
        """
        return self.realized_pnl + self.unrealized_pnl()
    
    def get_market_value(self, price: Optional[float] = None) -> float:
        """
        Calculate current market value of position.
        
        Args:
            price: Optional price to use (uses current_price if None)
            
        Returns:
            float: Market value
        """
        price = price or self.current_price
        return self.quantity * price
    
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.quantity > 0
    
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.quantity < 0
    
    def is_flat(self) -> bool:
        """Check if position is flat (no position)."""
        return self.quantity == 0
    
    def position_age(self, current_time=None) -> datetime.timedelta:
        """
        Calculate position age.
        
        Args:
            current_time: Optional current time (uses now if None)
            
        Returns:
            datetime.timedelta: Position age
        """
        if self.entry_time is None:
            return datetime.timedelta(0)
            
        current_time = current_time or datetime.datetime.now()
        return current_time - self.entry_time
    
    def position_direction(self) -> str:
        """
        Get position direction.
        
        Returns:
            str: "LONG", "SHORT", or "FLAT"
        """
        if self.quantity > 0:
            return "LONG"
        elif self.quantity < 0:
            return "SHORT"
        else:
            return "FLAT"
    
    def __str__(self) -> str:
        return (f"Position({self.symbol}, {self.position_direction()}, "
                f"quantity={self.quantity}, cost_basis={self.cost_basis:.2f}, "
                f"realized_pnl={self.realized_pnl:.2f}, unrealized_pnl={self.unrealized_pnl():.2f})")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert position to dictionary.
        
        Returns:
            dict: Position as dictionary
        """
        return {
            'id': self.id,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'cost_basis': self.cost_basis,
            'average_price': self.average_price,
            'current_price': self.current_price,
            'market_value': self.quantity * self.current_price,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl(),
            'total_pnl': self.total_pnl(),
            'direction': self.position_direction(),
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'last_update': self.last_update.isoformat(),
            'age': str(self.position_age()) if self.entry_time else "0:00:00"
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """
        Reconstruct position from dictionary.
        
        Args:
            data: Dictionary representation of position
            
        Returns:
            Position: Reconstructed position
        """
        position = cls(data["symbol"], data["quantity"], data["cost_basis"])
        position.realized_pnl = data["realized_pnl"]
        position.current_price = data["current_price"]
        
        # Set average_price from data or default to cost_basis
        if "average_price" in data:
            position.average_price = data["average_price"]
        else:
            position.average_price = data["cost_basis"]
            
        if "id" in data:
            position.id = data["id"]
            
        if "last_update" in data:
            if isinstance(data["last_update"], str):
                position.last_update = datetime.datetime.fromisoformat(data["last_update"])
            else:
                position.last_update = data["last_update"]
                
        if "entry_time" in data and data["entry_time"]:
            if isinstance(data["entry_time"], str):
                position.entry_time = datetime.datetime.fromisoformat(data["entry_time"])
            else:
                position.entry_time = data["entry_time"]
        
        return position