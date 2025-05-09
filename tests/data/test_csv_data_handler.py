"""
Tests for CSV data handler implementation.
"""
import os
import unittest
from datetime import datetime
import pandas as pd
from src.data.csv_data_handler import CSVDataHandler
from src.data.data_types import Bar, Timeframe

class TestCSVDataHandler(unittest.TestCase):
    """Test cases for CSVDataHandler class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create test directory
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create test data
        self.symbol = 'TEST'
        self.timeframe = Timeframe.MINUTE_1
        
        # Create test DataFrame
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=10, freq='1min'),
            'Open': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
            'High': [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0],
            'Low': [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0],
            'Close': [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5],
            'Volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        }
        self.df = pd.DataFrame(data)
        
        # Save test data to CSV
        self.csv_path = os.path.join(self.test_dir, f"{self.symbol}_1m.csv")
        self.df.to_csv(self.csv_path, index=False)
        
        # Create data handler
        self.data_handler = CSVDataHandler(
            name='test_csv_handler',
            data_dir=self.test_dir,
            filename_pattern='{symbol}_{timeframe}.csv',
            date_format='%Y-%m-%d %H:%M:%S'
        )
        
    def tearDown(self):
        """Clean up after tests."""
        # Remove test CSV
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
        
        # Remove test directory if empty
        if os.path.exists(self.test_dir) and not os.listdir(self.test_dir):
            os.rmdir(self.test_dir)
    
    def test_load_data(self):
        """Test loading data from CSV."""
        # Load data
        success = self.data_handler.load_data(
            symbols=[self.symbol],
            timeframe=self.timeframe
        )
        
        # Check result
        self.assertTrue(success)
        self.assertEqual(self.data_handler.symbols, [self.symbol])
        self.assertEqual(self.data_handler.timeframe, self.timeframe)
        self.assertIn(self.symbol, self.data_handler.bars)
        self.assertEqual(len(self.data_handler.bars[self.symbol]), 10)
    
    def test_get_latest_bar(self):
        """Test getting the latest bar."""
        # Load data
        self.data_handler.load_data(
            symbols=[self.symbol],
            timeframe=self.timeframe
        )
        
        # Initial state - no latest bar yet
        latest_bar = self.data_handler.get_latest_bar(self.symbol)
        self.assertIsNone(latest_bar)
        
        # Update bars
        self.data_handler.update_bars()
        
        # Now we should have a latest bar
        latest_bar = self.data_handler.get_latest_bar(self.symbol)
        self.assertIsNotNone(latest_bar)
        self.assertEqual(latest_bar.symbol, self.symbol)
        self.assertEqual(latest_bar.open, 100.0)
        self.assertEqual(latest_bar.high, 101.0)
        self.assertEqual(latest_bar.low, 99.0)
        self.assertEqual(latest_bar.close, 100.5)
        self.assertEqual(latest_bar.volume, 1000)
    
    def test_get_latest_bars(self):
        """Test getting multiple latest bars."""
        # Load data
        self.data_handler.load_data(
            symbols=[self.symbol],
            timeframe=self.timeframe
        )
        
        # Update bars multiple times
        for _ in range(5):
            self.data_handler.update_bars()
        
        # Get the latest 3 bars
        latest_bars = self.data_handler.get_latest_bars(self.symbol, 3)
        self.assertEqual(len(latest_bars), 3)
        
        # Check the bars
        self.assertEqual(latest_bars[0].close, 102.5)
        self.assertEqual(latest_bars[1].close, 103.5)
        self.assertEqual(latest_bars[2].close, 104.5)
    
    def test_get_all_bars(self):
        """Test getting all bars."""
        # Load data
        self.data_handler.load_data(
            symbols=[self.symbol],
            timeframe=self.timeframe
        )
        
        # Get all bars
        all_bars = self.data_handler.get_all_bars(self.symbol)
        self.assertEqual(len(all_bars), 10)
        
        # Check first and last bars
        self.assertEqual(all_bars[0].open, 100.0)
        self.assertEqual(all_bars[-1].close, 109.5)
    
    def test_update_bars(self):
        """Test updating bars."""
        # Create a mock event bus
        class MockEventBus:
            def __init__(self):
                self.events = []
                
            def publish(self, event):
                self.events.append(event)
        
        mock_bus = MockEventBus()
        
        # Load data
        self.data_handler.load_data(
            symbols=[self.symbol],
            timeframe=self.timeframe
        )
        
        # Set the event bus
        self.data_handler.event_bus = mock_bus
        
        # Update bars multiple times
        for i in range(5):
            self.data_handler.update_bars()
            
        # Check that the current index was updated
        self.assertEqual(self.data_handler.current_index[self.symbol], 5)
        
        # Check that events were published
        self.assertEqual(len(mock_bus.events), 5)
    
    def test_split_data(self):
        """Test splitting data."""
        # Load data
        self.data_handler.load_data(
            symbols=[self.symbol],
            timeframe=self.timeframe
        )
        
        # Split data with default ratio
        train_data, test_data = self.data_handler.split_data()
        
        # Check split
        self.assertEqual(len(train_data[self.symbol]), 7)  # 70% of 10
        self.assertEqual(len(test_data[self.symbol]), 3)   # 30% of 10
        
        # Check split with custom ratio
        train_data, test_data = self.data_handler.split_data(train_ratio=0.8)
        self.assertEqual(len(train_data[self.symbol]), 8)  # 80% of 10
        self.assertEqual(len(test_data[self.symbol]), 2)   # 20% of 10
    
    def test_reset(self):
        """Test resetting the data handler."""
        # Load data
        self.data_handler.load_data(
            symbols=[self.symbol],
            timeframe=self.timeframe
        )
        
        # Update bars a few times
        for _ in range(5):
            self.data_handler.update_bars()
        
        # Check current index
        self.assertEqual(self.data_handler.current_index[self.symbol], 5)
        
        # Reset
        self.data_handler.reset()
        
        # Check that current index was reset
        self.assertEqual(self.data_handler.current_index[self.symbol], 0)

if __name__ == '__main__':
    unittest.main()