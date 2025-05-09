"""
Objective functions for optimization.

This module provides functions for evaluating backtest results
to determine which parameter sets are optimal. All functions
use the standardized analytics module for calculations to ensure
consistency.
"""

import numpy as np

# Import metrics from functional.py which is the actual implementation
from src.analytics.metrics.functional import (
    total_return as analytics_total_return,
    sharpe_ratio as analytics_sharpe_ratio,
    profit_factor as analytics_profit_factor,
    max_drawdown as analytics_max_drawdown,
    win_rate as analytics_win_rate,
    calculate_all_metrics
)

def total_return(results):
    """
    Calculate total return from backtest results.
    
    Args:
        results (dict): Backtest results
        
    Returns:
        float: Total return
    """
    # Try to get the value from the statistics if already calculated
    stats = results.get('statistics', {})
    if 'return_pct' in stats:
        return stats.get('return_pct', 0)
    
    # Otherwise calculate using analytics module
    equity_curve = results.get('equity_curve', [])
    if equity_curve:
        return analytics_total_return(equity_curve)
    
    return 0.0

def sharpe_ratio(results, risk_free_rate=0.0):
    """
    Calculate Sharpe ratio from backtest results.
    
    Args:
        results (dict): Backtest results
        risk_free_rate (float, optional): Risk-free rate
        
    Returns:
        float: Sharpe ratio
    """
    # Try to get the value from the statistics if already calculated
    stats = results.get('statistics', {})
    if 'sharpe_ratio' in stats:
        return stats.get('sharpe_ratio', 0)
    
    # Otherwise calculate using analytics module
    equity_curve = results.get('equity_curve', [])
    if equity_curve:
        return analytics_sharpe_ratio(equity_curve, risk_free_rate=risk_free_rate)
    
    return 0.0

def profit_factor(results):
    """
    Calculate profit factor from backtest results.
    
    Args:
        results (dict): Backtest results
        
    Returns:
        float: Profit factor
    """
    # Try to get the value from the statistics if already calculated
    stats = results.get('statistics', {})
    if 'profit_factor' in stats:
        return stats.get('profit_factor', 0)
    
    # Otherwise calculate using analytics module
    trades = results.get('trades', [])
    if trades:
        return analytics_profit_factor(trades)
    
    return 0.0

def max_drawdown(results):
    """
    Calculate maximum drawdown from backtest results.
    
    Args:
        results (dict): Backtest results
        
    Returns:
        float: Negative of maximum drawdown (negative because we want to maximize)
    """
    # Try to get the value from the statistics if already calculated
    stats = results.get('statistics', {})
    if 'max_drawdown' in stats:
        # Return negative because we want to maximize
        return -stats.get('max_drawdown', 0)
    
    # Otherwise calculate using analytics module
    equity_curve = results.get('equity_curve', [])
    if equity_curve:
        # Return negative because we want to maximize
        return -analytics_max_drawdown(equity_curve)
    
    return 0.0

def win_rate(results):
    """
    Calculate win rate from backtest results.
    
    Args:
        results (dict): Backtest results
        
    Returns:
        float: Win rate (0-1)
    """
    # Try to get the value from the statistics if already calculated
    stats = results.get('statistics', {})
    if 'win_rate' in stats:
        return stats.get('win_rate', 0)
    
    # Otherwise calculate using analytics module
    trades = results.get('trades', [])
    if trades:
        return analytics_win_rate(trades)
    
    return 0.0

