#!/usr/bin/env python
"""
Simple script to run the standardized optimization framework.

This script provides an easy way to test the optimization framework.
"""

import os
import sys
import logging
import argparse
from src.strategy.optimization.optimizer import StrategyOptimizer

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to run optimization."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Run optimization')
    parser.add_argument('--config', required=True, help='Path to config file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create optimizer
    try:
        logger.info(f"Loading optimization configuration from {args.config}")
        optimizer = StrategyOptimizer(args.config)
        
        # Run optimization
        logger.info("Starting optimization")
        results = optimizer.optimize()
        logger.info("Optimization completed")
        
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
                print(f"  Return: {test_