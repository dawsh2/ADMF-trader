#!/usr/bin/env python
"""
ADMF-Trader main entry point.

This is a minimal entry point that handles:
1. Parsing command-line arguments
2. Setting up the bootstrap system
3. Running the appropriate command
"""

import os
import sys
import argparse
import traceback
import yaml
import pandas as pd
from datetime import datetime

from src.core.system_init import Bootstrap
from src.core.logging import configure_logging, get_logger

# Get logger - will be configured based on command line arguments
logger = get_logger('main')

def main():
    """
    Main entry point for the application.
    
    Returns:
        int: Exit code
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='ADMF-Trader CLI')
    parser.add_argument('--config', required=True, help='Path to configuration file')
    
    # System options
    parser.add_argument('--symbols', nargs='+', help='Override symbols in config')
    parser.add_argument('--start-date', help='Override start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='Override end date (YYYY-MM-DD)')
    parser.add_argument('--output-dir', help='Output directory for results')
    parser.add_argument('--optimize', action='store_true', help='Run parameter optimization')
    parser.add_argument('--analytics', action='store_true', help='Run analytics on trading results')
    parser.add_argument('--equity-file', help='Path to equity curve CSV file for analytics')
    parser.add_argument('--trades-file', help='Path to trades CSV file for analytics')
    parser.add_argument('--param-file', help='Parameter space file for optimization')
    parser.add_argument('--method', choices=['grid', 'random', 'walk_forward'], 
                       default='grid', help='Optimization method')
    parser.add_argument('--bars', type=int, help='Limit processing to specified number of bars (default: process all)')
    
    # Logging options
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging (INFO level)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging for all modules')
    parser.add_argument('--debug-module', action='append', dest='debug_modules',
                       help='Enable debug logging for specific module (can be used multiple times)')
    parser.add_argument('--log-file', help='Write logs to file')
    parser.add_argument('--quiet', action='store_true', help='Suppress console output')
    
    # Parse arguments
    args = parser.parse_args()
    
    try:
        # Configure logging based on arguments
        configure_logging(
            debug=args.debug,
            debug_modules=args.debug_modules,
            log_file=args.log_file,
            console=not args.quiet
        )
        
        # If verbose but not debug, set to INFO level
        if args.verbose and not args.debug:
            from src.core.logging.config import logging
            logger.setLevel(logging.INFO)
            
        # Load the config to determine mode
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check mode and determine what to run
        mode = config.get('mode', 'backtest')
        
        if args.optimize:
            return run_optimization(args)
        elif args.analytics or mode == 'analytics':
            # Import the analytics runner
            from src.analytics.runner import run_analytics
            success, message = run_analytics(
                config,
                equity_file=args.equity_file,
                trades_file=args.trades_file,
                output_dir=args.output_dir
            )
            if success:
                logger.info(message)
                return 0
            else:
                logger.error(message)
                return 1
        else:
            # Default is to run trading system (backtest or live based on config)
            return run_trading_system(args)
            
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        return 1

def run_trading_system(args):
    """
    Run the trading system (backtest or live).
    
    Args:
        args: Command-line arguments
        
    Returns:
        int: Exit code
    """
    # Set up bootstrap with logging options already configured
    bootstrap = Bootstrap(
        config_files=[args.config],
        debug=args.debug,
        log_file=args.log_file or "trading.log"
    )
    
    # Store max bars limit in the bootstrap context if specified
    if args.bars is not None:
        bootstrap.set_context_value('max_bars', args.bars)
    
    # Initialize system
    container, config = bootstrap.setup()
    
    # Determine if we're running in backtest or live mode based on config
    mode = config.get('mode', 'backtest')
    logger.info(f"Running in {mode} mode")
    
    if mode == 'backtest':
        # Get backtest from container
        if container.has('backtest'):
            backtest = container.get('backtest')
            
            # Override config with command-line arguments if provided
            if args.symbols:
                logger.info(f"Overriding symbols with {args.symbols}")
                # TODO: Apply override
                
            if args.start_date:
                logger.info(f"Overriding start date with {args.start_date}")
                # TODO: Apply override
                
            if args.end_date:
                logger.info(f"Overriding end date with {args.end_date}")
                # TODO: Apply override
                
            # Run backtest
            logger.info("Starting backtest")
            
            try:
                # Setup and run the backtest
                backtest.setup()  # Ensure components are properly initialized
                results = backtest.run()
                
                # Process results
                if results:
                    final_capital = results.get('final_capital', 0)
                    trades = results.get('trades', [])
                    statistics = results.get('statistics', {})
                    
                    # Log basic results
                    logger.info(f"Backtest completed with final capital: ${final_capital:.2f}")
                    logger.info(f"Total trades: {len(trades)}")
                    
                    # Log key metrics
                    if statistics:
                        logger.info("Performance metrics:")
                        for key in ['return_pct', 'sharpe_ratio', 'max_drawdown', 'profit_factor', 'win_rate']:
                            if key in statistics:
                                logger.info(f"  {key}: {statistics[key]}")
                    
                    return 0
                else:
                    logger.error("Backtest completed but returned no results")
                    return 1
            except Exception as e:
                logger.error(f"Error running backtest: {e}", exc_info=True)
                return 1
            
            return 0
        else:
            logger.error("Backtest component not available")
            return 1
    elif mode == 'live':
        # TODO: Implement live trading
        logger.info("Live trading not yet implemented")
        return 0
    else:
        logger.error(f"Unknown mode: {mode}")
        return 1

def run_optimization(args):
    """
    Run parameter optimization.
    
    Args:
        args: Command-line arguments
        
    Returns:
        int: Exit code
    """
    # Set up bootstrap with logging options already configured
    bootstrap = Bootstrap(
        config_files=[args.config],
        debug=args.debug,
        log_file=args.log_file or "optimization.log"
    )

    # Store max bars limit in the bootstrap context if specified
    if args.bars is not None:
        bootstrap.set_context_value('max_bars', args.bars)
        logger.info(f"Setting max_bars={args.bars} for optimization")

    # Initialize system - this sets up the container and loads the config
    container, config = bootstrap.setup()

    # Make sure bootstrap is available in the container
    if not hasattr(container, 'register_instance'):
        logger.warning("Container doesn't have register_instance method")
    else:
        # Register bootstrap in container so run_with_context can access it
        container.register_instance('bootstrap', bootstrap)
        logger.info(f"Registered bootstrap in container with max_bars={bootstrap.context.get('max_bars')}")

    # Also directly modify the config to include max_bars
    if args.bars is not None and hasattr(config, 'set'):
        config.set('max_bars', args.bars)
        logger.info(f"Set max_bars={args.bars} directly in config")

    # Import the optimization runner
    try:
        from src.strategy.optimization.runner import run_with_context
        
        # Run optimization with the configured container and any command line overrides
        # Pass max_bars directly as a keyword argument
        kwargs = {
            'method': args.method,
            'param_file': args.param_file,
            'output_dir': args.output_dir
        }

        # Add max_bars if specified
        if args.bars is not None:
            kwargs['max_bars'] = args.bars
            logger.info(f"Passing max_bars={args.bars} directly to run_with_context")

        success, message, _ = run_with_context(
            config,
            container,
            **kwargs
        )
        
        # Display result
        if success:
            logger.info(message)
            return 0
        else:
            logger.error(message)
            return 1
            
    except ImportError:
        logger.error("Optimization module not found")
        return 1
    except Exception as e:
        logger.error(f"Error running optimization: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())