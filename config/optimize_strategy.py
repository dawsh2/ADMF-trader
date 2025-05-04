# optimize_strategy.py
import pandas as pd
import numpy as np
import os
import yaml
import time
from datetime import datetime

from src.core.system_bootstrap import Bootstrap
from src.strategy.optimization import ParameterSpace, GridSearch, RandomSearch
from src.execution.backtest.backtest import BacktestCoordinator

def main():
    print("Starting strategy optimization...")
    
    # Load configuration
    config_path = "config/optimization_test.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Set up parameter space
    space = ParameterSpace("ma_crossover_optimization")
    space.add_integer("fast_window", 2, 20, 1)
    space.add_integer("slow_window", 10, 50, 5)
    space.add_categorical("price_key", ["open", "high", "low", "close"])
    
    print(f"Parameter space created with {space.get_grid_size()} combinations")
    
    # Choose optimizer (Grid Search or Random Search)
    optimizer = GridSearch(space)
    # optimizer = RandomSearch(space, seed=42)
    
    # Define objective function
    def objective_function(params):
        try:
            # Update strategy parameters
            config["strategies"]["ma_crossover"].update(params)
            
            # Run backtest with these parameters
            bootstrap = Bootstrap(config_files=[])
            bootstrap.config = config  # Use our loaded config directly
            container, _ = bootstrap.setup()
            
            backtest = container.get("backtest")
            results = backtest.run(
                symbols=config["backtest"]["symbols"],
                start_date=config["backtest"]["start_date"],
                end_date=config["backtest"]["end_date"],
                initial_capital=config["backtest"]["initial_capital"],
                timeframe=config["backtest"]["timeframe"]
            )
            
            # Get performance metrics
            metrics = results.get("metrics", {})
            sharpe = metrics.get("sharpe_ratio", 0.0)
            return float(sharpe)
        except Exception as e:
            print(f"Error evaluating parameters {params}: {e}")
            return -999.0  # Return very low score for failed evaluations
    
    # Run optimization
    print("Starting optimization...")
    max_evaluations = 20  # Limit for testing
    start_time = time.time()
    
    # For GridSearch
    results = optimizer.search(
        objective_function=objective_function,
        maximize=True,
        max_evaluations=max_evaluations
    )
    
    # For RandomSearch
    # results = optimizer.search(
    #     objective_function=objective_function,
    #     num_samples=max_evaluations,
    #     maximize=True
    # )
    
    duration = time.time() - start_time
    
    # Print results
    print(f"\nOptimization completed in {duration:.2f} seconds")
    print(f"Evaluated {len(optimizer.results)} parameter combinations")
    print(f"Best parameters: {results['best_params']}")
    print(f"Best Sharpe ratio: {results['best_score']}")
    
    # Save results
    output_dir = "optimization_results"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save all results to CSV
    results_df = pd.DataFrame(optimizer.results)
    results_df.to_csv(f"{output_dir}/optimization_results_{timestamp}.csv", index=False)
    print(f"Results saved to {output_dir}/optimization_results_{timestamp}.csv")

if __name__ == "__main__":
    main()
