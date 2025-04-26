"""
Strategy module for the algorithmic trading framework.

This package contains strategy components and implementations:
- components: Building blocks for strategies (indicators, features, rules)
- implementations: Concrete strategy implementations
"""

from .strategy_base import Strategy
from .components.component_base import Component

# Import implementations for easier access
try:
    from .implementations import MACrossoverStrategy
except ImportError:
    pass  # Optional dependency
