#!/usr/bin/env python
"""
Run optimization after fixing import issues
"""

import os
import sys
import logging
import subprocess
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fixed_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fixed_opt')

def run_command(cmd, cwd=None):
    """Run a command and log the output"""
    logger.info(f"Running command: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        logger.info(f"Command completed with exit code {result.returncode}")
        logger.info(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"Error: {e.stderr}")
        return False

def main():
    """Run the optimization after fixing imports"""
    # Step 1: Fix import paths
    logger.info("Step 1: Fixing import paths...")
    if not run_command([sys.executable, "fix_import_paths.py"]):
        logger.error("Failed to fix import paths, aborting.")
        return
    
    # Step 2: Run the optimization
    logger.info("Step 2: Running optimization...")
    
    # Directly run the optimizer in this process
    try:
        logger.info("Importing required modules...")
        
        # Import here after fixes have been applied
        from src.strategy.optimization.optimizer import StrategyOptimizer
        
        logger.info("Imported StrategyOptimizer successfully")
        
        # Set up debugging for event handlers
        def setup_event_debugging(context):
            """Set up debugging for events"""
            if 'event_bus' in context:
                event_bus = context['event_bus']
                logger.info(f"Setting up event debugging on {event_bus}")
                
                # Add debug listeners
                from src.core.events.event_types import EventType
                
                def debug_signal_listener(event):
                    logger.info(f"DEBUG SIGNAL EVENT: {event}")
                
                def debug_order_listener(event):
                    logger.info(f"DEBUG ORDER EVENT: {event}")
                
                def debug_trade_listener(event):
                    logger.info(f"DEBUG TRADE EVENT: {event}")
                
                # Subscribe to events
                if hasattr(event_bus, 'subscribe'):
                    event_bus.subscribe(EventType.SIGNAL, debug_signal_listener)
                    event_bus.subscribe(EventType.ORDER, debug_order_listener)
                    event_bus.subscribe(EventType.TRADE, debug_trade_listener)
                    logger.info("Added debug event listeners")
                else:
                    logger.warning("Event bus does not have a subscribe method")
        
        # Create and run the optimizer
        logger.info("Creating optimizer...")
        config_path = "config/ma_crossover_optimization.yaml"
        optimizer = StrategyOptimizer(config_path)
        
        # Add our debug hooks to the optimizer
        if hasattr(optimizer, 'run_backtest_with_params'):
            original_run = optimizer.run_backtest_with_params
            def debug_run(*args, **kwargs):
                logger.info(f"Running backtest with params: {args}, {kwargs}")
                result = original_run(*args, **kwargs)
                trades = result.get('trades', [])
                logger.info(f"Backtest completed with {len(trades)} trades")
                return result
            optimizer.run_backtest_with_params = debug_run
            logger.info("Added backtest debug hook")
        
        # Run the optimization
        logger.info("Running optimization...")
        results = optimizer.optimize()
        
        # Check the results
        all_results = results.get('all_results', [])
        best_params = results.get('best_parameters', {})
        
        logger.info(f"Optimization completed with {len(all_results)} parameter combinations")
        logger.info(f"Best parameters: {best_params}")
        
        # Check if any trades were generated
        trades_found = False
        for result_set in all_results:
            train_result = result_set.get('train_result', {})
            test_result = result_set.get('test_result', {})
            
            train_trades = train_result.get('trades', [])
            test_trades = test_result.get('trades', [])
            
            if train_trades or test_trades:
                trades_found = True
                logger.info(f"Found trades for parameters: {result_set.get('parameters', {})}")
                logger.info(f"Train trades: {len(train_trades)}, Test trades: {len(test_trades)}")
        
        if not trades_found:
            logger.warning("NO TRADES WERE GENERATED for any parameter combination!")
        
        logger.info("Optimization process completed successfully")
    
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
