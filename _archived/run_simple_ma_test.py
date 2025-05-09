#!/usr/bin/env python
"""
Simple script to test MA crossover with varying parameters and report trade counts.
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

def run_ma_test():
    """Test MA crossover with different parameters."""
    print("\n===== MOVING AVERAGE CROSSOVER PARAMETER TEST =====")
    print("Testing combinations of fast and slow windows to generate trades")
    
    # Create a simple test config
    base_config = {
        'backtest': {
            'initial_capital': 100000.0,
            'symbols': ['HEAD'],
            'timeframe': '1min',
            'data_source': 'csv',
            'data_dir': './data',
            'start_date': '2024-03-26',
            'end_date': '2024-03-28',
            'strategy': 'simple_ma_crossover'
        },
        'strategies': {
            'simple_ma_crossover': {
                'enabled': True,
                'symbols': ['HEAD'],
                'price_key': 'close'
            }
        },
        'risk_manager': {
            'type': 'simple',
            'position_sizing_method': 'fixed',
            'position_size': 1,
            'max_position_size': 10
        }
    }
    
    # Fast and slow window combinations to test
    fast_windows = [2, 3, 4, 5, 8, 10]
    slow_windows = [5, 8, 10, 15, 20, 30]
    
    # Import the necessary modules
    from src.core.system_bootstrap import Bootstrap
    
    # Results table
    results = []
    
    # Header for results table
    print("\n{:<6} {:<6} {:<8} {:<9} {:<10} {:<10}".format(
        "FAST", "SLOW", "TRADES", "WIN RATE", "BEST SCORE", "AVG TRADE"
    ))
    print("-" * 55)
    
    # Test each combination
    for fast in fast_windows:
        for slow in slow_windows:
            # Skip invalid combinations
            if fast >= slow:
                continue
                
            # Update strategy parameters
            config = base_config.copy()
            config['strategies']['simple_ma_crossover'].update({
                'fast_window': fast,
                'slow_window': slow
            })
            
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
                avg_trade = metrics.get('avg_trade', 0.0)
                
                # Store results
                results.append({
                    'fast': fast,
                    'slow': slow,
                    'trades': trade_count,
                    'win_rate': win_rate,
                    'sharpe': sharpe,
                    'avg_trade': avg_trade
                })
                
                # Print results
                print("{:<6} {:<6} {:<8} {:<9.2f}% {:<10.4f} {:<10.4f}".format(
                    fast, slow, trade_count, win_rate, sharpe, avg_trade
                ))
                
            except Exception as e:
                print(f"Error testing fast={fast}, slow={slow}: {str(e)}")
    
    # Save results to CSV
    if results:
        results_df = pd.DataFrame(results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"./ma_test_results_{timestamp}.csv"
        results_df.to_csv(output_file, index=False)
        print(f"\nResults saved to: {output_file}")
        
        # Show best combinations by trade count
        print("\nBest combinations by trade count:")
        trade_sorted = results_df.sort_values(by='trades', ascending=False).head(5)
        for i, (_, row) in enumerate(trade_sorted.iterrows(), 1):
            print(f"{i}. Fast={row['fast']}, Slow={row['slow']} → "
                 f"Trades: {row['trades']}, Win rate: {row['win_rate']:.2f}%")
        
        return True
    
    return False

if __name__ == "__main__":
    run_ma_test()
    sys.exit(0)