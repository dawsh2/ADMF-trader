"""
Standardized optimization module for trading strategies.

This module provides a consistent interface for strategy optimization,
leveraging the analytics module for performance calculations and handling
train/test validation.
"""

import os
import sys
import logging
import yaml
import json
import datetime
import uuid
from pathlib import Path

# Import optimization components
from src.strategy.optimization.parameter_space import ParameterSpace
from src.strategy.optimization.grid_search import GridSearch
# Update imports to match actual class names
try:
    from src.strategy.optimization.random_search import RandomSearch
except ImportError:
    from src.strategy.optimization.random_search import RandomSearchOptimizer as RandomSearch
try:
    from src.strategy.optimization.walk_forward import WalkForward
except ImportError:
    from src.strategy.optimization.walk_forward import WalkForwardOptimizer as WalkForward
from src.strategy.optimization.objective_functions import get_objective_function, OBJECTIVES
from src.strategy.optimization.reporter import OptimizationReporter

# Standard analytics imports for consistency
from src.analytics.metrics.functional import (
    total_return,
    sharpe_ratio,
    profit_factor,
    max_drawdown,
    calculate_all_metrics
)
from src.execution.backtest.optimizing_backtest import OptimizingBacktest
from src.strategy.strategy_factory import StrategyFactory

# Set up logging
logger = logging.getLogger(__name__)

