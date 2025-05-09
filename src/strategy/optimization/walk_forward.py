"""
Walk-forward optimization for strategy parameters.

This module provides walk-forward optimization capabilities for strategy robustness,
using time-based windows to better generalize to unseen market conditions.
"""

import time
import logging
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional, Callable, Union

from src.core.exceptions import OptimizationError
from src.strategy.optimization.parameter_space import ParameterSpace
from src.strategy.optimization.grid_search import GridSearch
from src.strategy.optimization.random_search import RandomSearch

logger = logging.getLogger(__name__)


class WalkForwardOptimizer:
    """Walk-forward optimizer for strategy parameters."""
    
    def __init__(self, data_handler, strategy_factory, optimization_method="grid"):
        """
        Initialize walk-forward optimizer.
        
        Args:
            data_handler: Data handler with walk-forward window support
            strategy_factory: Function to create strategy instances
            optimization_method: Method for optimization ('grid' or 'random')
        """
        self.data_handler = data_handler
        self.strategy_factory = strategy_factory
        self.optimization_method = optimization_method
        self.results = []
        self.windows = []
        self.best_parameters = None
    
    def optimize(self, parameter_space: ParameterSpace, 
                window_size_days: int, step_size_days: int, 
                test_size_days: Optional[int] = None,
                window_type: str = "rolling",
                objective_function: Callable = None,
                maximize: bool = True,
                max_evaluations_per_window: Optional[int] = None,
                random_samples: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform walk-forward optimization.
        
        Args:
            parameter_space: Parameter space to search
            window_size_days: Size of each window in days
            step_size_days: Size of each step forward in days
            test_size_days: Size of test portion in days (default: 20% of window_size)
            window_type: Type of window ('rolling' or 'expanding')
            objective_function: Function to evaluate parameter combinations
            maximize: Whether to maximize (True) or minimize (False) objective
            max_evaluations_per_window: Maximum evaluations per window for grid search
            random_samples: Number of random samples for random search
            
        Returns:
            Dictionary with optimization results
            
        Raises:
            OptimizationError: If optimization fails
        """
        # Reset results
        self.results = []
        self.windows = []
        
        # Create walk-forward windows
        try:
            self.windows = self.data_handler.create_walk_forward_windows(
                window_size_days=window_size_days,
                step_size_days=step_size_days,
                test_size_days=test_size_days,
                window_type=window_type
            )
        except Exception as e:
            raise OptimizationError(f"Error creating walk-forward windows: {e}")
        
        # Check if we have windows
        if not self.windows:
            raise OptimizationError("No walk-forward windows created")
        
        # Log window information
        logger.info(f"Created {len(self.windows)} walk-forward windows")
        
        # Start timing
        start_time = time.time()
        
        # Process each window
        for window_idx, window in enumerate(self.windows):
            logger.info(f"Processing window {window_idx+1}/{len(self.windows)}: "
                      f"{window['train_start']} to {window['test_end']}")
            
            # Set date range for training
            self.data_handler.set_date_range(window['train_start'], window['train_end'])
            
            # Create optimizer for this window
            if self.optimization_method == "grid":
                optimizer = GridSearch(parameter_space)
                # Run optimization
                window_opt_results = optimizer.search(
                    objective_function=objective_function,
                    maximize=maximize,
                    max_evaluations=max_evaluations_per_window
                )
            elif self.optimization_method == "random":
                optimizer = RandomSearch(parameter_space)
                # Run optimization
                window_opt_results = optimizer.search(
                    objective_function=objective_function,
                    num_samples=random_samples or 100,
                    maximize=maximize
                )
            else:
                raise OptimizationError(f"Invalid optimization method: {self.optimization_method}")
            
            # Extract best parameters
            best_params = window_opt_results.get('best_params')
            in_sample_score = window_opt_results.get('best_score')
            
            if not best_params:
                logger.warning(f"No best parameters found for window {window_idx+1}")
                continue
            
            # Set date range for out-of-sample testing
            self.data_handler.set_date_range(window['test_start'], window['test_end'])
            
            # Evaluate best parameters on test data
            try:
                out_of_sample_score = objective_function(best_params)
            except Exception as e:
                logger.error(f"Error evaluating parameters on test data: {e}")
                out_of_sample_score = None
            
            # Record results for this window
            window_result = {
                'window_idx': window_idx,
                'train_start': window['train_start'],
                'train_end': window['train_end'],
                'test_start': window['test_start'],
                'test_end': window['test_end'],
                'best_parameters': best_params,
                'in_sample_score': in_sample_score,
                'out_of_sample_score': out_of_sample_score,
                'optimization_results': window_opt_results
            }
            
            self.results.append(window_result)
            
            # Log window results
            logger.info(f"Window {window_idx+1} results: "
                      f"in-sample score: {in_sample_score:.6f}, "
                      f"out-of-sample score: {out_of_sample_score:.6f}, "
                      f"parameters: {best_params}")
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Analyze results
        analysis = self._analyze_results(maximize)
        
        # Compile final results
        final_results = {
            'windows': len(self.windows),
            'results': self.results,
            'elapsed_time': elapsed_time,
            'best_window': analysis.get('best_window'),
            'best_parameters': analysis.get('best_parameters'),
            'parameter_stability': analysis.get('parameter_stability'),
            'robustness_score': analysis.get('robustness_score')
        }
        
        # Store best parameters
        self.best_parameters = analysis.get('best_parameters')
        
        return final_results
    
    def _analyze_results(self, maximize: bool = True) -> Dict[str, Any]:
        """
        Analyze walk-forward optimization results.
        
        Args:
            maximize: Whether to maximize (True) or minimize (False) objective
            
        Returns:
            Dictionary with analysis results
        """
        if not self.results:
            return {
                'best_window': None,
                'best_parameters': None,
                'parameter_stability': {},
                'robustness_score': 0.0
            }
        
        # Find best window based on out-of-sample performance
        best_window = None
        best_score = None
        best_idx = -1
        
        for idx, result in enumerate(self.results):
            score = result.get('out_of_sample_score')
            if score is None:
                continue
                
            if best_score is None:
                best_score = score
                best_window = result
                best_idx = idx
            elif maximize and score > best_score:
                best_score = score
                best_window = result
                best_idx = idx
            elif not maximize and score < best_score:
                best_score = score
                best_window = result
                best_idx = idx
        
        # Select best parameters (recency bias - use most recent window with good performance)
        # This is a common approach in walk-forward optimization
        recent_good_window = None
        recent_good_idx = -1
        
        # Define "good" as within 10% of best performance
        if best_score is not None:
            threshold = best_score * 0.9 if maximize else best_score * 1.1
            
            # Start from the most recent window
            for idx in range(len(self.results) - 1, -1, -1):
                result = self.results[idx]
                score = result.get('out_of_sample_score')
                
                if score is None:
                    continue
                    
                if maximize and score >= threshold:
                    recent_good_window = result
                    recent_good_idx = idx
                    break
                elif not maximize and score <= threshold:
                    recent_good_window = result
                    recent_good_idx = idx
                    break
        
        # Choose parameters from the most recent good window, or the best window if none are "good"
        best_parameters = None
        if recent_good_window:
            best_parameters = recent_good_window.get('best_parameters')
            logger.info(f"Using parameters from most recent good window {recent_good_idx+1}")
        elif best_window:
            best_parameters = best_window.get('best_parameters')
            logger.info(f"Using parameters from best window {best_idx+1}")
        
        # Calculate parameter stability metrics
        param_stability = self._calculate_parameter_stability()
        
        # Calculate robustness score
        robustness_score = self._calculate_robustness_score(maximize)
        
        return {
            'best_window': best_window,
            'best_parameters': best_parameters,
            'parameter_stability': param_stability,
            'robustness_score': robustness_score
        }
    
    def _calculate_parameter_stability(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate parameter stability metrics.
        
        Returns:
            Dictionary with parameter stability metrics
        """
        if not self.results:
            return {}
        
        # Extract parameters from all windows
        all_params = {}
        
        for result in self.results:
            params = result.get('best_parameters')
            if not params:
                continue
                
            for param_name, param_value in params.items():
                if param_name not in all_params:
                    all_params[param_name] = []
                
                all_params[param_name].append(param_value)
        
        # Calculate stability metrics for each parameter
        stability_metrics = {}
        
        for param_name, values in all_params.items():
            if not values:
                continue
                
            # Convert to numeric if possible
            try:
                numeric_values = [float(v) for v in values]
                
                # Calculate statistics
                mean = sum(numeric_values) / len(numeric_values)
                std = (sum((x - mean) ** 2 for x in numeric_values) / len(numeric_values)) ** 0.5
                cv = std / mean if mean != 0 else float('inf')  # Coefficient of variation
                min_val = min(numeric_values)
                max_val = max(numeric_values)
                range_val = max_val - min_val
                
                stability_metrics[param_name] = {
                    'mean': mean,
                    'std': std,
                    'cv': cv,
                    'min': min_val,
                    'max': max_val,
                    'range': range_val,
                    'stable': cv < 0.25  # Consider stable if CV < 25%
                }
            except (ValueError, TypeError):
                # Handle non-numeric parameters
                # Count frequency of each value
                value_counts = {}
                for v in values:
                    v_str = str(v)
                    if v_str not in value_counts:
                        value_counts[v_str] = 0
                    value_counts[v_str] += 1
                
                # Find most common value and its frequency
                most_common = max(value_counts.items(), key=lambda x: x[1])
                most_common_pct = most_common[1] / len(values)
                
                stability_metrics[param_name] = {
                    'most_common': most_common[0],
                    'most_common_pct': most_common_pct,
                    'unique_values': len(value_counts),
                    'stable': most_common_pct > 0.5  # Consider stable if most common value appears in >50% of windows
                }
        
        return stability_metrics
    
    def _calculate_robustness_score(self, maximize: bool = True) -> float:
        """
        Calculate robustness score based on in-sample vs. out-of-sample performance.
        
        Args:
            maximize: Whether to maximize (True) or minimize (False) objective
            
        Returns:
            Robustness score (0.0-1.0)
        """
        if not self.results:
            return 0.0
        
        # Calculate performance ratios for each window
        ratios = []
        
        for result in self.results:
            in_sample = result.get('in_sample_score')
            out_of_sample = result.get('out_of_sample_score')
            
            if in_sample is None or out_of_sample is None or in_sample == 0:
                continue
                
            # Calculate ratio of out-of-sample to in-sample performance
            ratio = out_of_sample / in_sample
            
            # For minimization problems, invert the ratio
            if not maximize:
                ratio = 1.0 / ratio if ratio != 0 else float('inf')
                
            ratios.append(ratio)
        
        # Calculate average ratio
        if not ratios:
            return 0.0
            
        avg_ratio = sum(ratios) / len(ratios)
        
        # Normalize to 0-1 range
        # A perfect score would be 1.0 (out-of-sample == in-sample)
        # Anything >1.0 means out-of-sample was better than in-sample (unlikely but possible)
        # Anything <1.0 means out-of-sample was worse than in-sample (common due to overfitting)
        
        # Cap at 1.0 for scores > 1.0
        avg_ratio = min(avg_ratio, 1.0)
        
        return avg_ratio
    
    def get_best_parameters(self) -> Optional[Dict[str, Any]]:
        """
        Get the best parameters from walk-forward optimization.
        
        Returns:
            Best parameters or None if no optimization has been performed
        """
        return self.best_parameters
    
    def get_windows(self) -> List[Dict[str, Any]]:
        """
        Get the list of walk-forward windows.
        
        Returns:
            List of window specifications
        """
        return self.windows
    
    def get_results(self) -> List[Dict[str, Any]]:
        """
        Get the list of window results.
        
        Returns:
            List of window results
        """
        return self.results
    
    def get_parameter_stability(self) -> Dict[str, Dict[str, float]]:
        """
        Get parameter stability metrics.
        
        Returns:
            Dictionary with parameter stability metrics
        """
        return self._calculate_parameter_stability()
