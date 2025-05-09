"""
Standardized PnL calculation module to ensure consistency across the system.

This module centralizes all PnL calculations to avoid inconsistencies
between different components calculating PnL in different ways.
"""

import logging

logger = logging.getLogger(__name__)

class PnLCalculator:
    """Standardized PnL calculation across the system"""
    
    @staticmethod
    def calculate_trade_pnl(trade):
        """
        Calculate PnL for a single trade.
        
        Args:
            trade (dict): Trade data
            
        Returns:
            float: Calculated PnL
        """
        direction = trade.get('direction')
        entry_price = trade.get('entry_price', 0)
        exit_price = trade.get('close_price', 0)
        quantity = trade.get('quantity', 0)
        
        # Skip trades that aren't closed
        if not trade.get('closed', False) or exit_price is None:
            logger.debug(f"Skipping PnL calculation for open trade {trade.get('id', 'unknown')}")
            return 0.0
            
        if direction == 'LONG':
            pnl = (exit_price - entry_price) * quantity
        else:  # SHORT
            pnl = (entry_price - exit_price) * quantity
            
        # Subtract fees if available
        fees = trade.get('fees', 0)
        pnl -= fees
        
        logger.debug(f"Calculated PnL for trade {trade.get('id', 'unknown')}: {pnl:.2f}")
        return pnl
    
    @staticmethod
    def validate_pnl(trade_pnl, equity_change, tolerance=0.01):
        """
        Validate that trade PnL and equity change are consistent.
        
        Args:
            trade_pnl (float): Sum of trade PnLs
            equity_change (float): Change in equity
            tolerance (float): Tolerance for validation (as fraction)
            
        Returns:
            bool: True if consistent, False otherwise
        """
        # Avoid division by zero for small equity changes
        if abs(equity_change) < 1e-10:
            return abs(trade_pnl) < 0.01  # Small absolute tolerance for near-zero changes
        
        # Calculate percentage difference
        percent_diff = abs((trade_pnl - equity_change) / equity_change)
        is_valid = percent_diff <= tolerance
        
        if not is_valid:
            logger.warning(f"PnL validation failed: Trade PnL={trade_pnl:.2f}, Equity Change={equity_change:.2f}")
            logger.warning(f"Difference: {trade_pnl - equity_change:.2f}, Percentage: {percent_diff * 100:.2f}%")
        else:
            logger.debug(f"PnL validation passed: Trade PnL={trade_pnl:.2f}, Equity Change={equity_change:.2f}")
            
        return is_valid
    
    @staticmethod
    def calculate_total_pnl(trades):
        """
        Calculate total PnL from a list of trades.
        
        Args:
            trades (list): List of trade dictionaries
            
        Returns:
            float: Total PnL
        """
        closed_trades = [t for t in trades if t.get('closed', False)]
        total_pnl = sum(PnLCalculator.calculate_trade_pnl(trade) for trade in closed_trades)
        return total_pnl
