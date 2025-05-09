"""
Trade-specific metrics for financial analysis.

This module provides metrics for analyzing individual trades and trade patterns.
These metrics help assess trading performance beyond equity curve analysis.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
from collections import defaultdict


def trade_stats(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate basic trade statistics.
    
    Args:
        trades: List of trade dictionaries with at least 'pnl' field
        
    Returns:
        Dict containing:
        - total_trades: Total number of trades
        - winning_trades: Number of winning trades
        - losing_trades: Number of losing trades
        - break_even_trades: Number of break-even trades
        - win_rate: Percentage of winning trades
        - avg_trade: Average P&L per trade
        - avg_win: Average P&L of winning trades
        - avg_loss: Average P&L of losing trades
        - largest_win: Largest winning trade
        - largest_loss: Largest losing trade
        - total_pnl: Sum of all trade P&Ls
        
    Examples:
        >>> trades = [
        ...     {'pnl': 100},
        ...     {'pnl': -50},
        ...     {'pnl': 75},
        ...     {'pnl': 0}
        ... ]
        >>> trade_stats(trades)
        {'total_trades': 4, 'winning_trades': 2, ...}
    """
    if not trades:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'break_even_trades': 0,
            'win_rate': 0.0,
            'avg_trade': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'total_pnl': 0.0
        }
    
    # Extract P&L values
    pnl_values = []
    for trade in trades:
        if isinstance(trade, dict) and 'pnl' in trade:
            pnl_values.append(trade['pnl'])
    
    if not pnl_values:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'break_even_trades': 0,
            'win_rate': 0.0,
            'avg_trade': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'total_pnl': 0.0
        }
    
    # Calculate statistics
    total_trades = len(pnl_values)
    winning_trades = sum(1 for pnl in pnl_values if pnl > 0)
    losing_trades = sum(1 for pnl in pnl_values if pnl < 0)
    break_even_trades = sum(1 for pnl in pnl_values if pnl == 0)
    
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
    
    avg_trade = sum(pnl_values) / total_trades if total_trades > 0 else 0.0
    
    winning_pnls = [pnl for pnl in pnl_values if pnl > 0]
    avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0.0
    
    losing_pnls = [pnl for pnl in pnl_values if pnl < 0]
    avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0.0
    
    largest_win = max(pnl_values) if pnl_values else 0.0
    largest_loss = min(pnl_values) if pnl_values else 0.0
    
    total_pnl = sum(pnl_values)
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'break_even_trades': break_even_trades,
        'win_rate': win_rate,
        'avg_trade': avg_trade,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'total_pnl': total_pnl
    }


def profit_factor(trades: List[Dict[str, Any]]) -> float:
    """
    Calculate profit factor (gross profit / gross loss).
    
    Args:
        trades: List of trade dictionaries with at least 'pnl' field
        
    Returns:
        float: Profit factor (returns infinity if no losing trades)
        
    Examples:
        >>> trades = [
        ...     {'pnl': 100},
        ...     {'pnl': -50},
        ...     {'pnl': 75}
        ... ]
        >>> profit_factor(trades)
        3.5  # (100 + 75) / 50
    """
    if not trades:
        return 0.0
    
    # Extract P&L values
    pnl_values = []
    for trade in trades:
        if isinstance(trade, dict) and 'pnl' in trade:
            pnl_values.append(trade['pnl'])
    
    if not pnl_values:
        return 0.0
    
    # Calculate gross profit and gross loss
    gross_profit = sum(pnl for pnl in pnl_values if pnl > 0)
    gross_loss = sum(abs(pnl) for pnl in pnl_values if pnl < 0)
    
    # Calculate profit factor
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    
    return gross_profit / gross_loss


