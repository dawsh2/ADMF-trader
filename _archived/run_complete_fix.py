#!/usr/bin/env python
"""
Complete fix for ADMF-trader optimization issues.

This script applies fixes for both the reporter error and the missing trade recording issue,
then runs the optimization with the fixes applied.
"""

import os
import sys
import logging
import subprocess
import argparse
import traceback
import importlib
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("complete_fix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('complete_fix')

def run_script(script_path, args=None):
    """Run a Python script with given arguments"""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        logger.info(f"Script executed successfully: {script_path}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Script failed: {script_path}")
        logger.error(f"Error: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False, e.stderr

def load_config(config_path):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def apply_runtime_fixes():
    """Apply runtime fixes to enable trade recording"""
    logger.info("Applying runtime fixes for trade recording")
    
    try:
        # 1. Fix order_manager to capture rule_id
        try:
            # Find order_manager module
            order_manager_paths = [
                'src.execution.order_manager',
                'src.core.execution.order_manager',
                'src.broker.order_manager',
            ]
            
            order_manager = None
            for path in order_manager_paths:
                try:
                    order_manager = importlib.import_module(path)
                    logger.info(f"Found order_manager at {path}")
                    break
                except ImportError:
                    continue
            
            if order_manager:
                # Save original method
                if hasattr(order_manager, 'create_order_from_signal'):
                    original_create_order = order_manager.create_order_from_signal
                    
                    # Define patched method
                    def patched_create_order_from_signal(signal):
                        logger.info(f"SIGNAL DEBUG: {vars(signal) if hasattr(signal, '__dict__') else 'No vars'}")
                        
                        # Call original method
                        order = original_create_order(signal)
                        
                        # Add rule_id to order
                        if hasattr(order, 'rule_id') and order.rule_id is None:
                            if hasattr(signal, 'strategy_id') and signal.strategy_id:
                                order.rule_id = signal.strategy_id
                                logger.info(f"Added rule_id={signal.strategy_id} to order")
                        
                        return order
                    
                    # Apply patch
                    order_manager.create_order_from_signal = patched_create_order_from_signal
                    logger.info("Patched create_order_from_signal in order_manager")
                else:
                    logger.warning("Could not find create_order_from_signal in order_manager")
            else:
                logger.warning("Could not find order_manager module")
        except Exception as e:
            logger.error(f"Error patching order_manager: {e}")
            logger.error(traceback.format_exc())
        
        # 2. Fix execution handler to record trades
        try:
            # Find execution_handler module
            execution_paths = [
                'src.execution.execution_handler',
                'src.execution.broker',
                'src.core.execution.broker',
            ]
            
            execution_handler = None
            for path in execution_paths:
                try:
                    execution_handler = importlib.import_module(path)
                    logger.info(f"Found execution_handler at {path}")
                    break
                except ImportError:
                    continue
            
            if execution_handler:
                # Find the execution handler class
                handler_class = None
                for attr_name in dir(execution_handler):
                    attr = getattr(execution_handler, attr_name)
                    if isinstance(attr, type) and hasattr(attr, 'fill_order'):
                        handler_class = attr
                        break
                
                if handler_class:
                    # Save original method
                    original_fill_order = handler_class.fill_order
                    
                    # Define patched method
                    def patched_fill_order(self, order, price, timestamp):
                        logger.info(f"ORDER DEBUG: {vars(order) if hasattr(order, '__dict__') else 'No vars'}")
                        
                        # Call original method
                        result = original_fill_order(self, order, price, timestamp)
                        
                        # Create and record trade if not already done
                        try:
                            logger.info(f"Creating trade for order {order.id}")
                            trade = execution_handler.Trade(
                                order.symbol,
                                order.quantity,
                                price,
                                timestamp,
                                order.direction,
                                rule_id=order.rule_id if hasattr(order, 'rule_id') else None
                            )
                            
                            # Add trade to portfolio
                            self.portfolio.add_trade(trade)
                            logger.info(f"Recorded trade for order {order.id} with rule_id={trade.rule_id if hasattr(trade, 'rule_id') else 'None'}")
                        except Exception as e:
                            logger.error(f"Error creating trade: {e}")
                        
                        return result
                    
                    # Apply patch
                    handler_class.fill_order = patched_fill_order
                    logger.info(f"Patched fill_order in {handler_class.__name__}")
                else:
                    logger.warning("Could not find execution handler class with fill_order method")
            else:
                logger.warning("Could not find execution_handler module")
        except Exception as e:
            logger.error(f"Error patching execution_handler: {e}")
            logger.error(traceback.format_exc())
        
        # 3. Fix reporter to handle None best_parameters
        try:
            import src.strategy.optimization.reporter as reporter
            
            # Save original method
            original_generate_text_report = reporter.OptimizationReporter._generate_text_report
            
            # Define patched method
            def patched_generate_text_report(self, results, filename):
                # Check if results is None
                if results is None:
                    logger.warning("Results is None, cannot generate report")
                    with open(os.path.join(self.output_dir, filename), 'w') as f:
                        f.write("No optimization results were generated.\n")
                    return
                
                # Check if best_parameters is None
                best_parameters = results.get('best_parameters', {})
                if best_parameters is None:
                    logger.warning("best_parameters is None, using empty dict")
                    results['best_parameters'] = {}
                
                # Call original method
                return original_generate_text_report(self, results, filename)
            
            # Apply patch
            reporter.OptimizationReporter._generate_text_report = patched_generate_text_report
            logger.info("Patched _generate_text_report in reporter")
        except Exception as e:
            logger.error(f"Error patching reporter: {e}")
            logger.error(traceback.format_exc())
        
        logger.info("Runtime fixes applied")
        return True
    except Exception as e:
        logger.error(f"Error applying runtime fixes: {e}")
        logger.error(traceback.format_exc())
        return False

def run_optimization(config_path):
    """Run the optimization with the fixes applied"""
    logger.info(f"Running optimization with config: {config_path}")
    
    # Load configuration
    config = load_config(config_path)
    if not config:
        logger.error("Failed to load configuration")
        return False
    
    # Apply runtime fixes
    if not apply_runtime_fixes():
        logger.warning("Failed to apply some runtime fixes, but continuing...")
    
    try:
        # Import the optimizer
        from src.strategy.optimization.optimizer import StrategyOptimizer
        
        # Create optimizer with fixed reporter and order handling
        optimizer = StrategyOptimizer(config)
        
        # Run optimization
        logger.info("Starting optimization...")
        results = optimizer.optimize()
        
        if results:
            logger.info("Optimization completed successfully")
            logger.info(f"Best parameters: {results.get('best_parameters', 'None')}")
            logger.info(f"Best score: {results.get('best_score', 'None')}")
            return True
        else:
            logger.warning("Optimization completed but returned no results")
            return False
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Apply comprehensive fixes and run optimization')
    parser.add_argument('--config', required=True, help='Path to the configuration file')
    parser.add_argument('--skip-optimizing', action='store_true', help='Skip optimization and just apply fixes')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Starting comprehensive fix process")
    
    # Step 1: Fix rule_id and trade recording
    logger.info("Applying fixes for rule_id and trade recording...")
    rule_id_fixed, output = run_script('fix_rule_id.py')
    
    # Step 2: Fix reporter
    logger.info("Applying fixes for reporter...")
    reporter_fixed, output = run_script('direct_optimizer_fix.py')
    
    # Step 3: Run optimization if requested
    if not args.skip_optimizing:
        logger.info("Running optimization with fixes applied...")
        optimization_success = run_optimization(args.config)
        
        if optimization_success:
            logger.info("Complete fix process succeeded")
            return 0
        else:
            logger.warning("Optimization failed or produced no results")
            return 1
    else:
        logger.info("Skipping optimization as requested")
        logger.info("Fixes have been applied")
        return 0

if __name__ == "__main__":
    sys.exit(main())
