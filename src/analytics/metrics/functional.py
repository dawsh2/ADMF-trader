# src/core/analytics/metrics/functional.py
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union

def total_return(equity_curve: pd.DataFrame, trades: List[Dict] = None) -> float:
    """
    Calculate total return.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        trades: Optional list of trades
        
    Returns:
        float: Total return as decimal
    """
    if len(equity_curve) < 2:
        return 0.0
        
    initial = equity_curve['equity'].iloc[0]
    final = equity_curve['equity'].iloc[-1]
    
    return (final - initial) / initial

def annualized_return(equity_curve: pd.DataFrame, trades: List[Dict] = None, 
                     trading_days_per_year: int = 252) -> float:
    """
    Calculate annualized return.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        trades: Optional list of trades
        trading_days_per_year: Number of trading days per year
        
    Returns:
        float: Annualized return as decimal
    """
    if len(equity_curve) < 2:
        return 0.0
        
    total_ret = total_return(equity_curve, trades)
    duration_days = (equity_curve.index[-1] - equity_curve.index[0]).days
    
    if duration_days < 1:
        return 0.0
    
    years = duration_days / 365.0
    return (1 + total_ret) ** (1 / years) - 1

def sharpe_ratio(equity_curve: pd.DataFrame, trades: List[Dict] = None, 
                risk_free_rate: float = 0.0, annualization_factor: int = 252) -> float:
    """
    Calculate Sharpe ratio.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        trades: Optional list of trades
        risk_free_rate: Annualized risk-free rate
        annualization_factor: Annualization factor (252 for daily returns)
        
    Returns:
        float: Sharpe ratio
    """
    if len(equity_curve) < 2:
        return 0.0
        
    # Calculate returns
    returns = equity_curve['equity'].pct_change().dropna()
    
    if len(returns) == 0:
        return 0.0
        
    # Calculate annualized Sharpe ratio
    excess_returns = returns - (risk_free_rate / annualization_factor)
    sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(annualization_factor)
    
    return sharpe

def sortino_ratio(equity_curve: pd.DataFrame, trades: List[Dict] = None, 
                 risk_free_rate: float = 0.0, annualization_factor: int = 252, 
                 target_return: float = 0.0) -> float:
    """
    Calculate Sortino ratio.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        trades: Optional list of trades
        risk_free_rate: Annualized risk-free rate
        annualization_factor: Annualization factor (252 for daily returns)
        target_return: Target return for downside deviation calculation
        
    Returns:
        float: Sortino ratio
    """
    if len(equity_curve) < 2:
        return 0.0
        
    # Calculate returns
    returns = equity_curve['equity'].pct_change().dropna()
    
    if len(returns) == 0:
        return 0.0
        
    # Calculate excess returns
    excess_returns = returns - (risk_free_rate / annualization_factor)
    
    # Calculate downside deviation (standard deviation of negative excess returns)
    downside_returns = excess_returns[excess_returns < target_return]
    
    if len(downside_returns) == 0:
        return float('inf')  # No downside - perfect Sortino!
        
    downside_deviation = downside_returns.std() * np.sqrt(annualization_factor)
    
    if downside_deviation == 0:
        return float('inf')  # Avoid division by zero
        
    # Calculate Sortino ratio
    sortino = excess_returns.mean() * annualization_factor / downside_deviation
    
    return sortino

def max_drawdown(equity_curve: pd.DataFrame, trades: List[Dict] = None) -> float:
    """
    Calculate maximum drawdown.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        trades: Optional list of trades
        
    Returns:
        float: Maximum drawdown as positive decimal (e.g., 0.20 for 20%)
    """
    if len(equity_curve) < 2:
        return 0.0
        
    # Calculate running maximum
    running_max = equity_curve['equity'].cummax()
    
    # Calculate drawdown
    drawdown = (running_max - equity_curve['equity']) / running_max
    
    return drawdown.max()

def calmar_ratio(equity_curve: pd.DataFrame, trades: List[Dict] = None, 
                years: int = 3) -> float:
    """
    Calculate Calmar ratio.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        trades: Optional list of trades
        years: Number of years for Calmar ratio calculation
        
    Returns:
        float: Calmar ratio
    """
    if len(equity_curve) < 2:
        return 0.0
        
    # Calculate annualized return
    annual_ret = annualized_return(equity_curve, trades)
    
    # Calculate maximum drawdown
    max_dd = max_drawdown(equity_curve, trades)
    
    if max_dd == 0:
        return float('inf')  # Avoid division by zero
        
    return annual_ret / max_dd

