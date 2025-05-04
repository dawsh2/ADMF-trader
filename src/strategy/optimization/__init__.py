"""
Optimization module for ADMF-Trader.

This module provides tools and implementations for strategy optimization,
parameter tuning, and performance evaluation.
"""

from src.strategy.optimization.parameter_space import (
    Parameter,
    IntegerParameter,
    FloatParameter,
    CategoricalParameter,
    BooleanParameter,
    ParameterSpace
)

from src.strategy.optimization.grid_search import GridSearch
from src.strategy.optimization.random_search import RandomSearch

__all__ = [
    'Parameter',
    'IntegerParameter',
    'FloatParameter',
    'CategoricalParameter',
    'BooleanParameter',
    'ParameterSpace',
    'GridSearch',
    'RandomSearch'
]
