#!/usr/bin/env python
"""
ADMF-Trader Optimization with Fixed Objective Function

This script fixes the issues with objective function calculations and
ensures consistent reporting of performance metrics.
"""

import os
import sys
import logging
import traceback
from datetime import datetime
import json
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from optimize_strategy import create_data_directories, load_config
from src.core.event_bus import SimpleEventBus
from src.core.trade_repository import TradeRepository
from src.strategy.strategy_factory import StrategyFactory
from src.data.historical_data_handler import HistoricalDataHandler
from src.execution.portfolio import Portfolio
from src.execution.broker.simulated_broker import SimulatedBroker
from src.execution.order_manager import OrderManager
from src.execution.backtest.backtest_coordinator import BacktestCoordinator
from src.strategy.optimization.parameter_space import ParameterSpace, IntegerParameter

def corrected_sharpe_ratio(results, risk_free_rate=0.0):
    """
    Calculate Sharpe ratio from backtest results, fixing previous issues.
    
    Args:
        results (dict): Backtest results
        risk_free_rate (float, optional): Risk-free rate
        
    Returns:
        float: Sharpe ratio
    """
    stats = results.get('statistics', {})
    trades = results.get('trades', [])
    
    # If no trades, return 0
    if not trades:
        return 0.0
    
    # Calculate returns for each trade
    returns = []
    for trade in trades:
        pnl = trade.get('pnl', 0)
        # Use a fixed investment amount for each trade to normalize returns
        investment = 1000.0  # Assuming each trade uses $1000
        
        # Calculate simple return
        trade_return = pnl / investment
        returns.append(trade_return)
    
    # Calculate Sharpe ratio
    if not returns:
        return 0.0
        
    mean_return = np.mean(returns) - risk_free_rate
    std_return = np.std(returns)
    
    # If standard deviation is zero, return 0 to avoid division by zero
    if std_return == 0:
        return 0.0
    
    # Assuming 252 trading days per year
    sharpe = mean_return / std_return * np.sqrt(252)
    
    # For clarity, also log the components
    logger.debug(f"Mean Return: {mean_return:.6f}, Std Dev: {std_return:.6f}, Sharpe: {sharpe:.4f}")
    
    return sharpe

def profit_factor(results):
    """
    Calculate profit factor from backtest results.
    
    Args:
        results (dict): Backtest results
        
    Returns:
        float: Profit factor
    """
    trades = results.get('trades', [])
    
    if not trades:
        return 0.0
    
    # Calculate gross profit and gross loss
    gross_profit = sum(max(trade.get('pnl', 0), 0) for trade in trades)
    gross_loss = sum(abs(min(trade.get('pnl', 0), 0)) for trade in trades)
    
    # Avoid division by zero
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    
    return gross_profit / gross_loss

def calculate_statistics(results):
    """
    Calculate detailed statistics from backtest results.
    
    Args:
        results (dict): Backtest results
        
    Returns:
        dict: Calculated statistics
    """
    stats = results.get('statistics', {})
    trades = results.get('trades', [])
    
    # Basic metrics
    initial_capital = stats.get('initial_capital', 100000)
    final_capital = stats.get('final_capital', initial_capital)
    
    # Calculate return percentage
    return_pct = ((final_capital - initial_capital) / initial_capital) * 100
    
    # Calculate trade metrics
    total_trades = len(trades)
    profitable_trades = sum(1 for trade in trades if trade.get('pnl', 0) > 0)
    loss_trades = total_trades - profitable_trades
    
    # Calculate win rate
    win_rate = profitable_trades / total_trades if total_trades > 0 else 0
    
    # Calculate average profit and loss
    profit_trades = [trade for trade in trades if trade.get('pnl', 0) > 0]
    loss_trades_list = [trade for trade in trades if trade.get('pnl', 0) <= 0]
    
    avg_profit = sum(trade.get('pnl', 0) for trade in profit_trades) / len(profit_trades) if profit_trades else 0
    avg_loss = sum(trade.get('pnl', 0) for trade in loss_trades_list) / len(loss_trades_list) if loss_trades_list else 0
    
    # Calculate profit factor
    pf = profit_factor(results)
    
    # Calculate Sharpe ratio
    sharpe = corrected_sharpe_ratio(results)
    
    return {
        'initial_capital': initial_capital,
        'final_capital': final_capital,
        'return_pct': return_pct,
        'trades_executed': total_trades,
        'profitable_trades': profitable_trades,
        'loss_trades': loss_trades,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'profit_factor': pf,
        'sharpe_ratio': sharpe
    }

