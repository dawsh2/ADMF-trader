"""
Broker module for order execution and market simulation.

This module provides components for:
- Order execution and routing
- Market simulation for backtesting
- Slippage and commission modeling
"""
from src.execution.broker.broker_base import BrokerBase
from src.execution.broker.simulated_broker import SimulatedBroker
from src.execution.broker.market_simulator import MarketSimulator
from src.execution.broker.slippage_model import FixedSlippageModel, VariableSlippageModel
from src.execution.broker.commission_model import CommissionModel

__all__ = [
    'BrokerBase',
    'SimulatedBroker',
    'MarketSimulator',
    'FixedSlippageModel',
    'VariableSlippageModel',
    'CommissionModel'
]