class StrategyOptimizer:
    """
    Standard optimizer for trading strategies.
    
    This class handles the optimization process for strategy parameters,
    ensuring consistent evaluation across training and test datasets.
    """
    
    def __init__(self, config):
        """
        Initialize the optimizer with configuration.
        
        Args:
            config (dict): Optimization configuration which can be provided as:
                - Dictionary with direct configuration
                - Path to YAML file containing configuration
        """
        # Load config if it's a string (path to file)
        if isinstance(config, str):
            try:
                with open(config, 'r') as f:
                    self.config = yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Error loading configuration file {config}: {e}")
                raise
        else:
            self.config = config
            
        # Set up output directory
        self.output_dir = self.config.get('output_dir', './optimization_results')
        
        # Create output directory if it doesn't exist
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Set up components
        self.parameter_space = self._build_parameter_space()
        self.objective_function = self._get_objective_function()
        self.strategy_factory = self._setup_strategy_factory()
        
        # Create reporter
        self.reporter = OptimizationReporter(self.config)
        
    def _build_parameter_space(self):
        """
        Build parameter space from configuration.
        
        Returns:
            ParameterSpace: Parameter space for optimization
        """
        param_space = ParameterSpace()
        
        # Load parameter space configuration
        if 'parameter_space' in self.config:
            # Parameters are defined in the config
            param_config = {'parameters': self.config['parameter_space']}
            param_space.from_dict(param_config)
        elif 'parameter_file' in self.config:
            # Parameters are in a separate file
            param_file = self.config['parameter_file']
            try:
                with open(param_file, 'r') as f:
                    param_config = yaml.safe_load(f)
                param_space.from_dict(param_config)
            except Exception as e:
                logger.error(f"Error loading parameter file {param_file}: {e}")
                raise
        else:
            raise ValueError("No parameter space defined in config (use parameter_space or parameter_file)")
            
        return param_space
        
    def _get_objective_function(self):
        """
        Get objective function from configuration.
        
        Returns:
            callable: Objective function
        """
        # Get objective name from config
        objective_name = self.config.get('optimization', {}).get('objective', 'sharpe_ratio')
        
        # Get weights for combined objective
        weights = self.config.get('optimization', {}).get('weights', None)
        
        # If objective is combined_score, create a weighted function
        if objective_name == 'combined_score' and weights:
            # Extract weights
            return lambda results: self._calculate_combined_score(results, weights)
        elif objective_name == 'train_test_combined':
            # Create a function that combines train and test scores
            train_weight = self.config.get('optimization', {}).get('train_weight', 0.4)
            test_weight = self.config.get('optimization', {}).get('test_weight', 0.6)
            sub_objective = self.config.get('optimization', {}).get('sub_objective', 'sharpe_ratio')
            
            # Get the sub-objective function
            sub_func = get_objective_function(sub_objective)
            
            # Return combined function
            return lambda results: (
                train_weight * sub_func(results.get('train_results', {})) +
                test_weight * sub_func(results.get('test_results', {}))
            )
        else:
            # Get standard objective function
            return get_objective_function(objective_name)
            
    def _calculate_combined_score(self, results, weights):
        """
        Calculate a combined score from multiple metrics.
        
        Args:
            results (dict): Backtest results
            weights (dict): Weights for each metric
            
        Returns:
            float: Combined score
        """
        score = 0.0
        
        # Calculate weighted sum of metrics
        for metric_name, weight in weights.items():
            if metric_name in OBJECTIVES:
                metric_func = get_objective_function(metric_name)
                metric_value = metric_func(results)
                score += weight * metric_value
                
        return score
        
    def _setup_strategy_factory(self):
        """
        Set up the strategy factory.
        
        Returns:
            StrategyFactory: Strategy factory
        """
        # Define strategy directories
        strategy_dirs = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                        '..', 'implementations')
        ]
        
        # If custom strategy directories are specified, add them
        if 'strategy_dirs' in self.config:
            strategy_dirs.extend(self.config['strategy_dirs'])
        
        # Create strategy factory
        factory = StrategyFactory(strategy_dirs)
        
        return factory
        
    def _create_backtest_config(self):
        """
        Create backtest configuration from optimization config.
        
        Returns:
            dict: Backtest configuration
        """
        # Start with base configuration
        backtest_config = {}
        
        # Copy relevant backtest settings
        if 'backtest' in self.config:
            backtest_config.update(self.config['backtest'])
            
        # Copy data settings
        if 'data' in self.config:
            backtest_config['data'] = self.config['data']
            
        # Add fixed strategy parameters if provided
        if 'strategy' in self.config and 'fixed_params' in self.config['strategy']:
            backtest_config['strategy'] = {
                'name': self.config['strategy']['name'],
                'params': self.config['strategy']['fixed_params']
            }
            
        return backtest_config
        
    def optimize(self):
        """
        Run the optimization process.
        
        Returns:
            dict: Optimization results
        """
        # Log starting optimization
        logger.info(f"Starting optimization for strategy: {self.config['strategy']['name']}")
        logger.info(f"Parameter space: {self.parameter_space}")
        
        # Create backtest configuration
        backtest_config = self._create_backtest_config()
        
        # Create optimization context
        context = {
            'strategy_factory': self.strategy_factory
        }
        
        # Get optimization method
        optimization_method = self.config.get('optimization', {}).get('method', 'grid')
        
        # Get train/test split configuration
        train_test_config = self.config.get('data', {}).get('train_test_split', {})
        
        # Create optimizer based on method
        if optimization_method == 'grid':
            logger.info("Using grid search optimization")
            # Create optimizing backtest
            optimizer = OptimizingBacktest('optimizer', backtest_config, self.parameter_space)
            
            # Initialize optimizer
            optimizer.initialize(context)
            
            # Run optimization
            results = optimizer.optimize(
                self.config['strategy']['name'],
                self.objective_function,
                train_test_config
            )
        elif optimization_method == 'random':
            logger.info("Using random search optimization")
            # Get number of trials
            num_trials = self.config.get('optimization', {}).get('num_trials', 100)
            
            # Create optimizer with random search
            optimizer = RandomSearch(
                parameter_space=self.parameter_space,
                seed=self.config.get('optimization', {}).get('random_seed')
            )
            
            # Create an objective function wrapper for optimizing backtest
            def _objective_function(params):
                backtest = OptimizingBacktest('optimizer', backtest_config, self.parameter_space)
                backtest.initialize(context)
                backtest_results = backtest._run_backtest_with_params(
                    self.config['strategy']['name'], 
                    params, 
                    'train',
                    train_test_config
                )
                return self.objective_function(backtest_results)
            
            # Run random search
            search_results = optimizer.search(
                objective_function=_objective_function,
                num_samples=num_trials,
                maximize=True,
                max_time=self.config.get('optimization', {}).get('max_time')
            )
            
            # Run backtest with best parameters on test set
            backtest = OptimizingBacktest('optimizer', backtest_config, self.parameter_space)
            backtest.initialize(context)
            
            train_results = backtest._run_backtest_with_params(
                self.config['strategy']['name'], 
                search_results['best_params'], 
                'train',
                train_test_config
            )
            
            test_results = backtest._run_backtest_with_params(
                self.config['strategy']['name'], 
                search_results['best_params'], 
                'test',
                train_test_config
            )
            
            # Combine results
            results = {
                'best_parameters': search_results['best_params'],
                'best_score': search_results['best_score'],
                'train_results': train_results,
                'test_results': test_results,
                'evaluations': search_results['evaluations'],
                'elapsed_time': search_results['elapsed_time'],
                'results_grid': search_results['results']
            }
        elif optimization_method == 'walk_forward':
            logger.info("Using walk-forward optimization")
            # Get walk-forward parameters
            window_size = self.config.get('optimization', {}).get('window_size', 60)
            step_size = self.config.get('optimization', {}).get('step_size', 20)
            window_type = self.config.get('optimization', {}).get('window_type', 'rolling')
            
            # For walk-forward optimization, we'll use a simplified implementation for now
            # Create an optimizing backtest for each window
            logger.info(f"Walk-forward optimization with window size {window_size}, step size {step_size}")
            
            # This is a placeholder - actual walk-forward would use time windows
            # For now, we'll just do a standard grid search and add the walk-forward metadata
            backtest = OptimizingBacktest('optimizer', backtest_config, self.parameter_space)
            backtest.initialize(context)
            
            # Run standard optimization with proper train/test split
            results = backtest.optimize(
                self.config['strategy']['name'],
                self.objective_function,
                train_test_config
            )
            
            # Add walk-forward specific metadata
            results['walk_forward'] = {
                'window_size': window_size,
                'step_size': step_size,
                'window_type': window_type
            }
        else:
            raise ValueError(f"Unknown optimization method: {optimization_method}")
            
        # Add timestamp and ID to results
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results['timestamp'] = timestamp
        results['id'] = str(uuid.uuid4())
        results['config'] = self.config
        
        # Ensure best_score is properly set
        if 'best_train_score' in results and 'best_score' not in results:
            results['best_score'] = results['best_train_score']
        
        # Log optimization completion with best parameters and score
        logger.info(f"Optimization completed. Best parameters: {results.get('best_parameters', {})}, Best score: {results.get('best_score', 0):.4f}")
        
        # Print comprehensive summary to console
        print("\nOptimization Results Summary")
        print("=" * 80)
        print(f"Strategy: {self.config['strategy']['name']}")
        print(f"Best parameters: {results.get('best_parameters', {})}")
        
        # Get the best score - might be from train_score or best_score field
        best_score = results.get('best_score', 0)
        if best_score == 0 and 'best_train_score' in results:
            best_score = results['best_train_score']
        
        print(f"Best score: {best_score:.4f}")
        
        # Print train/test performance if available
        train_results = results.get('train_results', {})
        test_results = results.get('test_results', {})
        
        if train_results:
            train_stats = train_results.get('statistics', {})
            print("\nTraining Performance:")
            print(f"  Return: {train_stats.get('return_pct', 0):.2f}%")
            print(f"  Sharpe Ratio: {train_stats.get('sharpe_ratio', 0):.2f}")
            print(f"  Profit Factor: {train_stats.get('profit_factor', 0):.2f}")
            print(f"  Max Drawdown: {train_stats.get('max_drawdown', 0):.2f}%")
            print(f"  Trades: {train_stats.get('trades_executed', 0)}")
            
        if test_results:
            test_stats = test_results.get('statistics', {})
            print("\nTesting Performance:")
            print(f"  Return: {test_stats.get('return_pct', 0):.2f}%")
            print(f"  Sharpe Ratio: {test_stats.get('sharpe_ratio', 0):.2f}")
            print(f"  Profit Factor: {test_stats.get('profit_factor', 0):.2f}")
            print(f"  Max Drawdown: {test_stats.get('max_drawdown', 0):.2f}%")
            print(f"  Trades: {test_stats.get('trades_executed', 0)}")
            
        print(f"\nDetailed reports saved to: {self.output_dir}")
        print("=" * 80)
        
        # Generate report
        self.reporter.generate_report(results)
        
        # Save results
        self._save_results(results)
        
        return results
        
    def _save_results(self, results):
        """
        Save optimization results.
        
        Args:
            results (dict): Optimization results
        """
        # Create filename with timestamp
        timestamp = results.get('timestamp', 
                             datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        strategy_name = self.config['strategy']['name']
        filename = f"{strategy_name}_optimization_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Save results as JSON
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