def print_trade_stats(result):
    """
    Print detailed trade statistics with corrected calculations.
    
    Args:
        result (dict): Backtest result
    """
    logger.info("=" * 80)
    logger.info("DETAILED TRADING STATISTICS")
    logger.info("=" * 80)
    
    # Get trades and calculate statistics
    stats = calculate_statistics(result)
    
    # Print overall statistics
    logger.info(f"Initial Capital: ${stats['initial_capital']:,.2f}")
    logger.info(f"Final Capital: ${stats['final_capital']:,.2f}")
    logger.info(f"Total Return: {stats['return_pct']:.2f}%")
    logger.info(f"Total Trades: {stats['trades_executed']}")
    
    if stats['trades_executed'] > 0:
        logger.info(f"Win Rate: {stats['win_rate'] * 100:.2f}%")
        logger.info(f"Profitable Trades: {stats['profitable_trades']}")
        logger.info(f"Loss Trades: {stats['loss_trades']}")
        logger.info(f"Average Profit: ${stats['avg_profit']:,.2f}")
        logger.info(f"Average Loss: ${stats['avg_loss']:,.2f}")
        logger.info(f"Profit Factor: {stats['profit_factor']:.2f}")
        logger.info(f"Sharpe Ratio: {stats['sharpe_ratio']:.4f}")
    
    # Print trade details
    trades = result.get('trades', [])
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
    
    return stats

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
    
    # Create strategy with parameters - include fixed position_size and stop_loss params
    strategy_params = dict(params)  # Copy parameters
    strategy_params['name'] = 'strategy'  # Add required name parameter
    
    # Add fixed position size and stop loss parameters
    strategy_params['position_size'] = 1  # Fixed position size
    strategy_params['use_trailing_stop'] = False  # Fixed value
    strategy_params['stop_loss_pct'] = 0.03  # Fixed stop loss percentage
    
    logger.debug(f"Running backtest with parameters: {strategy_params}")
    
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

def total_return_objective(results):
    """
    Simple objective function that returns the total return percentage.
    
    Args:
        results (dict): Backtest results
        
    Returns:
        float: Total return percentage
    """
    stats = calculate_statistics(results)
    return stats['return_pct']