def expectancy(results):
    """
    Calculate expectancy from backtest results.
    
    Expectancy = (Win Rate * Average Win) - (Loss Rate * Average Loss)
    
    Args:
        results (dict): Backtest results
        
    Returns:
        float: Expectancy
    """
    trades = results.get('trades', [])
    if not trades:
        return 0.0
    
    # Split trades into winners and losers
    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
    
    # Calculate statistics
    win_rate = len(winning_trades) / len(trades) if trades else 0
    loss_rate = len(losing_trades) / len(trades) if trades else 0
    
    avg_win = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(abs(t.get('pnl', 0)) for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    # Calculate expectancy
    return (win_rate * avg_win) - (loss_rate * avg_loss)

def risk_adjusted_return(results):
    """
    Calculate risk-adjusted return from backtest results.
    
    Risk-adjusted return = Total Return / Max Drawdown
    
    Args:
        results (dict): Backtest results
        
    Returns:
        float: Risk-adjusted return
    """
    # Calculate total return
    ret = total_return(results)
    
    # Calculate max drawdown (positive value)
    dd = -max_drawdown(results)
    
    # Calculate risk-adjusted return
    if dd > 0:
        return ret / dd
    
    # If no drawdown, return total return
    return ret

def combined_score(results, weights=None):
    """
    Calculate a combined score from multiple metrics.
    
    Args:
        results (dict): Backtest results
        weights (dict, optional): Weights for each metric
        
    Returns:
        float: Combined score
    """
    # Default weights
    if weights is None:
        weights = {
            'sharpe_ratio': 0.5,
            'profit_factor': 0.3,
            'max_drawdown': 0.2
        }
        
    # Calculate individual metrics
    sharpe = sharpe_ratio(results)
    pf = profit_factor(results)
    dd = max_drawdown(results)
    
    # Calculate weighted score
    score = (
        weights.get('sharpe_ratio', 0) * sharpe +
        weights.get('profit_factor', 0) * pf +
        weights.get('max_drawdown', 0) * dd
    )
    
    return score

def stability_score(results):
    """
    Calculate stability score from equity curve.
    
    This measures the consistency of returns throughout the test period.
    
    Args:
        results (dict): Backtest results
        
    Returns:
        float: Stability score (higher is better)
    """
    equity_curve = results.get('equity_curve', [])
    if not equity_curve:
        return 0.0
    
    # Calculate R² of equity curve against linear regression
    import numpy as np
    try:
        from sklearn.linear_model import LinearRegression
        
        # Extract equity values
        y = np.array([e.get('equity', 0) for e in equity_curve])
        X = np.arange(len(y)).reshape(-1, 1)
        
        # Fit linear regression
        model = LinearRegression()
        model.fit(X, y)
        
        # Calculate R²
        y_pred = model.predict(X)
        ss_total = np.sum((y - np.mean(y)) ** 2)
        ss_residual = np.sum((y - y_pred) ** 2)
        r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 0
        
        return r_squared
    except ImportError:
        # If sklearn is not available, calculate a simpler version
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("sklearn not available, calculating simpler stability score")
        
        # Just return the inverse of the coefficient of variation
        eq_values = [e.get('equity', 0) for e in equity_curve]
        if not eq_values or len(eq_values) < 2:
            return 0.0
            
        std = np.std(eq_values)
        mean = np.mean(eq_values)
        
        if mean == 0:
            return 0.0
            
        cv = std / mean  # Coefficient of variation
        return 1.0 / (1.0 + cv)  # Lower CV = higher stability

# Dictionary mapping objective names to functions
OBJECTIVES = {
    'total_return': total_return,
    'sharpe_ratio': sharpe_ratio,
    'profit_factor': profit_factor,
    'max_drawdown': max_drawdown,
    'win_rate': win_rate,
    'expectancy': expectancy,
    'risk_adjusted_return': risk_adjusted_return,
    'combined_score': combined_score,
    'stability_score': stability_score
}

def get_objective_function(name):
    """
    Get an objective function by name.
    
    Args:
        name (str): Name of the objective function
        
    Returns:
        callable: Objective function
    """
    if name not in OBJECTIVES:
        valid_objectives = list(OBJECTIVES.keys())
        raise ValueError(f"Unknown objective function: {name}. "
                        f"Available objectives: {valid_objectives}")
        
    return OBJECTIVES[name]
