"""
Multi-Timeframe Moving Average Crossover Strategy.

This module implements a multi-timeframe moving average crossover strategy
that filters entry signals based on higher timeframe trend.
"""

import logging
from typing import Dict, List, Optional, Any, Union

from src.strategy.strategy import MultipleTimeframeStrategy
from src.data.data_types import Bar, Timeframe

logger = logging.getLogger(__name__)

class MultiTimeframeMACrossover(MultipleTimeframeStrategy):
    """
    Multi-Timeframe Moving Average Crossover Strategy.
    
    This strategy:
    - Uses a short-term MA crossover on a lower timeframe for entry signals
    - Filters entries using a longer-term MA crossover on a higher timeframe
    - Only takes long positions when higher timeframe trend is also bullish
    """
    
    def __init__(self, name: str, 
                 entry_tf: Union[str, Timeframe] = Timeframe.MINUTE_1, 
                 filter_tf: Union[str, Timeframe] = Timeframe.HOUR_1,
                 fast_period: int = 10, 
                 slow_period: int = 30,
                 filter_fast_period: int = 5,
                 filter_slow_period: int = 20):
        """
        Initialize the strategy.
        
        Args:
            name: Strategy name
            entry_tf: Timeframe for entry signals
            filter_tf: Timeframe for trend filtering
            fast_period: Fast MA period for entry timeframe
            slow_period: Slow MA period for entry timeframe
            filter_fast_period: Fast MA period for filter timeframe
            filter_slow_period: Slow MA period for filter timeframe
        """
        super().__init__(name)
        
        # Convert timeframes if strings
        if isinstance(entry_tf, str):
            entry_tf = Timeframe.from_string(entry_tf)
        if isinstance(filter_tf, str):
            filter_tf = Timeframe.from_string(filter_tf)
            
        # Store parameters
        self.parameters = {
            'entry_tf': entry_tf,
            'filter_tf': filter_tf,
            'fast_period': fast_period,
            'slow_period': slow_period,
            'filter_fast_period': filter_fast_period,
            'filter_slow_period': filter_slow_period
        }
        
        # Add timeframes
        self.add_timeframe(entry_tf)
        self.add_timeframe(filter_tf)
        
        # State tracking
        self.entry_signals = {}  # Dict[symbol, int] (1, -1, 0)
        self.filter_signals = {}  # Dict[symbol, int] (1, -1, 0)
        self.last_position = {}  # Dict[symbol, int]
    
    def initialize(self, context: Dict[str, Any] = None) -> None:
        """
        Initialize the strategy.
        
        Args:
            context: Optional context with dependencies
        """
        super().initialize(context)
        
        for symbol in self.symbols:
            self.entry_signals[symbol] = 0
            self.filter_signals[symbol] = 0
            self.last_position[symbol] = 0
        
        self.logger.info(f"Multi-TF MA Crossover {self.name} initialized with parameters: {self.parameters}")
    
    def calculate_signals_multi(self, symbol: str, timeframe: Timeframe) -> None:
        """
        Calculate signals for a specific timeframe.
        
        Args:
            symbol: Symbol to calculate for
            timeframe: Timeframe to use
        """
        entry_tf = self.parameters['entry_tf']
        filter_tf = self.parameters['filter_tf']
        
        # Process the correct timeframe
        if timeframe == entry_tf:
            self._calculate_entry_signals(symbol)
        elif timeframe == filter_tf:
            self._calculate_filter_signals(symbol)
        
        # If we have signals from both timeframes, determine combined signal
        if symbol in self.entry_signals and symbol in self.filter_signals:
            self._evaluate_combined_signals(symbol)
    
    def _calculate_entry_signals(self, symbol: str) -> None:
        """
        Calculate entry signals based on lower timeframe MA crossover.
        
        Args:
            symbol: Symbol to calculate for
        """
        entry_tf = self.parameters['entry_tf']
        fast_period = self.parameters['fast_period']
        slow_period = self.parameters['slow_period']
        
        # Get bars for this timeframe
        bars = self.get_bars(symbol, entry_tf)
        
        # Need at least slow_period bars
        if len(bars) < slow_period:
            return
        
        # Calculate MAs
        closes = [bar.close for bar in bars]
        fast_ma = sum(closes[-fast_period:]) / fast_period
        slow_ma = sum(closes[-slow_period:]) / slow_period
        
        # Calculate previous MAs if possible
        if len(closes) > slow_period:
            prev_closes = closes[:-1]
            prev_fast_ma = sum(prev_closes[-fast_period:]) / fast_period
            prev_slow_ma = sum(prev_closes[-slow_period:]) / slow_period
            
            # Determine signal
            was_above = prev_fast_ma > prev_slow_ma
            is_above = fast_ma > slow_ma
            
            if is_above and not was_above:
                # Bullish crossover
                self.entry_signals[symbol] = 1
                self.logger.debug(f"Entry timeframe BULLISH signal for {symbol}")
            elif not is_above and was_above:
                # Bearish crossover
                self.entry_signals[symbol] = -1
                self.logger.debug(f"Entry timeframe BEARISH signal for {symbol}")
    
    def _calculate_filter_signals(self, symbol: str) -> None:
        """
        Calculate filter signals based on higher timeframe MA crossover.
        
        Args:
            symbol: Symbol to calculate for
        """
        filter_tf = self.parameters['filter_tf']
        filter_fast_period = self.parameters['filter_fast_period']
        filter_slow_period = self.parameters['filter_slow_period']
        
        # Get bars for this timeframe
        bars = self.get_bars(symbol, filter_tf)
        
        # Need at least slow_period bars
        if len(bars) < filter_slow_period:
            return
        
        # Calculate MAs
        closes = [bar.close for bar in bars]
        fast_ma = sum(closes[-filter_fast_period:]) / filter_fast_period
        slow_ma = sum(closes[-filter_slow_period:]) / filter_slow_period
        
        # Determine signal based on current values
        if fast_ma > slow_ma:
            # Bullish trend
            self.filter_signals[symbol] = 1
            self.logger.debug(f"Filter timeframe BULLISH trend for {symbol}")
        else:
            # Bearish trend
            self.filter_signals[symbol] = -1
            self.logger.debug(f"Filter timeframe BEARISH trend for {symbol}")
    
    def _evaluate_combined_signals(self, symbol: str) -> None:
        """
        Evaluate combined signals from both timeframes and generate orders.
        
        Args:
            symbol: Symbol to evaluate
        """
        entry_signal = self.entry_signals[symbol]
        filter_signal = self.filter_signals[symbol]
        current_position = self.last_position.get(symbol, 0)
        
        # Only enter long if entry signal is bullish AND filter signal is bullish
        if entry_signal > 0 and filter_signal > 0 and current_position <= 0:
            self._generate_long_entry(symbol)
            self.last_position[symbol] = 1
            self.logger.info(f"Multi-TF MA Crossover: Long entry for {symbol} - " +
                            f"Entry timeframe: BULLISH, Filter timeframe: BULLISH")
        
        # Exit long if entry signal is bearish (regardless of filter)
        elif entry_signal < 0 and current_position > 0:
            self._generate_long_exit(symbol)
            self.last_position[symbol] = 0
            self.logger.info(f"Multi-TF MA Crossover: Long exit for {symbol} - " +
                            f"Entry timeframe: BEARISH")
        
        # Reset entry signal after processing
        self.entry_signals[symbol] = 0
    
    def _generate_long_entry(self, symbol: str) -> None:
        """
        Generate a long entry signal.
        
        Args:
            symbol: Symbol to enter long
        """
        self.emit_signal('ENTRY', symbol, 1, 1.0, {
            'reason': 'MULTI_TF_MA_CROSSOVER_LONG',
            'entry_tf': self.parameters['entry_tf'].to_string(),
            'filter_tf': self.parameters['filter_tf'].to_string()
        })
    
    def _generate_long_exit(self, symbol: str) -> None:
        """
        Generate a long exit signal.
        
        Args:
            symbol: Symbol to exit long
        """
        self.emit_signal('EXIT', symbol, 0, 1.0, {
            'reason': 'MULTI_TF_MA_CROSSOVER_EXIT',
            'entry_tf': self.parameters['entry_tf'].to_string(),
            'filter_tf': self.parameters['filter_tf'].to_string()
        })
    
    def reset(self) -> None:
        """Reset the strategy."""
        super().reset()
        
        # Reset strategy-specific state
        for symbol in self.symbols:
            self.entry_signals[symbol] = 0
            self.filter_signals[symbol] = 0
            self.last_position[symbol] = 0
        
        self.logger.info(f"Multi-TF MA Crossover {self.name} reset")