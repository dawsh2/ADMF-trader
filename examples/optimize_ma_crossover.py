#!/usr/bin/env python
"""
ADMF-Trader MA Crossover Strategy Optimization Example

This script demonstrates how to optimize a Moving Average Crossover strategy using
the ADMF-Trader optimization framework with train/test validation to prevent overfitting.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.system_bootstrap import Bootstrap
from src.strategy.optimization.parameter_space import ParameterSpace
from src.execution.backtest.optimizing_backtest import OptimizingBacktestCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("optimize_ma_crossover.log")
    ]
)

logger = logging.getLogger(__name__)


def create_parameter_space():
    """Create parameter space for MA Crossover strategy."""
    param_space = ParameterSpace(name="ma_crossover")
    
    # Add fast moving average window parameter
    param_space.add_integer(
        name="fast_window",
        min_value=2,
        max_value=50,
        step=1
    )
    
    # Add slow moving average window parameter
    param_space.add_integer(
        name="slow_window",
        min_value=10,
        max_value=200,
        step=5
    )
    
    # Add price key parameter
    param_space.add_categorical(
        name="price_key",
        categories=["open", "high", "low", "close"]
    )
    
    # Add signal threshold parameter
    param_space.add_float(
        name="signal_threshold",
        min_value=0.0,
        max_value=0.02,
        step=0.001
    )
    
    # Add volatility adjustment parameter
    param_space.add_boolean(
        name="use_volatility_adjustment"
    )
    
    return param_space


def plot_optimization_results(optimization_results):
    """
    Plot optimization results.
    
    Args:
        optimization_results: Dictionary with optimization results
    """
    # Create output directory for plots
    os.makedirs("./results/plots", exist_ok=True)
    
    # Extract data from results
    results = optimization_results.get('results', [])
    
    if not results:
        logger.warning("No results to plot")
        return
    
    # Extract parameters and scores
    params = {}
    scores = []
    
    for result in results:
        for param_name, param_value in result['params'].items():
            if param_name not in params:
                params[param_name] = []
            params[param_name].append(param_value)
        
        scores.append(result['score'])
    
    # Plot parameter distributions with scores
    for param_name, param_values in params.items():
        if param_name in ['price_key', 'use_volatility_adjustment']:
            # Categorical parameters - create bar chart
            plt.figure(figsize=(10, 6))
            
            # Group by parameter value
            unique_values = sorted(set(param_values))
            value_scores = {}
            
            for value, score in zip(param_values, scores):
                if value not in value_scores:
                    value_scores[value] = []
                
                value_scores[value].append(score)
            
            # Calculate mean score for each value
            mean_scores = [np.mean(value_scores.get(value, [0])) for value in unique_values]
            
            # Create bar chart
            plt.bar(unique_values, mean_scores)
            plt.xlabel(param_name)
            plt.ylabel('Mean Score')
            plt.title(f'Mean Score by {param_name}')
            plt.tight_layout()
            plt.savefig(f'./results/plots/param_{param_name}.png')
            plt.close()
        else:
            # Numerical parameters - create scatter plot
            plt.figure(figsize=(10, 6))
            plt.scatter(param_values, scores, alpha=0.5)
            plt.xlabel(param_name)
            plt.ylabel('Score')
            plt.title(f'Score vs {param_name}')
            plt.tight_layout()
            plt.savefig(f'./results/plots/param_{param_name}.png')
            plt.close()
    
    # Plot score distribution
    plt.figure(figsize=(10, 6))
    plt.hist(scores, bins=20)
    plt.xlabel('Score')
    plt.ylabel('Frequency')
    plt.title('Score Distribution')
    plt.tight_layout()
    plt.savefig('./results/plots/score_distribution.png')
    plt.close()


def plot_walk_forward_results(wf_results):
    """
    Plot walk-forward optimization results.
    
    Args:
        wf_results: Dictionary with walk-forward results
    """
    # Create output directory for plots
    os.makedirs("./results/plots", exist_ok=True)
    
    # Extract window results
    window_results = wf_results.get('results', [])
    
    if not window_results:
        logger.warning("No window results to plot")
        return
    
    # Extract data
    window_idx = []
    in_sample_scores = []
    out_of_sample_scores = []
    parameter_values = {}
    
    for window in window_results:
        window_idx.append(window['window_idx'])
        in_sample_scores.append(window['in_sample_score'])
        out_of_sample_scores.append(window['out_of_sample_score'])
        
        # Extract parameters
        for param_name, param_value in window['best_parameters'].items():
            if param_name not in parameter_values:
                parameter_values[param_name] = []
            
            parameter_values[param_name].append(param_value)
    
    # Plot in-sample vs out-of-sample performance
    plt.figure(figsize=(12, 6))
    plt.plot(window_idx, in_sample_scores, 'b-', label='In-Sample')
    plt.plot(window_idx, out_of_sample_scores, 'r-', label='Out-of-Sample')
    plt.xlabel('Window')
    plt.ylabel('Score')
    plt.title('In-Sample vs Out-of-Sample Performance')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('./results/plots/wf_performance.png')
    plt.close()
    
    # Plot parameter stability
    for param_name, values in parameter_values.items():
        if param_name in ['price_key', 'use_volatility_adjustment']:
            # Skip categorical parameters for now
            continue
            
        plt.figure(figsize=(12, 6))
        plt.plot(window_idx, values, 'g-o')
        plt.xlabel('Window')
        plt.ylabel(param_name)
        plt.title(f'{param_name} Stability')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f'./results/plots/wf_param_{param_name}.png')
        plt.close()


def plot_monte_carlo_results(mc_results):
    """
    Plot Monte Carlo simulation results.
    
    Args:
        mc_results: Dictionary with Monte Carlo results
    """
    # Create output directory for plots
    os.makedirs("./results/plots", exist_ok=True)
    
    # Extract metrics
    metrics = mc_results.get('metrics', {})
    
    if not metrics:
        logger.warning("No Monte Carlo metrics to plot")
        return
    
    # Create plots for key metrics
    key_metrics = ['total_return', 'sharpe_ratio', 'max_drawdown']
    
    for metric_name in key_metrics:
        if metric_name not in metrics:
            continue
            
        metric_data = metrics[metric_name]
        
        # Extract statistics
        mean = metric_data.get('mean', 0)
        median = metric_data.get('median', 0)
        std = metric_data.get('std', 0)
        p5 = metric_data.get('percentile_5', 0)
        p95 = metric_data.get('percentile_95', 0)
        
        # Create histogram with statistics
        plt.figure(figsize=(12, 6))
        
        # Generate synthetic data for histogram (limited to 95% confidence interval)
        synthetic_data = np.random.normal(mean, std, 1000)
        synthetic_data = synthetic_data[(synthetic_data >= p5) & (synthetic_data <= p95)]
        
        plt.hist(synthetic_data, bins=30, alpha=0.6, color='skyblue')
        
        # Add lines for key statistics
        plt.axvline(mean, color='r', linestyle='-', label=f'Mean: {mean:.4f}')
        plt.axvline(median, color='g', linestyle='-', label=f'Median: {median:.4f}')
        plt.axvline(p5, color='orange', linestyle='--', label=f'5%: {p5:.4f}')
        plt.axvline(p95, color='purple', linestyle='--', label=f'95%: {p95:.4f}')
        
        plt.title(f'Monte Carlo: {metric_name} Distribution')
        plt.xlabel(metric_name)
        plt.ylabel('Frequency')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f'./results/plots/mc_{metric_name}.png')
        plt.close()


def plot_regime_analysis(regime_results):
    """
    Plot regime analysis results.
    
    Args:
        regime_results: Dictionary with regime analysis results
    """
    # Create output directory for plots
    os.makedirs("./results/plots", exist_ok=True)
    
    # Extract regime performance
    regime_performance = regime_results.get('regime_performance', {})
    
    if not regime_performance:
        logger.warning("No regime performance data to plot")
        return
    
    # Create bar chart of regime performance
    regimes = list(regime_performance.keys())
    performance = [regime_performance[regime] for regime in regimes]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(regimes, performance)
    
    # Color bars based on performance
    for i, p in enumerate(performance):
        if p > 0:
            bars[i].set_color('green')
        else:
            bars[i].set_color('red')
    
    plt.title('Strategy Performance by Market Regime')
    plt.xlabel('Market Regime')
    plt.ylabel('Total Return')
    plt.xticks(rotation=45)
    plt.grid(True, axis='y')
    plt.tight_layout()
    plt.savefig('./results/plots/regime_performance.png')
    plt.close()


def main():
    """Main optimization workflow."""
    logger.info("Starting MA Crossover strategy optimization example")
    
    # Create output directory
    os.makedirs("./results", exist_ok=True)
    
    # Bootstrap the system
    config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "config/head_test.yaml")
    
    bootstrap = Bootstrap(
        config_files=[config_file],
        log_level="INFO"
    )
    
    try:
        # Set up the system
        container, config = bootstrap.setup()
        
        # Create optimizing backtest coordinator
        backtest = OptimizingBacktestCoordinator(container, config)
        
        # Set up train/test split (70/30)
        backtest.setup_train_test_split(train_ratio=0.7, method="ratio")
        
        # Create parameter space
        param_space = create_parameter_space()
        
        # Set parameter space for strategy
        backtest.set_parameter_space("ma_crossover", param_space)
        
        # Run grid search optimization
        logger.info("Running grid search optimization")
        grid_results = backtest.optimize_strategy(
            strategy_name="ma_crossover",
            method="grid",
            max_evaluations=100  # Limit evaluations for example
        )
        
        # Print best parameters from grid search
        best_params = grid_results.get('best_params')
        best_score = grid_results.get('best_score')
        
        logger.info(f"Best parameters from grid search: {best_params}")
        logger.info(f"Best score from grid search: {best_score}")
        
        # Plot grid search results
        plot_optimization_results(grid_results)
        
        # Run walk-forward optimization
        logger.info("Running walk-forward optimization")
        wf_results = backtest.optimize_strategy(
            strategy_name="ma_crossover",
            method="walk_forward",
            window_size_days=252,  # 1 year
            step_size_days=63,     # ~3 months
            window_type="rolling"
        )
        
        # Plot walk-forward results
        plot_walk_forward_results(wf_results)
        
        # Run Monte Carlo simulation with best parameters
        logger.info("Running Monte Carlo simulation")
        mc_results = backtest.run_monte_carlo(
            num_simulations=1000,
            method="bootstrap"
        )
        
        # Plot Monte Carlo results
        plot_monte_carlo_results(mc_results)
        
        # Run regime analysis
        logger.info("Running regime analysis")
        regime_results = backtest.analyze_market_regimes(
            detection_method="trend"
        )
        
        # Plot regime analysis results
        plot_regime_analysis(regime_results)
        
        logger.info("Optimization example completed successfully")
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
