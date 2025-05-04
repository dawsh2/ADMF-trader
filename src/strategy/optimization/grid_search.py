"""
Grid search optimization for strategy parameters.

This module provides grid search capabilities for strategy optimization,
supporting exhaustive search across parameter combinations.
"""

import time
import itertools
import logging
from typing import Dict, Any, List, Tuple, Optional, Callable, Union, Iterator

from src.core.exceptions import OptimizationError
from src.strategy.optimization.parameter_space import ParameterSpace
from src.core.logging.structured_logger import get_logger

logger = get_logger(__name__)


class GridSearch:
    """Grid search optimizer for strategy parameters."""
    
    def __init__(self, parameter_space: ParameterSpace):
        """Initialize grid search optimizer.
        
        Args:
            parameter_space: Parameter space to search
        """
        self.parameter_space = parameter_space
        self.results = []
        self.best_result = None
        self.best_score = None
        self.best_params = None
    
    def search(self, objective_function: Callable[[Dict[str, Any]], float], 
               maximize: bool = True, max_evaluations: Optional[int] = None,
               max_time: Optional[float] = None, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Perform grid search.
        
        Args:
            objective_function: Function to evaluate parameter combinations
            maximize: Whether to maximize (True) or minimize (False) objective
            max_evaluations: Maximum number of evaluations (default: None)
            max_time: Maximum time in seconds (default: None)
            callback: Optional callback function called after each evaluation
                with arguments (params, score, is_best)
            
        Returns:
            Dictionary with search results
            
        Raises:
            OptimizationError: If optimization fails
        """
        self.results = []
        self.best_result = None
        self.best_score = None
        self.best_params = None
        
        # Get all grid points
        all_points = self.parameter_space.get_all_grid_points()
        total_points = len(all_points)
        
        logger.info(f"Starting grid search with {total_points} parameter combinations")
        
        # Check if we have too many parameter combinations
        if max_evaluations is not None and total_points > max_evaluations:
            logger.warning(
                f"Grid size ({total_points}) exceeds max_evaluations ({max_evaluations}). "
                f"Consider using random search or reducing parameter space."
            )
        
        # Start timing
        start_time = time.time()
        evaluations = 0
        
        # Evaluate each parameter combination
        for params in all_points:
            # Check termination conditions
            if max_evaluations is not None and evaluations >= max_evaluations:
                logger.info(f"Stopping grid search: reached max evaluations ({max_evaluations})")
                break
            
            if max_time is not None and time.time() - start_time > max_time:
                logger.info(f"Stopping grid search: reached max time ({max_time}s)")
                break
            
            # Evaluate parameters
            try:
                score = objective_function(params)
                evaluations += 1
                
                # Record result
                result = {
                    'params': params,
                    'score': score,
                    'evaluation': evaluations,
                    'timestamp': time.time()
                }
                self.results.append(result)
                
                # Update best result
                is_best = False
                if self.best_score is None:
                    is_best = True
                elif maximize and score > self.best_score:
                    is_best = True
                elif not maximize and score < self.best_score:
                    is_best = True
                
                if is_best:
                    self.best_score = score
                    self.best_params = params
                    self.best_result = result
                    
                    logger.info(f"New best result: score={score}, params={params}")
                
                # Call callback if provided
                if callback:
                    callback(params, score, is_best)
                
            except Exception as e:
                logger.warning(f"Error evaluating parameters {params}: {e}")
                # Continue with next parameter combination
        
        # Calculate statistics
        elapsed_time = time.time() - start_time
        evaluations_per_second = evaluations / elapsed_time if elapsed_time > 0 else 0
        
        logger.info(
            f"Grid search complete: "
            f"{evaluations}/{total_points} evaluations, "
            f"{elapsed_time:.2f}s, "
            f"{evaluations_per_second:.2f} eval/s"
        )
        
        # Return search results
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'evaluations': evaluations,
            'total_points': total_points,
            'elapsed_time': elapsed_time,
            'results': self.results
        }
    
    def get_best_params(self) -> Optional[Dict[str, Any]]:
        """Get best parameters found.
        
        Returns:
            Best parameters or None if no search has been performed
        """
        return self.best_params
    
    def get_best_score(self) -> Optional[float]:
        """Get best score found.
        
        Returns:
            Best score or None if no search has been performed
        """
        return self.best_score
    
    def get_results(self) -> List[Dict[str, Any]]:
        """Get all evaluation results.
        
        Returns:
            List of evaluation results
        """
        return self.results
