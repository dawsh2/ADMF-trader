"""
Backtest orchestrator that manages the entire backtest process.

This module ensures proper state isolation between backtest runs and
between train/test splits during optimization.
"""

import logging
import yaml
from src.core.backtest_state import BacktestState
from src.risk.position_manager import PositionManager
from src.core.pnl_calculator import PnLCalculator

logger = logging.getLogger(__name__)

class BacktestOrchestrator:
    """Orchestrates backtests with proper state isolation"""
    
    def __init__(self, config):
        """
        Initialize the backtest orchestrator.
        
        Args:
            config (dict): Configuration for the backtest
        """
        self.config = config
        logger.info("BacktestOrchestrator initialized with config")
        
    def run_single_backtest(self, params, data_split=None):
        """
        Run a single backtest with complete state isolation.
        
        Args:
            params (dict): Strategy parameters
            data_split (str, optional): Data split to use ('train' or 'test')
            
        Returns:
            dict: Backtest results
        """
        logger.info(f"Running single backtest with params: {params}, split: {data_split}")
        
        # Create fresh state
        initial_capital = self.config.get('initial_capital', 100000.0)
        state = BacktestState(initial_capital)
        context = state.create_fresh_state()
        
        # Set up components with proper dependencies
        data_handler = self._create_data_handler(context)
        strategy = self._create_strategy(params, context)
        
        # Create position manager with fixed quantity
        fixed_quantity = self.config.get('risk', {}).get('position_manager', {}).get('fixed_quantity', 10)
        position_manager = PositionManager(context['event_bus'], fixed_quantity=fixed_quantity)
        
        broker = self._create_broker(context)
        
        # Create backtest coordinator
        from src.execution.backtest.backtest_coordinator import BacktestCoordinator
        coordinator = BacktestCoordinator('coordinator', self.config)
        
        # Register components with coordinator
        coordinator.add_component('data_handler', data_handler)
        coordinator.add_component('strategy', strategy)
        coordinator.add_component('position_manager', position_manager)
        coordinator.add_component('broker', broker)
        coordinator.add_component('portfolio', context['portfolio'])
        
        # Set up data split if provided
        if data_split and hasattr(data_handler, 'set_active_split'):
            data_handler.set_active_split(data_split)
            logger.info(f"Set active data split to: {data_split}")
            
        # Initialize coordinator with context
        coordinator.initialize(context)
        
        # Run backtest
        logger.info("Starting backtest execution")
        results = coordinator.run()
        
        # Validate results
        self._validate_results(results, context)
        
        logger.info("Backtest completed successfully")
        return results
    
    def _create_data_handler(self, context):
        """
        Create appropriate data handler based on config.
        
        Args:
            context (dict): Shared context
            
        Returns:
            object: Data handler instance
        """
        # Get data config
        data_config = self.config.get('data', {})
        
        # Import data handler factory
        from src.data.factory import create_data_handler
        
        # Create data handler using factory
        data_handler = create_data_handler(data_config, context['event_bus'])
        
        return data_handler
    
    def _create_strategy(self, params, context):
        """
        Create strategy with given parameters.
        
        Args:
            params (dict): Strategy parameters
            context (dict): Shared context
            
        Returns:
            object: Strategy instance
        """
        # Get strategy config
        strategy_config = self.config.get('strategy', {})
        strategy_name = strategy_config.get('name')
        
        # Import strategy factory
        from src.strategy.strategy_factory import create_strategy
        
        # Create strategy using factory
        strategy = create_strategy(strategy_name, params, context['event_bus'])
        
        return strategy
    
    def _create_broker(self, context):
        """
        Create broker based on config.
        
        Args:
            context (dict): Shared context
            
        Returns:
            object: Broker instance
        """
        # Import broker factory
        from src.execution.broker.simulated_broker import SimulatedBroker
        
        # Create broker
        broker = SimulatedBroker(context['event_bus'], context['portfolio'])
        
        return broker
    
    def _validate_results(self, results, context):
        """
        Validate the consistency of backtest results.
        
        Args:
            results (dict): Backtest results
            context (dict): Shared context
        """
        # Get trades and equity curve
        trades = results.get('trades', [])
        equity_curve = results.get('equity_curve', [])
        
        if not trades or not equity_curve:
            logger.warning("Cannot validate results - missing trades or equity curve")
            return
            
        # Calculate sum of trade PnLs using standard calculator
        trade_pnl_sum = PnLCalculator.calculate_total_pnl(trades)
        
        # Get equity change
        if len(equity_curve) > 1:
            initial_equity = equity_curve[0].get('equity', 0)
            final_equity = equity_curve[-1].get('equity', 0)
            equity_change = final_equity - initial_equity
            
            # Validate PnL consistency
            if not PnLCalculator.validate_pnl(trade_pnl_sum, equity_change):
                logger.warning(f"PnL inconsistency detected between trade PnL ({trade_pnl_sum:.2f}) and equity change ({equity_change:.2f})")
                
                # Analyze the inconsistency
                diff = trade_pnl_sum - equity_change
                if abs(equity_change) > 1e-10:
                    percent_diff = (diff / abs(equity_change)) * 100
                    logger.warning(f"Difference: {diff:.2f}, Percentage: {percent_diff:.2f}%")
                else:
                    logger.warning(f"Difference: {diff:.2f}, Percentage: N/A (equity change near zero)")
            else:
                logger.info(f"PnL validation passed: Trade PnL={trade_pnl_sum:.2f}, Equity Change={equity_change:.2f}")
