#!/usr/bin/env python
"""
Simplified Backtest Runner Using Bootstrap Pattern

This script demonstrates using the Bootstrap pattern to set up
and run a backtest with proper dependency injection and direct strategy registration.
"""
import os
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bootstrap_backtest.log', mode='w')
    ]
)

logger = logging.getLogger("ADMF-Trader")

# Import core components
from src.core.bootstrap import Bootstrap
from src.strategy.implementations.ma_crossover import MACrossoverStrategy

# Make sure output directory exists
os.makedirs('./results', exist_ok=True)

# Main script
if __name__ == "__main__":
    try:
        logger.info("=== Starting ADMF-Trader Backtest Using Bootstrap ===")
        
        # Define symbols and date range
        symbols = ['AAPL', 'MSFT']
        start_date = '2023-01-01'
        end_date = '2023-02-28'
        
        # Initialize bootstrap with config file
        bootstrap = Bootstrap(config_files=['backtest_config.yaml'])
        
        # Set up container and components
        container, config = bootstrap.setup()
        
        # Check if strategy was registered and register it manually if not
        if not container.has('strategy'):
            logger.info("Strategy not registered by discovery, registering manually")
            
            # Get the registry from bootstrap
            strategy_registry = bootstrap.registries.get("strategies")
            if strategy_registry:
                # Register our strategy class
                strategy_registry.register("ma_crossover", MACrossoverStrategy)
                logger.info("Registered MACrossoverStrategy with registry")
            
            # Get dependencies
            event_bus = container.get("event_bus")
            data_handler = container.get("data_handler")
            
            # Create strategy instance
            strategy_config = config.get_section("strategies").get_section("ma_crossover")
            strategy = MACrossoverStrategy(event_bus, data_handler, name="ma_crossover")
            strategy.configure(strategy_config)
            
            # Register with container
            container.register_instance("strategy", strategy)
            
            # Register with event manager
            event_manager = container.get("event_manager")
            event_manager.register_component("strategy", strategy)
            
            logger.info("Registered and configured strategy manually")
        
        # Get backtest coordinator
        backtest = container.get('backtest')
        
        # Check if setup is successful
        if not backtest.setup():
            logger.error("Backtest setup failed")
            print("Backtest setup failed - see logs for details")
            exit(1)
        
        # Run the backtest
        results = backtest.run(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            initial_capital=100000.0
        )
        
        # Process and display results
        if results:
            equity_curve = results.get('equity_curve')
            trades = results.get('trades', [])
            metrics = results.get('metrics', {})
            
            # Display trade info
            print(f"\n=== Backtest Completed Successfully with {len(trades)} trades ===")
            
            # Display key metrics
            if metrics:
                print("\nKey Performance Metrics:")
                key_metrics = ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor']
                for metric in key_metrics:
                    if metric in metrics:
                        print(f"  {metric}: {metrics[metric]:.4f}")
            
            # Save results to files
            if equity_curve is not None and not equity_curve.empty:
                equity_curve.to_csv("./results/equity_curve.csv")
                print("Saved equity curve to './results/equity_curve.csv'")
            
            detailed_report = results.get('detailed_report', '')
            if detailed_report:
                with open('./results/backtest_report.txt', 'w') as f:
                    f.write(detailed_report)
                print("Saved detailed report to './results/backtest_report.txt'")
        else:
            print("\n=== Backtest Failed! No results returned ===")
    
    except Exception as e:
        logger.error(f"Backtest failed with error: {e}", exc_info=True)
        print(f"Error: {e}")
