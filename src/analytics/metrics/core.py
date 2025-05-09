"""
Core performance metrics for financial analysis.

This module provides fundamental performance metrics for analyzing trading strategies,
portfolios, and investments. All functions are designed to be pure and handle edge
cases gracefully.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta


def total_return(equity_curve: pd.DataFrame, 
                 column: str = 'equity') -> float:
    """
    Calculate total return over the entire period.
    
    Args:
        equity_curve: DataFrame containing equity values over time
        column: Name of the column containing equity values (default: 'equity')
        
    Returns:
        float: Total return as a decimal (e.g., 0.1 for 10% return)
        
    Examples:
        >>> import pandas as pd
        >>> equity = pd.DataFrame({'equity': [10000, 11000, 12000]})
        >>> total_return(equity)
        0.2
    """
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame):
        return 0.0
        
    if equity_curve.empty or len(equity_curve) < 2 or column not in equity_curve.columns:
        return 0.0
        
    initial = equity_curve[column].iloc[0]
    final = equity_curve[column].iloc[-1]
    
    if initial <= 0:
        return 0.0
        
    return (final - initial) / initial


def simple_returns(equity_curve: pd.DataFrame, 
                  column: str = 'equity',
                  drop_na: bool = True) -> pd.Series:
    """
    Calculate simple returns from an equity curve.
    
    Args:
        equity_curve: DataFrame containing equity values over time
        column: Name of the column containing equity values (default: 'equity')
        drop_na: Whether to drop NA values from the result (default: True)
        
    Returns:
        pd.Series: Series of simple returns
        
    Examples:
        >>> import pandas as pd
        >>> equity = pd.DataFrame({'equity': [10000, 11000, 12000]})
        >>> simple_returns(equity)
        1    0.1
        2    0.090909
        dtype: float64
    """
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame):
        return pd.Series()
        
    if equity_curve.empty or len(equity_curve) < 2 or column not in equity_curve.columns:
        return pd.Series()
    
    # Calculate simple returns: (price_t / price_{t-1}) - 1
    returns = equity_curve[column].pct_change()
    
    if drop_na:
        returns = returns.dropna()
        
    return returns


def log_returns(equity_curve: pd.DataFrame, 
               column: str = 'equity',
               drop_na: bool = True) -> pd.Series:
    """
    Calculate logarithmic returns from an equity curve.
    
    Log returns are advantageous for statistical analysis due to their 
    additive property and better approximation of normal distribution.
    
    Args:
        equity_curve: DataFrame containing equity values over time
        column: Name of the column containing equity values (default: 'equity')
        drop_na: Whether to drop NA values from the result (default: True)
        
    Returns:
        pd.Series: Series of logarithmic returns
        
    Examples:
        >>> import pandas as pd
        >>> equity = pd.DataFrame({'equity': [10000, 11000, 12000]})
        >>> log_returns(equity)
        1    0.095310
        2    0.086178
        dtype: float64
    """
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame):
        return pd.Series()
        
    if equity_curve.empty or len(equity_curve) < 2 or column not in equity_curve.columns:
        return pd.Series()
    
    # Check if there are non-positive values that would cause issues with log
    if (equity_curve[column] <= 0).any():
        return pd.Series()
    
    # Calculate log returns: ln(price_t / price_{t-1})
    returns = np.log(equity_curve[column] / equity_curve[column].shift(1))
    
    if drop_na:
        returns = returns.dropna()
        
    return returns


def annualized_return(equity_curve: pd.DataFrame, 
                     column: str = 'equity',
                     periods_per_year: int = 252,
                     use_log_returns: bool = True) -> float:
    """
    Calculate annualized return over the entire period.
    
    Args:
        equity_curve: DataFrame containing equity values over time
        column: Name of the column containing equity values (default: 'equity')
        periods_per_year: Number of periods in a year (default: 252 for trading days)
        use_log_returns: Whether to use logarithmic returns for calculation (default: True)
        
    Returns:
        float: Annualized return as a decimal
        
    Examples:
        >>> import pandas as pd
        >>> equity = pd.DataFrame({'equity': [10000, 11000, 12000]})
        >>> annualized_return(equity, periods_per_year=252)
        # Returns annualized value based on 252 trading days per year
    """
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame):
        return 0.0
        
    if equity_curve.empty or len(equity_curve) < 2 or column not in equity_curve.columns:
        return 0.0
    
    # Calculate total periods
    periods = len(equity_curve) - 1
    
    if periods <= 0:
        return 0.0
    
    # Calculate total return
    initial = equity_curve[column].iloc[0]
    final = equity_curve[column].iloc[-1]
    
    if initial <= 0:
        return 0.0
    
    total_ret = (final / initial) - 1
    
    # Calculate annualized return
    if use_log_returns:
        # Using log returns: exp(log(1 + total_return) * (periods_per_year / periods)) - 1
        log_ret = np.log(1 + total_ret)
        annualized = np.exp(log_ret * (periods_per_year / periods)) - 1
    else:
        # Using simple returns: (1 + total_return)^(periods_per_year / periods) - 1
        annualized = (1 + total_ret) ** (periods_per_year / periods) - 1
    
    return annualized


def cagr(equity_curve: pd.DataFrame, 
        column: str = 'equity',
        date_column: str = 'date') -> float:
    """
    Calculate Compound Annual Growth Rate (CAGR).
    
    CAGR provides a more accurate measure of annualized return when 
    the exact time period is known.
    
    Args:
        equity_curve: DataFrame containing equity values over time
        column: Name of the column containing equity values (default: 'equity')
        date_column: Name of the column containing dates (default: 'date')
        
    Returns:
        float: CAGR as a decimal
        
    Examples:
        >>> import pandas as pd
        >>> from datetime import datetime
        >>> equity = pd.DataFrame({
        ...     'date': [datetime(2020, 1, 1), datetime(2021, 1, 1)],
        ...     'equity': [10000, 12000]
        ... })
        >>> cagr(equity)
        0.2
    """
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame):
        return 0.0
        
    if (equity_curve.empty or len(equity_curve) < 2 or 
        column not in equity_curve.columns):
        return 0.0
    
    # Check if date column exists
    if date_column not in equity_curve.columns:
        # Use annualized return as fallback if no date column is provided
        return annualized_return(equity_curve, column=column)
    
    # Extract start and end values and dates
    initial = equity_curve[column].iloc[0]
    final = equity_curve[column].iloc[-1]
    start_date = pd.to_datetime(equity_curve[date_column].iloc[0])
    end_date = pd.to_datetime(equity_curve[date_column].iloc[-1])
    
    if initial <= 0:
        return 0.0
    
    # Calculate years between start and end dates
    days_diff = (end_date - start_date).days
    years = days_diff / 365.25
    
    if years <= 0:
        return 0.0
    
    # Calculate CAGR: (final / initial)^(1 / years) - 1
    return (final / initial) ** (1 / years) - 1


def volatility(returns: pd.Series, 
              annualization_factor: int = 252) -> float:
    """
    Calculate volatility (standard deviation of returns) with annualization.
    
    Args:
        returns: Series of returns (either simple or logarithmic)
        annualization_factor: Factor to annualize volatility (default: 252 for trading days)
        
    Returns:
        float: Annualized volatility as a decimal
        
    Examples:
        >>> import pandas as pd
        >>> import numpy as np
        >>> np.random.seed(42)
        >>> returns = pd.Series(np.random.normal(0.001, 0.01, 100))
        >>> volatility(returns)
        # Returns the annualized volatility
    """
    if returns is None or not isinstance(returns, pd.Series):
        return 0.0
        
    if returns.empty:
        return 0.0
    
    # Calculate standard deviation of returns
    std_dev = returns.std()
    
    # Annualize volatility
    annualized_vol = std_dev * np.sqrt(annualization_factor)
    
    return annualized_vol


def drawdowns(equity_curve: pd.DataFrame, 
             column: str = 'equity') -> pd.DataFrame:
    """
    Calculate drawdowns for an equity curve.
    
    Returns a DataFrame with:
    - 'equity': Original equity values
    - 'peak': Running peak value
    - 'drawdown': Drawdown from peak in decimal format
    
    Args:
        equity_curve: DataFrame containing equity values over time
        column: Name of the column containing equity values (default: 'equity')
        
    Returns:
        pd.DataFrame: DataFrame with drawdown information
        
    Examples:
        >>> import pandas as pd
        >>> equity = pd.DataFrame({'equity': [10000, 11000, 10500, 10800, 12000]})
        >>> drawdowns(equity)
        # Returns DataFrame with columns: ['equity', 'peak', 'drawdown']
    """
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame):
        return pd.DataFrame()
        
    if equity_curve.empty or column not in equity_curve.columns:
        return pd.DataFrame()
    
    # Create copy to avoid modifying original
    result = equity_curve.copy()
    
    # Calculate running peak
    result['peak'] = result[column].cummax()
    
    # Calculate drawdown in decimal format
    result['drawdown'] = (result[column] - result['peak']) / result['peak']
    
    return result


def max_drawdown(equity_curve: pd.DataFrame, 
                column: str = 'equity') -> float:
    """
    Calculate maximum drawdown.
    
    Args:
        equity_curve: DataFrame containing equity values over time
        column: Name of the column containing equity values (default: 'equity')
        
    Returns:
        float: Maximum drawdown as a positive decimal (e.g., 0.2 for 20% drawdown)
        
    Examples:
        >>> import pandas as pd
        >>> equity = pd.DataFrame({'equity': [10000, 11000, 9000, 10000]})
        >>> max_drawdown(equity)
        0.18181818181818182  # Maximum drawdown of 18.18%
    """
    dd = drawdowns(equity_curve, column=column)
    
    if dd.empty or 'drawdown' not in dd.columns:
        return 0.0
    
    # Return max drawdown as a positive value
    return abs(dd['drawdown'].min())


def drawdown_stats(equity_curve: pd.DataFrame, 
                  column: str = 'equity',
                  threshold: float = 0.0) -> Dict[str, Any]:
    """
    Calculate detailed drawdown statistics.
    
    Args:
        equity_curve: DataFrame containing equity values over time
        column: Name of the column containing equity values (default: 'equity')
        threshold: Minimum drawdown to consider (default: 0.0)
        
    Returns:
        Dict containing:
        - max_drawdown: Maximum drawdown as a positive decimal
        - avg_drawdown: Average drawdown depth as a positive decimal
        - max_length: Maximum drawdown length in periods
        - avg_length: Average drawdown length in periods
        - num_drawdowns: Number of drawdowns exceeding threshold
        - time_in_drawdown: Percentage of time spent in drawdown
        
    Examples:
        >>> import pandas as pd
        >>> equity = pd.DataFrame({'equity': [10000, 11000, 9000, 10000, 12000, 11000]})
        >>> drawdown_stats(equity)
        # Returns dictionary with drawdown statistics
    """
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame):
        return {
            'max_drawdown': 0.0,
            'avg_drawdown': 0.0,
            'max_length': 0,
            'avg_length': 0,
            'num_drawdowns': 0,
            'time_in_drawdown': 0.0
        }
        
    if equity_curve.empty or column not in equity_curve.columns:
        return {
            'max_drawdown': 0.0,
            'avg_drawdown': 0.0,
            'max_length': 0,
            'avg_length': 0,
            'num_drawdowns': 0,
            'time_in_drawdown': 0.0
        }
    
    # Calculate drawdowns
    dd = drawdowns(equity_curve, column=column)
    
    # Initialize variables
    current_dd = 0
    current_length = 0
    max_dd = 0
    max_length = 0
    total_periods = len(dd)
    time_in_dd = 0
    dd_depths = []
    dd_lengths = []
    in_drawdown = False
    
    # Analyze drawdowns
    for _, row in dd.iterrows():
        drawdown = abs(row['drawdown'])
        
        if drawdown > threshold:
            time_in_dd += 1
            
            if not in_drawdown:
                # Start of new drawdown
                in_drawdown = True
                current_length = 1
                current_dd = drawdown
            else:
                # Continuing drawdown
                current_length += 1
                current_dd = max(current_dd, drawdown)
        else:
            if in_drawdown:
                # End of drawdown
                dd_depths.append(current_dd)
                dd_lengths.append(current_length)
                max_dd = max(max_dd, current_dd)
                max_length = max(max_length, current_length)
                in_drawdown = False
    
    # Handle case where we end while in a drawdown
    if in_drawdown:
        dd_depths.append(current_dd)
        dd_lengths.append(current_length)
        max_dd = max(max_dd, current_dd)
        max_length = max(max_length, current_length)
    
    # Calculate statistics
    num_drawdowns = len(dd_depths)
    avg_drawdown = np.mean(dd_depths) if dd_depths else 0.0
    avg_length = np.mean(dd_lengths) if dd_lengths else 0
    time_in_drawdown = time_in_dd / total_periods if total_periods > 0 else 0.0
    
    return {
        'max_drawdown': max_dd,
        'avg_drawdown': avg_drawdown,
        'max_length': max_length,
        'avg_length': avg_length,
        'num_drawdowns': num_drawdowns,
        'time_in_drawdown': time_in_drawdown
    }