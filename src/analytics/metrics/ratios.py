"""
Performance ratio metrics for financial analysis.

This module provides financial ratios commonly used to evaluate trading strategies
and portfolio performance. These ratios help assess risk-adjusted returns and other
performance characteristics.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta

from .core import drawdowns, max_drawdown, volatility, log_returns, simple_returns, annualized_return


def sharpe_ratio(returns: pd.Series, 
                risk_free_rate: float = 0.0,
                annualization_factor: int = 252) -> float:
    """
    Calculate Sharpe ratio - returns per unit of risk.
    
    The Sharpe ratio is a measure of risk-adjusted return that compares the 
    excess return of an investment over the risk-free rate to its volatility.
    
    Args:
        returns: Series of returns (either simple or logarithmic)
        risk_free_rate: Annualized risk-free rate (default: 0.0)
        annualization_factor: Periods per year (default: 252 for trading days)
        
    Returns:
        float: Sharpe ratio
        
    Examples:
        >>> import pandas as pd
        >>> import numpy as np
        >>> np.random.seed(42)
        >>> returns = pd.Series(np.random.normal(0.001, 0.01, 100))
        >>> sharpe_ratio(returns, risk_free_rate=0.02/252)
        # Returns the Sharpe ratio
    """
    if returns is None or not isinstance(returns, pd.Series) or returns.empty:
        return 0.0
    
    # Calculate mean daily return
    mean_return = returns.mean()
    
    # Calculate daily risk-free rate
    daily_rfr = risk_free_rate / annualization_factor
    
    # Calculate excess return
    excess_return = mean_return - daily_rfr
    
    # Calculate volatility
    vol = returns.std()
    
    if vol == 0:
        return 0.0
    
    # Calculate daily Sharpe ratio
    daily_sharpe = excess_return / vol
    
    # Annualize Sharpe ratio
    annualized_sharpe = daily_sharpe * np.sqrt(annualization_factor)
    
    return annualized_sharpe


def sortino_ratio(returns: pd.Series, 
                 risk_free_rate: float = 0.0, 
                 target_return: float = 0.0,
                 annualization_factor: int = 252) -> float:
    """
    Calculate Sortino ratio - returns per unit of downside risk.
    
    The Sortino ratio improves upon the Sharpe ratio by focusing only on downside
    volatility, which better reflects an investor's concern with downside risk.
    
    Args:
        returns: Series of returns (either simple or logarithmic)
        risk_free_rate: Annualized risk-free rate (default: 0.0)
        target_return: Minimum acceptable return (default: 0.0)
        annualization_factor: Periods per year (default: 252 for trading days)
        
    Returns:
        float: Sortino ratio
        
    Examples:
        >>> import pandas as pd
        >>> import numpy as np
        >>> np.random.seed(42)
        >>> returns = pd.Series(np.random.normal(0.001, 0.01, 100))
        >>> sortino_ratio(returns, risk_free_rate=0.02/252)
        # Returns the Sortino ratio
    """
    if returns is None or not isinstance(returns, pd.Series) or returns.empty:
        return 0.0
    
    # Calculate mean daily return
    mean_return = returns.mean()
    
    # Calculate daily risk-free rate
    daily_rfr = risk_free_rate / annualization_factor
    
    # Calculate excess return
    excess_return = mean_return - daily_rfr
    
    # Calculate downside deviation
    # Only consider returns below the target (typically 0 or risk-free rate)
    downside_returns = returns[returns < target_return] - target_return
    downside_deviation = np.sqrt(np.mean(downside_returns**2)) if len(downside_returns) > 0 else 0
    
    if downside_deviation == 0:
        return 0.0
    
    # Calculate daily Sortino ratio
    daily_sortino = excess_return / downside_deviation
    
    # Annualize Sortino ratio
    annualized_sortino = daily_sortino * np.sqrt(annualization_factor)
    
    return annualized_sortino


def calmar_ratio(equity_curve: pd.DataFrame, 
                column: str = 'equity', 
                periods_per_year: int = 252,
                window_years: int = 3) -> float:
    """
    Calculate Calmar ratio - returns relative to maximum drawdown.
    
    The Calmar ratio is a performance measure used to evaluate the risk-adjusted
    return of investment strategies, calculated by dividing the annualized return 
    by the maximum drawdown over the specified period.
    
    Args:
        equity_curve: DataFrame containing equity values over time
        column: Name of the column containing equity values (default: 'equity')
        periods_per_year: Periods per year (default: 252 for trading days)
        window_years: Number of years to calculate the ratio over (default: 3)
        
    Returns:
        float: Calmar ratio
        
    Examples:
        >>> import pandas as pd
        >>> equity = pd.DataFrame({'equity': [10000, 11000, 9000, 10000, 12000]})
        >>> calmar_ratio(equity)
        # Returns the Calmar ratio
    """
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame):
        return 0.0
        
    if equity_curve.empty or len(equity_curve) < 2 or column not in equity_curve.columns:
        return 0.0
    
    # Determine window size
    window_periods = window_years * periods_per_year
    
    # Use full equity curve if it's shorter than window size
    if len(equity_curve) <= window_periods:
        window_equity = equity_curve
    else:
        window_equity = equity_curve.iloc[-window_periods:]
    
    # Calculate annualized return
    annual_ret = annualized_return(window_equity, column=column, periods_per_year=periods_per_year)
    
    # Calculate maximum drawdown (as a positive value)
    max_dd = max_drawdown(window_equity, column=column)
    
    if max_dd == 0:
        return 0.0
    
    # Calculate Calmar ratio
    calmar = annual_ret / max_dd
    
    return calmar


def omega_ratio(returns: pd.Series, 
               threshold: float = 0.0,
               annualization_factor: int = 252) -> float:
    """
    Calculate Omega ratio - probability-weighted ratio of gains versus losses.
    
    The Omega ratio is a performance measure that considers all moments of the
    returns distribution, making it more comprehensive than traditional risk-adjusted
    return measures.
    
    Args:
        returns: Series of returns (either simple or logarithmic)
        threshold: Return threshold (default: 0.0)
        annualization_factor: Periods per year (default: 252 for trading days)
        
    Returns:
        float: Omega ratio
        
    Examples:
        >>> import pandas as pd
        >>> import numpy as np
        >>> np.random.seed(42)
        >>> returns = pd.Series(np.random.normal(0.001, 0.01, 100))
        >>> omega_ratio(returns)
        # Returns the Omega ratio
    """
    if returns is None or not isinstance(returns, pd.Series) or returns.empty:
        return 0.0
    
    # Sort returns
    sorted_returns = returns.sort_values()
    
    # Find the threshold index (where returns cross the threshold)
    threshold_index = sorted_returns.searchsorted(threshold)
    
    # Calculate areas above and below threshold
    if threshold_index == 0:  # All returns above threshold
        return float('inf')
    elif threshold_index == len(sorted_returns):  # All returns below threshold
        return 0.0
    
    # Calculate areas above and below threshold
    returns_below = sorted_returns[:threshold_index]
    returns_above = sorted_returns[threshold_index:]
    
    area_below = (threshold - returns_below).sum()
    area_above = (returns_above - threshold).sum()
    
    if area_below == 0:
        return float('inf')
    
    # Calculate Omega ratio
    omega = area_above / area_below
    
    return omega


def information_ratio(returns: pd.Series, 
                     benchmark_returns: pd.Series,
                     annualization_factor: int = 252) -> float:
    """
    Calculate Information Ratio - excess returns per unit of tracking error.
    
    The Information Ratio measures the excess return of a strategy relative to a
    benchmark, divided by the tracking error (standard deviation of those excess returns).
    
    Args:
        returns: Series of strategy returns
        benchmark_returns: Series of benchmark returns
        annualization_factor: Periods per year (default: 252 for trading days)
        
    Returns:
        float: Information ratio
        
    Examples:
        >>> import pandas as pd
        >>> import numpy as np
        >>> np.random.seed(42)
        >>> returns = pd.Series(np.random.normal(0.001, 0.01, 100))
        >>> benchmark = pd.Series(np.random.normal(0.0005, 0.015, 100))
        >>> information_ratio(returns, benchmark)
        # Returns the Information ratio
    """
    if (returns is None or not isinstance(returns, pd.Series) or returns.empty or
        benchmark_returns is None or not isinstance(benchmark_returns, pd.Series) or 
        benchmark_returns.empty):
        return 0.0
    
    # Align returns and benchmark returns
    common_index = returns.index.intersection(benchmark_returns.index)
    if len(common_index) == 0:
        return 0.0
    
    aligned_returns = returns.loc[common_index]
    aligned_benchmark = benchmark_returns.loc[common_index]
    
    # Calculate excess returns
    excess_returns = aligned_returns - aligned_benchmark
    
    # Calculate mean excess return
    mean_excess = excess_returns.mean()
    
    # Calculate tracking error
    tracking_error = excess_returns.std()
    
    if tracking_error == 0:
        return 0.0
    
    # Calculate Information Ratio
    ir = mean_excess / tracking_error
    
    # Annualize Information Ratio
    annualized_ir = ir * np.sqrt(annualization_factor)
    
    return annualized_ir


def treynor_ratio(returns: pd.Series, 
                 benchmark_returns: pd.Series,
                 risk_free_rate: float = 0.0,
                 annualization_factor: int = 252) -> float:
    """
    Calculate Treynor Ratio - excess returns per unit of systematic risk.
    
    The Treynor Ratio measures returns earned in excess of the risk-free rate per
    unit of market risk (beta).
    
    Args:
        returns: Series of strategy returns
        benchmark_returns: Series of benchmark returns
        risk_free_rate: Annualized risk-free rate (default: 0.0)
        annualization_factor: Periods per year (default: 252 for trading days)
        
    Returns:
        float: Treynor ratio
        
    Examples:
        >>> import pandas as pd
        >>> import numpy as np
        >>> np.random.seed(42)
        >>> returns = pd.Series(np.random.normal(0.001, 0.01, 100))
        >>> benchmark = pd.Series(np.random.normal(0.0005, 0.015, 100))
        >>> treynor_ratio(returns, benchmark)
        # Returns the Treynor ratio
    """
    if (returns is None or not isinstance(returns, pd.Series) or returns.empty or
        benchmark_returns is None or not isinstance(benchmark_returns, pd.Series) or 
        benchmark_returns.empty):
        return 0.0
    
    # Align returns and benchmark returns
    common_index = returns.index.intersection(benchmark_returns.index)
    if len(common_index) < 2:
        return 0.0
    
    aligned_returns = returns.loc[common_index]
    aligned_benchmark = benchmark_returns.loc[common_index]
    
    # Calculate excess returns
    daily_rfr = risk_free_rate / annualization_factor
    excess_returns = aligned_returns - daily_rfr
    
    # Calculate beta using covariance / variance
    cov_matrix = np.cov(aligned_returns, aligned_benchmark)
    beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 0
    
    if beta == 0:
        return 0.0
    
    # Calculate annualized excess return
    annualized_excess = excess_returns.mean() * annualization_factor
    
    # Calculate Treynor Ratio
    treynor = annualized_excess / abs(beta)
    
    return treynor


def upside_potential_ratio(returns: pd.Series, 
                          threshold: float = 0.0,
                          annualization_factor: int = 252) -> float:
    """
    Calculate Upside Potential Ratio - a measure of return vs. downside risk.
    
    The Upside Potential Ratio divides the higher partial moment (upside) by 
    the downside deviation, providing a measure of return vs. downside risk.
    
    Args:
        returns: Series of returns (either simple or logarithmic)
        threshold: Return threshold (default: 0.0)
        annualization_factor: Periods per year (default: 252 for trading days)
        
    Returns:
        float: Upside Potential Ratio
        
    Examples:
        >>> import pandas as pd
        >>> import numpy as np
        >>> np.random.seed(42)
        >>> returns = pd.Series(np.random.normal(0.001, 0.01, 100))
        >>> upside_potential_ratio(returns)
        # Returns the Upside Potential Ratio
    """
    if returns is None or not isinstance(returns, pd.Series) or returns.empty:
        return 0.0
    
    # Calculate upside returns
    upside_returns = returns[returns > threshold]
    upside_potential = upside_returns.mean() if len(upside_returns) > 0 else 0
    
    # Calculate downside deviation
    downside_returns = returns[returns < threshold] - threshold
    downside_deviation = np.sqrt(np.mean(downside_returns**2)) if len(downside_returns) > 0 else 0
    
    if downside_deviation == 0:
        return float('inf') if upside_potential > 0 else 0.0
    
    # Calculate Upside Potential Ratio
    upr = upside_potential / downside_deviation
    
    return upr