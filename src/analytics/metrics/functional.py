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
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame) or equity_curve.empty or len(equity_curve) < 2:
        return 0.0
        
    initial = equity_curve['equity'].iloc[0]
    final = equity_curve['equity'].iloc[-1]
    
    return (final - initial) / initial

def calculate_log_returns(equity_curve: pd.DataFrame) -> pd.Series:
    """
    Calculate logarithmic returns from equity curve.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        
    Returns:
        pandas.Series: Series of log returns
    """
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame) or equity_curve.empty or len(equity_curve) < 2:
        return pd.Series()
    
    # Calculate log returns: ln(price_t / price_{t-1})
    log_returns = np.log(equity_curve['equity'] / equity_curve['equity'].shift(1)).dropna()
    return log_returns

def annualized_return(equity_curve: pd.DataFrame, trades: List[Dict] = None, 
                     trading_days_per_year: int = 252) -> float:
    """
    Calculate annualized return using log returns.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        trades: Optional list of trades
        trading_days_per_year: Number of trading days per year
        
    Returns:
        float: Annualized return as decimal
    """
    if len(equity_curve) < 2:
        return 0.0
        
    # Calculate using log returns for more accurate compounding
    initial = equity_curve['equity'].iloc[0]
    final = equity_curve['equity'].iloc[-1]
    
    # Calculate time period in years
    duration_days = (equity_curve.index[-1] - equity_curve.index[0]).days
    if duration_days < 1:
        return 0.0
    
    years = duration_days / 365.0
    
    # Calculate log return and then annualize
    total_log_return = np.log(final / initial)
    annualized_log_return = total_log_return / years
    
    # Convert back to simple return for reporting
    return np.exp(annualized_log_return) - 1

