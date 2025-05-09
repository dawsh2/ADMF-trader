"""
Utility functions for position calculations.

This module provides utility functions for position-related calculations
such as position sizing, P&L calculations, and position metrics.
"""
import math
import logging
from typing import Dict, Any, List, Optional, Union, Tuple

from .position import Position

logger = logging.getLogger(__name__)

def calculate_position_value(quantity: float, price: float) -> float:
    """
    Calculate position market value.
    
    Args:
        quantity: Position quantity
        price: Current price
        
    Returns:
        float: Position market value
    """
    return quantity * price

def calculate_pnl(entry_price: float, exit_price: float, quantity: float, direction: str) -> float:
    """
    Calculate P&L for a round-trip trade.
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        quantity: Position quantity (absolute)
        direction: Position direction ('LONG' or 'SHORT')
        
    Returns:
        float: P&L amount
    """
    if direction.upper() == 'LONG':
        return quantity * (exit_price - entry_price)
    elif direction.upper() == 'SHORT':
        return quantity * (entry_price - exit_price)
    else:
        logger.warning(f"Invalid direction: {direction}")
        return 0.0

def calculate_return(entry_price: float, exit_price: float, direction: str) -> float:
    """
    Calculate return percentage for a round-trip trade.
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        direction: Position direction ('LONG' or 'SHORT')
        
    Returns:
        float: Return percentage (as decimal)
    """
    if entry_price == 0:
        logger.warning("Entry price is zero, cannot calculate return")
        return 0.0
        
    if direction.upper() == 'LONG':
        return (exit_price - entry_price) / entry_price
    elif direction.upper() == 'SHORT':
        return (entry_price - exit_price) / entry_price
    else:
        logger.warning(f"Invalid direction: {direction}")
        return 0.0

def calculate_position_size(equity: float, risk_per_trade: float, price: float, 
                          stop_loss: Optional[float] = None) -> float:
    """
    Calculate position size based on risk per trade.
    
    Args:
        equity: Current equity
        risk_per_trade: Risk per trade as percentage of equity (decimal)
        price: Current price
        stop_loss: Optional stop loss price
        
    Returns:
        float: Position size
    """
    # If stop loss is not provided, default to 2% of price
    if stop_loss is None:
        stop_loss = price * 0.98 if price > 0 else 0
        
    # Calculate risk amount
    risk_amount = equity * risk_per_trade
    
    # Calculate risk per unit
    risk_per_unit = abs(price - stop_loss)
    
    # Calculate position size
    if risk_per_unit > 0:
        size = risk_amount / risk_per_unit
    else:
        logger.warning("Risk per unit is zero, using default size")
        size = 0
        
    return size

def calculate_kelly_size(equity: float, win_rate: float, avg_win_pct: float, 
                        avg_loss_pct: float) -> float:
    """
    Calculate position size using Kelly Criterion.
    
    Args:
        equity: Current equity
        win_rate: Win rate as decimal (0.0 - 1.0)
        avg_win_pct: Average win as decimal percentage
        avg_loss_pct: Average loss as decimal percentage (positive value)
        
    Returns:
        float: Kelly position size as fraction of equity
    """
    if avg_loss_pct == 0:
        logger.warning("Average loss is zero, cannot calculate Kelly size")
        return 0.0
        
    # Kelly formula: f* = (p * b - q) / b
    # where f* is fraction of bankroll, p is win probability,
    # q is loss probability (1-p), and b is win/loss ratio
    
    win_loss_ratio = avg_win_pct / avg_loss_pct
    loss_rate = 1.0 - win_rate
    
    kelly = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio
    
    # Clamp result to [0, 1] range
    kelly = max(0.0, min(1.0, kelly))
    
    return kelly * equity

def calculate_atr_position_size(equity: float, risk_per_trade: float, atr: float, 
                              atr_multiplier: float, price: float) -> float:
    """
    Calculate position size based on Average True Range (ATR).
    
    Args:
        equity: Current equity
        risk_per_trade: Risk per trade as percentage of equity (decimal)
        atr: Average True Range value
        atr_multiplier: Multiplier for ATR to determine stop distance
        price: Current price
        
    Returns:
        float: Position size
    """
    # Calculate risk amount
    risk_amount = equity * risk_per_trade
    
    # Calculate stop distance based on ATR
    stop_distance = atr * atr_multiplier
    
    # Calculate position size
    if stop_distance > 0:
        size = risk_amount / stop_distance
    else:
        logger.warning("Stop distance is zero, using default size")
        size = 0
        
    return size

def calculate_max_position_size(equity: float, max_position_pct: float, price: float) -> float:
    """
    Calculate maximum position size based on percentage of equity.
    
    Args:
        equity: Current equity
        max_position_pct: Maximum position size as percentage of equity (decimal)
        price: Current price
        
    Returns:
        float: Maximum position size
    """
    max_position_value = equity * max_position_pct
    
    if price > 0:
        return max_position_value / price
    else:
        logger.warning("Price is zero, cannot calculate position size")
        return 0.0

def round_position_size(size: float, min_size: float = 0.0, 
                       size_increment: float = 1.0) -> float:
    """
    Round position size to valid increment.
    
    Args:
        size: Raw position size
        min_size: Minimum position size
        size_increment: Position size increment
        
    Returns:
        float: Rounded position size
    """
    # Check minimum size
    if abs(size) < min_size:
        return 0.0
        
    # Round to increment
    rounded_size = math.floor(size / size_increment) * size_increment
    
    # Preserve direction
    if size < 0:
        rounded_size = -rounded_size
        
    return rounded_size

def adjust_position_size_for_notional_limits(size: float, price: float, 
                                           min_notional: float = 0.0, 
                                           max_notional: float = float('inf')) -> float:
    """
    Adjust position size to comply with notional value limits.
    
    Args:
        size: Position size
        price: Current price
        min_notional: Minimum notional value
        max_notional: Maximum notional value
        
    Returns:
        float: Adjusted position size
    """
    notional = abs(size) * price
    
    # Check minimum notional
    if notional < min_notional:
        logger.debug(f"Adjusting position size for minimum notional: {notional} < {min_notional}")
        if price > 0:
            adjusted_size = min_notional / price
        else:
            logger.warning("Price is zero, cannot adjust for minimum notional")
            adjusted_size = size
    # Check maximum notional
    elif notional > max_notional:
        logger.debug(f"Adjusting position size for maximum notional: {notional} > {max_notional}")
        if price > 0:
            adjusted_size = max_notional / price
        else:
            logger.warning("Price is zero, cannot adjust for maximum notional")
            adjusted_size = size
    else:
        adjusted_size = size
        
    # Preserve direction
    if size < 0:
        adjusted_size = -abs(adjusted_size)
    else:
        adjusted_size = abs(adjusted_size)
        
    return adjusted_size