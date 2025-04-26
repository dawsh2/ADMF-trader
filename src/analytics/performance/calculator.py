# src/core/analytics/performance/calculator.py
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Union
from collections import defaultdict

# Import functional metrics - assuming we're importing from the improved functional.py
from ..metrics.functional import (
    total_return, annualized_return, sharpe_ratio, sortino_ratio,
    max_drawdown, calmar_ratio, win_rate, profit_factor,
    average_trade, drawdown_stats, calculate_all_metrics,
    calculate_log_returns, logarithmic_returns_statistics
)

class PerformanceCalculator:
    """Performance calculator using log-based functional metrics."""
    
    def __init__(self, equity_curve=None, trades=None):
        """
        Initialize the performance calculator.
        
        Args:
            equity_curve: DataFrame with 'equity' column
            trades: List of trade records
        """
        self.equity_curve = equity_curve
        self.trades = trades or []
        self.metric_functions = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'log_returns_stats': logarithmic_returns_statistics
        }
        self.metric_params = {
            # Default parameters for metrics
            'sharpe_ratio': {'risk_free_rate': 0.0, 'annualization_factor': 252},
            'sortino_ratio': {'risk_free_rate': 0.0, 'annualization_factor': 252, 'target_return': 0.0},
            'calmar_ratio': {'years': 3}
        }
    
    def set_equity_curve(self, equity_curve):
        """Set equity curve."""
        self.equity_curve = equity_curve
    
    def set_trades(self, trades):
        """Set trades."""
        self.trades = trades
    
    def add_metric_function(self, name, function, params=None):
        """
        Add a metric function.
        
        Args:
            name: Metric name
            function: Metric calculation function
            params: Optional parameters for the function
        """
        self.metric_functions[name] = function
        if params:
            self.metric_params[name] = params
    
    def set_metric_param(self, metric_name, param_name, param_value):
        """
        Set a parameter for a specific metric.
        
        Args:
            metric_name: Name of the metric
            param_name: Parameter name
            param_value: Parameter value
        """
        if metric_name not in self.metric_params:
            self.metric_params[metric_name] = {}
        self.metric_params[metric_name][param_name] = param_value
    
    def calculate_metrics(self, metrics_to_calculate=None):
        """
        Calculate selected metrics.
        
        Args:
            metrics_to_calculate: List of metric names to calculate (None for all)
            
        Returns:
            dict: Metric name -> value
        """
        if self.equity_curve is None or len(self.equity_curve) == 0:
            return {}
            
        if metrics_to_calculate is None:
            metrics_to_calculate = list(self.metric_functions.keys())
            
        results = {}
        
        for metric_name in metrics_to_calculate:
            if metric_name in self.metric_functions:
                try:
                    # Get metric function and any parameters
                    metric_func = self.metric_functions[metric_name]
                    params = self.metric_params.get(metric_name, {})
                    
                    # Call metric function with parameters
                    if metric_name in ['win_rate', 'profit_factor'] and not self.trades:
                        # Skip trade-specific metrics if no trades
                        continue
                    else:
                        value = metric_func(self.equity_curve, self.trades, **params)
                        
                    # Store result
                    if isinstance(value, dict):
                        results.update(value)
                    else:
                        results[metric_name] = value
                except Exception as e:
                    print(f"Error calculating {metric_name}: {e}")
            
        # Add composite metrics
        if 'average_trade' not in results and self.trades:
            avg_metrics = average_trade(self.trades)
            results.update(avg_metrics)
            
        if 'drawdown_stats' not in results:
            dd_metrics = drawdown_stats(self.equity_curve)
            results.update(dd_metrics)
            
        return results

    def calculate_all_metrics(self):
        """
        Calculate all available metrics using log returns.
        
        Returns:
            dict: All metrics
        """
        if self.equity_curve is None or not isinstance(self.equity_curve, pd.DataFrame) or len(self.equity_curve) == 0:
            return {'warning': 'No equity curve data available'}
        
        # Use the improved calculate_all_metrics that uses log returns
        return calculate_all_metrics(self.equity_curve, self.trades)
    
    def get_returns(self):
        """
        Get percentage return series.
        
        Returns:
            Series: Percentage return series
        """
        if self.equity_curve is None or len(self.equity_curve) == 0:
            return pd.Series()
            
        return self.equity_curve['equity'].pct_change().dropna()
    
    def get_log_returns(self):
        """
        Get logarithmic return series.
        
        Returns:
            Series: Logarithmic return series
        """
        if self.equity_curve is None or len(self.equity_curve) == 0:
            return pd.Series()
            
        return calculate_log_returns(self.equity_curve)
    
    def get_drawdowns(self):
        """
        Get drawdown series.
        
        Returns:
            Series: Drawdown series
        """
        if self.equity_curve is None or len(self.equity_curve) == 0:
            return pd.Series()
            
        running_max = self.equity_curve['equity'].cummax()
        drawdown = (running_max - self.equity_curve['equity']) / running_max
        
        return drawdown
    
    def analyze_returns(self):
        """
        Analyze return characteristics using log returns.
        
        Returns:
            dict: Return statistics
        """
        if self.equity_curve is None or len(self.equity_curve) == 0:
            return {}
        
        # Calculate log returns
        log_returns = calculate_log_returns(self.equity_curve)
        
        if len(log_returns) == 0:
            return {}
        
        # Calculate basic statistics
        stats = {
            'mean_log_return': log_returns.mean(),
            'volatility': log_returns.std(),
            'skewness': log_returns.skew() if hasattr(log_returns, 'skew') else 0.0,
            'kurtosis': log_returns.kurtosis() if hasattr(log_returns, 'kurtosis') else 0.0,
            'annualized_return': annualized_return(self.equity_curve)
        }
        
        # Calculate rolling metrics if enough data
        if len(log_returns) > 20:
            # Rolling volatility (20-day)
            rolling_vol = log_returns.rolling(window=20).std() * np.sqrt(252)
            stats['current_volatility'] = rolling_vol.iloc[-1] if not rolling_vol.empty else stats['volatility']
            
            # Rolling Sharpe (20-day)
            rolling_sharpe = (log_returns.rolling(window=20).mean() * 252) / (log_returns.rolling(window=20).std() * np.sqrt(252))
            stats['current_sharpe'] = rolling_sharpe.iloc[-1] if not rolling_sharpe.empty else 0.0
        
        return stats
    
    def analyze_trades(self):
        """
        Analyze trades.
        
        Returns:
            dict: Trade statistics
        """
        if not self.trades:
            return {}
            
        # Get statistics using functional approach
        trade_stats = {
            'win_rate': win_rate(self.trades),
            'profit_factor': profit_factor(self.trades)
        }
        
        # Add average trade metrics
        trade_stats.update(average_trade(self.trades))
        
        # Add additional statistics
        trade_stats['total_trades'] = len(self.trades)
        trade_stats['total_pnl'] = sum(trade.get('pnl', 0) for trade in self.trades)
        
        return trade_stats