def sharpe_ratio(equity_curve: pd.DataFrame, trades: List[Dict] = None,
                risk_free_rate: float = 0.0, annualization_factor: int = 252) -> float:
    """
    Calculate Sharpe ratio using log returns.

    Args:
        equity_curve: DataFrame with 'equity' column
        trades: Optional list of trades
        risk_free_rate: Annualized risk-free rate
        annualization_factor: Annualization factor (252 for daily returns)

    Returns:
        float: Sharpe ratio
    """
    # Import logging for debugging
    import logging
    logger = logging.getLogger(__name__)

    # Create a simple in-memory cache to avoid duplicate warnings
    if not hasattr(sharpe_ratio, '_warning_cache'):
        sharpe_ratio._warning_cache = set()

    # Need at least 2 equity points to calculate returns
    if equity_curve is None or len(equity_curve) < 2:
        warn_key = "insufficient_data_points"
        if warn_key not in sharpe_ratio._warning_cache:
            logger.warning("Insufficient data points for Sharpe ratio calculation")
            sharpe_ratio._warning_cache.add(warn_key)
        return 0.0

    # Check if equity_curve is a DataFrame (convert to DataFrame if it's a list)
    if isinstance(equity_curve, list):
        # Convert list of dictionaries to DataFrame
        try:
            equity_curve = pd.DataFrame(equity_curve)
            # Set timestamp as index if available
            if 'timestamp' in equity_curve.columns:
                equity_curve.set_index('timestamp', inplace=True)
        except Exception as e:
            warn_key = f"df_conversion_error_{str(e)[:20]}"
            if warn_key not in sharpe_ratio._warning_cache:
                logger.error(f"Failed to convert equity curve to DataFrame: {e}")
                sharpe_ratio._warning_cache.add(warn_key)
            return 0.0

    # Make sure equity column exists
    if 'equity' not in equity_curve.columns:
        # Try full_equity or closed_only_equity if available
        for col in ['full_equity', 'closed_only_equity']:
            if col in equity_curve.columns:
                equity_curve['equity'] = equity_curve[col]
                logger.info(f"Using {col} as equity for Sharpe ratio calculation")
                break
        else:
            warn_key = f"no_equity_column_{','.join(equity_curve.columns)[:30]}"
            if warn_key not in sharpe_ratio._warning_cache:
                logger.warning(f"Equity column not found in equity_curve. Available: {equity_curve.columns}")
                sharpe_ratio._warning_cache.add(warn_key)
            return 0.0

    # Check for constant equity values (flat equity curve)
    if equity_curve['equity'].std() == 0:
        warn_key = "constant_equity"
        if warn_key not in sharpe_ratio._warning_cache:
            logger.warning("Constant equity values detected - Sharpe ratio undefined")
            sharpe_ratio._warning_cache.add(warn_key)
        return 0.0

    # IMPROVED: Check for negative equity values and handle them
    if (equity_curve['equity'] <= 0).any():
        warn_key = "negative_equity"
        if warn_key not in sharpe_ratio._warning_cache:
            logger.warning("Negative equity values detected - using absolute returns instead of log returns")
            sharpe_ratio._warning_cache.add(warn_key)

        # Use simple returns instead of log returns for negative equity
        simple_returns = equity_curve['equity'].pct_change().dropna()
        if len(simple_returns) == 0:
            return 0.0

        # Check if returns data is valid (not all zeros or NaN)
        if simple_returns.std() == 0 or np.isnan(simple_returns.std()):
            warn_key = "zero_std_simple_returns"
            if warn_key not in sharpe_ratio._warning_cache:
                logger.warning("Simple returns have zero standard deviation or contain NaN")
                sharpe_ratio._warning_cache.add(warn_key)
            return 0.0

        # Calculate with simple returns
        daily_rf_rate = risk_free_rate / annualization_factor
        excess_returns = simple_returns - daily_rf_rate
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(annualization_factor)

        # Cap absurdly high values (likely numerical artifacts)
        if abs(sharpe) > 100:
            logger.warning(f"Extreme Sharpe ratio calculated ({sharpe:.2f}), capping at -10 or 10")
            return 10.0 if sharpe > 0 else -10.0

        logger.info(f"Calculated Sharpe ratio with simple returns: {sharpe:.4f}")
        return sharpe

    # Standard calculation with log returns for positive equity curve
    # Calculate log returns
    returns = calculate_log_returns(equity_curve)

    if len(returns) == 0:
        warn_key = "no_log_returns"
        if warn_key not in sharpe_ratio._warning_cache:
            logger.warning("No log returns could be calculated")
            sharpe_ratio._warning_cache.add(warn_key)
        return 0.0

    # Check if returns data is valid (not all zeros or NaN)
    if returns.std() == 0 or np.isnan(returns.std()):
        warn_key = "zero_std_log_returns"
        if warn_key not in sharpe_ratio._warning_cache:
            logger.warning("Log returns have zero standard deviation or contain NaN")
            sharpe_ratio._warning_cache.add(warn_key)
        return 0.0

    # Daily risk-free rate using continuous compounding
    daily_rf_rate = np.log(1 + risk_free_rate) / annualization_factor

    # Calculate annualized Sharpe ratio
    excess_returns = returns - daily_rf_rate
    sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(annualization_factor)

    # IMPROVED: Log detailed calculation values for debugging
    info_key = f"sharpe_{excess_returns.mean():.4f}_{excess_returns.std():.4f}"
    if info_key not in sharpe_ratio._warning_cache:
        logger.info(f"Sharpe calculation: mean_excess={excess_returns.mean():.4f}, "
                  f"std_excess={excess_returns.std():.4f}, "
                  f"sqrt_annual={np.sqrt(annualization_factor):.2f}, "
                  f"sharpe={sharpe:.4f}")
        sharpe_ratio._warning_cache.add(info_key)

    # Cap absurdly high values (likely numerical artifacts)
    if abs(sharpe) > 100:
        logger.warning(f"Extreme Sharpe ratio calculated ({sharpe:.2f}), capping at -10 or 10")
        return 10.0 if sharpe > 0 else -10.0

    return sharpe

