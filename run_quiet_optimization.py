#!/usr/bin/env python
"""
Runs the optimization with minimal output, showing only parameter combinations being tested.
"""
import os
import sys
import logging
import argparse
import yaml
import time
from datetime import datetime
import pandas as pd

from src.core.system_bootstrap import Bootstrap
from src.strategy.optimization import ParameterSpace, GridSearch, RandomSearch

def print_param_combination(params, score=None, is_best=False):
    """Format and print parameter combination."""
    params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
    if score is not None:
        status = "✓ BEST" if is_best else ""
        print(f"Testing: {params_str} → Score: {score:.4f} {status}")
    else:
        print(f"Testing: {params_str}...")

def run_optimization():
    """Run optimization with minimal output, showing parameter combinations."""
    parser = argparse.ArgumentParser(description="ADMF-Trader Optimization with Minimal Output")
    
    parser.add_argument("--config", required=True, help="Configuration file path")
    parser.add_argument("--max-evals", type=int, default=None, 
                      help="Maximum number of evaluations")
    parser.add_argument("--output-dir", default="./optimization_results", 
                      help="Results output directory")
    parser.add_argument("--save-all", action="store_true",
                      help="Save detailed reports for all parameter combinations")
    
    args = parser.parse_args()
    
    # Silence all loggers
    logging.getLogger().setLevel(logging.CRITICAL)
    for module in ["matplotlib", "urllib3", "pandas", "src"]:
        logging.getLogger(module).setLevel(logging.CRITICAL)
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get optimization settings
    if "optimization" not in config:
        print(f"Error: No optimization section found in {args.config}")
        return False
    
    opt_config = config["optimization"]
    if not opt_config.get("enabled", False):
        print(f"Error: Optimization not enabled in {args.config}")
        return False
    
    # Get strategy name
    strategy_name = config["backtest"].get("strategy")
    if not strategy_name:
        print("Error: No strategy specified in configuration")
        return False
    
    # Set up parameter space from config
    param_space = opt_config.get("parameter_space", {}).get(strategy_name, {})
    if not param_space:
        print(f"Error: No parameter space defined for strategy '{strategy_name}'")
        return False
    
    # Create parameter space object
    space = ParameterSpace(f"{strategy_name}_optimization")
    for param_name, param_config in param_space.items():
        param_type = param_config.get("type")
        if param_type == "integer":
            space.add_integer(
                param_name, 
                param_config.get("min"), 
                param_config.get("max"), 
                param_config.get("step", 1)
            )
        elif param_type == "float":
            space.add_float(
                param_name, 
                param_config.get("min"), 
                param_config.get("max"), 
                param_config.get("step", 0.1)
            )
        elif param_type == "categorical":
            space.add_categorical(
                param_name, 
                param_config.get("options", [])
            )
    
    # Setup optimizer
    method = opt_config.get("method", "grid_search")
    max_evaluations = args.max_evals or opt_config.get("max_evaluations", 50)
    max_time = opt_config.get("max_time", 600)
    objective = opt_config.get("objective", "sharpe_ratio")
    maximize = opt_config.get("maximize", True)
    
    # Create optimizer
    if method == "grid_search":
        optimizer = GridSearch(space)
        print(f"Grid Search with {space.get_grid_size()} combinations (max {max_evaluations})")
    elif method == "random_search":
        seed = opt_config.get("random_search", {}).get("seed", 42)
        optimizer = RandomSearch(space, seed=seed)
        print(f"Random Search with seed {seed}, max {max_evaluations} evaluations")
    else:
        print(f"Error: Unknown optimization method '{method}'")
        return False
    
    # Results storage
    all_results = []
    
    # Define objective function with callback
    def objective_function(params):
        try:
            # Update strategy parameters in config
            config["strategies"][strategy_name].update(params)
            
            # Print parameter combination
            print_param_combination(params)
            
            # Redirect stdout to avoid backtest output
            original_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            
            # Run backtest with these parameters
            bootstrap = Bootstrap(log_level="CRITICAL")
            bootstrap.config = config  # Use loaded config directly
            container, _ = bootstrap.setup()
            
            backtest = container.get("backtest")
            results = backtest.run()
            
            # Restore stdout
            sys.stdout.close()
            sys.stdout = original_stdout
            
            # Get performance metrics
            metrics = results.get("metrics", {})
            score = metrics.get(objective, 0.0)
            
            # Add to all results
            result_data = {
                "params": params,
                "score": score,
                "metrics": metrics
            }
            all_results.append(result_data)
            
            # Print result
            is_best = False
            if optimizer.best_score is None or (maximize and score > optimizer.best_score) or (not maximize and score < optimizer.best_score):
                is_best = True
            print_param_combination(params, score, is_best)
            
            return float(score)
        except Exception as e:
            # Restore stdout if exception occurred
            if 'original_stdout' in locals():
                sys.stdout.close()
                sys.stdout = original_stdout
            print(f"Error evaluating parameters {params}: {e}")
            return -999.0 if maximize else 999.0
    
    # Run optimization
    print(f"Starting optimization for {strategy_name}...")
    print(f"Objective: {'Maximize' if maximize else 'Minimize'} {objective}")
    start_time = time.time()
    
    results = optimizer.search(
        objective_function=objective_function,
        maximize=maximize,
        max_evaluations=max_evaluations,
        max_time=max_time
    )
    
    duration = time.time() - start_time
    
    # Print final results
    print("\n" + "="*60)
    print(f"Optimization completed in {duration:.2f} seconds")
    print(f"Evaluated {len(optimizer.results)}/{space.get_grid_size()} parameter combinations")
    print(f"Best parameters: {results['best_params']}")
    print(f"Best {objective}: {results['best_score']:.6f}")
    print("="*60)
    
    # Save results
    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save all results to CSV
    results_df = pd.DataFrame([
        {
            **{f"param_{k}": v for k, v in r['params'].items()},
            "score": r.get('score', None),
            **{f"metric_{k}": v for k, v in r.get('metrics', {}).items()}
        }
        for r in optimizer.results
    ])
    results_file = f"{args.output_dir}/optimization_results_{timestamp}.csv"
    results_df.to_csv(results_file, index=False)
    print(f"Results saved to {results_file}")
    
    return True

if __name__ == "__main__":
    try:
        success = run_optimization()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)