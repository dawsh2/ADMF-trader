#!/usr/bin/env python
"""
Script to run a complete grid search for MA crossover parameters and show trade results.
"""
import os
import sys
import yaml
import logging
import pandas as pd
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(message)s')  # Simplified format for cleaner output
logger = logging.getLogger()

def optimize_ma_crossover():
    """Run a comprehensive grid search for MA Crossover parameters."""
    print("\n===== MA CROSSOVER OPTIMIZATION GRID =====")
    
    # Define the parameter grid
    fast_range = range(2, 21, 1)  # 2-20 by 1
    slow_range = range(5, 51, 5)  # 5-50 by 5
    
    # Parameter combinations to test
    combinations = []
    for fast in fast_range:
        for slow in slow_range:
            if fast < slow:  # Ensure fast period is less than slow period
                combinations.append((fast, slow))
    
    print(f"Testing {len(combinations)} parameter combinations...")
    
    # Base configuration
    config_path = 'config/optimization_test.yaml'
    with open(config_path, 'r') as f:
        base_config = yaml.safe_load(f)
    
    # Ensure proper strategy configuration
    base_config['backtest']['strategy'] = 'ma_crossover'
    if 'ma_crossover' not in base_config['strategies']:
        if 'simple_ma_crossover' in base_config['strategies']:
            base_config['strategies']['ma_crossover'] = base_config['strategies'].pop('simple_ma_crossover')
        else:
            base_config['strategies']['ma_crossover'] = {
                'enabled': True,
                'symbols': base_config['backtest']['symbols'],
                'price_key': 'close'
            }
    
    # Ensure proper dates for data
    base_config['backtest']['start_date'] = '2024-03-26'
    base_config['backtest']['end_date'] = '2024-03-28'
    
    # Import required modules
    from src.core.system_bootstrap import Bootstrap
    
    # Results collection
    results = []
    
    # Header for results table
    print("\n{:<6} {:<6} {:<8} {:<9} {:<10} {:<10}".format(
        "FAST", "SLOW", "TRADES", "WIN RATE", "SHARPE", "PROFIT"
    ))
    print("-" * 60)
    
    # Test each combination
    for fast, slow in combinations:
        # Create a copy of the config for this run
        config = base_config.copy()
        
        # Set parameters for this run
        config['strategies']['ma_crossover']['fast_window'] = fast
        config['strategies']['ma_crossover']['slow_window'] = slow
        config['strategies']['ma_crossover']['price_key'] = 'close'
        
        try:
            # Initialize bootstrap
            bootstrap = Bootstrap()
            bootstrap.config = config
            container, _ = bootstrap.setup()
            
            # Run backtest
            backtest = container.get('backtest')
            backtest_results = backtest.run()
            
            # Extract results
            trades = backtest_results.get('trades', [])
            metrics = backtest_results.get('metrics', {})
            trade_count = len(trades)
            win_rate = metrics.get('win_rate', 0.0) * 100
            sharpe = metrics.get('sharpe_ratio', 0.0)
            total_return = metrics.get('total_return', 0.0) * 100
            
            # Store result
            result = {
                'fast': fast,
                'slow': slow,
                'trades': trade_count,
                'win_rate': win_rate,
                'sharpe': sharpe,
                'total_return': total_return
            }
            results.append(result)
            
            # Print result row
            print("{:<6} {:<6} {:<8} {:<9.2f}% {:<10.4f} {:<10.2f}%".format(
                fast, slow, trade_count, win_rate, sharpe, total_return
            ))
            
        except Exception as e:
            print(f"Error with fast={fast}, slow={slow}: {str(e)}")
    
    # Save results to CSV
    if results:
        results_df = pd.DataFrame(results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"ma_grid_results_{timestamp}.csv"
        results_df.to_csv(output_file, index=False)
        print(f"\nFull results saved to: {output_file}")
        
        # Show best combinations by trades, win rate, and return
        if not results_df.empty:
            print("\n----- OPTIMIZATION RESULTS -----")
            
            print("\nBest by TRADE COUNT:")
            trade_sorted = results_df.sort_values(by='trades', ascending=False).head(5)
            for i, (_, row) in enumerate(trade_sorted.iterrows(), 1):
                print(f"{i}. Fast={int(row['fast'])}, Slow={int(row['slow'])} → "
                     f"Trades: {int(row['trades'])}, Win: {row['win_rate']:.1f}%, Return: {row['total_return']:.2f}%")
            
            print("\nBest by WIN RATE (min 5 trades):")
            win_sorted = results_df[results_df['trades'] >= 5].sort_values(by='win_rate', ascending=False).head(5)
            if not win_sorted.empty:
                for i, (_, row) in enumerate(win_sorted.iterrows(), 1):
                    print(f"{i}. Fast={int(row['fast'])}, Slow={int(row['slow'])} → "
                         f"Win: {row['win_rate']:.1f}%, Trades: {int(row['trades'])}, Return: {row['total_return']:.2f}%")
            else:
                print("No combinations with 5+ trades")
            
            print("\nBest by RETURN:")
            return_sorted = results_df.sort_values(by='total_return', ascending=False).head(5)
            for i, (_, row) in enumerate(return_sorted.iterrows(), 1):
                print(f"{i}. Fast={int(row['fast'])}, Slow={int(row['slow'])} → "
                     f"Return: {row['total_return']:.2f}%, Trades: {int(row['trades'])}, Win: {row['win_rate']:.1f}%")
            
        return True
    
    print("No valid results were produced.")
    return False

if __name__ == "__main__":
    optimize_ma_crossover()
    sys.exit(0)