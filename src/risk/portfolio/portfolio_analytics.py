"""
Portfolio analytics for performance measurement and risk analysis.

This module provides classes and functions for analyzing portfolio performance,
calculating risk metrics, and generating performance reports.
"""
import datetime
import math
import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

class PortfolioAnalytics:
    """
    Analytics for portfolio performance and risk measurement.
    
    Key features:
    - Calculate portfolio metrics (Sharpe, Sortino, etc.)
    - Analyze drawdowns
    - Calculate correlation matrix
    - Calculate beta and other risk metrics
    - Generate portfolio snapshots
    """
    
    def __init__(self, portfolio_manager):
        """
        Initialize portfolio analytics.
        
        Args:
            portfolio_manager: Portfolio manager instance
        """
        self.portfolio_manager = portfolio_manager
        self.metrics_cache = {}
        self.drawdown_cache = None
        self.last_update = None
    
    def calculate_returns(self, frequency: str = 'D') -> pd.Series:
        """
        Calculate return series from equity curve.
        
        Args:
            frequency: Resampling frequency ('D' for daily, etc.)
            
        Returns:
            Series with returns
        """
        # Get equity curve
        equity_df = self.portfolio_manager.get_equity_curve_df()
        
        if equity_df.empty:
            return pd.Series()
        
        # Resample if needed
        if frequency and frequency != 'native':
            equity_df = equity_df.resample(frequency).last().fillna(method='ffill')
        
        # Calculate returns
        returns = equity_df['equity'].pct_change().fillna(0)
        
        return returns
    
    def calculate_metrics(self, risk_free_rate: float = 0.0) -> Dict[str, float]:
        """
        Calculate portfolio performance metrics.
        
        Args:
            risk_free_rate: Annual risk-free rate (decimal)
            
        Returns:
            Dict with performance metrics
        """
        # Check cache
        cache_key = f"metrics_{risk_free_rate}"
        if cache_key in self.metrics_cache and self.last_update == len(self.portfolio_manager.equity_curve):
            return self.metrics_cache[cache_key]
        
        # Update cache timestamp
        self.last_update = len(self.portfolio_manager.equity_curve)
        
        # Get returns
        returns = self.calculate_returns()
        
        if returns.empty:
            return {
                'total_return': 0.0,
                'cagr': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0
            }
        
        # Calculate total return
        initial_equity = self.portfolio_manager.initial_cash
        final_equity = self.portfolio_manager.equity
        total_return = (final_equity / initial_equity) - 1.0
        
        # Calculate CAGR
        start_date = self.portfolio_manager.equity_curve[0]['timestamp']
        end_date = self.portfolio_manager.equity_curve[-1]['timestamp']
        years = (end_date - start_date).days / 365.25
        cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
        
        # Calculate volatility (annualized)
        trading_days_per_year = 252
        volatility = returns.std() * math.sqrt(trading_days_per_year)
        
        # Calculate Sharpe ratio
        daily_risk_free = (1 + risk_free_rate) ** (1 / trading_days_per_year) - 1
        excess_returns = returns - daily_risk_free
        sharpe_ratio = excess_returns.mean() / returns.std() * math.sqrt(trading_days_per_year) if returns.std() > 0 else 0.0
        
        # Calculate Sortino ratio
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * math.sqrt(trading_days_per_year) if len(downside_returns) > 0 else 0.0
        sortino_ratio = excess_returns.mean() / downside_deviation * math.sqrt(trading_days_per_year) if downside_deviation > 0 else 0.0
        
        # Calculate max drawdown
        equity_series = pd.Series([point['equity'] for point in self.portfolio_manager.equity_curve],
                                index=[point['timestamp'] for point in self.portfolio_manager.equity_curve])
        running_max = equity_series.cummax()
        drawdown = (equity_series / running_max) - 1.0
        max_drawdown = abs(drawdown.min())
        
        # Calculate win rate and profit factor
        closed_trades = self.portfolio_manager.get_closed_trades()
        if closed_trades:
            winning_trades = [trade for trade in closed_trades if trade['realized_pnl'] > 0]
            losing_trades = [trade for trade in closed_trades if trade['realized_pnl'] < 0]
            
            win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0.0
            
            gross_profit = sum(trade['realized_pnl'] for trade in winning_trades)
            gross_loss = abs(sum(trade['realized_pnl'] for trade in losing_trades))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        else:
            win_rate = 0.0
            profit_factor = 0.0
        
        # Assemble metrics
        metrics = {
            'total_return': total_return,
            'cagr': cagr,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'equity': final_equity,
            'initial_equity': initial_equity,
            'trades': len(closed_trades),
            'average_trade': total_return / len(closed_trades) if closed_trades else 0.0
        }
        
        # Update cache
        self.metrics_cache[cache_key] = metrics
        
        return metrics
    
    def analyze_drawdowns(self, threshold: float = 0.0) -> List[Dict]:
        """
        Analyze portfolio drawdowns.
        
        Args:
            threshold: Minimum drawdown threshold to include (decimal)
            
        Returns:
            List of drawdown periods
        """
        # Check cache
        if self.drawdown_cache is not None and self.last_update == len(self.portfolio_manager.equity_curve):
            # Filter by threshold
            return [dd for dd in self.drawdown_cache if dd['depth'] >= threshold]
        
        # Update cache timestamp
        self.last_update = len(self.portfolio_manager.equity_curve)
        
        # Get equity curve
        equity_df = self.portfolio_manager.get_equity_curve_df()
        
        if equity_df.empty:
            self.drawdown_cache = []
            return []
        
        # Calculate drawdown series
        equity_series = equity_df['equity']
        running_max = equity_series.cummax()
        drawdown = (equity_series / running_max) - 1.0
        
        # Find drawdown periods
        in_drawdown = False
        drawdown_periods = []
        current_period = {}
        
        for i, (timestamp, value) in enumerate(drawdown.items()):
            if value < -0.0001 and not in_drawdown:  # Start of drawdown
                in_drawdown = True
                current_period = {
                    'start_date': timestamp,
                    'start_equity': running_max[timestamp],
                    'start_index': i
                }
            elif value >= -0.0001 and in_drawdown:  # End of drawdown
                in_drawdown = False
                current_period['end_date'] = timestamp
                current_period['end_equity'] = equity_series[timestamp]
                current_period['end_index'] = i
                current_period['duration'] = (current_period['end_date'] - current_period['start_date']).days
                
                # Find lowest point
                lowest_idx = drawdown[current_period['start_index']:current_period['end_index']+1].idxmin()
                current_period['lowest_date'] = lowest_idx
                current_period['lowest_equity'] = equity_series[lowest_idx]
                current_period['depth'] = abs(drawdown[lowest_idx])
                current_period['recovery_time'] = (current_period['end_date'] - current_period['lowest_date']).days
                
                drawdown_periods.append(current_period)
                current_period = {}
        
        # Handle ongoing drawdown
        if in_drawdown:
            current_period['end_date'] = equity_series.index[-1]
            current_period['end_equity'] = equity_series.iloc[-1]
            current_period['end_index'] = len(equity_series) - 1
            current_period['duration'] = (current_period['end_date'] - current_period['start_date']).days
            
            # Find lowest point
            lowest_idx = drawdown[current_period['start_index']:current_period['end_index']+1].idxmin()
            current_period['lowest_date'] = lowest_idx
            current_period['lowest_equity'] = equity_series[lowest_idx]
            current_period['depth'] = abs(drawdown[lowest_idx])
            current_period['recovery_time'] = (current_period['end_date'] - current_period['lowest_date']).days
            current_period['ongoing'] = True
            
            drawdown_periods.append(current_period)
        
        # Sort by depth
        drawdown_periods.sort(key=lambda x: x['depth'], reverse=True)
        
        # Update cache
        self.drawdown_cache = drawdown_periods
        
        # Filter by threshold
        return [dd for dd in drawdown_periods if dd['depth'] >= threshold]
    
    def calculate_correlation_matrix(self, returns_dict: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Calculate correlation matrix between portfolio and other instruments.
        
        Args:
            returns_dict: Dict mapping names to return series
            
        Returns:
            DataFrame with correlation matrix
        """
        # Get portfolio returns
        portfolio_returns = self.calculate_returns()
        
        if portfolio_returns.empty:
            return pd.DataFrame()
        
        # Combine all returns
        all_returns = {'Portfolio': portfolio_returns}
        all_returns.update(returns_dict)
        
        # Create DataFrame
        returns_df = pd.DataFrame(all_returns)
        
        # Calculate correlation matrix
        corr_matrix = returns_df.corr()
        
        return corr_matrix
    
    def calculate_beta(self, benchmark_returns: pd.Series) -> float:
        """
        Calculate portfolio beta relative to benchmark.
        
        Args:
            benchmark_returns: Benchmark return series
            
        Returns:
            float: Beta value
        """
        # Get portfolio returns
        portfolio_returns = self.calculate_returns()
        
        if portfolio_returns.empty or benchmark_returns.empty:
            return 0.0
        
        # Align series
        portfolio_returns, benchmark_returns = portfolio_returns.align(benchmark_returns, join='inner')
        
        if len(portfolio_returns) < 2:
            return 0.0
        
        # Calculate beta
        covariance = portfolio_returns.cov(benchmark_returns)
        variance = benchmark_returns.var()
        
        if variance == 0:
            return 0.0
            
        beta = covariance / variance
        
        return beta
    
    def calculate_alpha(self, benchmark_returns: pd.Series, risk_free_rate: float = 0.0) -> float:
        """
        Calculate portfolio alpha relative to benchmark.
        
        Args:
            benchmark_returns: Benchmark return series
            risk_free_rate: Annual risk-free rate (decimal)
            
        Returns:
            float: Alpha value (annualized)
        """
        # Get portfolio returns
        portfolio_returns = self.calculate_returns()
        
        if portfolio_returns.empty or benchmark_returns.empty:
            return 0.0
        
        # Align series
        portfolio_returns, benchmark_returns = portfolio_returns.align(benchmark_returns, join='inner')
        
        if len(portfolio_returns) < 2:
            return 0.0
        
        # Calculate beta
        beta = self.calculate_beta(benchmark_returns)
        
        # Calculate alpha
        trading_days_per_year = 252
        daily_risk_free = (1 + risk_free_rate) ** (1 / trading_days_per_year) - 1
        
        portfolio_return = portfolio_returns.mean() * trading_days_per_year
        benchmark_return = benchmark_returns.mean() * trading_days_per_year
        
        alpha = portfolio_return - (daily_risk_free * trading_days_per_year + beta * (benchmark_return - daily_risk_free * trading_days_per_year))
        
        return alpha
    
    def calculate_var(self, confidence_level: float = 0.95) -> float:
        """
        Calculate Value at Risk (VaR).
        
        Args:
            confidence_level: Confidence level (decimal)
            
        Returns:
            float: VaR as fraction of portfolio
        """
        # Get returns
        returns = self.calculate_returns()
        
        if returns.empty:
            return 0.0
        
        # Calculate VaR
        var = -np.percentile(returns, 100 * (1 - confidence_level))
        
        return var
    
    def generate_snapshot(self) -> Dict[str, Any]:
        """
        Generate comprehensive portfolio snapshot.
        
        Returns:
            Dict with portfolio snapshot
        """
        # Calculate basic metrics
        metrics = self.calculate_metrics()
        
        # Get portfolio summary
        portfolio_summary = self.portfolio_manager.get_portfolio_summary()
        
        # Analyze drawdowns
        drawdowns = self.analyze_drawdowns(threshold=0.02)  # 2% threshold
        
        # Get trade statistics
        closed_trades = self.portfolio_manager.get_closed_trades()
        
        # Calculate daily returns
        daily_returns = self.calculate_returns(frequency='D')
        
        # Calculate monthly returns
        monthly_returns = self.calculate_returns(frequency='M')
        
        # Generate snapshot
        snapshot = {
            'overview': {
                'equity': portfolio_summary['equity'],
                'cash': portfolio_summary['cash'],
                'positions': portfolio_summary['positions'],
                'initial_capital': portfolio_summary['initial_cash'],
                'total_return': metrics['total_return'],
                'cagr': metrics['cagr'],
                'max_drawdown': metrics['max_drawdown'],
                'current_drawdown': (portfolio_summary['peak_equity'] - portfolio_summary['equity']) / portfolio_summary['peak_equity'] if portfolio_summary['peak_equity'] > 0 else 0.0
            },
            'performance_metrics': metrics,
            'position_summary': portfolio_summary,
            'drawdowns': drawdowns[:5],  # Top 5 drawdowns
            'trade_summary': {
                'total_trades': len(closed_trades),
                'winning_trades': sum(1 for trade in closed_trades if trade['realized_pnl'] > 0),
                'losing_trades': sum(1 for trade in closed_trades if trade['realized_pnl'] < 0),
                'win_rate': metrics['win_rate'],
                'profit_factor': metrics['profit_factor'],
                'average_trade': sum(trade['realized_pnl'] for trade in closed_trades) / len(closed_trades) if closed_trades else 0.0,
                'average_win': sum(trade['realized_pnl'] for trade in closed_trades if trade['realized_pnl'] > 0) / 
                              sum(1 for trade in closed_trades if trade['realized_pnl'] > 0) if sum(1 for trade in closed_trades if trade['realized_pnl'] > 0) > 0 else 0.0,
                'average_loss': sum(trade['realized_pnl'] for trade in closed_trades if trade['realized_pnl'] < 0) / 
                               sum(1 for trade in closed_trades if trade['realized_pnl'] < 0) if sum(1 for trade in closed_trades if trade['realized_pnl'] < 0) > 0 else 0.0,
            },
            'exposure': {
                'long_exposure': portfolio_summary['long_exposure'],
                'short_exposure': portfolio_summary['short_exposure'],
                'net_exposure': portfolio_summary['net_exposure'],
                'exposure_ratio': portfolio_summary['exposure_ratio']
            },
            'returns': {
                'daily_mean': daily_returns.mean(),
                'daily_std': daily_returns.std(),
                'monthly_mean': monthly_returns.mean(),
                'monthly_std': monthly_returns.std(),
                'best_day': daily_returns.max(),
                'worst_day': daily_returns.min(),
                'best_month': monthly_returns.max(),
                'worst_month': monthly_returns.min(),
                'positive_days': (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0.0
            }
        }
        
        return snapshot
    
    def run_stress_test(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run stress test on portfolio.
        
        Args:
            scenario: Stress test scenario with parameters
            
        Returns:
            Dict with stress test results
        """
        # Extract scenario parameters
        scenario_type = scenario.get('type', 'market_shock')
        shock_size = scenario.get('shock_size', -0.10)  # Default to 10% drop
        affected_symbols = scenario.get('affected_symbols', None)  # None means all
        
        # Get current portfolio state
        positions = self.portfolio_manager.get_all_positions()
        current_equity = self.portfolio_manager.equity
        current_cash = self.portfolio_manager.cash
        
        # Apply scenario
        if scenario_type == 'market_shock':
            # Calculate impact on positions
            total_impact = 0.0
            
            for symbol, position in positions.items():
                if affected_symbols is None or symbol in affected_symbols:
                    # Apply shock to position
                    current_value = position.get_market_value()
                    impact = current_value * shock_size
                    total_impact += impact
            
            # Calculate new equity
            new_equity = current_equity + total_impact
            
        elif scenario_type == 'volatility_shock':
            # Increase in volatility, calculate VaR impact
            var_multiplier = scenario.get('var_multiplier', 2.0)
            confidence_level = scenario.get('confidence_level', 0.95)
            
            # Calculate current VaR
            current_var = self.calculate_var(confidence_level)
            
            # Apply multiplier to VaR
            stressed_var = current_var * var_multiplier
            
            # Calculate impact on equity
            total_impact = -(stressed_var - current_var) * current_equity
            new_equity = current_equity + total_impact
            
        elif scenario_type == 'liquidity_crisis':
            # Liquidity crisis - forced liquidation at unfavorable prices
            slippage = scenario.get('slippage', 0.05)  # 5% slippage
            
            # Calculate liquidation impact
            total_impact = 0.0
            
            for symbol, position in positions.items():
                current_value = position.get_market_value()
                liquidation_impact = current_value * slippage * -1  # Always negative
                total_impact += liquidation_impact
            
            # Calculate new equity
            new_equity = current_equity + total_impact
            
        else:
            # Unknown scenario type
            logger.warning(f"Unknown stress test scenario type: {scenario_type}")
            return {
                'error': f"Unknown scenario type: {scenario_type}",
                'current_equity': current_equity,
                'new_equity': current_equity,
                'impact': 0.0,
                'impact_pct': 0.0
            }
        
        # Calculate impact
        absolute_impact = new_equity - current_equity
        percentage_impact = absolute_impact / current_equity if current_equity > 0 else 0.0
        
        # Assemble results
        results = {
            'scenario': scenario_type,
            'current_equity': current_equity,
            'new_equity': new_equity,
            'impact': absolute_impact,
            'impact_pct': percentage_impact,
            'parameters': scenario
        }
        
        return results