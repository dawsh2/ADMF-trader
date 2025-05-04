"""
Random search optimization for strategy parameters.

This module provides random search capabilities for strategy optimization,
which can be more efficient than grid search for high-dimensional spaces.
"""

import time
import random
import logging
from typing import Dict, Any, List, Tuple, Optional, Callable, Union, Iterator

from src.core.exceptions import OptimizationError
from src.strategy.optimization.parameter_space import ParameterSpace
from src.core.logging.structured_logger import get_logger

logger = get_logger(__name__)


class RandomSearch:
    """Random search optimizer for strategy parameters."""
    
    def __init__(self, parameter_space: ParameterSpace, seed: Optional[int] = None):
        """Initialize random search optimizer.
        
        Args:
            parameter_space: Parameter space to search
            seed: Random seed for reproducibility (default: None)
        """
        self.parameter_space = parameter_space
        self.results = []
        self.best_result = None
        self.best_score = None
        self.best_params = None
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
    
    def search(self, objective_function: Callable[[Dict[str, Any]], float], 
               num_samples: int, maximize: bool = True, 
               max_time: Optional[float] = None, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Perform random search.
        
        Args:
            objective_function: Function to evaluate parameter combinations
            num_samples: Number of random samples to evaluate
            maximize: Whether to maximize (True) or minimize (False) objective
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
        
        logger.info(f"Starting random search with {num_samples} samples")
        
        # Start timing
        start_time = time.time()
        evaluations = 0
        
        # Evaluate random parameter combinations
        for i in range(num_samples):
            # Check time limit
            if max_time is not None and time.time() - start_time > max_time:
                logger.info(f"Stopping random search: reached max time ({max_time}s)")
                break
            
            # Generate random parameters
            params = self.parameter_space.get_random_point()
            
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
            f"Random search complete: "
            f"{evaluations} evaluations, "
            f"{elapsed_time:.2f}s, "
            f"{evaluations_per_second:.2f} eval/s"
        )
        
        # Return search results
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'evaluations': evaluations,
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
