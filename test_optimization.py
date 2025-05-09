#!/usr/bin/env python
"""
Test script for the standardized optimization framework.

This script tests the optimization framework using a simple configuration
and reports the results.
"""

import os
import sys
import logging
import yaml
import json
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import optimizer
from src.strategy.optimization.optimizer import StrategyOptimizer

def run_test():
    """
    Run a test optimization with a simple configuration.
    
    Returns:
        dict: Optimization results
    """
    # Use a simple configuration
    config = {
        'strategy': {
            'name': 'simple_ma_crossover'
        },
        'parameter_space': [
            {
                'name': 'fast_period',
                'type': 'integer',
                'min': 5,
                'max': 20,
                'step': 5
            },
            {
                'name': 'slow_period',
                'type': 'integer',
                'min': 20,
                'max': 50,
                'step': 10
            }
        ],
        'optimization': {
            'method': 'grid',
            'objective': 'sharpe_ratio'
        },
        'data': {
            'symbols': ['AAPL'],
            'sources': [
                {
                    'symbol': 'AAPL',
                    'file': 'data/AAPL_1day.csv'
                }
            ],
            'train_test_split': {
                'enabled': True,
                'method': 'ratio',
                'train_ratio': 0.7,
                'test_ratio': 0.3
            }
        },
        'output_dir': './test_optimization_results'
    }
    
    # Create output directory
    Path(config['output_dir']).mkdir(parents=True, exist_ok=True)
    
    # Create optimizer
    optimizer = StrategyOptimizer(config)
    
    # Run optimization
    logger.info("Starting test optimization")
    results = optimizer.optimize()
    logger.info("Test optimization completed")
    
    # Print summary
    if results:
        print("\nOptimization Results Summary")
        print("============================")
        print(f"Best parameters: {results.get('best_parameters', {})}")
        print(f"Best score: {results.get('best_score', 0)}")
        
        # Print train/test performance if available
        train_results = results.get('train_results', {})
        test_results = results.get('test_results', {})
        
        if train_results:
            train_stats = train_results.get('statistics', {})
            print("\nTraining Performance:")
            print(f"  Return: {train_stats.get('return_pct', 0):.2f}%")
            print(f"  Sharpe Ratio: {train_stats.get('sharpe_ratio', 0):.2f}")
            
        if test_results:
            test_stats = test_results.get('statistics', {})
            print("\nTesting Performance:")
            print(f"  Return: {test_stats.get('return_pct', 0):.2f}%")
            print(f"  Sharpe Ratio: {test_stats.get('sharpe_ratio', 0):.2f}")
            
        # Print report location
        print(f"\nDetailed reports saved to: {config['output_dir']}")
    else:
        logger.error("Optimization failed")
        
    return results

if __name__ == "__main__":
    run_test()