def sortino_ratio(equity_curve: pd.DataFrame, trades: List[Dict] = None, 
                 risk_free_rate: float = 0.0, annualization_factor: int = 252, 
                 target_return: float = 0.0) -> float:
    """
    Calculate Sortino ratio using log returns.
    
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
        
    # Calculate log returns
    returns = calculate_log_returns(equity_curve)
    
    if len(returns) == 0:
        return 0.0
        
    # Daily risk-free rate and target rate (continuous compounding)
    daily_rf_rate = np.log(1 + risk_free_rate) / annualization_factor
    daily_target_rate = np.log(1 + target_return) / annualization_factor
    
    # Calculate excess returns
    excess_returns = returns - daily_rf_rate
    
    # Calculate downside deviation (standard deviation of negative excess returns)
    downside_returns = excess_returns[excess_returns < daily_target_rate]
    
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
    
    # Import logging for debugging
    import logging
    logger = logging.getLogger(__name__)
    
    # Create a simple in-memory cache to avoid duplicate warnings
    if not hasattr(max_drawdown, '_warning_cache'):
        max_drawdown._warning_cache = set()
    
    # Ensure equity values are reasonable
    initial_equity = equity_curve['equity'].iloc[0]
    min_equity = equity_curve['equity'].min()
    
    # Handle negative equity values by offsetting 
    if min_equity <= 0:
        warning_key = f"negative_equity_{min_equity:.2f}"
        if warning_key not in max_drawdown._warning_cache:
            logger.warning(f"Negative equity values detected (min={min_equity}). Adjusting for drawdown calculation.")
            max_drawdown._warning_cache.add(warning_key)
            
        offset = abs(min_equity) + 1.0  # Add 1.0 to avoid division by zero
        adjusted_equity = equity_curve['equity'] + offset
        
        # Calculate running maximum and drawdown on adjusted values
        running_max = adjusted_equity.cummax()
        drawdown = (running_max - adjusted_equity) / running_max
    else:
        # Calculate running maximum
        running_max = equity_curve['equity'].cummax()
        
        # Calculate drawdown
        drawdown = (running_max - equity_curve['equity']) / running_max
    
    # Get max drawdown and cap at 1.0 (100%)
    max_dd = drawdown.max()
    
    # Validate max drawdown is between 0 and 1
    if max_dd < 0:
        warning_key = f"negative_max_dd_{max_dd:.4f}"
        if warning_key not in max_drawdown._warning_cache:
            logger.warning(f"Negative max drawdown calculated ({max_dd}). Setting to 0.")
            max_drawdown._warning_cache.add(warning_key)
        max_dd = 0.0
    elif max_dd > 1.0:
        # Log extreme drawdown for diagnostics
        warning_key = f"excessive_max_dd_{max_dd:.4f}"
        if warning_key not in max_drawdown._warning_cache:
            logger.warning(f"Excessive drawdown calculated ({max_dd}). Capping at 1.0 (100%).")
            max_drawdown._warning_cache.add(warning_key)
        max_dd = 1.0
    
    # Add debugging to help diagnose extreme values, but only once per run
    initial_value = equity_curve['equity'].iloc[0]
    final_value = equity_curve['equity'].iloc[-1]
    min_value = equity_curve['equity'].min()
    debug_key = f"drawdown_stats_{initial_value:.2f}_{final_value:.2f}_{min_value:.2f}"
    if debug_key not in max_drawdown._warning_cache:
        logger.info(f"Drawdown stats: Initial={initial_value:.2f}, Final={final_value:.2f}, Min={min_value:.2f}, Max DD={max_dd:.4f}")
        max_drawdown._warning_cache.add(debug_key)
    
    return max_dd

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
        
    # Calculate annualized return (using the improved log-based function)
    annual_ret = annualized_return(equity_curve, trades)
    
    # Calculate maximum drawdown
    max_dd = max_drawdown(equity_curve, trades)
    
    if max_dd == 0:
        return float('inf')  # Avoid division by zero
        
    return annual_ret / max_dd

def win_rate(trades: List[Dict]) -> float:
    """
    Calculate win rate with improved robustness.
    
    Args:
        trades: List of trade records with 'pnl' field
        
    Returns:
        float: Win rate as decimal
    """
    if not trades:
        return 0.0
    
    # Import logging for debugging
    import logging
    logger = logging.getLogger(__name__)
    
    # Create a simple in-memory cache to avoid duplicate warnings
    if not hasattr(win_rate, '_warning_cache'):
        win_rate._warning_cache = set()
    
    # Count valid trades (those with PnL field)
    valid_trades = [t for t in trades if 'pnl' in t and t['pnl'] is not None]
    
    # If no valid trades found, try alternate fields
    if not valid_trades:
        # Try alternate field names like 'realized_pnl'
        valid_trades = [t for t in trades if 'realized_pnl' in t and t['realized_pnl'] is not None]
        # Use the first field we can find
        if valid_trades:
            info_key = "using_realized_pnl_win_rate"
            if info_key not in win_rate._warning_cache:
                logger.info(f"Using 'realized_pnl' instead of 'pnl' for win rate calculation")
                win_rate._warning_cache.add(info_key)
                
            wins = sum(1 for trade in valid_trades if trade.get('realized_pnl', 0) > 0)
            return wins / len(valid_trades)
            
    # If we still have no valid trades
    if not valid_trades:
        warning_key = "no_valid_trades_for_win_rate"
        if warning_key not in win_rate._warning_cache:
            logger.warning(f"No valid trades with PnL found for win rate calculation")
            win_rate._warning_cache.add(warning_key)
        return 0.0
        
    # Standard calculation with valid trades
    wins = sum(1 for trade in valid_trades if trade.get('pnl', 0) > 0)
    
    info_key = f"win_rate_{wins}_{len(valid_trades)}"
    if info_key not in win_rate._warning_cache:
        logger.info(f"Win rate calculation: {wins} wins out of {len(valid_trades)} valid trades")
        win_rate._warning_cache.add(info_key)
        
    return wins / len(valid_trades)

def profit_factor(trades: List[Dict]) -> float:
    """
    Calculate profit factor with improved robustness.
    
    Args:
        trades: List of trade records with 'pnl' field
        
    Returns:
        float: Profit factor (gross_profit / gross_loss)
    """
    if not trades:
        return 0.0
        
    # Import logging for debugging
    import logging
    logger = logging.getLogger(__name__)
    
    # Create a simple in-memory cache to avoid duplicate warnings
    if not hasattr(profit_factor, '_warning_cache'):
        profit_factor._warning_cache = set()
    
    # IMPROVED: Filter only completed trades with valid PnL
    valid_trades = [t for t in trades if 'pnl' in t and t['pnl'] is not None and t.get('closed', True)]
    
    # If no valid trades found, try alternate fields
    if not valid_trades:
        # Try alternate field names like 'realized_pnl'
        valid_trades = [t for t in trades if 'realized_pnl' in t and t['realized_pnl'] is not None and t.get('closed', True)]
        # Use the first field we can find
        if valid_trades:
            info_key = "using_realized_pnl"
            if info_key not in profit_factor._warning_cache:
                logger.info(f"Using 'realized_pnl' instead of 'pnl' for profit factor calculation")
                profit_factor._warning_cache.add(info_key)
                
            gross_profit = sum(trade.get('realized_pnl', 0) for trade in valid_trades if trade.get('realized_pnl', 0) > 0)
            gross_loss = abs(sum(trade.get('realized_pnl', 0) for trade in valid_trades if trade.get('realized_pnl', 0) < 0))
            
            # Calculate total PnL for consistency check
            total_pnl = sum(trade.get('realized_pnl', 0) for trade in valid_trades)
            
            if gross_loss == 0:
                return float('inf') if gross_profit > 0 else 0.0
            return gross_profit / gross_loss
    
    # If we still have no valid trades
    if not valid_trades:
        warning_key = "no_valid_trades_for_profit_factor"
        if warning_key not in profit_factor._warning_cache:
            logger.warning(f"No valid trades with PnL found for profit factor calculation")
            profit_factor._warning_cache.add(warning_key)
        return 0.0
    
    # IMPROVED: Calculate gross profit and loss, including zero PnL trades
    # This ensures all closed trades are counted properly
    gross_profit = sum(max(0, trade.get('pnl', 0)) for trade in valid_trades)
    gross_loss = abs(sum(min(0, trade.get('pnl', 0)) for trade in valid_trades))
    
    # Calculate total PnL for consistency check
    total_pnl = sum(trade.get('pnl', 0) for trade in valid_trades)
    
    # Add debugging to check for imbalanced values - log only once for similar values 
    total_trades = len(valid_trades)
    winning_trades = sum(1 for t in valid_trades if t.get('pnl', 0) > 0)
    losing_trades = sum(1 for t in valid_trades if t.get('pnl', 0) < 0)
    trades_with_zero_pnl = sum(1 for t in valid_trades if t.get('pnl', 0) == 0)
    
    info_key = f"trade_stats_{total_trades}_{winning_trades}_{losing_trades}"
    if info_key not in profit_factor._warning_cache:
        logger.info(f"Valid trades: {total_trades}, Winners: {winning_trades}, Losers: {losing_trades}")
        logger.info(f"Profit factor calculation: gross profit={gross_profit:.2f}, gross loss={gross_loss:.2f}")
        logger.info(f"Total PnL: {total_pnl:.2f}, Trades with zero PnL: {trades_with_zero_pnl}")
        profit_factor._warning_cache.add(info_key)
    
    # IMPROVED: Check for inconsistency between total PnL and gross profit minus loss
    pnl_diff = abs(total_pnl - (gross_profit - gross_loss))
    if pnl_diff > 0.01:  # More than 1 cent difference
        warning_key = f"pnl_inconsistency_{pnl_diff:.2f}"
        if warning_key not in profit_factor._warning_cache:
            logger.warning(f"PnL inconsistency detected: total_pnl={total_pnl:.2f} but profit-loss={gross_profit-gross_loss:.2f}")
            profit_factor._warning_cache.add(warning_key)
    
    # Sanity check - if gross profit and loss are very imbalanced with many trades
    if total_trades > 10 and gross_profit > 0 and gross_loss > 0:
        ratio = gross_profit / gross_loss
        if ratio > 100:
            warning_key = f"high_profit_factor_{ratio:.2f}"
            if warning_key not in profit_factor._warning_cache:
                logger.warning(f"Extremely high profit factor detected ({ratio:.2f}). Capping at 100.")
                profit_factor._warning_cache.add(warning_key)
            return 100.0
        
        # IMPROVED: Check for return and profit factor consistency
        if (total_pnl > 0 and ratio < 1) or (total_pnl < 0 and ratio > 1):
            warning_key = f"profit_factor_inconsistency_{total_pnl:.2f}_{ratio:.2f}"
            if warning_key not in profit_factor._warning_cache:
                logger.warning(f"Inconsistency between total PnL ({total_pnl:.2f}) and profit factor ({ratio:.2f})")
                profit_factor._warning_cache.add(warning_key)
    
    if gross_loss < 0.001:  # Use a small epsilon to avoid division by zero
        if gross_profit > 0:
            warning_key = "no_losing_trades"
            if warning_key not in profit_factor._warning_cache:
                logger.warning("No losing trades detected, capping profit factor at 100")
                profit_factor._warning_cache.add(warning_key)
            return 100.0
        return 0.0
        
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

def logarithmic_returns_statistics(equity_curve: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate various statistics on logarithmic returns.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        
    Returns:
        Dict with return statistics
    """
    if len(equity_curve) < 2:
        return {'mean_log_return': 0.0, 'volatility': 0.0, 'skewness': 0.0, 'kurtosis': 0.0}
    
    log_returns = calculate_log_returns(equity_curve)
    
    if len(log_returns) == 0:
        return {'mean_log_return': 0.0, 'volatility': 0.0, 'skewness': 0.0, 'kurtosis': 0.0}
    
    # Calculate statistics
    mean_return = log_returns.mean()
    volatility = log_returns.std()
    skewness = log_returns.skew() if hasattr(log_returns, 'skew') else 0.0
    kurtosis = log_returns.kurtosis() if hasattr(log_returns, 'kurtosis') else 0.0
    
    return {
        'mean_log_return': mean_return,
        'volatility': volatility,
        'skewness': skewness,
        'kurtosis': kurtosis
    }

