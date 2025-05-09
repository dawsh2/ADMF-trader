"""
CSV data handler implementation.

This module provides a concrete implementation of the DataHandler interface
for loading and managing market data from CSV files.
"""

import os
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union, Iterator
import collections

from src.core.component import Component
from src.core.event_system import Event, EventType
from src.data.data_handler import DataHandler
from src.data.data_types import Bar, Tick, Timeframe

logger = logging.getLogger(__name__)

class CSVDataHandler(DataHandler):
    """
    Data handler implementation for CSV files.
    
    CSVDataHandler loads OHLCV data from CSV files and provides
    methods for accessing the data and emitting bar events.
    """
    
    def __init__(self, name: str, data_dir: str, 
                 filename_pattern='{symbol}_{timeframe}.csv',
                 date_column='timestamp', 
                 date_format='%Y-%m-%d %H:%M:%S',
                 column_map=None):
        """
        Initialize the CSV data handler.
        
        Args:
            name: Component name
            data_dir: Directory containing CSV files
            filename_pattern: Pattern for filenames
            date_column: Column containing dates
            date_format: Format of dates in CSV
            column_map: Map of CSV columns to standard column names
        """
        super().__init__(name)
        self.data_dir = data_dir
        self.filename_pattern = filename_pattern
        self.date_column = date_column
        self.date_format = date_format
        self.column_map = column_map or {
            'open': ['open', 'Open', 'OPEN'],
            'high': ['high', 'High', 'HIGH'],
            'low': ['low', 'Low', 'LOW'],
            'close': ['close', 'Close', 'CLOSE'],
            'volume': ['volume', 'Volume', 'VOLUME', 'vol', 'Vol']
        }
        
        # Data storage
        self.data = {}  # Dict[symbol, pd.DataFrame]
        self.bars = {}  # Dict[symbol, List[Bar]]
        self.symbols = []
        self.current_index = {}  # Dict[symbol, int]
        self.timeframe = Timeframe.DAY_1
        
    def load_data(self, symbols: List[str], start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None, 
                 timeframe: Union[str, Timeframe] = Timeframe.DAY_1) -> bool:
        """
        Load data for the specified symbols and time range.
        
        Args:
            symbols: List of symbols to load
            start_date: Start date for data, or None for all available
            end_date: End date for data, or None for all available
            timeframe: Timeframe for data
            
        Returns:
            bool: True if data loaded successfully, False otherwise
        """
        self.logger.info(f"Loading data for symbols: {symbols}")
        
        # Store the symbols and timeframe
        self.symbols = symbols
        
        # Convert timeframe to enum if it's a string
        if isinstance(timeframe, str):
            self.timeframe = Timeframe.from_string(timeframe)
        else:
            self.timeframe = timeframe
            
        timeframe_str = self.timeframe.to_string()
        
        # Load data for each symbol
        success = True
        for symbol in symbols:
            try:
                # Get filename for the symbol and timeframe
                filename = self._get_filename(symbol, timeframe_str)
                
                if not os.path.exists(filename):
                    self.logger.warning(f"File not found: {filename}")
                    success = False
                    continue
                
                # Read CSV file
                df = pd.read_csv(filename)
                self.logger.info(f"Loaded {len(df)} rows for {symbol}")
                
                # Process date column
                if self.date_column in df.columns:
                    # Convert date column to datetime
                    df[self.date_column] = pd.to_datetime(
                        df[self.date_column], 
                        format=self.date_format,
                        errors='coerce'  # Replace invalid dates with NaT
                    )
                    
                    # Drop rows with invalid dates
                    df = df.dropna(subset=[self.date_column])
                    
                    # Filter by date range if provided
                    if start_date:
                        df = df[df[self.date_column] >= start_date]
                        
                    if end_date:
                        df = df[df[self.date_column] <= end_date]
                else:
                    self.logger.warning(f"Date column {self.date_column} not found in {filename}")
                    success = False
                    continue
                
                # Map column names to standard names
                column_mapping = self._map_columns(df.columns)
                df = df.rename(columns=column_mapping)
                
                # Ensure required columns exist
                required_columns = ['open', 'high', 'low', 'close']
                if not all(col in df.columns for col in required_columns):
                    missing = [col for col in required_columns if col not in df.columns]
                    self.logger.warning(f"Missing required columns in {filename}: {missing}")
                    success = False
                    continue
                
                # Add volume if not present
                if 'volume' not in df.columns:
                    df['volume'] = 0
                    self.logger.info(f"Added placeholder volume column to {filename}")
                
                # Store the DataFrame
                self.data[symbol] = df
                
                # Debug column mapping and date column
                self.logger.info(f"Columns after mapping: {list(df.columns)}")
                self.logger.info(f"Date column: {self.date_column}")
                if self.date_column in df.columns:
                    self.logger.info(f"First few timestamps: {df[self.date_column].head(3).tolist()}")
                
                # Convert to Bar objects
                self.bars[symbol] = self._dataframe_to_bars(df, symbol)
                
                # Initialize current index
                self.current_index[symbol] = 0
                
                self.logger.info(f"Successfully loaded data for {symbol}: {len(self.bars[symbol])} bars")
                
            except Exception as e:
                self.logger.error(f"Error loading data for {symbol}: {e}", exc_info=True)
                success = False
        
        return success
    
    def get_latest_bar(self, symbol: str) -> Optional[Bar]:
        """
        Get the latest bar for a symbol.
        
        Args:
            symbol: Symbol to get bar for
            
        Returns:
            Optional[Bar]: Latest bar or None if not available
        """
        if symbol not in self.bars or not self.bars[symbol]:
            return None
        
        bars = self.bars[symbol]
        idx = self.current_index.get(symbol, 0)
        
        if idx >= len(bars):
            return None
            
        return bars[idx - 1] if idx > 0 else None
    
    def get_latest_bars(self, symbol: str, n: int = 1) -> List[Bar]:
        """
        Get the latest n bars for a symbol.
        
        Args:
            symbol: Symbol to get bars for
            n: Number of bars to get
            
        Returns:
            List[Bar]: List of bars (may be empty)
        """
        if symbol not in self.bars or not self.bars[symbol]:
            return []
        
        bars = self.bars[symbol]
        idx = self.current_index.get(symbol, 0)
        
        # Return the latest n bars up to the current index
        start_idx = max(0, idx - n)
        return bars[start_idx:idx] if idx > 0 else []
    
    def get_all_bars(self, symbol: str) -> List[Bar]:
        """
        Get all bars for a symbol.
        
        Args:
            symbol: Symbol to get bars for
            
        Returns:
            List[Bar]: List of all bars (may be empty)
        """
        if symbol not in self.bars:
            return []
            
        return self.bars[symbol]
    
    def update_bars(self):
        """
        Update bars and emit bar events.
        
        This method advances to the next bar for each symbol
        and emits bar events.
        """
        any_bars_updated = False
        
        for symbol in self.symbols:
            if symbol not in self.bars or not self.bars[symbol]:
                self.logger.warning(f"No bars available for {symbol}")
                continue
                
            bars = self.bars[symbol]
            idx = self.current_index.get(symbol, 0)
            
            if idx >= len(bars):
                self.logger.debug(f"Reached end of data for {symbol} at index {idx}")
                continue
                
            # Get the current bar
            bar = bars[idx]
            any_bars_updated = True
            
            # Emit bar event if event bus is set
            if self.event_bus:
                # Convert bar to dict and print for debugging (set to debug level)
                bar_dict = bar.to_dict()
                self.logger.debug(f"Emitting bar event for {symbol} at {bar.timestamp}: {bar_dict}")
                
                self.emit_bar_event(bar)
                self.logger.debug(f"Emitted bar event for {symbol} at {bar.timestamp}")
            else:
                self.logger.warning(f"Event bus not set, cannot emit bar event for {symbol}")
            
            # Advance to the next bar
            self.current_index[symbol] = idx + 1
            
            if idx % 100 == 0:  # Only log occasionally to avoid flooding
                self.logger.info(f"Updated bar for {symbol}: {bar.timestamp}, index {idx}/{len(bars)}")
        
        return any_bars_updated
    
    def split_data(self, train_ratio: float = 0.7) -> Tuple[Dict[str, List[Bar]], Dict[str, List[Bar]]]:
        """
        Split data into training and testing sets.
        
        Args:
            train_ratio: Ratio of data to use for training (0.0-1.0)
            
        Returns:
            Tuple[Dict[str, List[Bar]], Dict[str, List[Bar]]]: Training and testing data
        """
        train_data = {}
        test_data = {}
        
        for symbol in self.symbols:
            if symbol not in self.bars or not self.bars[symbol]:
                train_data[symbol] = []
                test_data[symbol] = []
                continue
                
            bars = self.bars[symbol]
            split_idx = int(len(bars) * train_ratio)
            
            train_data[symbol] = bars[:split_idx]
            test_data[symbol] = bars[split_idx:]
            
            self.logger.info(f"Split data for {symbol}: {len(train_data[symbol])} training bars, "
                            f"{len(test_data[symbol])} testing bars")
        
        return train_data, test_data
    
    def reset(self) -> None:
        """Reset the data handler."""
        super().reset()
        
        # Reset current indices
        for symbol in self.symbols:
            self.current_index[symbol] = 0
            
        self.logger.info(f"Reset data handler {self.name}")
        
    def _get_filename(self, symbol: str, timeframe: str) -> str:
        """
        Get the filename for a symbol and timeframe.
        
        Args:
            symbol: Symbol
            timeframe: Timeframe string
            
        Returns:
            str: Full path to the file
        """
        # Format the filename according to the pattern
        filename = self.filename_pattern.format(symbol=symbol, timeframe=timeframe)
        full_path = os.path.join(self.data_dir, filename)
        
        # Check if the file exists
        if not os.path.exists(full_path):
            # Try alternative filenames
            alternatives = [
                f"{symbol}_{timeframe}.csv",
                f"{symbol}_{timeframe}in.csv",  # Handle 1min vs 1m difference
                f"{symbol}.csv"
            ]
            
            for alt in alternatives:
                alt_path = os.path.join(self.data_dir, alt)
                if os.path.exists(alt_path):
                    self.logger.info(f"Using alternative filename: {alt} instead of {filename}")
                    return alt_path
        
        return full_path
    
    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """
        Map CSV columns to standard names.
        
        Args:
            columns: List of column names from CSV
            
        Returns:
            Dict[str, str]: Mapping from original to standard column names
        """
        result = {}
        
        for std_name, possible_names in self.column_map.items():
            for col in columns:
                # Compare case-insensitively
                if col.lower() in [name.lower() for name in possible_names]:
                    result[col] = std_name
                    break
        
        return result
    
    def _dataframe_to_bars(self, df: pd.DataFrame, symbol: str) -> List[Bar]:
        """
        Convert DataFrame to list of Bar objects.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Symbol for the data
            
        Returns:
            List[Bar]: List of Bar objects
        """
        bars = []
        
        # Debug required columns
        self.logger.info(f"DataFrame columns: {list(df.columns)}")
        required_cols = ['open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            self.logger.error(f"Missing required columns: {missing_cols}")
            return bars
        
        if len(df) == 0:
            self.logger.warning(f"DataFrame is empty for {symbol}")
            return bars
            
        # Log a few sample rows
        self.logger.info(f"Sample row 0: {dict(df.iloc[0])}")
        
        for idx, row in df.iterrows():
            try:
                bar = Bar(
                    timestamp=row[self.date_column],
                    symbol=symbol,
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row.get('volume', 0)),
                    timeframe=self.timeframe
                )
                bars.append(bar)
            except (KeyError, ValueError) as e:
                self.logger.warning(f"Error creating bar from row {row}: {e}")
                continue
        
        return bars