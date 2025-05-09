"""
Asset allocation utilities for portfolio management.

This module provides functions and classes for asset allocation calculations,
including position sizing, allocation targets, and rebalancing.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class Allocation:
    """Base class for asset allocation methods."""
    
    def __init__(self, name: str = None):
        """
        Initialize allocation.
        
        Args:
            name: Allocation name
        """
        self._name = name or self.__class__.__name__
    
    def calculate_allocation(self, portfolio_value: float, 
                           targets: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate asset allocation.
        
        Args:
            portfolio_value: Total portfolio value
            targets: Target allocation percentages as decimals
            
        Returns:
            Dict mapping assets to allocation amounts
        """
        raise NotImplementedError("Subclasses must implement calculate_allocation")
    
    @property
    def name(self):
        """Get allocation name."""
        return self._name


class EqualWeightAllocation(Allocation):
    """Equal weight allocation across all assets."""
    
    def calculate_allocation(self, portfolio_value: float, 
                           assets: List[str]) -> Dict[str, float]:
        """
        Calculate equal weight allocation.
        
        Args:
            portfolio_value: Total portfolio value
            assets: List of asset identifiers
            
        Returns:
            Dict mapping assets to allocation amounts
        """
        if not assets:
            return {}
        
        weight = 1.0 / len(assets)
        allocation = {asset: portfolio_value * weight for asset in assets}
        
        return allocation


class TargetWeightAllocation(Allocation):
    """Target weight allocation based on specified weights."""
    
    def calculate_allocation(self, portfolio_value: float, 
                           targets: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate target weight allocation.
        
        Args:
            portfolio_value: Total portfolio value
            targets: Target allocation percentages as decimals
            
        Returns:
            Dict mapping assets to allocation amounts
        """
        # Normalize weights if they don't sum to 1.0
        total_weight = sum(targets.values())
        
        if total_weight == 0:
            logger.warning("Total allocation weight is zero, returning empty allocation")
            return {}
        
        normalized_targets = {
            asset: weight / total_weight 
            for asset, weight in targets.items()
        }
        
        # Calculate allocation
        allocation = {
            asset: portfolio_value * weight 
            for asset, weight in normalized_targets.items()
        }
        
        return allocation


class RiskParityAllocation(Allocation):
    """Risk parity allocation based on asset volatilities."""
    
    def calculate_allocation(self, portfolio_value: float, 
                           volatilities: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate risk parity allocation.
        
        Args:
            portfolio_value: Total portfolio value
            volatilities: Asset volatilities
            
        Returns:
            Dict mapping assets to allocation amounts
        """
        if not volatilities:
            return {}
        
        # Invert volatilities to get weights
        inverse_vols = {
            asset: 1.0 / vol if vol > 0 else 0.0 
            for asset, vol in volatilities.items()
        }
        
        # Normalize weights
        total_inverse_vol = sum(inverse_vols.values())
        
        if total_inverse_vol == 0:
            logger.warning("Total inverse volatility is zero, returning empty allocation")
            return {}
        
        normalized_weights = {
            asset: inv_vol / total_inverse_vol 
            for asset, inv_vol in inverse_vols.items()
        }
        
        # Calculate allocation
        allocation = {
            asset: portfolio_value * weight 
            for asset, weight in normalized_weights.items()
        }
        
        return allocation


class MinimumVarianceAllocation(Allocation):
    """Minimum variance allocation based on covariance matrix."""
    
    def calculate_allocation(self, portfolio_value: float, 
                           cov_matrix: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate minimum variance allocation.
        
        Args:
            portfolio_value: Total portfolio value
            cov_matrix: Covariance matrix
            
        Returns:
            Dict mapping assets to allocation amounts
        """
        if cov_matrix.empty:
            return {}
        
        try:
            # Calculate inverse of covariance matrix
            inv_cov = np.linalg.inv(cov_matrix.values)
            
            # Calculate weights
            ones = np.ones(len(cov_matrix))
            weights = np.dot(inv_cov, ones)
            weights /= np.sum(weights)
            
            # Map weights to assets
            allocation = {
                asset: portfolio_value * weight 
                for asset, weight in zip(cov_matrix.index, weights)
            }
            
            return allocation
            
        except np.linalg.LinAlgError:
            logger.error("Matrix inversion failed, using equal weight allocation")
            return EqualWeightAllocation().calculate_allocation(portfolio_value, list(cov_matrix.index))


def calculate_rebalance_trades(current_positions: Dict[str, float], 
                             target_allocation: Dict[str, float], 
                             prices: Dict[str, float],
                             threshold: float = 0.0) -> Dict[str, float]:
    """
    Calculate trades required to rebalance portfolio to target allocation.
    
    Args:
        current_positions: Current positions (asset -> quantity)
        target_allocation: Target allocation (asset -> value)
        prices: Current prices (asset -> price)
        threshold: Minimum deviation threshold before rebalancing
        
    Returns:
        Dict mapping assets to trade quantities (positive for buy, negative for sell)
    """
    # Calculate current allocation
    current_allocation = {
        asset: qty * prices.get(asset, 0) 
        for asset, qty in current_positions.items()
    }
    
    # Calculate trades
    trades = {}
    
    # Add assets in target but not in current
    for asset in target_allocation:
        if asset not in current_allocation:
            if target_allocation[asset] > 0 and asset in prices and prices[asset] > 0:
                qty = target_allocation[asset] / prices[asset]
                trades[asset] = qty
    
    # Calculate adjustments for existing positions
    for asset, current_value in current_allocation.items():
        target_value = target_allocation.get(asset, 0)
        
        # Calculate deviation
        deviation = abs(current_value - target_value) / max(current_value, target_value, 1.0)
        
        # Check if deviation exceeds threshold
        if deviation > threshold:
            if asset in prices and prices[asset] > 0:
                # Calculate required quantity adjustment
                current_qty = current_positions.get(asset, 0)
                target_qty = target_value / prices[asset]
                
                # Calculate trade quantity
                trade_qty = target_qty - current_qty
                
                # Add to trades if non-zero
                if abs(trade_qty) > 0.0001:  # Minimum trade size
                    trades[asset] = trade_qty
    
    return trades


def get_allocation_factory(method: str) -> Allocation:
    """
    Get allocation factory based on method name.
    
    Args:
        method: Allocation method name
        
    Returns:
        Allocation factory instance
    """
    factories = {
        'equal_weight': EqualWeightAllocation,
        'target_weight': TargetWeightAllocation,
        'risk_parity': RiskParityAllocation,
        'minimum_variance': MinimumVarianceAllocation
    }
    
    if method in factories:
        return factories[method]()
    else:
        logger.warning(f"Unknown allocation method: {method}, using equal weight")
        return EqualWeightAllocation()