#!/usr/bin/env python
"""
ADMF-Trader Complete Optimization with Detailed Results

This script runs a full optimization process and properly stores all the results
including detailed trading statistics for each parameter combination.
"""

import os
import sys
import logging
import yaml
import traceback
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from optimize_strategy import create_data_directories, load_config, load_parameter_space
from src.strategy.optimization.objective_functions import get_objective_function
from src.core.event_bus import SimpleEventBus
from src.core.trade_repository import TradeRepository
from src.strategy.strategy_factory import StrategyFactory
from src.data.historical_data_handler import HistoricalDataHandler
from src.execution.portfolio import Portfolio
from src.execution.broker.simulated_broker import SimulatedBroker
from src.execution.order_manager import OrderManager
from src.execution.backtest.backtest_coordinator import BacktestCoordinator

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
        logger.info("\nTRADES:")
        logger.info("-" * 80)
        logger.info(f"{'Symbol':<10} {'Direction':<10} {'Entry Time':<25} {'Exit Time':<25} {'PnL':>15}")
        logger.info("-" * 80)
        
        # Sort trades by entry time
        sorted_trades = sorted(trades, key=lambda t: t.get('entry_time', datetime.min))
        
        # Print all trades (up to 20)
        for trade in sorted_trades[:20]:
            symbol = trade.get('symbol', '')
            direction = trade.get('direction', '')
            entry_time = trade.get('entry_time', '')
            exit_time = trade.get('exit_time', '')
            pnl = trade.get('pnl', 0)
            
            logger.info(f"{symbol:<10} {direction:<10} {str(entry_time):<25} {str(exit_time):<25} ${pnl:>13,.2f}")
        
        if len(sorted_trades) > 20:
            logger.info(f"...and {len(sorted_trades) - 20} more trades")
    
    logger.info("=" * 80)
    
    return {
        'initial_capital': stats.get('initial_capital', 0),
        'final_capital': stats.get('final_capital', 0),
        'return_pct': stats.get('return_pct', 0),
        'trades_executed': stats.get('trades_executed', 0),
        'win_rate': stats.get('win_rate', 0),
        'profitable_trades': stats.get('profitable_trades', 0),
        'loss_trades': stats.get('loss_trades', 0),
        'avg_profit': stats.get('avg_profit', 0),
        'avg_loss': stats.get('avg_loss', 0),
        'profit_factor': stats.get('profit_factor', 0)
    }

def run_backtest(strategy_name, params, data_config=None):
    """
    Run a single backtest with specified parameters.
    
    Args:
        strategy_name (str): Name of the strategy to use
        params (dict): Strategy parameters
        data_config (dict, optional): Data configuration for train/test split
        
    Returns:
        dict: Backtest results
    """
    # Load configuration
    config = load_config('config/backtest_config.yaml')
    
    # Create event bus
    event_bus = SimpleEventBus()
    
    # Create trade repository
    trade_repository = TradeRepository()
    
    # Create context
    context = {
        'event_bus': event_bus,
        'trade_repository': trade_repository,
        'config': config
    }
    
    # Create backtest coordinator
    backtest = BacktestCoordinator("backtest", config)
    
    # Create data handler
    data_handler = HistoricalDataHandler("data_handler", config.get('data', {}))
    data_handler.initialize(context)
    
    # Set up train/test split if provided
    if data_config:
        data_handler.setup_train_test_split(
            method=data_config.get('method', 'ratio'),
            train_ratio=data_config.get('train_ratio', 0.7),
            test_ratio=data_config.get('test_ratio', 0.3),
            split_date=data_config.get('split_date'),
            train_periods=data_config.get('train_periods'),
            test_periods=data_config.get('test_periods')
        )
        
        # Set active split
        data_handler.set_active_split(data_config.get('active_split', 'train'))
    
    # Set up strategy factory
    strategy_factory = StrategyFactory([
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'strategy', 'implementations')
    ])
    
    # Create strategy with parameters
    strategy_params = dict(params)  # Copy parameters
    strategy_params['name'] = 'strategy'  # Add required name parameter
    
    # CRITICAL FIX: Adjust position size to a reasonable value
    if 'position_size' in strategy_params and strategy_params['position_size'] > 10:
        logger.info(f"Limiting position size from {strategy_params['position_size']} to 5")
        strategy_params['position_size'] = 5  # Limit position size to avoid excessive risk
    
    strategy = strategy_factory.create_strategy(strategy_name, **strategy_params)
    
    # Create other components
    portfolio = Portfolio("portfolio", config.get('initial_capital', 100000))
    broker = SimulatedBroker("broker")
    order_manager = OrderManager("order_manager")
    
    # Add components to backtest
    backtest.add_component('data_handler', data_handler)
    backtest.add_component('strategy', strategy)
    backtest.add_component('portfolio', portfolio)
    backtest.add_component('broker', broker)
    backtest.add_component('order_manager', order_manager)
    
    # Initialize backtest
    backtest.initialize(context)
    
    # Setup and run backtest
    backtest.setup()
    results = backtest.run()
    
    # Add parameters to results
    results['parameters'] = params
    
    return results