def win_rate(trades: List[Dict[str, Any]]) -> float:
    """
    Calculate win rate (percentage of winning trades).
    
    Args:
        trades: List of trade dictionaries with at least 'pnl' field
        
    Returns:
        float: Win rate as a decimal (0.0 to 1.0)
        
    Examples:
        >>> trades = [
        ...     {'pnl': 100},
        ...     {'pnl': -50},
        ...     {'pnl': 75}
        ... ]
        >>> win_rate(trades)
        0.6666666666666666  # 2/3 trades are winners
    """
    if not trades:
        return 0.0
    
    # Extract P&L values
    pnl_values = []
    for trade in trades:
        if isinstance(trade, dict) and 'pnl' in trade:
            pnl_values.append(trade['pnl'])
    
    if not pnl_values:
        return 0.0
    
    # Calculate win rate
    winning_trades = sum(1 for pnl in pnl_values if pnl > 0)
    total_trades = len(pnl_values)
    
    return winning_trades / total_trades if total_trades > 0 else 0.0


def expectancy(trades: List[Dict[str, Any]]) -> float:
    """
    Calculate trade expectancy (average amount you can expect to win or lose per trade).
    
    Args:
        trades: List of trade dictionaries with at least 'pnl' field
        
    Returns:
        float: Expectancy value
        
    Examples:
        >>> trades = [
        ...     {'pnl': 100},
        ...     {'pnl': -50},
        ...     {'pnl': 75}
        ... ]
        >>> expectancy(trades)
        41.66666666666667  # Average P&L per trade
    """
    if not trades:
        return 0.0
    
    # Extract P&L values
    pnl_values = []
    for trade in trades:
        if isinstance(trade, dict) and 'pnl' in trade:
            pnl_values.append(trade['pnl'])
    
    if not pnl_values:
        return 0.0
    
    # Calculate expectancy
    return sum(pnl_values) / len(pnl_values)


def risk_reward_ratio(trades: List[Dict[str, Any]]) -> float:
    """
    Calculate average risk-reward ratio.
    
    Args:
        trades: List of trade dictionaries with 'pnl' and 'risk' fields
        
    Returns:
        float: Average risk-reward ratio
        
    Examples:
        >>> trades = [
        ...     {'pnl': 100, 'risk': 50},
        ...     {'pnl': -40, 'risk': 40},
        ...     {'pnl': 60, 'risk': 30}
        ... ]
        >>> risk_reward_ratio(trades)
        1.6  # Average ratio of profit to risk
    """
    if not trades:
        return 0.0
    
    # Filter trades with valid data
    valid_trades = []
    for trade in trades:
        if (isinstance(trade, dict) and 
            'pnl' in trade and 
            'risk' in trade and 
            trade['risk'] != 0):
            valid_trades.append(trade)
    
    if not valid_trades:
        return 0.0
    
    # Calculate risk-reward ratios for winning trades
    ratios = []
    for trade in valid_trades:
        if trade['pnl'] > 0:
            ratios.append(trade['pnl'] / trade['risk'])
    
    # Calculate average ratio
    return sum(ratios) / len(ratios) if ratios else 0.0


