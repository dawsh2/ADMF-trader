import os
import sys
import logging
import argparse
import yaml
import importlib.util

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("main.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('main')

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

def run_optimization(config_path, verbose=False):
    """Run optimization with the specified configuration"""
    # Set log level based on verbosity
    if verbose:
        logger.setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config(config_path)
    if not config:
        logger.error("Failed to load configuration")
        return False
    
    # Log the configuration for debugging
    logger.debug(f"Configuration: {config}")
    
    # Check if the strategy has symbols defined
    strategy_symbols = config.get('strategy', {}).get('parameters', {}).get('symbols', [])
    logger.info(f"Strategy symbols defined in config: {strategy_symbols}")
    
    # Check if backtest has symbols defined
    backtest_symbols = config.get('backtest', {}).get('symbols', [])
    logger.info(f"Backtest symbols defined in config: {backtest_symbols}")
    
    # Check data sources
    data_sources = config.get('data', {}).get('sources', [])
    source_symbols = [source.get('symbol') for source in data_sources]
    logger.info(f"Data source symbols: {source_symbols}")
    
    # Run debug optimization first
    if os.path.exists("debug_optimization.py"):
        logger.info("Running debug optimization to verify signals...")
        
        # Import and run the debug module
        spec = importlib.util.spec_from_file_location("debug_optimization", "debug_optimization.py")
        debug_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(debug_module)
        debug_module.main()
    
    # Mock optimization run
    logger.info("Starting optimization...")
    for param in config.get('parameter_space', []):
        param_name = param.get('name')
        param_min = param.get('min')
        param_max = param.get('max')
        param_step = param.get('step')
        
        logger.info(f"Optimizing parameter: {param_name} from {param_min} to {param_max} with step {param_step}")
        
        # Mock results for each parameter combination
        for value in range(param_min, param_max + 1, param_step):
            logger.info(f"Testing {param_name} = {value}")
            # In a real system, we would run the backtest here with the parameter value
    
    logger.info("Optimization completed successfully")
    return True

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='Run trading strategy optimization')
    subparsers = parser.add_subparsers(dest='command', help='sub-command help')
    
    # Optimize command
    optimize_parser = subparsers.add_parser('optimize', help='Optimize a trading strategy')
    optimize_parser.add_argument('--config', required=True, help='Path to the configuration file')
    optimize_parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command == 'optimize':
        run_optimization(args.config, args.verbose)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()