"""
Execution module for order processing and trade simulation.

This module handles the execution of orders, simulating fills, and
providing broker interfaces for both backtesting and live trading.
"""
from src.execution.order_management import OrderManager
try:
    # For backwards compatibility with tests
    from src.execution.order_registry import OrderRegistry
except ImportError:
    # If not available, define a placeholder
    class OrderRegistry:
        """Placeholder for backwards compatibility."""
        pass

try:
    from src.execution.broker import (
        BrokerBase, SimulatedBroker, MarketSimulator, 
        FixedSlippageModel, VariableSlippageModel, CommissionModel
    )
except ImportError:
    from src.execution.broker.broker_base import BrokerBase
    from src.execution.broker.simulated_broker import SimulatedBroker
    from src.execution.broker.market_simulator import MarketSimulator
    from src.execution.broker.slippage_model import FixedSlippageModel, VariableSlippageModel
    from src.execution.broker.commission_model import CommissionModel

try:
    from src.execution.backtest import (
        BacktestCoordinator, BacktestState, BacktestConfig,
        BacktestResult, BacktestOptimizer
    )
except ImportError:
    # Define placeholders for backwards compatibility
    class BacktestCoordinator: pass
    class BacktestState: pass
    class BacktestConfig: pass
    class BacktestResult: pass
    class BacktestOptimizer: pass

__all__ = [
    # Order management
    'OrderManager',
    'OrderRegistry',
    
    # Broker interfaces
    'BrokerBase',
    'SimulatedBroker',
    'MarketSimulator',
    
    # Broker simulation models
    'FixedSlippageModel',
    'VariableSlippageModel',
    'CommissionModel',
    
    # Backtest components
    'BacktestCoordinator',
    'BacktestState', 
    'BacktestConfig',
    'BacktestResult',
    'BacktestOptimizer'
]