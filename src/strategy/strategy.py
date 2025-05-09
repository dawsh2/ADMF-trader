"""
Strategy interface and base classes.

This module defines the Strategy interface and related base classes
for implementing trading strategies in ADMF-Trader.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set, Union

from src.core.component import Component
from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType
from src.data.data_types import Bar, Timeframe

logger = logging.getLogger(__name__)

class Strategy(Component, ABC):
    """
    Base class for all trading strategies.
    
    A Strategy is responsible for:
    - Processing market data
    - Generating trading signals
    - Emitting signal events
    """
    
    def __init__(self, name: str):
        """
        Initialize the strategy.
        
        Args:
            name: Strategy name
        """
        super().__init__(name)
        self.symbols = []
        self.active = True
        self.parameters = {}
        self.last_bar = {}  # Dict[symbol, Bar]
        
    def initialize(self, context: Dict[str, Any] = None) -> None:
        """
        Initialize the strategy.
        
        Args:
            context: Optional context with dependencies
        """
        if context is None:
            context = {}
            
        super().initialize(context)
        self.logger.info(f"Strategy {self.name} initialized with parameters: {self.parameters}")
        
    def start(self) -> None:
        """Start the strategy."""
        super().start()
        self.active = True
        self.logger.info(f"Strategy {self.name} started")
        
    def stop(self) -> None:
        """Stop the strategy."""
        super().stop()
        self.active = False
        self.logger.info(f"Strategy {self.name} stopped")
        
    def reset(self) -> None:
        """Reset the strategy."""
        super().reset()
        self.last_bar = {}
        self.logger.info(f"Strategy {self.name} reset")
    
    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """
        Set strategy parameters.
        
        Args:
            parameters: Dictionary of parameter name-value pairs
        """
        self.parameters.update(parameters)
        self.logger.info(f"Strategy {self.name} parameters updated: {parameters}")
        
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get strategy parameters.
        
        Returns:
            Dict[str, Any]: Strategy parameters
        """
        return self.parameters.copy()
    
    def add_symbols(self, symbols: Union[str, List[str]]) -> None:
        """
        Add symbols to the strategy.
        
        Args:
            symbols: Symbol or list of symbols to add
        """
        if isinstance(symbols, str):
            symbols = [symbols]
            
        new_symbols = [s for s in symbols if s not in self.symbols]
        if new_symbols:
            self.symbols.extend(new_symbols)
            self.logger.info(f"Added symbols to strategy {self.name}: {new_symbols}")
    
    def get_symbols(self) -> List[str]:
        """
        Get the symbols traded by this strategy.
        
        Returns:
            List[str]: List of symbols
        """
        return self.symbols.copy()
    
    def on_bar(self, event) -> None:
        """
        Process a bar event.
        
        This method is called when a new bar event is received. It extracts
        the bar data, updates the last bar, and delegates to calculate_signals.
        
        Args:
            event: Either a Bar object directly or an Event containing bar data
        """
        if not self.active:
            return
        
        try:
            # Check if we received a Bar object directly or an Event
            if isinstance(event, Bar):
                # Direct Bar object - use it as is
                bar = event
            else:
                # Assume it's an Event - extract bar data from event
                bar_data = event.data
                
                # Convert event data to Bar object
                bar = Bar(
                    timestamp=bar_data['timestamp'],
                    symbol=bar_data['symbol'],
                    open=bar_data['open'],
                    high=bar_data['high'],
                    low=bar_data['low'],
                    close=bar_data['close'],
                    volume=bar_data.get('volume', 0),
                    timeframe=Timeframe.from_string(bar_data['timeframe'])
                )
            
            symbol = bar.symbol
            
            # Log receipt of bar
            self.logger.debug(f"Received bar for {symbol} at {bar.timestamp}")
            
            # Store the bar
            self.last_bar[symbol] = bar
            
            # Generate signals
            self.calculate_signals(bar)
            
        except Exception as e:
            self.logger.error(f"Error processing bar event: {e}", exc_info=True)
    
    @abstractmethod
    def calculate_signals(self, bar: Bar) -> None:
        """
        Calculate trading signals based on the current bar.
        
        This method must be implemented by subclasses to define
        the strategy's signal generation logic.
        
        Args:
            bar: Current bar
        """
        pass
    
    def emit_signal(self, signal_type: str, symbol: str, direction: int,
                   strength: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit a signal event.
        
        Args:
            signal_type: Type of signal (e.g., 'ENTRY', 'EXIT')
            symbol: Symbol the signal is for
            direction: Direction of signal (1 for long, -1 for short, 0 for exit)
            strength: Signal strength (0.0-1.0)
            metadata: Additional signal metadata
        """
        if not self.event_bus:
            self.logger.warning(f"Cannot emit signal: event bus not set")
            return
            
        # Create signal data
        signal_data = {
            'type': signal_type,
            'symbol': symbol,
            'direction': direction,
            'strength': strength,
            'strategy': self.name,
            'timestamp': self.last_bar.get(symbol).timestamp if symbol in self.last_bar else None,
            'metadata': metadata or {}
        }
        
        # Create signal event
        event = Event(EventType.SIGNAL, signal_data)
        
        # Publish event
        self.event_bus.publish(event)
        self.logger.debug(f"Emitted signal event: {signal_data}")


class MultipleTimeframeStrategy(Strategy):
    """
    Base class for strategies that use multiple timeframes.
    
    This class extends the basic Strategy to support multiple timeframes,
    automatically aggregating bars into higher timeframes.
    """
    
    def __init__(self, name: str):
        """
        Initialize the strategy.
        
        Args:
            name: Strategy name
        """
        super().__init__(name)
        self.timeframes = []  # List of Timeframe objects
        self.bars = {}  # Dict[symbol, Dict[timeframe, List[Bar]]]
        
    def add_timeframe(self, timeframe: Union[str, Timeframe]) -> None:
        """
        Add a timeframe to the strategy.
        
        Args:
            timeframe: Timeframe to add
        """
        if isinstance(timeframe, str):
            timeframe = Timeframe.from_string(timeframe)
            
        if timeframe not in self.timeframes:
            self.timeframes.append(timeframe)
            self.logger.info(f"Added timeframe to strategy {self.name}: {timeframe.to_string()}")
            
            # Initialize bars for this timeframe for all symbols
            for symbol in self.symbols:
                if symbol not in self.bars:
                    self.bars[symbol] = {}
                self.bars[symbol][timeframe] = []
    
    def on_bar(self, event: Event) -> None:
        """
        Process a bar event.
        
        This method overrides the base on_bar method to handle multiple timeframes.
        It creates a Bar object and then processes it through the timeframes.
        
        Args:
            event: Bar event containing bar data
        """
        if not self.active:
            return
        
        # First call the parent's on_bar to convert the event to a Bar object
        super().on_bar(event)
        
        # Now get the bar that the parent extracted and stored
        bar_data = event.data
        symbol = bar_data['symbol']
        
        # Skip if we don't have the bar yet (parent might have failed)
        if symbol not in self.last_bar:
            self.logger.warning(f"Bar for {symbol} not found in last_bar after parent processing")
            return
            
        bar = self.last_bar[symbol]
        bar_tf = bar.timeframe
        
        # Process through all timeframes
        for tf in self.timeframes:
            # Initialize if needed
            if symbol not in self.bars:
                self.bars[symbol] = {}
            if tf not in self.bars[symbol]:
                self.bars[symbol][tf] = []
                
            # Skip if bar's timeframe is higher than requested
            try:
                if bar_tf.to_seconds() > tf.to_seconds():
                    continue
            except ValueError:
                self.logger.warning(f"Cannot compare tick timeframe, skipping aggregation")
                continue
                
            # If same timeframe, just add the bar
            if bar_tf == tf:
                self.bars[symbol][tf].append(bar)
                try:
                    self.calculate_signals_multi(symbol, tf)
                except Exception as e:
                    self.logger.error(f"Error calculating signals for {symbol} at {tf}: {e}", exc_info=True)
                continue
                
            # If lower timeframe, aggregate into higher timeframe
            # This is a simplified aggregation - in production you'd need a more robust approach
            current_bars = self.bars[symbol][tf]
            last_bar = current_bars[-1] if current_bars else None
            
            # Check if we need to start a new aggregation
            if not last_bar or self._is_new_period(bar.timestamp, last_bar.timestamp, tf):
                # Start new aggregation with this bar
                new_bar = self._create_aggregated_bar(symbol, bar, tf)
                current_bars.append(new_bar)
                self.logger.debug(f"Created new aggregated bar for {symbol} at {tf}")
            else:
                # Update existing aggregation
                self._update_aggregated_bar(current_bars[-1], bar)
                self.logger.debug(f"Updated aggregated bar for {symbol} at {tf}")
                
            # Signal calculation for this timeframe
            try:
                self.calculate_signals_multi(symbol, tf)
            except Exception as e:
                self.logger.error(f"Error calculating signals for {symbol} at {tf}: {e}", exc_info=True)
    
    @abstractmethod
    def calculate_signals_multi(self, symbol: str, timeframe: Timeframe) -> None:
        """
        Calculate trading signals for a symbol at a specific timeframe.
        
        This method must be implemented by subclasses to define
        the strategy's multi-timeframe signal generation logic.
        
        Args:
            symbol: Symbol to calculate signals for
            timeframe: Timeframe to use
        """
        pass
    
    def calculate_signals(self, bar: Bar) -> None:
        """
        Implement the single-timeframe signal calculation.
        
        This implementation just forwards to calculate_signals_multi
        using the bar's timeframe.
        
        Args:
            bar: Current bar
        """
        self.calculate_signals_multi(bar.symbol, bar.timeframe)
    
    def get_bars(self, symbol: str, timeframe: Union[str, Timeframe], n: int = -1) -> List[Bar]:
        """
        Get bars for a symbol at a specific timeframe.
        
        Args:
            symbol: Symbol to get bars for
            timeframe: Timeframe to use
            n: Number of bars to get (-1 for all)
            
        Returns:
            List[Bar]: List of bars
        """
        if isinstance(timeframe, str):
            timeframe = Timeframe.from_string(timeframe)
            
        if symbol not in self.bars or timeframe not in self.bars[symbol]:
            return []
            
        bars = self.bars[symbol][timeframe]
        
        if n <= 0:
            return bars.copy()
        return bars[-n:].copy()
    
    def _is_new_period(self, timestamp1: Any, timestamp2: Any, timeframe: Timeframe) -> bool:
        """
        Check if two timestamps belong to different periods for a timeframe.
        
        Args:
            timestamp1: First timestamp
            timestamp2: Second timestamp
            timeframe: Timeframe to use
            
        Returns:
            bool: True if the timestamps are in different periods
        """
        # Simple implementation - in production you'd need more robust period checking
        if timeframe == Timeframe.MINUTE_1:
            return timestamp1.replace(second=0, microsecond=0) != timestamp2.replace(second=0, microsecond=0)
        elif timeframe == Timeframe.MINUTE_5:
            t1 = timestamp1.replace(second=0, microsecond=0)
            t2 = timestamp2.replace(second=0, microsecond=0)
            return t1.minute // 5 != t2.minute // 5 or t1.hour != t2.hour or t1.day != t2.day
        elif timeframe == Timeframe.MINUTE_15:
            t1 = timestamp1.replace(second=0, microsecond=0)
            t2 = timestamp2.replace(second=0, microsecond=0)
            return t1.minute // 15 != t2.minute // 15 or t1.hour != t2.hour or t1.day != t2.day
        elif timeframe == Timeframe.MINUTE_30:
            t1 = timestamp1.replace(second=0, microsecond=0)
            t2 = timestamp2.replace(second=0, microsecond=0)
            return t1.minute // 30 != t2.minute // 30 or t1.hour != t2.hour or t1.day != t2.day
        elif timeframe == Timeframe.HOUR_1:
            return timestamp1.replace(minute=0, second=0, microsecond=0) != timestamp2.replace(minute=0, second=0, microsecond=0)
        elif timeframe == Timeframe.HOUR_4:
            t1 = timestamp1.replace(minute=0, second=0, microsecond=0)
            t2 = timestamp2.replace(minute=0, second=0, microsecond=0)
            return t1.hour // 4 != t2.hour // 4 or t1.day != t2.day
        elif timeframe == Timeframe.DAY_1:
            return timestamp1.date() != timestamp2.date()
        else:
            # For other timeframes, default to false to avoid over-aggregation
            return False
    
    def _create_aggregated_bar(self, symbol: str, bar: Bar, timeframe: Timeframe) -> Bar:
        """
        Create a new aggregated bar from a lower timeframe bar.
        
        Args:
            symbol: Symbol for the bar
            bar: Lower timeframe bar
            timeframe: Target timeframe
            
        Returns:
            Bar: New aggregated bar
        """
        return Bar(
            timestamp=bar.timestamp,
            symbol=symbol,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            timeframe=timeframe
        )
    
    def _update_aggregated_bar(self, agg_bar: Bar, new_bar: Bar) -> None:
        """
        Update an aggregated bar with a new lower timeframe bar.
        
        Args:
            agg_bar: Aggregated bar to update
            new_bar: New lower timeframe bar
        """
        agg_bar.high = max(agg_bar.high, new_bar.high)
        agg_bar.low = min(agg_bar.low, new_bar.low)
        agg_bar.close = new_bar.close
        agg_bar.volume += new_bar.volume