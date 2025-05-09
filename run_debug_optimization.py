#!/usr/bin/env python
"""
Run optimization with detailed logging
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("optimization_detailed.log"),
        logging.StreamHandler()
    ]
)

# Import here to avoid circular imports
sys.path.append(os.getcwd())
from src.strategy.optimization.optimizer import StrategyOptimizer

def run_debug_optimization():
    """Run the optimization with detailed logging"""
    config_path = "config/ma_crossover_optimization.yaml"
    
    # Create optimizer with detailed logging
    optimizer = StrategyOptimizer(config_path)
    
    # Monkey patch the optimizer to add more detailed signal logging
    original_optimize = optimizer.optimize
    
    def patched_optimize():
        print("Starting optimization with detailed logging...")
        logging.info("Adding signal/order/trade event listeners")
        
        # Add this method to hook into the optimization process
        def hook_event_bus(context):
            if 'event_bus' in context:
                event_bus = context['event_bus']
                
                # Add signal listener
                def signal_listener(event):
                    logging.info(f"SIGNAL DETECTED: {event}")
                event_bus.subscribe('SIGNAL', signal_listener)
                
                # Add order listener
                def order_listener(event):
                    logging.info(f"ORDER DETECTED: {event}")
                event_bus.subscribe('ORDER', order_listener)
                
                # Add trade listener
                def trade_listener(event):
                    logging.info(f"TRADE DETECTED: {event}")
                event_bus.subscribe('TRADE', trade_listener)
        
        # Patch the _run_backtest_with_params method
        original_run_backtest = optimizer._run_backtest_with_params
        
        def patched_run_backtest(strategy_name, params, data_split, train_test_config):
            logging.info(f"Running backtest with params: {params}, split: {data_split}")
            result = original_run_backtest(strategy_name, params, data_split, train_test_config)
            
            # Check for trades
            trades = result.get('trades', [])
            logging.info(f"BACKTEST RESULT: {len(trades)} trades generated")
            if trades:
                for i, trade in enumerate(trades[:5]):
                    logging.info(f"Trade {i+1}: {trade}")
            else:
                logging.warning("NO TRADES GENERATED!")
            
            return result
        
        # Apply monkey patches
        optimizer._run_backtest_with_params = patched_run_backtest
        
        # Run the original optimize method
        return original_optimize()
    
    # Apply the monkey patch
    optimizer.optimize = patched_optimize
    
    # Run optimization
    results = optimizer.optimize()
    return results

if __name__ == "__main__":
    run_debug_optimization()
