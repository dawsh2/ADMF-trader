#!/usr/bin/env python
"""
Runs the trading system with minimal console output.
"""
import os
import sys
import logging
import argparse

# Import the main function
from main import main

def run_with_minimal_output():
    """Run main with minimal console output"""
    parser = argparse.ArgumentParser(description="ADMF-Trader with Minimal Output")
    
    # Add all the arguments from the main script
    parser.add_argument("--config", required=True, help="Configuration file path")
    parser.add_argument("--output-dir", default="./results", help="Results output directory")
    parser.add_argument("--data-dir", default="./data", help="Data directory")
    parser.add_argument("--log-level", default="ERROR", 
                      choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Logging level (defaults to ERROR for minimal output)")
    
    # Data generation options
    parser.add_argument("--generate-data", action="store_true", 
                      help="Generate synthetic data before running backtest")
    parser.add_argument("--data-type", default="multi_regime", 
                      choices=["multi_regime", "trend", "mean_reversion", "volatility", "random"],
                      help="Type of synthetic data to generate")
    parser.add_argument("--plot-data", action="store_true", 
                      help="Plot generated data")
    
    # Output control options
    parser.add_argument("--quiet", action="store_true", 
                      help="Suppress all output except final results")
    parser.add_argument("--only-optimal", action="store_true", 
                      help="Only show the optimal parameters and performance")
    
    args = parser.parse_args()
    
    # Set root logger to the specified level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Silence all common modules
    for module in ["matplotlib", "urllib3", "pandas", "src"]:
        logging.getLogger(module).setLevel(logging.CRITICAL)
    
    # Redirect stdout if quiet mode is enabled
    original_stdout = sys.stdout
    if args.quiet:
        sys.stdout = open(os.devnull, 'w')
    
    # Create modified argv for main()
    sys.argv = [sys.argv[0]]
    for key, value in vars(args).items():
        if key not in ('quiet', 'only_optimal'):  # Skip our custom args
            if isinstance(value, bool):
                if value:
                    sys.argv.append(f"--{key.replace('_', '-')}")
            elif isinstance(value, list):
                if value:
                    sys.argv.append(f"--{key.replace('_', '-')}")
                    sys.argv.extend(value)
            elif value is not None:
                sys.argv.append(f"--{key.replace('_', '-')}")
                sys.argv.append(str(value))
    
    try:
        # Run the main function
        success = main()
        
        # Restore stdout if it was redirected
        if args.quiet:
            sys.stdout = original_stdout
            
        # Print minimal result if successful
        if success:
            # Get the results file for the configuration
            config_name = os.path.splitext(os.path.basename(args.config))[0]
            strategy_output_dir = os.path.join(args.output_dir, config_name)
            
            if args.only_optimal and "optimization" in config_name:
                # Try to find the latest optimization results file
                results_dir = "./optimization_results"
                result_files = []
                if os.path.exists(results_dir):
                    result_files = [f for f in os.listdir(results_dir) if f.startswith("optimization_results_")]
                
                if result_files:
                    latest_file = sorted(result_files)[-1]
                    result_path = os.path.join(results_dir, latest_file)
                    print(f"Optimal parameters found in: {result_path}")
                else:
                    print("Optimization completed successfully.")
            else:
                print(f"Backtest completed successfully. Results in {strategy_output_dir}")
        else:
            print("Backtest failed to produce results.")
            
        return success
    except Exception as e:
        # Restore stdout if it was redirected
        if args.quiet:
            sys.stdout = original_stdout
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = run_with_minimal_output()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)