def calculate_all_metrics(equity_curve: pd.DataFrame, trades: List[Dict] = None) -> Dict[str, Any]:
    """
    Calculate all performance metrics using improved log return methods.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        trades: Optional list of trades
        
    Returns:
        Dict with all metrics
    """
    # Import logging for debugging
    import logging
    logger = logging.getLogger(__name__)
    
    # Create a simple in-memory cache to avoid duplicate warnings
    if not hasattr(calculate_all_metrics, '_warning_cache'):
        calculate_all_metrics._warning_cache = set()
    
    if equity_curve is None or not isinstance(equity_curve, pd.DataFrame) or equity_curve.empty:
        warning_key = "no_equity_curve"
        if warning_key not in calculate_all_metrics._warning_cache:
            logger.warning("No equity curve data available for metrics calculation")
            calculate_all_metrics._warning_cache.add(warning_key)
        return {'warning': 'No equity curve data available'}

    # Ensure trades is a list, not None
    if trades is None:
        trades = []
        warning_key = "no_trades"
        if warning_key not in calculate_all_metrics._warning_cache:
            logger.warning("No trades provided for metrics calculation")
            calculate_all_metrics._warning_cache.add(warning_key)

    # Log trade info for debugging once per equity curve size + trade count 
    # to prevent duplicate logs for repeated calculations on same dataset
    info_key = f"metrics_calc_{len(trades)}_{len(equity_curve)}"
    if info_key not in calculate_all_metrics._warning_cache:
        logger.info(f"Calculating metrics for {len(trades)} trades and {len(equity_curve)} equity points")
        calculate_all_metrics._warning_cache.add(info_key)
    
    # Calculate primary metrics
    try:
        metrics = {
            'total_return': total_return(equity_curve, trades),
            'annualized_return': annualized_return(equity_curve, trades),
            'sharpe_ratio': sharpe_ratio(equity_curve, trades),
            'sortino_ratio': sortino_ratio(equity_curve, trades),
            'max_drawdown': max_drawdown(equity_curve, trades),
            'calmar_ratio': calmar_ratio(equity_curve, trades)
        }
    except Exception as e:
        logger.error(f"Error calculating primary metrics: {e}")
        metrics = {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'calmar_ratio': 0.0
        }
    
    # Add log return statistics with error handling
    try:
        metrics.update(logarithmic_returns_statistics(equity_curve))
    except Exception as e:
        logger.error(f"Error calculating log returns statistics: {e}")
    
    # Add trade-specific metrics if trades are provided and non-empty
    if trades and len(trades) > 0:
        try:
            # Add trade counts regardless of errors elsewhere - FORCE COUNT ALL TRADES
            metrics['trade_count'] = len(trades)
            logger.info(f"Setting trade_count metric to {len(trades)} total trades")
            
            # Validate trade data - do we have PnL fields?
            pnl_count = sum(1 for t in trades if 'pnl' in t and t['pnl'] is not None)
            if pnl_count > 0:
                # Calculate win rate and profit factor
                metrics.update({
                    'win_rate': win_rate(trades),
                    'profit_factor': profit_factor(trades)
                })
                
                # Add average trade metrics
                metrics.update(average_trade(trades))
            else:
                logger.warning(f"No valid PnL fields found in trades, using zero for trade metrics")
                metrics.update({
                    'win_rate': 0.0,
                    'profit_factor': 0.0,
                    'avg_trade': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'win_loss_ratio': 0.0
                })
        except Exception as e:
            logger.error(f"Error calculating trade metrics: {e}")
    else:
        logger.warning("No valid trades for trade metrics calculation")
        # Add placeholders for trade metrics
        metrics.update({
            'trade_count': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_trade': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'win_loss_ratio': 0.0
        })
    
    # Add drawdown statistics with error handling
    try:
        metrics.update(drawdown_stats(equity_curve))
    except Exception as e:
        logger.error(f"Error calculating drawdown statistics: {e}")
    
    return metrics
