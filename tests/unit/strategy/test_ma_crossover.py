"""
Unit tests for the Moving Average Crossover strategy.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.core.events.event_types import EventType, Event
from src.strategy.implementations.ma_crossover import MACrossoverStrategy


@pytest.mark.unit
@pytest.mark.strategy
class TestMACrossoverStrategy:
    
    @pytest.fixture
    def strategy(self, event_bus):
        """Fixture to provide a properly configured MA Crossover strategy."""
        # Create a basic configuration
        parameters = {
            'fast_window': 5,
            'slow_window': 15,
            'price_key': 'close',
            'symbols': ['TEST']
        }
        
        # Mock data handler - not needed for unit tests as we'll directly feed bar events
        data_handler = None
        
        # Create the strategy
        strategy = MACrossoverStrategy(event_bus, data_handler, parameters=parameters)
        
        return strategy
    
    @pytest.fixture
    def price_series(self):
        """Fixture to provide a series of increasing and decreasing prices."""
        # Create a series that will cause crossovers
        np.random.seed(42)
        
        # Start with an uptrend
        uptrend = np.linspace(100, 120, 20) + np.random.normal(0, 0.5, 20)
        
        # Then a downtrend
        downtrend = np.linspace(120, 100, 20) + np.random.normal(0, 0.5, 20)
        
        # Then another uptrend
        uptrend2 = np.linspace(100, 130, 20) + np.random.normal(0, 0.5, 20)
        
        # Combine into a single series
        prices = np.concatenate([uptrend, downtrend, uptrend2])
        
        return prices
    
    @pytest.fixture
    def bar_events(self, price_series):
        """Fixture to provide a series of bar events with the price series."""
        events = []
        start_date = datetime(2024, 1, 1, 9, 30)
        
        for i, price in enumerate(price_series):
            timestamp = start_date + timedelta(minutes=i)
            event_data = {
                'symbol': 'TEST',
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'open': price - 0.1,
                'high': price + 0.2,
                'low': price - 0.2,
                'close': price,
                'volume': 1000
            }
            event = Event(EventType.BAR, event_data)
            events.append(event)
        
        return events
    
    def test_initialization(self, strategy):
        """Test strategy initialization."""
        assert strategy is not None
        assert strategy.name == "ma_crossover"
        assert strategy.fast_window == 5
        assert strategy.slow_window == 15
        assert strategy.price_key == 'close'
        assert 'TEST' in strategy.symbols
    
    def test_configuration(self, event_bus):
        """Test strategy configuration."""
        # Create with default parameters
        strategy = MACrossoverStrategy(event_bus, None)
        
        # Default values
        assert strategy.fast_window == 5
        assert strategy.slow_window == 15
        
        # Reconfigure with new parameters
        new_config = {
            'fast_window': 10,
            'slow_window': 30,
            'price_key': 'open',
            'symbols': ['TEST2']
        }
        strategy.configure(new_config)
        
        # Verify new configuration
        assert strategy.fast_window == 10
        assert strategy.slow_window == 30
        assert strategy.price_key == 'open'
        assert 'TEST2' in strategy.symbols
    
    def test_reset(self, strategy):
        """Test strategy reset."""
        # Add some mock data
        strategy.data = {'TEST': [1, 2, 3, 4, 5]}
        strategy.fast_ma = {'TEST': [1, 2, 3]}
        strategy.slow_ma = {'TEST': [1, 2]}
        strategy.current_position = {'TEST': 1}
        
        # Reset the strategy
        strategy.reset()
        
        # Verify state was reset
        assert strategy.data == {'TEST': []}
        assert strategy.fast_ma == {'TEST': []}
        assert strategy.slow_ma == {'TEST': []}
        assert strategy.current_position == {'TEST': 0}
    
    def test_signal_generation(self, strategy, bar_events, event_bus):
        """Test signal generation logic."""
        # Create a list to capture emitted signals
        captured_signals = []
        
        def signal_handler(event):
            if event.get_type() == EventType.SIGNAL:
                captured_signals.append(event)
            return event
        
        # Register signal handler
        event_bus.register(EventType.SIGNAL, signal_handler)
        
        # Process bar events
        for event in bar_events:
            strategy.on_bar(event)
        
        # Verify signals were generated after sufficient data
        assert len(captured_signals) > 0
        
        # Count buy and sell signals
        buy_signals = [s for s in captured_signals if s.get_data().get('signal_value') == 1]
        sell_signals = [s for s in captured_signals if s.get_data().get('signal_value') == -1]
        
        # Should have both buy and sell signals due to our price pattern
        assert len(buy_signals) > 0
        assert len(sell_signals) > 0
        
        # Verify signal data structure
        for signal in captured_signals:
            data = signal.get_data()
            assert 'symbol' in data
            assert 'signal_value' in data
            assert 'price' in data
            assert 'timestamp' in data
    
    def test_moving_average_calculation(self, strategy, bar_events):
        """Test the internal calculation of moving averages."""
        # Process the first N+1 bars where N is the slow window
        # This will ensure we have enough data for both MAs
        for i in range(strategy.slow_window + 1):
            strategy.on_bar(bar_events[i])
        
        # Verify moving averages were calculated
        symbol = 'TEST'
        assert len(strategy.data[symbol]) == strategy.slow_window + 1
        assert len(strategy.fast_ma[symbol]) > 0
        assert len(strategy.slow_ma[symbol]) > 0
        
        # Verify fast MA has more values than slow MA (since it has a smaller window)
        assert len(strategy.fast_ma[symbol]) >= len(strategy.slow_ma[symbol])
        
        # Manually calculate expected MAs for verification
        prices = [event.get_data()['close'] for event in bar_events[:strategy.slow_window + 1]]
        expected_fast_ma = np.mean(prices[-strategy.fast_window:])
        expected_slow_ma = np.mean(prices[-strategy.slow_window:])
        
        # Verify calculated values (allow for small floating point differences)
        assert abs(strategy.fast_ma[symbol][-1] - expected_fast_ma) < 1e-10
        assert abs(strategy.slow_ma[symbol][-1] - expected_slow_ma) < 1e-10
    
    @pytest.mark.parametrize("fast_window,slow_window", [
        (5, 15),  # Default
        (3, 10),  # Smaller windows
        (10, 30)  # Larger windows
    ])
    def test_parameterized_windows(self, event_bus, bar_events, fast_window, slow_window):
        """Test strategy with different MA window parameters."""
        # Create strategy with specific parameters
        parameters = {
            'fast_window': fast_window,
            'slow_window': slow_window,
            'price_key': 'close',
            'symbols': ['TEST']
        }
        strategy = MACrossoverStrategy(event_bus, None, parameters=parameters)
        
        # Process enough bars to generate signals
        for event in bar_events[:slow_window+10]:
            strategy.on_bar(event)
        
        # Verify MAs are calculated correctly with different window sizes
        symbol = 'TEST'
        assert len(strategy.fast_ma[symbol]) > 0
        assert len(strategy.slow_ma[symbol]) > 0
        
        # Calculate expected values for verification
        prices = [event.get_data()['close'] for event in bar_events[:slow_window+10]]
        expected_fast_ma = np.mean(prices[-fast_window:])
        expected_slow_ma = np.mean(prices[-slow_window:])
        
        # Verify calculated values
        assert abs(strategy.fast_ma[symbol][-1] - expected_fast_ma) < 1e-10
        assert abs(strategy.slow_ma[symbol][-1] - expected_slow_ma) < 1e-10
