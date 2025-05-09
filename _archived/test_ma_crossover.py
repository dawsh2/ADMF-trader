#!/usr/bin/env python
# test_ma_crossover.py - Test script for MA Crossover strategy
import logging
from src.core.system_bootstrap import Bootstrap

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_ma_crossover():
    print("Testing MA Crossover strategy with fixed configuration...")
    
    # Initialize bootstrap with the fixed config
    bootstrap = Bootstrap(config_files=['config/test_ma.yaml'], log_level="INFO")
    container, config = bootstrap.setup()
    
    # Get the strategy
    strategy = container.get('strategy')
    print(f"Strategy name: {strategy.name}")
    print(f"Fast window: {strategy.fast_window}")
    print(f"Slow window: {strategy.slow_window}")
    print(f"Symbols: {strategy.symbols}")
    
    # Run backtest
    backtest = container.get('backtest')
    results = backtest.run()
    
    # Check results
    trades = results.get('trades', []) if results else []
    print(f"Trades generated: {len(trades)}")
    
    if trades:
        print("First few trades:")
        for i, trade in enumerate(trades[:3]):
            print(f"  Trade {i+1}: {trade['symbol']} {trade['direction']} @ {trade['price']}")
    
    return len(trades) > 0

if __name__ == "__main__":
    success = test_ma_crossover()
    print(f"Test {'succeeded' if success else 'failed'} (trades were {'generated' if success else 'not generated'})")
