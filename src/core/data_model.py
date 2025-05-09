"""
Standardized data model for consistent field naming across the system.

This module defines standard data structures with consistent field naming
to address issues with inconsistent field names (like 'size' vs 'quantity').
"""

from enum import Enum
from datetime import datetime

class OrderType(Enum):
    """Standard order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderStatus(Enum):
    """Standard order statuses."""
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"

class Direction(Enum):
    """Standard trade directions."""
    LONG = "LONG"
    SHORT = "SHORT"

class DataModel:
    """
    Base class for all data models with field validation.
    
    This provides consistent behavior for validation and conversion
    of data structure instances.
    """
    
    @classmethod
    def validate(cls, data):
        """
        Validate that the data has all required fields.
        
        Args:
            data (dict): Data to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        for field in cls.REQUIRED_FIELDS:
            if field not in data:
                return False
        return True
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a new instance from a dictionary.
        
        Args:
            data (dict): Data to convert
            
        Returns:
            dict: Standardized dictionary with all required fields
        """
        if not cls.validate(data):
            missing = [f for f in cls.REQUIRED_FIELDS if f not in data]
            raise ValueError(f"Missing required fields: {missing}")
        
        # Start with required fields
        result = {field: data[field] for field in cls.REQUIRED_FIELDS}
        
        # Add optional fields if present
        for field in cls.OPTIONAL_FIELDS:
            if field in data:
                result[field] = data[field]
        
        # Convert legacy field names if present
        for legacy, standard in cls.LEGACY_MAPPINGS.items():
            if legacy in data and standard not in data:
                result[standard] = data[legacy]
        
        return result

class Order(DataModel):
    """Standard order model."""
    
    REQUIRED_FIELDS = [
        "id",
        "symbol",
        "direction",  # LONG or SHORT
        "quantity",   # Standard field name
        "order_type", # MARKET, LIMIT, etc.
        "status",     # CREATED, SUBMITTED, etc.
        "timestamp",  # When the order was created
    ]
    
    OPTIONAL_FIELDS = [
        "price",      # For LIMIT and STOP_LIMIT orders
        "stop_price", # For STOP and STOP_LIMIT orders
        "filled_quantity",
        "average_fill_price",
        "commission",
        "parent_id",  # For child orders (e.g., in bracket orders)
    ]
    
    # Legacy field mappings
    LEGACY_MAPPINGS = {
        "size": "quantity",
        "filled_size": "filled_quantity",
        "avg_fill_price": "average_fill_price",
    }

class Fill(DataModel):
    """Standard fill model."""
    
    REQUIRED_FIELDS = [
        "id",
        "order_id",
        "symbol",
        "direction",
        "quantity",    # Standard field name
        "price",
        "timestamp",
    ]
    
    OPTIONAL_FIELDS = [
        "commission",
        "exchange",
    ]
    
    # Legacy field mappings
    LEGACY_MAPPINGS = {
        "size": "quantity",
        "fill_price": "price",
    }

class Trade(DataModel):
    """Standard trade model."""
    
    REQUIRED_FIELDS = [
        "id",
        "symbol",
        "direction",
        "quantity",      # Standard field name
        "entry_price",
        "entry_time",
    ]
    
    OPTIONAL_FIELDS = [
        "exit_price",
        "exit_time",
        "pnl",
        "closed",
        "exit_reason",
        "related_order_ids",
    ]
    
    # Legacy field mappings
    LEGACY_MAPPINGS = {
        "size": "quantity",
        "open_price": "entry_price",
        "close_price": "exit_price",
        "open_time": "entry_time",
        "close_time": "exit_time",
    }

class Bar(DataModel):
    """Standard price bar model."""
    
    REQUIRED_FIELDS = [
        "symbol",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
    ]
    
    OPTIONAL_FIELDS = [
        "volume",
        "adj_close",
        "period",  # e.g., '1d', '1h', '5m'
    ]
    
    # Legacy field mappings
    LEGACY_MAPPINGS = {
        "date": "timestamp",
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "O": "open",
        "H": "high",
        "L": "low",
        "C": "close",
        "V": "volume",
    }