def optimize(strategy_name, param_space, objective_function, train_test_config):
    """
    Run optimization with proper result tracking.
    
    Args:
        strategy_name (str): Name of the strategy to use
        param_space: Parameter space to search
        objective_function: Function to evaluate results
        train_test_config: Train/test configuration
        
    Returns:
        dict: Optimization results with detailed statistics
    """
    # Get parameter combinations
    parameter_combinations = param_space.get_combinations()
    
    if not parameter_combinations:
        raise ValueError("No parameter combinations to test")
    
    # Track results
    all_results = []
    best_train_score = float('-inf')
    best_train_result = None
    best_test_result = None
    best_parameters = None
    
    # Test each parameter combination
    for params in parameter_combinations:
        logger.info(f"Testing parameters: {params}")
        
        # Run backtest with training data
        train_config = dict(train_test_config)
        train_config['active_split'] = 'train'
        train_result = run_backtest(strategy_name, params, train_config)
        
        # Evaluate result
        train_score = objective_function(train_result)
        
        # Run backtest with test data
        test_config = dict(train_test_config)
        test_config['active_split'] = 'test'
        test_result = run_backtest(strategy_name, params, test_config)
        
        # Evaluate test result
        test_score = objective_function(test_result)
        
        # Store result
        result = {
            'parameters': params,
            'train_score': train_score,
            'test_score': test_score,
            'train_stats': print_trade_stats(train_result),
            'test_stats': print_trade_stats(test_result)
        }
        
        all_results.append(result)
        
        # Update best result if this is better
        if train_score > best_train_score:
            best_train_score = train_score
            best_parameters = params
            best_train_result = train_result
            best_test_result = test_result
    
    # Sort results by train score
    all_results.sort(key=lambda x: x['train_score'], reverse=True)
    
    # Prepare final results
    optimization_results = {
        'best_parameters': best_parameters,
        'best_train_score': best_train_score,
        'best_test_score': objective_function(best_test_result),
        'best_train_stats': print_trade_stats(best_train_result),
        'best_test_stats': print_trade_stats(best_test_result),
        'all_results': all_results,
        'parameter_counts': len(parameter_combinations)
    }
    
    return optimization_results

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
        
        # Get objective function
        logger.info("Getting objective function...")
        objective_function = get_objective_function(objective_name)
        
        # Use a smaller parameter space for testing
        logger.info("Setting up restricted parameter space for testing...")
        # Define a more reasonable parameter space
        param_space.parameters['fast_period'].min_value = 5
        param_space.parameters['fast_period'].max_value = 20
        param_space.parameters['fast_period'].step = 5
        param_space.parameters['slow_period'].min_value = 20
        param_space.parameters['slow_period'].max_value = 50
        param_space.parameters['slow_period'].step = 10
        param_space.parameters['position_size'].min_value = 1
        param_space.parameters['position_size'].max_value = 5
        param_space.parameters['position_size'].step = 1
        
        # Set up train/test configuration
        train_test_config = {
            'method': 'ratio',
            'train_ratio': 0.7,
            'test_ratio': 0.3
        }
        
        # Run optimization
        logger.info("Starting optimization process...")
        results = optimize(strategy_name, param_space, objective_function, train_test_config)
        
        # Print results
        logger.info("Optimization completed!")
        
        # Print best parameters
        logger.info(f"Best parameters: {results['best_parameters']}")
        logger.info(f"Best train score: {results['best_train_score']}")
        logger.info(f"Best test score: {results['best_test_score']}")
        
        # Print all tested parameters and their results
        logger.info("\nALL TESTED PARAMETERS:")
        for i, result in enumerate(results.get('all_results', [])):
            params = result.get('parameters', {})
            train_score = result.get('train_score', 0)
            test_score = result.get('test_score', 0)
            train_return = result.get('train_stats', {}).get('return_pct', 0)
            test_return = result.get('test_stats', {}).get('return_pct', 0)
            logger.info(f"{i+1}. {params}")
            logger.info(f"   - Train score: {train_score:.4f}, Return: {train_return:.2f}%")
            logger.info(f"   - Test score: {test_score:.4f}, Return: {test_return:.2f}%")
        
        # Save results to file
        with open('optimization_results.json', 'w') as f:
            # Convert any non-serializable objects to strings
            clean_results = json.dumps(results, default=str, indent=2)
            f.write(clean_results)
        
        logger.info("Results saved to optimization_results.json")
        
        return results
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        logger.error(traceback.format_exc())
        return None

if __name__ == '__main__':
    main()