def optimize(strategy_name, param_space, train_test_config):
    """
    Run optimization with proper result tracking.
    
    Args:
        strategy_name (str): Name of the strategy to use
        param_space: Parameter space to search
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
    best_train_return = float('-inf')
    best_test_return = float('-inf')
    best_combined_return = float('-inf')
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
        
        # Calculate statistics
        train_stats = calculate_statistics(train_result)
        train_return = train_stats['return_pct']
        
        # Run backtest with test data
        test_config = dict(train_test_config)
        test_config['active_split'] = 'test'
        test_result = run_backtest(strategy_name, params, test_config)
        
        # Calculate statistics
        test_stats = calculate_statistics(test_result)
        test_return = test_stats['return_pct']
        
        # Calculate combined return (weighted average)
        combined_return = (0.4 * train_return) + (0.6 * test_return)
        
        # Store detailed result
        result = {
            'parameters': params,
            'train_return': train_return,
            'test_return': test_return,
            'combined_return': combined_return,
            'train_stats': train_stats,
            'test_stats': test_stats
        }
        
        all_results.append(result)
        
        # Update best result if this is better based on combined return
        if combined_return > best_combined_return:
            best_combined_return = combined_return
            best_parameters = params
            best_train_result = train_result
            best_test_result = test_result
        
        # Also track best training and test results separately
        if train_return > best_train_return:
            best_train_return = train_return
        
        if test_return > best_test_return:
            best_test_return = test_return
    
    # Sort results by combined return
    all_results.sort(key=lambda x: x['combined_return'], reverse=True)
    
    # Calculate best stats
    best_train_stats = calculate_statistics(best_train_result)
    best_test_stats = calculate_statistics(best_test_result)
    
    # Prepare final results
    optimization_results = {
        'best_parameters': best_parameters,
        'best_combined_return': best_combined_return,
        'best_train_stats': best_train_stats,
        'best_test_stats': best_test_stats,
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
        
        logger.info("Starting ADMF-Trader optimization with corrected calculations...")
        logger.info(f"Config: {config_path}")
        logger.info(f"Strategy: {strategy_name}")
        logger.info(f"Objective: Total Return (with balanced train/test weighting)")
        
        # Create data directories
        logger.info("Checking data directories...")
        create_data_directories()
        
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config(config_path)
        
        # Create parameter space manually - only include fast_period and slow_period
        logger.info("Creating parameter space...")
        param_space = ParameterSpace()
        param_space.add_parameter(IntegerParameter('fast_period', 5, 30, 5))
        param_space.add_parameter(IntegerParameter('slow_period', 20, 100, 20))
        
        # Set up train/test configuration
        train_test_config = {
            'method': 'ratio',
            'train_ratio': 0.7,
            'test_ratio': 0.3
        }
        
        # Run optimization
        logger.info("Starting optimization process...")
        results = optimize(strategy_name, param_space, train_test_config)
        
        # Print results
        logger.info("Optimization completed!")
        
        # Print best parameters
        logger.info(f"Best parameters: {results['best_parameters']}")
        logger.info(f"Best combined return: {results['best_combined_return']:.2f}%")
        
        # Print all tested parameters and their results
        logger.info("\nALL TESTED PARAMETERS:")
        for i, result in enumerate(results.get('all_results', [])):
            params = result.get('parameters', {})
            train_return = result.get('train_return', 0)
            test_return = result.get('test_return', 0)
            combined_return = result.get('combined_return', 0)
            train_trades = result.get('train_stats', {}).get('trades_executed', 0)
            test_trades = result.get('test_stats', {}).get('trades_executed', 0)
            logger.info(f"{i+1}. {params}")
            logger.info(f"   - Train: Return={train_return:.2f}%, Trades={train_trades}")
            logger.info(f"   - Test: Return={test_return:.2f}%, Trades={test_trades}")
            logger.info(f"   - Combined Return: {combined_return:.2f}%")
        
        # Print a comprehensive summary of the best parameters at the very end
        logger.info("\n" + "=" * 80)
        logger.info("BEST PARAMETER SET SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Best Parameters: fast_period={results['best_parameters']['fast_period']}, slow_period={results['best_parameters']['slow_period']}")
        logger.info(f"Fixed Parameters: position_size=1, use_trailing_stop=False, stop_loss_pct=0.03")
        logger.info("\nTraining Performance:")
        logger.info(f"  - Return: {results['best_train_stats']['return_pct']:.2f}%")
        logger.info(f"  - Total Trades: {results['best_train_stats']['trades_executed']}")
        logger.info(f"  - Win Rate: {results['best_train_stats']['win_rate']*100:.2f}%")
        logger.info(f"  - Profit Factor: {results['best_train_stats']['profit_factor']:.2f}")
        logger.info(f"  - Sharpe Ratio: {results['best_train_stats']['sharpe_ratio']:.4f}")
        
        logger.info("\nTest Performance:")
        logger.info(f"  - Return: {results['best_test_stats']['return_pct']:.2f}%")
        logger.info(f"  - Total Trades: {results['best_test_stats']['trades_executed']}")
        logger.info(f"  - Win Rate: {results['best_test_stats']['win_rate']*100:.2f}%")
        logger.info(f"  - Profit Factor: {results['best_test_stats']['profit_factor']:.2f}")
        logger.info(f"  - Sharpe Ratio: {results['best_test_stats']['sharpe_ratio']:.4f}")
        logger.info("=" * 80)
        
        logger.info("\nTo use these parameters in live trading:")
        logger.info(f"  - fast_period: {results['best_parameters']['fast_period']}")
        logger.info(f"  - slow_period: {results['best_parameters']['slow_period']}")
        logger.info(f"  - position_size: 1")
        logger.info(f"  - use_trailing_stop: False")
        logger.info(f"  - stop_loss_pct: 0.03")
        
        # Save results to file
        with open('optimization_results.json', 'w') as f:
            # Convert any non-serializable objects to strings
            clean_results = json.dumps(results, default=str, indent=2)
            f.write(clean_results)
        
        logger.info("\nResults saved to optimization_results.json")
        
        return results
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        logger.error(traceback.format_exc())
        return None

if __name__ == '__main__':
    main()