def consecutive_wins_losses(trades: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Calculate statistics on consecutive wins and losses.
    
    Args:
        trades: List of trade dictionaries with at least 'pnl' field
        
    Returns:
        Dict containing:
        - max_consecutive_wins: Maximum number of consecutive winning trades
        - max_consecutive_losses: Maximum number of consecutive losing trades
        - current_consecutive_wins: Current streak of winning trades
        - current_consecutive_losses: Current streak of losing trades
        
    Examples:
        >>> trades = [
        ...     {'pnl': 100},
        ...     {'pnl': 50},
        ...     {'pnl': -30},
        ...     {'pnl': -40},
        ...     {'pnl': -20},
        ...     {'pnl': 80}
        ... ]
        >>> consecutive_wins_losses(trades)
        {'max_consecutive_wins': 2, 'max_consecutive_losses': 3, 'current_consecutive_wins': 1, 'current_consecutive_losses': 0}
    """
    if not trades:
        return {
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'current_consecutive_wins': 0,
            'current_consecutive_losses': 0
        }
    
    # Extract P&L values
    pnl_values = []
    for trade in trades:
        if isinstance(trade, dict) and 'pnl' in trade:
            pnl_values.append(trade['pnl'])
    
    if not pnl_values:
        return {
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'current_consecutive_wins': 0,
            'current_consecutive_losses': 0
        }
    
    # Initialize counters
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_consecutive_wins = 0
    current_consecutive_losses = 0
    
    # Count streaks
    for pnl in pnl_values:
        if pnl > 0:
            # Winning trade
            current_consecutive_wins += 1
            current_consecutive_losses = 0
            max_consecutive_wins = max(max_consecutive_wins, current_consecutive_wins)
        elif pnl < 0:
            # Losing trade
            current_consecutive_losses += 1
            current_consecutive_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
        else:
            # Break-even trade - reset both counters
            current_consecutive_wins = 0
            current_consecutive_losses = 0
    
    return {
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses,
        'current_consecutive_wins': current_consecutive_wins,
        'current_consecutive_losses': current_consecutive_losses
    }


def average_holding_period(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate average holding periods for trades.
    
    Args:
        trades: List of trade dictionaries with 'entry_time' and 'exit_time' fields
        
    Returns:
        Dict containing:
        - avg_holding_period: Average holding period for all trades
        - avg_winning_holding_period: Average holding period for winning trades
        - avg_losing_holding_period: Average holding period for losing trades
        
    Examples:
        >>> from datetime import datetime
        >>> trades = [
        ...     {'pnl': 100, 'entry_time': datetime(2023, 1, 1), 'exit_time': datetime(2023, 1, 2)},
        ...     {'pnl': -50, 'entry_time': datetime(2023, 1, 3), 'exit_time': datetime(2023, 1, 5)},
        ... ]
        >>> average_holding_period(trades)
        {'avg_holding_period': 1.5, 'avg_winning_holding_period': 1.0, 'avg_losing_holding_period': 2.0}
    """
    if not trades:
        return {
            'avg_holding_period': 0.0,
            'avg_winning_holding_period': 0.0,
            'avg_losing_holding_period': 0.0
        }
    
    # Filter trades with valid data
    valid_trades = []
    for trade in trades:
        if (isinstance(trade, dict) and 
            'pnl' in trade and 
            'entry_time' in trade and 
            'exit_time' in trade):
            valid_trades.append(trade)
    
    if not valid_trades:
        return {
            'avg_holding_period': 0.0,
            'avg_winning_holding_period': 0.0,
            'avg_losing_holding_period': 0.0
        }
    
    # Calculate holding periods
    all_periods = []
    winning_periods = []
    losing_periods = []
    
    for trade in valid_trades:
        entry_time = pd.to_datetime(trade['entry_time'])
        exit_time = pd.to_datetime(trade['exit_time'])
        
        # Calculate holding period in days
        holding_period = (exit_time - entry_time).total_seconds() / (24 * 3600)
        all_periods.append(holding_period)
        
        if trade['pnl'] > 0:
            winning_periods.append(holding_period)
        elif trade['pnl'] < 0:
            losing_periods.append(holding_period)
    
    # Calculate averages
    avg_holding_period = sum(all_periods) / len(all_periods) if all_periods else 0.0
    avg_winning_holding_period = sum(winning_periods) / len(winning_periods) if winning_periods else 0.0
    avg_losing_holding_period = sum(losing_periods) / len(losing_periods) if losing_periods else 0.0
    
    return {
        'avg_holding_period': avg_holding_period,
        'avg_winning_holding_period': avg_winning_holding_period,
        'avg_losing_holding_period': avg_losing_holding_period
    }


def trade_pnl_distribution(trades: List[Dict[str, Any]], bins: int = 10) -> Dict[str, Any]:
    """
    Calculate trade P&L distribution statistics.
    
    Args:
        trades: List of trade dictionaries with at least 'pnl' field
        bins: Number of bins for the histogram
        
    Returns:
        Dict containing:
        - histogram: Dict with bin_edges and bin_values
        - mean: Mean P&L
        - median: Median P&L
        - std_dev: Standard deviation of P&L
        - skew: Skewness of P&L distribution
        - kurtosis: Kurtosis of P&L distribution
        
    Examples:
        >>> trades = [
        ...     {'pnl': 100},
        ...     {'pnl': -50},
        ...     {'pnl': 75},
        ...     {'pnl': 25}
        ... ]
        >>> result = trade_pnl_distribution(trades)
        # Returns distribution statistics
    """
    if not trades:
        return {
            'histogram': {'bin_edges': [], 'bin_values': []},
            'mean': 0.0,
            'median': 0.0,
            'std_dev': 0.0,
            'skew': 0.0,
            'kurtosis': 0.0
        }
    
    # Extract P&L values
    pnl_values = []
    for trade in trades:
        if isinstance(trade, dict) and 'pnl' in trade:
            pnl_values.append(trade['pnl'])
    
    if not pnl_values:
        return {
            'histogram': {'bin_edges': [], 'bin_values': []},
            'mean': 0.0,
            'median': 0.0,
            'std_dev': 0.0,
            'skew': 0.0,
            'kurtosis': 0.0
        }
    
    # Convert to numpy array
    pnl_array = np.array(pnl_values)
    
    # Calculate histogram
    hist, bin_edges = np.histogram(pnl_array, bins=bins)
    
    # Calculate statistics
    mean = np.mean(pnl_array)
    median = np.median(pnl_array)
    std_dev = np.std(pnl_array)
    
    # Calculate skewness and kurtosis (if scipy is available)
    try:
        from scipy.stats import skew, kurtosis
        skewness = skew(pnl_array)
        kurt = kurtosis(pnl_array)
    except ImportError:
        # Fallback to manual calculation if scipy is not available
        skewness = ((pnl_array - mean) ** 3).mean() / std_dev ** 3 if std_dev != 0 else 0.0
        kurt = ((pnl_array - mean) ** 4).mean() / std_dev ** 4 - 3 if std_dev != 0 else 0.0
    
    return {
        'histogram': {
            'bin_edges': bin_edges.tolist(),
            'bin_values': hist.tolist()
        },
        'mean': float(mean),
        'median': float(median),
        'std_dev': float(std_dev),
        'skew': float(skewness),
        'kurtosis': float(kurt)
    }


def trade_by_time_analysis(trades: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Analyze trade performance by time (hour of day, day of week, month).
    
    Args:
        trades: List of trade dictionaries with 'pnl' and 'entry_time' fields
        
    Returns:
        Dict containing:
        - by_hour: Dict mapping hour to average P&L
        - by_day: Dict mapping day of week to average P&L
        - by_month: Dict mapping month to average P&L
        
    Examples:
        >>> from datetime import datetime
        >>> trades = [
        ...     {'pnl': 100, 'entry_time': datetime(2023, 1, 1, 10, 0)},
        ...     {'pnl': -50, 'entry_time': datetime(2023, 2, 2, 14, 0)},
        ... ]
        >>> trade_by_time_analysis(trades)
        # Returns time-based performance breakdown
    """
    if not trades:
        return {
            'by_hour': {},
            'by_day': {},
            'by_month': {}
        }
    
    # Filter trades with valid data
    valid_trades = []
    for trade in trades:
        if (isinstance(trade, dict) and 
            'pnl' in trade and 
            'entry_time' in trade):
            valid_trades.append(trade)
    
    if not valid_trades:
        return {
            'by_hour': {},
            'by_day': {},
            'by_month': {}
        }
    
    # Initialize accumulators
    by_hour = defaultdict(list)
    by_day = defaultdict(list)
    by_month = defaultdict(list)
    
    # Categorize trades
    for trade in valid_trades:
        entry_time = pd.to_datetime(trade['entry_time'])
        pnl = trade['pnl']
        
        by_hour[entry_time.hour].append(pnl)
        by_day[entry_time.day_name() if hasattr(entry_time, 'day_name') else entry_time.strftime('%A')].append(pnl)
        by_month[entry_time.month_name() if hasattr(entry_time, 'month_name') else entry_time.strftime('%B')].append(pnl)
    
    # Calculate averages
    avg_by_hour = {hour: sum(pnls) / len(pnls) for hour, pnls in by_hour.items()}
    avg_by_day = {day: sum(pnls) / len(pnls) for day, pnls in by_day.items()}
    avg_by_month = {month: sum(pnls) / len(pnls) for month, pnls in by_month.items()}
    
    return {
        'by_hour': avg_by_hour,
        'by_day': avg_by_day,
        'by_month': avg_by_month
    }