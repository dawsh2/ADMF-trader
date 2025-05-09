"""
Moving Average Crossover Strategy.

This module implements a simple moving average crossover strategy
that generates entry and exit signals when fast MA crosses slow MA.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple

from src.strategy.strategy import Strategy
from src.data.data_types import Bar, Timeframe

logger = logging.getLogger(__name__)

class MovingAverageCrossover(Strategy):
    """
    Simple Moving Average Crossover Strategy.
    
    This strategy generates:
    - Long entry signals when the fast MA crosses above the slow MA
    - Long exit signals when the fast MA crosses below the slow MA
    """
    
    def __init__(self, name: str, fast_period: int = 10, slow_period: int = 30):
        """
        Initialize the strategy.
        
        Args:
            name: Strategy name
            fast_period: Fast moving average period
            slow_period: Slow moving average period
        """
        super().__init__(name)
        self.parameters = {
            'fast_period': fast_period,
            'slow_period': slow_period
        }
        
        # Data storage for each symbol
        self.bars_dict = {}  # Dict[symbol, List[Bar]]
        self.last_fast_ma = {}  # Dict[symbol, float]
        self.last_slow_ma = {}  # Dict[symbol, float]
        self.last_position = {}  # Dict[symbol, int] (1 for long, -1 for short, 0 for flat)
        
    def initialize(self, context: Dict[str, Any] = None) -> None:
        """
        Initialize the strategy.
        
        Args:
            context: Optional context with dependencies
        """
        super().initialize(context)
        
        for symbol in self.symbols:
            self.bars_dict[symbol] = []
            self.last_fast_ma[symbol] = None
            self.last_slow_ma[symbol] = None
            self.last_position[symbol] = 0  # Start flat
    
    def calculate_signals(self, bar: Bar) -> None:
        """
        Calculate trading signals based on the current bar.
        
        This method is called for each new bar. It calculates moving averages
        and generates signals when crossovers occur.
        
        Args:
            bar: Current bar data
        """
        symbol = bar.symbol
        
        # Debug output to show we're processing the bar
        self.logger.debug(f"Calculating signals for {symbol} at {bar.timestamp}: O={bar.open:.2f}, H={bar.high:.2f}, L={bar.low:.2f}, C={bar.close:.2f}")
        
        # Initialize if needed
        if symbol not in self.bars_dict:
            self.bars_dict[symbol] = []
            self.last_fast_ma[symbol] = None
            self.last_slow_ma[symbol] = None
            self.last_position[symbol] = 0
            self.logger.debug(f"Initialized data structures for {symbol}")
        
        # Store the bar
        self.bars_dict[symbol].append(bar)
        self.logger.debug(f"Added bar to history for {symbol}, total bars: {len(self.bars_dict[symbol])}")
        
        # Need at least slow_period bars to calculate
        slow_period = self.parameters.get('slow_period', 30)
        if len(self.bars_dict[symbol]) < slow_period:
            return
        
        # Calculate moving averages
        fast_period = self.parameters.get('fast_period', 10)
        current_fast_ma, current_slow_ma = self._calculate_mas(symbol, fast_period, slow_period)
        
        # Check if we have previous values to compare
        if self.last_fast_ma[symbol] is not None and self.last_slow_ma[symbol] is not None:
            # Check for crossover
            was_above = self.last_fast_ma[symbol] > self.last_slow_ma[symbol]
            is_above = current_fast_ma > current_slow_ma
            
            # Long entry: fast MA crosses above slow MA
            if is_above and not was_above:
                # Only enter if not already long
                if self.last_position[symbol] <= 0:
                    self.logger.info(f"Crossover detected: Fast MA ({current_fast_ma:.2f}) crossed above Slow MA ({current_slow_ma:.2f}) for {symbol}")
                    self._generate_long_entry(symbol)
                    self.last_position[symbol] = 1
                else:
                    self.logger.debug(f"Ignoring buy signal for {symbol} - already long")
            
            # Long exit: fast MA crosses below slow MA
            elif was_above and not is_above:
                # Only exit if currently long
                if self.last_position[symbol] > 0:
                    self.logger.info(f"Crossover detected: Fast MA ({current_fast_ma:.2f}) crossed below Slow MA ({current_slow_ma:.2f}) for {symbol}")
                    self._generate_long_exit(symbol)
                    self.last_position[symbol] = 0
                else:
                    self.logger.debug(f"Ignoring sell signal for {symbol} - not long")
        
        # Update last values
        self.last_fast_ma[symbol] = current_fast_ma
        self.last_slow_ma[symbol] = current_slow_ma
    
    def _calculate_mas(self, symbol: str, fast_period: int, slow_period: int) -> Tuple[float, float]:
        """
        Calculate fast and slow moving averages.
        
        Args:
            symbol: Symbol to calculate for
            fast_period: Fast moving average period
            slow_period: Slow moving average period
            
        Returns:
            Tuple[float, float]: Fast and slow MA values
        """
        bars = self.bars_dict[symbol]
        closes = [bar.close for bar in bars]
        
        # Debug the calculation
        self.logger.debug(f"Calculating MAs for {symbol} with {len(closes)} close prices")
        self.logger.debug(f"Fast period: {fast_period}, Slow period: {slow_period}")
        
        # Calculate fast MA
        fast_data = closes[-fast_period:]
        fast_ma = sum(fast_data) / fast_period
        
        # Calculate slow MA
        slow_data = closes[-slow_period:]
        slow_ma = sum(slow_data) / slow_period
        
        self.logger.debug(f"MA results - Fast: {fast_ma:.4f}, Slow: {slow_ma:.4f}, Diff: {fast_ma - slow_ma:.4f}")
        
        return fast_ma, slow_ma
    
    def _generate_long_entry(self, symbol: str) -> None:
        """
        Generate a long entry signal.
        
        Args:
            symbol: Symbol to enter long
        """
        self.logger.info(f"MA Crossover: Long entry signal for {symbol}")
        self.emit_signal('ENTRY', symbol, 1, 1.0, {
            'reason': 'MA_CROSSOVER_LONG',
            'fast_ma': self.last_fast_ma[symbol],
            'slow_ma': self.last_slow_ma[symbol]
        })
    
    def _generate_long_exit(self, symbol: str) -> None:
        """
        Generate a long exit signal.
        
        Args:
            symbol: Symbol to exit long
        """
        self.logger.info(f"MA Crossover: Long exit signal for {symbol}")
        self.emit_signal('EXIT', symbol, 0, 1.0, {
            'reason': 'MA_CROSSOVER_EXIT',
            'fast_ma': self.last_fast_ma[symbol],
            'slow_ma': self.last_slow_ma[symbol]
        })
    
    def reset(self) -> None:
        """Reset the strategy."""
        super().reset()
        
        # Reset strategy-specific state
        for symbol in self.symbols:
            self.bars_dict[symbol] = []
            self.last_fast_ma[symbol] = None
            self.last_slow_ma[symbol] = None
            self.last_position[symbol] = 0  # Reset to flat
        
        self.logger.info(f"MA Crossover strategy {self.name} reset")