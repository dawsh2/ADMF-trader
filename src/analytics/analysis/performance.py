"""
Performance analyzer for financial strategies.

This module provides a comprehensive performance analysis for trading strategies
by combining various metrics and producing detailed reports.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
import json
import logging

# Import metrics modules
from ..metrics.core import (
    total_return, annualized_return, cagr, 
    volatility, drawdowns, max_drawdown, drawdown_stats,
    simple_returns, log_returns
)
from ..metrics.ratios import (
    sharpe_ratio, sortino_ratio, calmar_ratio, 
    omega_ratio, information_ratio, treynor_ratio
)
from ..metrics.trade import (
    trade_stats, profit_factor, win_rate, 
    expectancy, consecutive_wins_losses, average_holding_period,
    trade_pnl_distribution, trade_by_time_analysis
)

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Comprehensive performance analyzer for trading strategies.
    
    This class combines various metrics to provide a detailed analysis of
    trading strategy performance, including returns, risk-adjusted metrics,
    and trade statistics.
    """
    
    def __init__(self, 
                equity_curve: Optional[pd.DataFrame] = None, 
                trades: Optional[List[Dict[str, Any]]] = None,
                benchmark: Optional[pd.DataFrame] = None):
        """
        Initialize the performance analyzer.
        
        Args:
            equity_curve: DataFrame with at least 'equity' and 'date' columns
            trades: List of trade dictionaries
            benchmark: Optional benchmark equity curve for comparison
        """
        self.equity_curve = equity_curve
        self.trades = trades or []
        self.benchmark = benchmark
        self.metrics = {}
        self.return_series = None
        self.benchmark_returns = None
        
        # Initialize if data is provided
        if self.equity_curve is not None:
            self._prepare_return_series()
    
    def set_equity_curve(self, equity_curve: pd.DataFrame) -> None:
        """
        Set or update the equity curve.
        
        Args:
            equity_curve: DataFrame with at least 'equity' and 'date' columns
        """
        self.equity_curve = equity_curve
        self._prepare_return_series()
    
    def set_trades(self, trades: List[Dict[str, Any]]) -> None:
        """
        Set or update the trades list.
        
        Args:
            trades: List of trade dictionaries
        """
        self.trades = trades
    
    def set_benchmark(self, benchmark: pd.DataFrame) -> None:
        """
        Set or update the benchmark equity curve.
        
        Args:
            benchmark: Benchmark equity curve for comparison
        """
        self.benchmark = benchmark
        self._prepare_benchmark_returns()
    
    def _prepare_return_series(self) -> None:
        """Prepare return series from equity curve."""
        if self.equity_curve is None or not isinstance(self.equity_curve, pd.DataFrame):
            self.return_series = None
            return
            
        if self.equity_curve.empty or 'equity' not in self.equity_curve.columns:
            self.return_series = None
            return
        
        # Calculate returns
        try:
            self.simple_returns = simple_returns(self.equity_curve, column='equity')
            self.log_returns = log_returns(self.equity_curve, column='equity')
            self.return_series = self.log_returns  # Default to log returns
        except Exception as e:
            logger.error(f"Error calculating returns: {e}")
            self.return_series = None
    
    def _prepare_benchmark_returns(self) -> None:
        """Prepare benchmark return series."""
        if self.benchmark is None or not isinstance(self.benchmark, pd.DataFrame):
            self.benchmark_returns = None
            return
            
        if self.benchmark.empty or 'equity' not in self.benchmark.columns:
            self.benchmark_returns = None
            return
        
        # Calculate benchmark returns
        try:
            self.benchmark_returns = log_returns(self.benchmark, column='equity')
        except Exception as e:
            logger.error(f"Error calculating benchmark returns: {e}")
            self.benchmark_returns = None
    
    def calculate_return_metrics(self, 
                               risk_free_rate: float = 0.0, 
                               periods_per_year: int = 252) -> Dict[str, float]:
        """
        Calculate return-based metrics.
        
        Args:
            risk_free_rate: Annualized risk-free rate (default: 0.0)
            periods_per_year: Number of periods in a year (default: 252 for trading days)
            
        Returns:
            Dict of return metrics
        """
        if self.equity_curve is None or not isinstance(self.equity_curve, pd.DataFrame):
            return {}
            
        if self.equity_curve.empty or 'equity' not in self.equity_curve.columns:
            return {}
        
        try:
            metrics = {}
            
            # Basic return metrics
            metrics['total_return'] = total_return(self.equity_curve, column='equity')
            metrics['annualized_return'] = annualized_return(
                self.equity_curve, 
                column='equity', 
                periods_per_year=periods_per_year
            )
            
            # Calculate CAGR if date column exists
            if 'date' in self.equity_curve.columns:
                metrics['cagr'] = cagr(self.equity_curve, column='equity', date_column='date')
            
            # Risk metrics
            if self.return_series is not None and not self.return_series.empty:
                metrics['volatility'] = volatility(self.return_series, annualization_factor=periods_per_year)
                
                # Risk-adjusted return metrics
                metrics['sharpe_ratio'] = sharpe_ratio(
                    self.return_series, 
                    risk_free_rate=risk_free_rate, 
                    annualization_factor=periods_per_year
                )
                metrics['sortino_ratio'] = sortino_ratio(
                    self.return_series, 
                    risk_free_rate=risk_free_rate, 
                    annualization_factor=periods_per_year
                )
                metrics['calmar_ratio'] = calmar_ratio(
                    self.equity_curve, 
                    column='equity', 
                    periods_per_year=periods_per_year
                )
                metrics['omega_ratio'] = omega_ratio(
                    self.return_series, 
                    threshold=risk_free_rate/periods_per_year
                )
            
            # Drawdown metrics
            dd_stats = drawdown_stats(self.equity_curve, column='equity')
            metrics.update(dd_stats)
            
            # Benchmark comparison if available
            if self.benchmark_returns is not None and not self.benchmark_returns.empty:
                metrics['alpha'] = self._calculate_alpha(risk_free_rate, periods_per_year)
                metrics['beta'] = self._calculate_beta()
                metrics['information_ratio'] = information_ratio(
                    self.return_series, 
                    self.benchmark_returns, 
                    annualization_factor=periods_per_year
                )
                metrics['treynor_ratio'] = treynor_ratio(
                    self.return_series, 
                    self.benchmark_returns, 
                    risk_free_rate=risk_free_rate, 
                    annualization_factor=periods_per_year
                )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating return metrics: {e}")
            return {}
    
    def calculate_trade_metrics(self) -> Dict[str, Any]:
        """
        Calculate trade-based metrics.
        
        Returns:
            Dict of trade metrics
        """
        if not self.trades:
            return {}
        
        try:
            metrics = {}
            
            # Basic trade statistics
            metrics.update(trade_stats(self.trades))
            
            # Additional trade metrics
            metrics['profit_factor'] = profit_factor(self.trades)
            metrics['win_rate'] = win_rate(self.trades)
            metrics['expectancy'] = expectancy(self.trades)
            
            # Trade patterns
            metrics['consecutive_stats'] = consecutive_wins_losses(self.trades)
            
            # Time-based analysis
            metrics['avg_holding_period'] = average_holding_period(self.trades)
            metrics['time_analysis'] = trade_by_time_analysis(self.trades)
            
            # Distribution analysis
            metrics['pnl_distribution'] = trade_pnl_distribution(self.trades)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating trade metrics: {e}")
            return {}
    
    def _calculate_alpha(self, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
        """
        Calculate Jensen's Alpha.
        
        Args:
            risk_free_rate: Annualized risk-free rate
            periods_per_year: Number of periods in a year
            
        Returns:
            float: Alpha value
        """
        if (self.return_series is None or 
            self.benchmark_returns is None or 
            self.return_series.empty or 
            self.benchmark_returns.empty):
            return 0.0
        
        # Align series
        common_index = self.return_series.index.intersection(self.benchmark_returns.index)
        if len(common_index) < 2:
            return 0.0
            
        strategy_returns = self.return_series.loc[common_index]
        benchmark_returns = self.benchmark_returns.loc[common_index]
        
        # Calculate beta
        beta = self._calculate_beta()
        
        # Calculate daily risk-free rate
        daily_rfr = risk_free_rate / periods_per_year
        
        # Calculate alpha
        alpha = (strategy_returns.mean() - daily_rfr) - beta * (benchmark_returns.mean() - daily_rfr)
        
        # Annualize alpha
        annualized_alpha = alpha * periods_per_year
        
        return annualized_alpha
    
    def _calculate_beta(self) -> float:
        """
        Calculate beta (market risk).
        
        Returns:
            float: Beta value
        """
        if (self.return_series is None or 
            self.benchmark_returns is None or 
            self.return_series.empty or 
            self.benchmark_returns.empty):
            return 0.0
        
        # Align series
        common_index = self.return_series.index.intersection(self.benchmark_returns.index)
        if len(common_index) < 2:
            return 0.0
            
        strategy_returns = self.return_series.loc[common_index]
        benchmark_returns = self.benchmark_returns.loc[common_index]
        
        # Calculate covariance matrix
        cov_matrix = np.cov(strategy_returns, benchmark_returns)
        
        # Extract beta (covariance / variance)
        if cov_matrix[1, 1] != 0:
            beta = cov_matrix[0, 1] / cov_matrix[1, 1]
        else:
            beta = 0.0
        
        return beta
    
    def analyze_performance(self, 
                          risk_free_rate: float = 0.0, 
                          periods_per_year: int = 252) -> Dict[str, Any]:
        """
        Perform a comprehensive performance analysis.
        
        Args:
            risk_free_rate: Annualized risk-free rate (default: 0.0)
            periods_per_year: Number of periods in a year (default: 252 for trading days)
            
        Returns:
            Dict containing all performance metrics
        """
        self.metrics = {}
        
        # Calculate return-based metrics
        return_metrics = self.calculate_return_metrics(
            risk_free_rate=risk_free_rate,
            periods_per_year=periods_per_year
        )
        self.metrics.update(return_metrics)
        
        # Calculate trade-based metrics if trades are available
        if self.trades:
            trade_metrics = self.calculate_trade_metrics()
            self.metrics['trade_metrics'] = trade_metrics
        
        return self.metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert analyzer and results to a dictionary representation.
        
        Returns:
            Dict representation of the analyzer
        """
        return {
            'metrics': self.metrics,
            'has_equity_curve': self.equity_curve is not None and not self.equity_curve.empty,
            'has_trades': bool(self.trades),
            'has_benchmark': self.benchmark is not None and not self.benchmark.empty,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def to_json(self, filepath: Optional[str] = None) -> str:
        """
        Convert analyzer results to JSON.
        
        Args:
            filepath: Optional file path to save JSON output
            
        Returns:
            str: JSON representation of the analyzer
        """
        data = self.to_dict()
        
        # Convert non-serializable objects
        def json_serialize(obj):
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        # Convert to JSON
        json_data = json.dumps(data, default=json_serialize, indent=2)
        
        # Save to file if filepath provided
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    f.write(json_data)
            except Exception as e:
                logger.error(f"Error saving JSON to file {filepath}: {e}")
        
        return json_data