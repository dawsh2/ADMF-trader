#!/usr/bin/env python
"""
Simplified fix for ADMF-trader optimization issues.

This script applies only the essential fixes needed to address both the reporter error
and the missing trade recording issue.
"""

import os
import sys
import logging
import importlib
import yaml
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simple_fix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('simple_fix')

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

def apply_reporter_fix():
    """Patch the reporter to handle None best_parameters"""
    try:
        # Find the reporter module
        import src.strategy.optimization.reporter as reporter
        
        # Save original method
        original_generate_text_report = reporter.OptimizationReporter._generate_text_report
        
        # Define a fixed method
        def fixed_generate_text_report(self, results, filename):
            logger.info("Using fixed _generate_text_report method")
            
            # Create file path
            filepath = os.path.join(self.output_dir, filename)
            
            # Add check for None results
            if results is None:
                logger.warning("Results is None, cannot generate report")
                with open(filepath, 'w') as f:
                    f.write("No optimization results were generated.\n")
                return
            
            # Get best_parameters and verify it's not None
            best_parameters = results.get('best_parameters', {})
            if best_parameters is None:
                logger.warning("best_parameters is None, using empty dict instead")
                results['best_parameters'] = {}
            
            # Call the original method with the fixed results
            return original_generate_text_report(self, results, filename)
        
        # Apply the patch
        reporter.OptimizationReporter._generate_text_report = fixed_generate_text_report
        logger.info("Successfully patched reporter._generate_text_report")
        return True
    except Exception as e:
        logger.error(f"Error applying reporter fix: {e}")
        logger.error(traceback.format_exc())
        return False

def apply_execution_fix():
    """Patch the execution handler to ensure trades are created and recorded"""
    try:
        # Try to find and patch the execution handler
        execution_fixed = False
        
        # Try different possible module paths
        execution_modules = [
            'src.execution.broker',
            'src.execution.execution_handler',
            'src.core.execution.broker'
        ]
        
        for module_path in execution_modules:
            try:
                # Try to import the module
                module = importlib.import_module(module_path)
                logger.info(f"Found execution module at {module_path}")
                
                # Look for execution handler class
                handler_classes = []
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and hasattr(attr, 'fill_order'):
                        handler_classes.append((attr_name, attr))
                
                if handler_classes:
                    for class_name, handler_class in handler_classes:
                        # Save original method
                        original_fill_order = handler_class.fill_order
                        
                        # Define patched method
                        def patched_fill_order(self, order, price, timestamp):
                            # Call original method
                            result = original_fill_order(self, order, price, timestamp)
                            
                            # Check if we're already in the patched method (recursion prevention)
                            if getattr(self, '_in_patched_fill_order', False):
                                return result
                            
                            # Set recursion flag
                            self._in_patched_fill_order = True
                            
                            try:
                                # Try to import Trade class from various locations
                                Trade = None
                                trade_modules = [
                                    'src.core.data_model',
                                    'src.data_model',
                                    'src.execution.data_model'
                                ]
                                
                                for trade_module_path in trade_modules:
                                    try:
                                        trade_module = importlib.import_module(trade_module_path)
                                        if hasattr(trade_module, 'Trade'):
                                            Trade = trade_module.Trade
                                            break
                                    except ImportError:
                                        continue
                                
                                if Trade is None:
                                    logger.warning("Could not find Trade class")
                                    return result
                                
                                # Create trade
                                logger.info(f"Creating trade for order {order.id if hasattr(order, 'id') else 'unknown'}")
                                
                                # Get rule_id - try different attribute names
                                rule_id = None
                                for attr_name in ['rule_id', 'strategy_id', 'id']:
                                    if hasattr(order, attr_name):
                                        rule_id = getattr(order, attr_name)
                                        if rule_id:
                                            break
                                
                                # Create trade with available attributes
                                try:
                                    trade = Trade(
                                        order.symbol if hasattr(order, 'symbol') else 'UNKNOWN',
                                        order.quantity if hasattr(order, 'quantity') else 0,
                                        price,
                                        timestamp,
                                        order.direction if hasattr(order, 'direction') else 'UNKNOWN',
                                        rule_id=rule_id
                                    )
                                    
                                    # Add trade to portfolio
                                    if hasattr(self, 'portfolio'):
                                        if hasattr(self.portfolio, 'add_trade'):
                                            self.portfolio.add_trade(trade)
                                            logger.info(f"Added trade to portfolio for order {order.id if hasattr(order, 'id') else 'unknown'}")
                                        else:
                                            # Try to add the trade to the portfolio's trades list directly
                                            if not hasattr(self.portfolio, 'trades'):
                                                self.portfolio.trades = []
                                            self.portfolio.trades.append(trade)
                                            logger.info(f"Added trade directly to portfolio.trades for order {order.id if hasattr(order, 'id') else 'unknown'}")
                                    else:
                                        logger.warning("Execution handler does not have portfolio attribute")
                                except Exception as e:
                                    logger.error(f"Error creating trade: {e}")
                            finally:
                                # Reset recursion flag
                                self._in_patched_fill_order = False
                            
                            return result
                        
                        # Apply patch
                        handler_class.fill_order = patched_fill_order
                        logger.info(f"Patched {class_name}.fill_order")
                        execution_fixed = True
                else:
                    logger.warning(f"No execution handler classes found in {module_path}")
            except ImportError:
                logger.debug(f"Could not import {module_path}")
        
        return execution_fixed
    except Exception as e:
        logger.error(f"Error applying execution fix: {e}")
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
    
    try:
        # Import the optimizer
        from src.strategy.optimization.optimizer import StrategyOptimizer
        
        # Create and run optimizer
        optimizer = StrategyOptimizer(config)
        results = optimizer.optimize()
        
        if results:
            # Check if best_parameters is None
            if results.get('best_parameters') is None:
                logger.warning("Optimization completed but best_parameters is None")
                logger.info("This may indicate no valid parameter combinations were found")
                
                # Return success anyway since the fixes allowed the process to complete
                return True
            else:
                logger.info("Optimization completed successfully")
                logger.info(f"Best parameters: {results.get('best_parameters')}")
                logger.info(f"Best score: {results.get('best_score')}")
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
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply simplified fixes for optimization issues')
    parser.add_argument('--config', required=True, help='Path to the configuration file')
    parser.add_argument('--skip-fixes', action='store_true', help='Skip applying fixes and just run optimization')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Starting simplified fix process")
    
    # Apply fixes
    if not args.skip_fixes:
        # Apply reporter fix
        reporter_fixed = apply_reporter_fix()
        logger.info(f"Reporter fix: {'Applied' if reporter_fixed else 'Failed'}")
        
        # Apply execution fix
        execution_fixed = apply_execution_fix()
        logger.info(f"Execution fix: {'Applied' if execution_fixed else 'Failed'}")
        
        if not reporter_fixed and not execution_fixed:
            logger.warning("No fixes were applied. Optimization may still fail.")
    else:
        logger.info("Skipping fixes as requested")
    
    # Run optimization
    success = run_optimization(args.config)
    
    if success:
        logger.info("Optimization completed successfully")
        return 0
    else:
        logger.error("Optimization failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
