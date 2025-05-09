#!/usr/bin/env python
"""
Run optimization with fixed reporter module.

This script runs the optimizer with patches to fix the 'NoneType' object has no attribute 'items'
error in the reporter.py file.
"""

import os
import sys
import logging
import yaml
import traceback
import importlib.util
import importlib
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fixed_reporter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fixed_reporter')

# Apply monkey patch to fix None best_parameters issue
def fix_reporter_module():
    """Monkey patch the reporter module to handle None best_parameters"""
    try:
        # Import the reporter module
        import src.strategy.optimization.reporter as reporter
        
        # Save the original _generate_text_report method
        original_generate_text_report = reporter.OptimizationReporter._generate_text_report
        
        # Define a fixed method
        def fixed_generate_text_report(self, results, filename):
            # Add check for None results or best_parameters
            if results is None:
                logger.warning("Results is None, cannot generate report")
                return
                
            # Create file path
            filepath = os.path.join(self.output_dir, filename)
            
            # Extract best_parameters and verify it's not None
            best_parameters = results.get('best_parameters', {})
            if best_parameters is None:
                logger.warning("best_parameters is None, using empty dict")
                best_parameters = {}
                results['best_parameters'] = {}
            
            # Call the original method which should now work with the modified results
            return original_generate_text_report(self, results, filename)
        
        # Apply the monkey patch
        reporter.OptimizationReporter._generate_text_report = fixed_generate_text_report
        logger.info("Successfully monkey patched reporter module")
        return True
    except Exception as e:
        logger.error(f"Error patching reporter module: {e}")
        logger.error(traceback.format_exc())
        return False

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

def main():
    """Main entry point for the application"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run optimization with fixed reporter module')
    parser.add_argument('--config', required=True, help='Path to the configuration file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        logger.error("Failed to load configuration")
        return 1
        
    # Apply the reporter fix
    if not fix_reporter_module():
        logger.warning("Failed to apply reporter fix, but continuing...")
    
    try:
        # Fix objective functions using monkey patching
        try:
            import src.strategy.optimization.objective_functions as objective_functions
            # Add None check to sharpe_ratio function
            original_sharpe_ratio = objective_functions.sharpe_ratio
            def fixed_sharpe_ratio(results):
                if results is None:
                    return 0.0
                return original_sharpe_ratio(results)
            objective_functions.sharpe_ratio = fixed_sharpe_ratio
            
            # Add None check to profit_factor function
            if hasattr(objective_functions, 'profit_factor'):
                original_profit_factor = objective_functions.profit_factor
                def fixed_profit_factor(results):
                    if results is None:
                        return 0.0
                    return original_profit_factor(results)
                objective_functions.profit_factor = fixed_profit_factor
            
            # Add None check to max_return function
            if hasattr(objective_functions, 'max_return'):
                original_max_return = objective_functions.max_return
                def fixed_max_return(results):
                    if results is None:
                        return 0.0
                    return original_max_return(results)
                objective_functions.max_return = fixed_max_return
                
            logger.info("Successfully patched objective functions")
        except Exception as e:
            logger.warning(f"Error patching objective functions: {e}")
        
        # Import the optimizer and run
        from src.strategy.optimization.optimizer import StrategyOptimizer
        
        logger.info("Running optimization with patched reporter...")
        optimizer = StrategyOptimizer(config)
        results = optimizer.optimize()
        
        if results:
            logger.info("Optimization completed successfully")
            return 0
        else:
            logger.warning("Optimization completed but returned no results")
            return 1
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
