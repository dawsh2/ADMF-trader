#!/usr/bin/env python
"""
ADMF-Trader Detailed Optimization Runner

This script runs the optimization and provides detailed trading statistics
for the best parameter combination.
"""

import os
import sys
import logging
import yaml
import traceback
import pprint

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from optimize_strategy import create_data_directories, load_config, load_parameter_space, setup_strategy_factory
from src.strategy.optimization.objective_functions import get_objective_function
from src.core.event_bus import SimpleEventBus
from src.core.trade_repository import TradeRepository
from src.execution.backtest.optimizing_backtest import OptimizingBacktest

def print_trade_stats(result):
    """
    Print detailed trade statistics.
    
    Args:
        result (dict): Backtest result
    """
    logger.info("=" * 80)
    logger.info("DETAILED TRADING STATISTICS")
    logger.info("=" * 80)
    
    # Get trades and statistics
    trades = result.get('trades', [])
    stats = result.get('statistics', {})
    
    # Print overall statistics
    logger.info(f"Initial Capital: ${stats.get('initial_capital', 0):,.2f}")
    logger.info(f"Final Capital: ${stats.get('final_capital', 0):,.2f}")
    logger.info(f"Total Return: {stats.get('return_pct', 0):.2f}%")
    logger.info(f"Total Trades: {stats.get('trades_executed', 0)}")
    
    if stats.get('trades_executed', 0) > 0:
        logger.info(f"Win Rate: {stats.get('win_rate', 0) * 100:.2f}%")
        logger.info(f"Profitable Trades: {stats.get('profitable_trades', 0)}")
        logger.info(f"Loss Trades: {stats.get('loss_trades', 0)}")
        logger.info(f"Average Profit: ${stats.get('avg_profit', 0):,.2f}")
        logger.info(f"Average Loss: ${stats.get('avg_loss', 0):,.2f}")
        logger.info(f"Profit Factor: {stats.get('profit_factor', 0):.2f}")
    
    # Print trade details
    if trades:
        logger.info("\nTOP 10 TRADES:")
        logger.info("-" * 80)
        logger.info(f"{'Symbol':<10} {'Direction':<10} {'Entry Time':<25} {'Exit Time':<25} {'PnL':>15}")
        logger.info("-" * 80)
        
        # Sort trades by PnL
        sorted_trades = sorted(trades, key=lambda t: t.get('pnl', 0), reverse=True)
        
        # Print top 10 trades
        for trade in sorted_trades[:10]:
            symbol = trade.get('symbol', '')
            direction = trade.get('direction', '')
            entry_time = trade.get('entry_time', '')
            exit_time = trade.get('exit_time', '')
            pnl = trade.get('pnl', 0)
            
            logger.info(f"{symbol:<10} {direction:<10} {str(entry_time):<25} {str(exit_time):<25} ${pnl:>13,.2f}")
    
    logger.info("=" * 80)

def main():
    """Main function."""
    try:
        # Configuration
        config_path = 'config/backtest_config.yaml'
        strategy_name = 'simple_ma_crossover'
        param_file = 'config/parameter_spaces/ma_crossover_params.yaml'
        objective_name = 'sharpe_ratio'
        
        logger.info("Starting ADMF-Trader optimization...")
        logger.info(f"Config: {config_path}")
        logger.info(f"Strategy: {strategy_name}")
        logger.info(f"Parameter file: {param_file}")
        logger.info(f"Objective: {objective_name}")
        
        # Create data directories
        logger.info("Checking data directories...")
        create_data_directories()
        
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config(config_path)
        
        # Load parameter space
        logger.info("Loading parameter space...")
        param_space = load_parameter_space(param_file)
        
        # Set up strategy factory
        logger.info("Setting up strategy factory...")
        strategy_factory = setup_strategy_factory()
        
        # Get objective function
        logger.info("Getting objective function...")
        objective_function = get_objective_function(objective_name)
        
        # Create optimization context
        logger.info("Creating optimization context...")
        context = {
            'strategy_factory': strategy_factory
        }
        
        # Create optimizing backtest
        logger.info("Creating optimizing backtest...")
        optimizer = OptimizingBacktest('optimizer', config, param_space)
        
        # Initialize optimizer
        logger.info("Initializing optimizer...")
        optimizer.initialize(context)
        
        # Set up train/test configuration
        train_test_config = {
            'method': 'ratio',
            'train_ratio': 0.7,
            'test_ratio': 0.3
        }
        
        # Use a smaller parameter space for testing
        logger.info("Restricting parameter space for initial testing...")
        # Get only two combinations to test
        param_space.parameters['fast_period'].min_value = 5
        param_space.parameters['fast_period'].max_value = 10
        param_space.parameters['slow_period'].min_value = 20
        param_space.parameters['slow_period'].max_value = 30
        
        # Run optimization
        logger.info("Starting optimization process...")
        results = optimizer.optimize(strategy_name, objective_function, train_test_config)
        
        # Print results
        logger.info("Optimization completed!")
        
        # Print best parameters
        logger.info(f"Best parameters: {results['best_parameters']}")
        logger.info(f"Best train score: {results['best_train_score']}")
        logger.info(f"Best test score: {results['best_test_score']}")
        
        # Print detailed statistics for best train result
        logger.info("\nBEST TRAINING SET PERFORMANCE:")
        print_trade_stats(results['best_train_result'])
        
        # Print detailed statistics for best test result
        logger.info("\nBEST TEST SET PERFORMANCE:")
        print_trade_stats(results['best_test_result'])
        
        # Print all tested parameters and their results
        logger.info("\nALL TESTED PARAMETERS:")
        for i, result in enumerate(results.get('all_results', [])):
            params = result.get('parameters', {})
            train_score = result.get('train_score', 0)
            test_score = result.get('test_score', 0)
            logger.info(f"{i+1}. {params} - Train: {train_score:.4f}, Test: {test_score:.4f}")
        
        return results
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        logger.error(traceback.format_exc())
        return None

if __name__ == '__main__':
    main()
