"""
Tests for MovingAverageCrossover strategy.
"""
import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.strategy.implementations.ma_crossover import MovingAverageCrossover
from src.data.data_types import Bar, Timeframe
from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType

class TestMovingAverageCrossover(unittest.TestCase):
    """Test cases for MovingAverageCrossover strategy."""
    
    def setUp(self):
        """Set up test environment."""
        # Create strategy
        self.strategy = MovingAverageCrossover(
            name="test_ma_crossover",
            fast_period=2,
            slow_period=3
        )
        
        # Create mock event bus
        self.mock_event_bus = MagicMock()
        self.strategy.event_bus = self.mock_event_bus
        
        # Add a test symbol
        self.symbol = "TEST"
        self.strategy.add_symbols([self.symbol])
        
        # Initialize strategy
        self.strategy.initialize()
    
    def _create_bar(self, close_price, timestamp=None):
        """Helper to create a bar with the given close price."""
        if timestamp is None:
            timestamp = datetime.now()
            
        return Bar(
            timestamp=timestamp,
            symbol=self.symbol,
            open=close_price,
            high=close_price + 1,
            low=close_price - 1,
            close=close_price,
            volume=1000,
            timeframe=Timeframe.MINUTE_1
        )
    
    def test_initialization(self):
        """Test strategy initialization."""
        self.assertEqual(self.strategy.name, "test_ma_crossover")
        self.assertEqual(self.strategy.parameters['fast_period'], 2)
        self.assertEqual(self.strategy.parameters['slow_period'], 3)
        self.assertIn(self.symbol, self.strategy.symbols)
        
    def test_insufficient_bars(self):
        """Test behavior with insufficient data."""
        # Process 2 bars (not enough for slow period)
        self.strategy.on_bar(self._create_bar(100))
        self.strategy.on_bar(self._create_bar(105))
        
        # No signals should be generated yet
        self.mock_event_bus.publish.assert_not_called()
    
    def test_buy_signal(self):
        """Test buy signal generation on fast MA crossing above slow MA."""
        # Process enough bars to calculate MAs
        self.strategy.on_bar(self._create_bar(100))
        self.strategy.on_bar(self._create_bar(95))
        self.strategy.on_bar(self._create_bar(90))
        
        # No crossover yet
        self.mock_event_bus.publish.assert_not_called()
        
        # Create a crossover (fast crosses above slow)
        self.strategy.on_bar(self._create_bar(110))  # Fast MA becomes (110+95)/2 = 102.5, Slow MA = (110+95+90)/3 = 98.33
        
        # Buy signal should be generated
        self.mock_event_bus.publish.assert_called_once()
        args = self.mock_event_bus.publish.call_args[0]
        signal_event = args[0]
        
        self.assertEqual(signal_event.event_type, EventType.SIGNAL)
        self.assertEqual(signal_event.data['type'], 'ENTRY')
        self.assertEqual(signal_event.data['symbol'], self.symbol)
        self.assertEqual(signal_event.data['direction'], 1)
        self.assertEqual(signal_event.data['metadata']['reason'], 'MA_CROSSOVER_LONG')
    
    def test_sell_signal(self):
        """Test sell signal generation on fast MA crossing below slow MA."""
        # First generate a buy signal
        self.strategy.on_bar(self._create_bar(100))
        self.strategy.on_bar(self._create_bar(95))
        self.strategy.on_bar(self._create_bar(90))
        self.strategy.on_bar(self._create_bar(110))  # Buy signal
        
        # Reset mock
        self.mock_event_bus.publish.reset_mock()
        
        # Now create a sell crossover (fast crosses below slow)
        # We need a more dramatic price change to ensure the crossover
        self.strategy.on_bar(self._create_bar(80))
        self.strategy.on_bar(self._create_bar(70))  # This should trigger the crossover
        
        # Sell signal should be generated
        self.mock_event_bus.publish.assert_called_once()
        args = self.mock_event_bus.publish.call_args[0]
        signal_event = args[0]
        
        self.assertEqual(signal_event.event_type, EventType.SIGNAL)
        self.assertEqual(signal_event.data['type'], 'EXIT')
        self.assertEqual(signal_event.data['symbol'], self.symbol)
        self.assertEqual(signal_event.data['direction'], 0)
        self.assertEqual(signal_event.data['metadata']['reason'], 'MA_CROSSOVER_EXIT')
    
    def test_no_duplicate_signals(self):
        """Test that duplicate signals are not generated."""
        # Generate a buy signal
        self.strategy.on_bar(self._create_bar(100))
        self.strategy.on_bar(self._create_bar(95))
        self.strategy.on_bar(self._create_bar(90))
        self.strategy.on_bar(self._create_bar(110))  # Buy signal
        
        # Reset mock
        self.mock_event_bus.publish.reset_mock()
        
        # Process another bar with similar prices (no crossover)
        self.strategy.on_bar(self._create_bar(111))
        
        # No signal should be generated
        self.mock_event_bus.publish.assert_not_called()
        
    def test_reset(self):
        """Test strategy reset."""
        # Process some bars
        self.strategy.on_bar(self._create_bar(100))
        self.strategy.on_bar(self._create_bar(95))
        self.strategy.on_bar(self._create_bar(90))
        
        # Reset strategy
        self.strategy.reset()
        
        # State should be cleared
        self.assertEqual(len(self.strategy.bars_dict[self.symbol]), 0)
        self.assertIsNone(self.strategy.last_fast_ma[self.symbol])
        self.assertIsNone(self.strategy.last_slow_ma[self.symbol])
        self.assertEqual(self.strategy.last_position[self.symbol], 0)

if __name__ == '__main__':
    unittest.main()