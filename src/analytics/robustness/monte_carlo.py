"""
Monte Carlo simulation for strategy robustness testing.

This module provides functionality for testing strategy robustness through Monte Carlo
simulations, including trade sequence bootstrapping and statistical analysis.
"""

import numpy as np
import pandas as pd
import random
import logging
import time
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


class MonteCarloSimulator:
    """
    Perform Monte Carlo simulations by resampling trades or returns.
    
    This helps evaluate strategy robustness by creating alternative paths
    that could have occurred, providing confidence intervals and other statistics.
    """
    
    def __init__(self, trades: List[Dict[str, Any]] = None, 
                equity_curve: pd.DataFrame = None,
                initial_capital: float = 100000.0,
                num_simulations: int = 1000, 
                simulation_method: str = "bootstrap"):
        """
        Initialize Monte Carlo simulator.
        
        Args:
            trades: List of trade dictionaries
            equity_curve: Equity curve as pandas DataFrame with DatetimeIndex
            initial_capital: Initial capital for simulations
            num_simulations: Number of simulations to run
            simulation_method: Method for simulation ('bootstrap', 'block_bootstrap', or 'random_returns')
        """
        self.trades = trades or []
        self.equity_curve = equity_curve
        self.initial_capital = initial_capital
        self.num_simulations = num_simulations
        self.simulation_method = simulation_method
        self.results = []
        self.metrics = {}
        
        # Calculate trade returns if trades are provided
        if self.trades:
            self._calculate_trade_returns()
    
    def _calculate_trade_returns(self) -> None:
        """Calculate percentage returns for each trade."""
        self.trade_returns = []
        self.trade_durations = []
        
        for trade in self.trades:
            entry_price = trade.get('entry_price', 0)
            exit_price = trade.get('exit_price', 0)
            direction = trade.get('direction', 'BUY')
            
            if entry_price <= 0:
                logger.warning(f"Invalid entry price: {entry_price}, skipping trade")
                continue
            
            # Calculate return
            if direction == 'BUY' or direction == 1:
                ret = (exit_price / entry_price) - 1.0
            else:  # SELL or -1
                ret = 1.0 - (exit_price / entry_price)
                
            self.trade_returns.append(ret)
            
            # Calculate duration if timestamps available
            entry_time = trade.get('entry_time')
            exit_time = trade.get('exit_time')
            
            if entry_time and exit_time:
                if isinstance(entry_time, str):
                    entry_time = pd.Timestamp(entry_time)
                if isinstance(exit_time, str):
                    exit_time = pd.Timestamp(exit_time)
                    
                duration = (exit_time - entry_time).total_seconds() / 86400  # in days
                self.trade_durations.append(duration)
            else:
                self.trade_durations.append(1.0)  # default to 1 day
    
    def bootstrap_trades(self, trade_returns: List[float] = None) -> List[float]:
        """
        Generate bootstrapped trade returns.
        
        Args:
            trade_returns: List of trade returns to sample from (defaults to self.trade_returns)
            
        Returns:
            List of bootstrapped trade returns
        """
        returns = trade_returns or self.trade_returns
        
        if not returns:
            raise ValueError("No trade returns available for bootstrapping")
        
        # Sample with replacement from original returns
        return random.choices(returns, k=len(returns))
    
    def block_bootstrap_trades(self, block_size: int = 5) -> List[float]:
        """
        Generate block bootstrapped trade returns to preserve autocorrelation.
        
        Args:
            block_size: Number of consecutive trades to keep together
            
        Returns:
            List of block bootstrapped trade returns
        """
        if not self.trade_returns:
            raise ValueError("No trade returns available for block bootstrapping")
            
        # Create blocks
        blocks = []
        for i in range(0, len(self.trade_returns) - block_size + 1):
            blocks.append(self.trade_returns[i:i + block_size])
        
        if not blocks:
            # If we don't have enough trades for blocks, fall back to regular bootstrap
            return self.bootstrap_trades()
        
        # Sample blocks with replacement
        sampled_blocks = random.choices(blocks, k=(len(self.trade_returns) // block_size) + 1)
        
        # Flatten blocks and trim to original length
        flat_returns = [ret for block in sampled_blocks for ret in block]
        return flat_returns[:len(self.trade_returns)]
    
    def random_returns(self, mean: float = None, std: float = None, 
                       distribution: str = "normal") -> List[float]:
        """
        Generate random returns based on the statistical properties of the original returns.
        
        Args:
            mean: Mean return (defaults to mean of trade_returns)
            std: Standard deviation of returns (defaults to std of trade_returns)
            distribution: Distribution to use ('normal', 'lognormal', or 't')
            
        Returns:
            List of random returns
        """
        if not self.trade_returns and (mean is None or std is None):
            raise ValueError("No trade returns available and no mean/std provided")
            
        # Calculate statistics if not provided
        if mean is None:
            mean = np.mean(self.trade_returns)
        if std is None:
            std = np.std(self.trade_returns)
            
        # Generate random returns based on distribution
        if distribution == "normal":
            returns = np.random.normal(mean, std, len(self.trade_returns))
        elif distribution == "lognormal":
            # Adjust parameters for lognormal to match desired mean and std
            loc = np.log(mean**2 / np.sqrt(std**2 + mean**2))
            scale = np.sqrt(np.log(1 + std**2 / mean**2))
            returns = np.random.lognormal(loc, scale, len(self.trade_returns))
        elif distribution == "t":
            # T distribution with 5 degrees of freedom (heavier tails)
            returns = np.random.standard_t(5, len(self.trade_returns))
            # Scale to match desired mean and std
            returns = returns * std / np.std(returns) + mean
        else:
            raise ValueError(f"Unknown distribution: {distribution}")
            
        return returns.tolist()
    
    def _calculate_equity_curve(self, returns: List[float]) -> pd.DataFrame:
        """
        Calculate equity curve from trade returns.
        
        Args:
            returns: List of trade returns
            
        Returns:
            Equity curve as pandas DataFrame
        """
        # Initialize equity curve
        equity = [self.initial_capital]
        
        # Calculate compounded equity
        for ret in returns:
            # Apply return to previous equity
            next_equity = equity[-1] * (1 + ret)
            equity.append(next_equity)
        
        # Create DataFrame
        equity_df = pd.DataFrame({"equity": equity})
        
        return equity_df
    
    def _calculate_metrics(self, equity_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate performance metrics from equity curve.
        
        Args:
            equity_df: Equity curve DataFrame
            
        Returns:
            Dictionary of metrics
        """
        equity = equity_df["equity"].values
        
        # Calculate returns
        returns = [equity[i] / equity[i-1] - 1 for i in range(1, len(equity))]
        
        # Total return
        total_return = (equity[-1] / equity[0]) - 1
        
        # Annualized return (assume 252 trading days)
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        # Volatility (annualized)
        volatility = np.std(returns) * np.sqrt(252)
        
        # Sharpe ratio (annualized, risk-free rate = 0)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Maximum drawdown
        max_drawdown = 0
        peak = equity[0]
        
        for value in equity:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calmar ratio (annualized return / max drawdown)
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
        
        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "calmar_ratio": calmar_ratio
        }
    
    def run_simulations(self) -> Dict[str, Any]:
        """
        Run Monte Carlo simulations.
        
        Returns:
            Dictionary with simulation results and metrics
            
        Raises:
            ValueError: If no trades or equity curve is available
        """
        if not self.trades and self.equity_curve is None:
            raise ValueError("Need either trades or equity curve for simulations")
            
        # Reset results
        self.results = []
        self.metrics = {}
        
        logger.info(f"Running {self.num_simulations} Monte Carlo simulations")
        
        # Start timing
        start_time = time.time()
        
        # Run simulations
        for i in range(self.num_simulations):
            try:
                # Generate simulated returns
                if self.simulation_method == "bootstrap":
                    returns = self.bootstrap_trades()
                elif self.simulation_method == "block_bootstrap":
                    returns = self.block_bootstrap_trades()
                elif self.simulation_method == "random_returns":
                    returns = self.random_returns()
                else:
                    raise ValueError(f"Unknown simulation method: {self.simulation_method}")
                
                # Calculate equity curve
                equity_df = self._calculate_equity_curve(returns)
                
                # Calculate metrics
                metrics = self._calculate_metrics(equity_df)
                
                # Store result
                self.results.append({
                    "id": i,
                    "equity_curve": equity_df,
                    "metrics": metrics
                })
                
                # Log progress periodically
                if (i+1) % 100 == 0 or i == self.num_simulations - 1:
                    elapsed = time.time() - start_time
                    logger.info(f"Completed {i+1}/{self.num_simulations} simulations, elapsed: {elapsed:.2f}s")
                    
            except Exception as e:
                logger.error(f"Error in simulation {i}: {e}")
        
        # Calculate aggregate metrics
        self._calculate_aggregate_metrics()
        
        return self._compile_results()
    
    def _calculate_aggregate_metrics(self) -> None:
        """Calculate aggregate metrics across all simulations."""
        if not self.results:
            return
            
        # Extract metrics from all simulations
        all_metrics = defaultdict(list)
        
        for result in self.results:
            for name, value in result["metrics"].items():
                all_metrics[name].append(value)
        
        # Calculate statistics for each metric
        aggregate_metrics = {}
        
        for name, values in all_metrics.items():
            values_array = np.array(values)
            
            aggregate_metrics[name] = {
                "mean": np.mean(values_array),
                "median": np.median(values_array),
                "std": np.std(values_array),
                "min": np.min(values_array),
                "max": np.max(values_array),
                "percentile_5": np.percentile(values_array, 5),
                "percentile_25": np.percentile(values_array, 25),
                "percentile_75": np.percentile(values_array, 75),
                "percentile_95": np.percentile(values_array, 95)
            }
        
        self.metrics = aggregate_metrics
    
    def _compile_results(self) -> Dict[str, Any]:
        """Compile simulation results into a summary dictionary."""
        # Calculate elapsed time
        elapsed_time = time.time() - (self.results[0]["equity_curve"].index[0] if self.results else time.time())
        
        # Compile final results
        return {
            "num_simulations": len(self.results),
            "simulation_method": self.simulation_method,
            "initial_capital": self.initial_capital,
            "metrics": self.metrics,
            "elapsed_time": elapsed_time
        }
    
    def get_confidence_intervals(self, metric_name: str, 
                               confidence_levels: List[float] = [0.95, 0.99]) -> Dict[str, Tuple[float, float]]:
        """
        Get confidence intervals for a specific metric.
        
        Args:
            metric_name: Name of metric to get confidence intervals for
            confidence_levels: List of confidence levels (0-1)
            
        Returns:
            Dictionary mapping confidence levels to (lower, upper) tuples
        """
        if not self.metrics or metric_name not in self.metrics:
            logger.warning(f"No data available for metric: {metric_name}")
            return {}
            
        intervals = {}
        
        for confidence in confidence_levels:
            lower_percentile = (1 - confidence) / 2 * 100
            upper_percentile = (1 + confidence) / 2 * 100
            
            metric_data = [result["metrics"][metric_name] for result in self.results]
            lower = np.percentile(metric_data, lower_percentile)
            upper = np.percentile(metric_data, upper_percentile)
            
            intervals[confidence] = (lower, upper)
        
        return intervals
    
    def get_probability_of_profit(self) -> float:
        """
        Calculate the probability of profit based on simulations.
        
        Returns:
            Probability of profit (0-1)
        """
        if not self.results:
            return 0.0
            
        profit_count = sum(1 for r in self.results if r["metrics"]["total_return"] > 0)
        return profit_count / len(self.results)
    
    def get_probability_of_target_return(self, target_return: float) -> float:
        """
        Calculate the probability of achieving a target return.
        
        Args:
            target_return: Target return to calculate probability for
            
        Returns:
            Probability of achieving target return (0-1)
        """
        if not self.results:
            return 0.0
            
        target_count = sum(1 for r in self.results if r["metrics"]["total_return"] >= target_return)
        return target_count / len(self.results)
    
    def get_probability_of_max_drawdown(self, max_drawdown: float) -> float:
        """
        Calculate the probability of experiencing a drawdown greater than specified.
        
        Args:
            max_drawdown: Maximum drawdown threshold
            
        Returns:
            Probability of exceeding threshold (0-1)
        """
        if not self.results:
            return 0.0
            
        count = sum(1 for r in self.results if r["metrics"]["max_drawdown"] >= max_drawdown)
        return count / len(self.results)
    
    def get_worst_case_metrics(self, percentile: float = 0.05) -> Dict[str, float]:
        """
        Get worst-case metrics based on a percentile of simulations.
        
        Args:
            percentile: Percentile for worst-case (e.g., 0.05 for 5th percentile)
            
        Returns:
            Dictionary with worst-case metrics
        """
        worst_case = {}
        
        for metric_name, stats in self.metrics.items():
            worst_case[metric_name] = stats[f"percentile_{int(percentile * 100)}"]
            
        return worst_case
