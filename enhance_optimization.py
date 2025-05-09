#!/usr/bin/env python
"""
Script to enhance optimization output by showing parameter combinations and their scores.
"""
import os
import sys
import yaml
import argparse
import logging
import pandas as pd
from datetime import datetime

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_enhanced_optimization():
    """Run optimization with better output showing parameter combinations."""
    parser = argparse.ArgumentParser(description="Enhanced MA Strategy Optimization")
    parser.add_argument("--config", required=True, help="Configuration file path")
    parser.add_argument("--max-evals", type=int, default=20, help="Maximum evaluations to run")
    parser.add_argument("--log-level", default="WARNING", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       help="Logging level for system components")
    args = parser.parse_args()
    
    # Suppress system logging
    for logger_name in ["matplotlib", "urllib3", "pandas", "src"]:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    try:
        strategy_name = config["backtest"]["strategy"]
        strategy_config = config["strategies"][strategy_name]
        if not strategy_config.get("enabled", False):
            logger.error(f"Strategy {strategy_name} is not enabled in config")
            return False
    except KeyError as e:
        logger.error(f"Missing configuration key: {e}")
        return False
    
    # Set up optimization parameters
    if "optimization" not in config:
        logger.error("No optimization section found in config")
        return False
    
    opt_config = config["optimization"]
    if not opt_config.get("enabled", False):
        logger.error("Optimization not enabled in config")
        return False
    
    # Show optimization plan
    param_space = opt_config.get("parameter_space", {}).get(strategy_name, {})
    if not param_space:
        logger.error(f"No parameter space defined for {strategy_name}")
        return False
    
    # Print optimization plan
    print("\n" + "="*60)
    print(f"OPTIMIZATION PLAN FOR {strategy_name.upper()}")
    print("="*60)
    print(f"Maximum evaluations: {args.max_evals}")
    print(f"Optimizing for: {opt_config.get('objective', 'sharpe_ratio')}")
    print(f"{'Maximizing' if opt_config.get('maximize', True) else 'Minimizing'} objective\n")
    
    print("Parameter space:")
    for param, settings in param_space.items():
        param_type = settings.get("type")
        if param_type == "integer":
            print(f"  {param}: {settings.get('min')} to {settings.get('max')} (step: {settings.get('step', 1)})")
        elif param_type == "float":
            print(f"  {param}: {settings.get('min')} to {settings.get('max')} (step: {settings.get('step', 0.1)})")
        elif param_type == "categorical":
            print(f"  {param}: {', '.join(str(x) for x in settings.get('options', []))}")
    print("="*60 + "\n")
    
    # Modify config for optimization
    config["optimization"]["max_evaluations"] = args.max_evals
    
    # Import required modules here to reduce overhead
    from src.core.system_bootstrap import Bootstrap
    from src.strategy.optimization import ParameterSpace, GridSearch
    
    # Create parameter space
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
    
    # Create optimizer
    optimizer = GridSearch(space)
    
    # Store results
    all_results = []
    
    # Define callback for reporting results
    def report_result(params, score, is_best):
        """Report optimization progress."""
        # Format for output
        params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        status = "★ BEST" if is_best else ""
        print(f"[{len(all_results)+1}/{args.max_evals}] {params_str} → Score: {score:.6f} {status}")
    
    # Define objective function
    def objective_function(params):
        """Run backtest with parameters and return score."""
        # Output parameter set being tested
        params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        print(f"\nTesting parameters: {params_str}")
        
        try:
            # Update strategy parameters in config
            config["strategies"][strategy_name].update(params)
            
            # Set up system
            bootstrap = Bootstrap(log_level=args.log_level)
            bootstrap.config = config
            container, _ = bootstrap.setup()
            
            # Run backtest
            backtest = container.get("backtest")
            results = backtest.run()
            
            # Get score from metrics
            metrics = results.get("metrics", {})
            score = metrics.get(opt_config.get("objective", "sharpe_ratio"), 0.0)
            
            # Store result
            result_data = {
                **params,
                "score": score,
                **{f"metric_{k}": v for k, v in metrics.items()}
            }
            all_results.append(result_data)
            
            return float(score)
        except Exception as e:
            logger.error(f"Error evaluating parameters {params}: {e}")
            return -999.0 if opt_config.get("maximize", True) else 999.0
    
    # Run optimization
    print(f"Starting optimization...")
    start_time = datetime.now()
    
    results = optimizer.search(
        objective_function=objective_function,
        maximize=opt_config.get("maximize", True),
        max_evaluations=args.max_evals,
        callback=report_result
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Print results summary
    print("\n" + "="*60)
    print("OPTIMIZATION RESULTS")
    print("="*60)
    print(f"Completed in {duration:.2f} seconds")
    print(f"Evaluated {len(optimizer.results)}/{space.get_grid_size()} parameter combinations")
    print(f"Best parameters: {results['best_params']}")
    print(f"Best score: {results['best_score']:.6f}")
    print("="*60)
    
    # Save results to CSV
    if all_results:
        output_dir = opt_config.get("output", {}).get("results_dir", "./optimization_results")
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/optimization_results_{timestamp}.csv"
        
        results_df = pd.DataFrame(all_results)
        results_df.to_csv(output_file, index=False)
        print(f"\nResults saved to: {output_file}")
        
        # Print top results
        top_n = min(5, len(results_df))
        if top_n > 0:
            print(f"\nTop {top_n} parameter combinations:")
            sorted_df = results_df.sort_values(by="score", ascending=not opt_config.get("maximize", True))
            for i, (_, row) in enumerate(sorted_df.head(top_n).iterrows(), 1):
                params_str = ", ".join([f"{k}={v}" for k, v in row.items() 
                                      if not (k.startswith("metric_") or k == "score")])
                print(f"{i}. {params_str} → Score: {row['score']:.6f}")
    
    return True

if __name__ == "__main__":
    success = run_enhanced_optimization()
    sys.exit(0 if success else 1)