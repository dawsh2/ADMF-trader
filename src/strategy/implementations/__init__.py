"""
Strategy implementations package.

This package contains concrete implementations of trading strategies.
"""

# Import strategies for easy access
from .ma_crossover import MACrossoverStrategy

# List of all available strategies for discovery
__all__ = ['MACrossoverStrategy']