def win_rate(trades: List[Dict]) -> float:
    """
    Calculate win rate.
    
    Args:
        trades: List of trade records with 'pnl' field
        
    Returns:
        float: Win rate as decimal
    """
    if not trades:
        return 0.0
        
    wins = sum(1 for trade in trades if trade.get('pnl', 0) > 0)
    return wins / len(trades)

def profit_factor(trades: List[Dict]) -> float:
    """
    Calculate profit factor.
    
    Args:
        trades: List of trade records with 'pnl' field
        
    Returns:
        float: Profit factor (gross_profit / gross_loss)
    """
    if not trades:
        return 0.0
        
    gross_profit = sum(trade.get('pnl', 0) for trade in trades if trade.get('pnl', 0) > 0)
    gross_loss = abs(sum(trade.get('pnl', 0) for trade in trades if trade.get('pnl', 0) < 0))
    
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
        
    return gross_profit / gross_loss

def average_trade(trades: List[Dict]) -> Dict[str, float]:
    """
    Calculate average trade metrics.
    
    Args:
        trades: List of trade records with 'pnl' field
        
    Returns:
        Dict with average metrics
    """
    if not trades:
        return {'avg_trade': 0.0, 'avg_win': 0.0, 'avg_loss': 0.0, 'win_loss_ratio': 0.0}
        
    # All trades
    all_pnl = [trade.get('pnl', 0) for trade in trades]
    avg_trade = sum(all_pnl) / len(all_pnl) if all_pnl else 0.0
    
    # Winning trades
    win_pnl = [pnl for pnl in all_pnl if pnl > 0]
    avg_win = sum(win_pnl) / len(win_pnl) if win_pnl else 0.0
    
    # Losing trades
    loss_pnl = [abs(pnl) for pnl in all_pnl if pnl < 0]
    avg_loss = sum(loss_pnl) / len(loss_pnl) if loss_pnl else 0.0
    
    # Win/loss ratio
    win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
    
    return {
        'avg_trade': avg_trade,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'win_loss_ratio': win_loss_ratio
    }

def drawdown_stats(equity_curve: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate drawdown statistics.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        
    Returns:
        Dict with drawdown statistics
    """
    if len(equity_curve) < 2:
        return {'max_drawdown': 0.0, 'avg_drawdown': 0.0, 'max_drawdown_duration': 0}
        
    # Calculate running maximum
    equity = equity_curve['equity']
    running_max = equity.cummax()
    
    # Calculate drawdown
    drawdown = (running_max - equity) / running_max
    
    # Identify drawdown periods
    in_drawdown = False
    drawdown_periods = []
    current_period_start = None
    
    for i, dd in enumerate(drawdown):
        if not in_drawdown and dd > 0:
            # Start of drawdown
            in_drawdown = True
            current_period_start = i
        elif in_drawdown and dd == 0:
            # End of drawdown
            in_drawdown = False
            if current_period_start is not None:
                drawdown_periods.append((current_period_start, i))
                current_period_start = None
    
    # If still in drawdown at the end
    if in_drawdown and current_period_start is not None:
        drawdown_periods.append((current_period_start, len(drawdown) - 1))
    
    # Calculate statistics
    max_dd = drawdown.max()
    avg_dd = drawdown[drawdown > 0].mean() if len(drawdown[drawdown > 0]) > 0 else 0.0
    
    # Calculate maximum drawdown duration
    if drawdown_periods:
        durations = [(end - start) for start, end in drawdown_periods]
        max_duration = max(durations) if durations else 0
    else:
        max_duration = 0
    
    return {
        'max_drawdown': max_dd,
        'avg_drawdown': avg_dd,
        'max_drawdown_duration': max_duration
    }

def calculate_all_metrics(equity_curve: pd.DataFrame, trades: List[Dict] = None) -> Dict[str, Any]:
    """
    Calculate all performance metrics.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        trades: Optional list of trades
        
    Returns:
        Dict with all metrics
    """
    metrics = {
        'total_return': total_return(equity_curve, trades),
        'annualized_return': annualized_return(equity_curve, trades),
        'sharpe_ratio': sharpe_ratio(equity_curve, trades),
        'sortino_ratio': sortino_ratio(equity_curve, trades),
        'max_drawdown': max_drawdown(equity_curve, trades),
        'calmar_ratio': calmar_ratio(equity_curve, trades)
    }
    
    # Add trade-specific metrics if trades are provided
    if trades:
        metrics.update({
            'win_rate': win_rate(trades),
            'profit_factor': profit_factor(trades)
        })
        
        # Add average trade metrics
        metrics.update(average_trade(trades))
    
    # Add drawdown statistics
    metrics.update(drawdown_stats(equity_curve))
    
    return metrics
