"""
Position class for tracking positions in instruments.
"""
import datetime
import uuid
import logging
from typing import Dict, Any, List, Optional, Union

from src.core.events.utils import ObjectRegistry

logger = logging.getLogger(__name__)

@ObjectRegistry.register
class Position:
    """Class representing a position in a single instrument."""
    
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
        
        # Track transactions for analysis
        self.transactions = []
        
        # Initialize internal tracking
        self._total_cost = abs(quantity) * cost_basis if quantity != 0 else 0.0

    # Fix for Position.update method in src/risk/portfolio/position.py

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

        # Debug log for position update
        logger.debug(f"Updating position {self.symbol}: current={self.quantity}, change={quantity_change}, price={price}")

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
        if self.quantity == 0:
            # Opening new position
            self.quantity = quantity_change
            self._total_cost = abs(quantity_change) * price
            self.cost_basis = price
            logger.debug(f"Opening new position: quantity={self.quantity}, cost_basis={self.cost_basis}")

        elif self.quantity * quantity_change > 0:
            # Adding to existing position (same direction)
            new_quantity = self.quantity + quantity_change
            new_cost = self._total_cost + (abs(quantity_change) * price)

            # Update position
            self.quantity = new_quantity
            self._total_cost = new_cost

            # Update cost basis
            if abs(new_quantity) > 0:  # Avoid division by zero
                self.cost_basis = new_cost / abs(new_quantity)
            logger.debug(f"Adding to position: quantity={self.quantity}, cost_basis={self.cost_basis}")

        else:
            # Reducing or flipping position (opposite direction)
            if abs(quantity_change) < abs(self.quantity):
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
                if abs(self.quantity) > 0:  # Avoid setting _total_cost negative
                    self._total_cost -= reduced_cost
                # Cost basis remains the same
                logger.debug(f"Partial reduction: quantity={self.quantity}, pnl={realized_pnl}")

            elif abs(quantity_change) == abs(self.quantity):
                # Full position closure
                if self.quantity > 0:  # Long position
                    realized_pnl = self.quantity * (price - self.cost_basis)
                else:  # Short position
                    realized_pnl = abs(self.quantity) * (self.cost_basis - price)

                # Close position
                self.quantity = 0
                self._total_cost = 0
                # Cost basis remains for historical reference
                logger.debug(f"Full position closure: pnl={realized_pnl}")

            else:
                # Position flip
                # First close existing position
                if self.quantity > 0:  # Long position
                    realized_pnl = self.quantity * (price - self.cost_basis)
                else:  # Short position
                    realized_pnl = abs(self.quantity) * (self.cost_basis - price)

                # Then open new position in opposite direction
                remaining_quantity = quantity_change + self.quantity  # Will be opposite sign of original
                self.quantity = remaining_quantity
                self._total_cost = abs(remaining_quantity) * price
                self.cost_basis = price
                logger.debug(f"Position flip: quantity={self.quantity}, cost_basis={self.cost_basis}, pnl={realized_pnl}")

        # Cap realized P&L to avoid extreme values
        if abs(realized_pnl) > 10000:
            logger.warning(f"Capping extreme PnL value: {realized_pnl} -> {10000 if realized_pnl > 0 else -10000}")
            realized_pnl = 10000 if realized_pnl > 0 else -10000

        # Update realized P&L
        self.realized_pnl += realized_pnl

        # Update current price and market value
        self.current_price = price
        self.market_value = self.current_price * self.quantity

        return realized_pnl        
    

    
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
    
    def market_value(self, price: Optional[float] = None) -> float:
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
        current_time = current_time or datetime.datetime.now()
        
        if not self.transactions:
            return datetime.timedelta(0)
            
        oldest_transaction = min(self.transactions, key=lambda t: t['timestamp'])
        return current_time - oldest_transaction['timestamp']
    
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
            'current_price': self.current_price,
            'market_value': self.quantity * self.current_price,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl(),
            'total_pnl': self.total_pnl(),
            'direction': self.position_direction(),
            'last_update': self.last_update.isoformat()
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
        
        if "id" in data:
            position.id = data["id"]
            
        if "last_update" in data:
            if isinstance(data["last_update"], str):
                position.last_update = datetime.datetime.fromisoformat(data["last_update"])
            else:
                position.last_update = data["last_update"]
        
        return position
