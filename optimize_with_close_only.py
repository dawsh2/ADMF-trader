#!/usr/bin/env python
"""
Script to run optimization using only close prices with a wider range of fast/slow windows.
"""
import os
import sys
import yaml
import argparse
import logging
import time
import pandas as pd
from datetime import datetime

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables for tracking best results
best_score = None
best_params = None

def run_close_optimization():
    """Run optimization using only close prices and more window variations."""
    parser = argparse.ArgumentParser(description="MA Strategy Optimization (Close Prices Only)")
    parser.add_argument("--config", required=True, help="Configuration file path")
    parser.add_argument("--max-evals", type=int, default=30, help="Maximum evaluations to run")
    parser.add_argument("--min-fast", type=int, default=2, help="Minimum fast window")
    parser.add_argument("--max-fast", type=int, default=50, help="Maximum fast window")
    parser.add_argument("--min-slow", type=int, default=10, help="Minimum slow window")
    parser.add_argument("--max-slow", type=int, default=100, help="Maximum slow window")
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
    
    # Override configuration to use only close prices
    try:
        strategy_name = config["backtest"]["strategy"]
        config["strategies"][strategy_name]["price_key"] = "close"
    except KeyError as e:
        logger.error(f"Missing configuration key: {e}")
        return False
    
    # Ensure optimization is enabled
    if "optimization" not in config:
        config["optimization"] = {}
    
    config["optimization"]["enabled"] = True
    config["optimization"]["method"] = "grid_search"
    config["optimization"]["max_evaluations"] = args.max_evals
    config["optimization"]["objective"] = "sharpe_ratio"
    config["optimization"]["maximize"] = True
    
    # Set up parameter space with close price only but wider window ranges
    param_space = {
        "fast_window": {
            "type": "integer",
            "min": args.min_fast,
            "max": args.max_fast,
            "step": 3
        },
        "slow_window": {
            "type": "integer",
            "min": args.min_slow,
            "max": args.max_slow,
            "step": 5
        }
    }
    
    config["optimization"]["parameter_space"] = {
        strategy_name: param_space
    }
    
    # Print optimization plan
    print("\n" + "="*60)
    print(f"CLOSE-PRICE ONLY OPTIMIZATION FOR {strategy_name.upper()}")
    print("="*60)
    print(f"Maximum evaluations: {args.max_evals}")
    print(f"Optimizing for: {config['optimization']['objective']}")
    print(f"Price key: close (fixed)")
    
    print("\nParameter space:")
    print(f"  fast_window: {args.min_fast} to {args.max_fast} (step: 3)")
    print(f"  slow_window: {args.min_slow} to {args.max_slow} (step: 5)")
    
    print("\nNote: A wider range of parameters is being tested to find")
    print("      meaningful signals in the data.\n")
    print("="*60 + "\n")
    
    # Import required modules
    from src.core.system_bootstrap import Bootstrap
    from src.strategy.optimization import ParameterSpace, GridSearch
    
    # Create parameter space
    space = ParameterSpace(f"{strategy_name}_optimization")
    space.add_integer("fast_window", args.min_fast, args.max_fast, 3)
    space.add_integer("slow_window", args.min_slow, args.max_slow, 5)
    
    # Create optimizer
    optimizer = GridSearch(space)
    
    # Store results
    all_results = []
    
    # Define objective function
    def objective_function(params):
        """Run backtest with parameters and return score."""
        global best_score, best_params
        
        # Add fixed price_key
        params["price_key"] = "close"
        
        # Output parameter set being tested
        params_str = f"fast={params['fast_window']}, slow={params['slow_window']}"
        print(f"\nTesting: {params_str}")
        
        # Add small delay to make output more readable
        time.sleep(0.1)
        
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
            
            # Get metrics
            metrics = results.get("metrics", {})
            trades = results.get("trades", [])
            score = metrics.get(config["optimization"]["objective"], 0.0)
            
            # Check if this is best score
            is_best = False
            if best_score is None or score > best_score:
                is_best = True
                best_score = score
                best_params = params.copy()
            
            # Output result
            trade_count = len(trades) if trades is not None else 0
            status = "★ BEST" if is_best else ""
            win_rate = metrics.get("win_rate", 0.0)
            
            print(f"Result: Score={score:.4f}, Trades={trade_count}, Win rate={win_rate:.1f}% {status}")
            
            # Store result
            result_data = {
                **params,
                "score": score,
                "trade_count": trade_count,
                "win_rate": win_rate,
                **{f"metric_{k}": v for k, v in metrics.items()}
            }
            all_results.append(result_data)
            
            return float(score)
        except Exception as e:
            logger.error(f"Error evaluating parameters {params}: {e}")
            return -999.0
    
    # Run optimization
    print(f"Starting optimization...")
    start_time = datetime.now()
    
    results = optimizer.search(
        objective_function=objective_function,
        maximize=config["optimization"]["maximize"],
        max_evaluations=args.max_evals
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Print results summary
    print("\n" + "="*60)
    print("OPTIMIZATION RESULTS")
    print("="*60)
    print(f"Completed in {duration:.2f} seconds")
    print(f"Evaluated {len(optimizer.results)} parameter combinations")
    print(f"Best parameters: fast={results['best_params']['fast_window']}, slow={results['best_params']['slow_window']}")
    print(f"Best score: {results['best_score']:.6f}")
    print("="*60)
    
    # Save results to CSV
    if all_results:
        output_dir = "./optimization_results"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/close_optimization_{timestamp}.csv"
        
        results_df = pd.DataFrame(all_results)
        results_df.to_csv(output_file, index=False)
        print(f"\nResults saved to: {output_file}")
        
        # Print top 5 results or all if less than 5
        results_df = results_df.sort_values(by="score", ascending=False)
        top_n = min(5, len(results_df))
        
        if top_n > 0:
            print(f"\nTop {top_n} parameter combinations:")
            for i, (_, row) in enumerate(results_df.head(top_n).iterrows(), 1):
                print(f"{i}. fast={row['fast_window']}, slow={row['slow_window']} → "
                     f"Score: {row['score']:.4f}, Trades: {row['trade_count']}, "
                     f"Win rate: {row['win_rate']:.1f}%")
    
    return True

if __name__ == "__main__":
    success = run_close_optimization()
    sys.exit(0 if success else 1)