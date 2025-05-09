#!/usr/bin/env python
"""
ADMF-Trader Single Backtest Runner

This script runs a single backtest with the best parameters found from optimization
and provides detailed performance statistics.
"""

import os
import sys
import logging
import yaml
import traceback
from datetime import datetime

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
from src.execution.backtest.backtest_coordinator import BacktestCoordinator
from src.data.historical_data_handler import HistoricalDataHandler
from src.execution.portfolio import Portfolio
from src.execution.broker.simulated_broker import SimulatedBroker
from src.execution.order_manager import OrderManager
from src.strategy.strategy_factory import StrategyFactory

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

def run_backtest(strategy_name, params):
    """
    Run a single backtest with specified parameters.
    
    Args:
        strategy_name (str): Name of the strategy to use
        params (dict): Strategy parameters
        
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
    
    # Set up strategy factory
    strategy_factory = StrategyFactory([
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'strategy', 'implementations')
    ])
    
    # Create strategy with parameters
    strategy_params = dict(params)  # Copy parameters
    strategy_params['name'] = 'strategy'  # Add required name parameter
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

def main():
    """Main function."""
    try:
        # Create data directories
        create_data_directories()
        
        # Best parameters from previous optimization
        best_params = {
            'fast_period': 5,
            'slow_period': 20,
            'position_size': 50.0,
            'use_trailing_stop': True,
            'stop_loss_pct': 0.01
        }
        
        logger.info("Running backtest with best parameters:")
        logger.info(f"Parameters: {best_params}")
        
        # Run backtest
        results = run_backtest('simple_ma_crossover', best_params)
        
        # Print detailed statistics
        print_trade_stats(results)
        
        return results
    except Exception as e:
        logger.error(f"Error during backtest: {e}")
        logger.error(traceback.format_exc())
        return None

if __name__ == '__main__':
    main()
