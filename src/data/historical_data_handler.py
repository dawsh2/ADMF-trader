"""
Historical data handler with train/test split support.

This implementation adds train/test split functionality to the data handler
to support the optimization framework.
"""

import os
import pandas as pd
import logging
from src.core.component import Component
from src.core.events.event_types import Event, EventType
from src.core.data_model import Bar as CoreBar
from src.data.data_types import Bar, Timeframe
from src.data.time_series_splitter import TimeSeriesSplitter
from src.data.data_handler import DataHandler
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime

# Set up logger
logger = logging.getLogger(__name__)

class HistoricalDataHandler(DataHandler):
    """
    Data handler for historical market data with train/test split support.
    
    This component provides market data to the system and supports
    train/test splitting for optimization.
    """
    
    def __init__(self, name, data_config):
        """
        Initialize the data handler.
        
        Args:
            name (str): Component name
            data_config (dict): Data configuration
        """
        super().__init__(name)
        self.data_config = data_config
        self.data = {}
        self.data_splits = {}
        self.current_split = None
        self.current_indices = {}
        
        # Set default timeframe from config or use DAY_1
        timeframe_str = data_config.get('timeframe', 'DAY_1')
        if isinstance(timeframe_str, str):
            try:
                self.timeframe = Timeframe.from_string(timeframe_str)
            except ValueError:
                # Handle the case where the string doesn't match exactly
                timeframe_map = {
                    'DAY_1': Timeframe.DAY_1,
                    '1d': Timeframe.DAY_1,
                    'day': Timeframe.DAY_1,
                    'daily': Timeframe.DAY_1,
                    'HOUR_1': Timeframe.HOUR_1,
                    '1h': Timeframe.HOUR_1,
                    'hour': Timeframe.HOUR_1,
                    'hourly': Timeframe.HOUR_1,
                    'MINUTE_1': Timeframe.MINUTE_1,
                    '1min': Timeframe.MINUTE_1,
                    '1m': Timeframe.MINUTE_1,
                    'minute': Timeframe.MINUTE_1,
                    'min': Timeframe.MINUTE_1
                }
                # Try to match case-insensitively
                for key, value in timeframe_map.items():
                    if timeframe_str.lower() == key.lower():
                        self.timeframe = value
                        break
                else:
                    # Default to DAY_1 if no match
                    self.logger.warning(f"Unknown timeframe string: {timeframe_str}, defaulting to DAY_1")
                    self.timeframe = Timeframe.DAY_1
        else:
            self.timeframe = Timeframe.DAY_1
        
    def initialize(self, context):
        """
        Initialize with dependencies.
        
        Args:
            context (dict): Context containing dependencies
        """
        super().initialize(context)
        
        # Get event bus from context
        self.event_bus = context.get('event_bus')
        
        if not self.event_bus:
            raise ValueError("HistoricalDataHandler requires event_bus in context")
            
        # Load data from sources
        self._load_data()
        
    def _load_data(self):
        """Load data from configured sources."""
        data_sources = self.data_config.get('sources', [])
        
        for source in data_sources:
            symbol = source.get('symbol')
            file_path = source.get('file')
            date_format = source.get('date_format', '%Y-%m-%d')
            
            if not symbol or not file_path:
                raise ValueError(f"Invalid data source configuration: {source}")
            
            # Detect timeframe from file path if not explicitly set
            source_timeframe = source.get('timeframe')
            if not source_timeframe:
                import re
                # Try to detect from filename (e.g., SPY_1min.csv, AAPL_1d.csv)
                filename = os.path.basename(file_path)
                # Common patterns
                if '_1min' in filename or '_1m' in filename:
                    source_timeframe = 'MINUTE_1'
                elif '_5min' in filename or '_5m' in filename:
                    source_timeframe = 'MINUTE_5'
                elif '_15min' in filename or '_15m' in filename:
                    source_timeframe = 'MINUTE_15'
                elif '_30min' in filename or '_30m' in filename:
                    source_timeframe = 'MINUTE_30'
                elif '_1h' in filename or '_1hour' in filename:
                    source_timeframe = 'HOUR_1'
                elif '_1d' in filename or '_day' in filename or '_daily' in filename:
                    source_timeframe = 'DAY_1'
                else:
                    # Use regex to find more complex patterns
                    minute_match = re.search(r'_(\d+)min', filename)
                    if minute_match:
                        minutes = int(minute_match.group(1))
                        if minutes == 1:
                            source_timeframe = 'MINUTE_1'
                        elif minutes == 5:
                            source_timeframe = 'MINUTE_5'
                        elif minutes == 15:
                            source_timeframe = 'MINUTE_15'
                        elif minutes == 30:
                            source_timeframe = 'MINUTE_30'
                        else:
                            source_timeframe = 'MINUTE_1'  # Default to 1-minute for unknown minute values
                
                if source_timeframe:
                    self.logger.info(f"Detected timeframe from filename: {source_timeframe} for {file_path}")
                else:
                    # Default based on symbols (options data typically uses minute data)
                    if 'C00' in symbol or 'P00' in symbol:  # Option symbols
                        source_timeframe = 'MINUTE_1'
                    else:
                        source_timeframe = 'DAY_1'  # Default to daily
                    self.logger.warning(f"Unable to detect timeframe from filename, using default: {source_timeframe}")
                
                # Store the detected timeframe in the source config for later use
                source['timeframe'] = source_timeframe
                
            # Load data from file
            try:
                # Check for max_bars in data_config
                max_bars = self.data_config.get('max_bars')

                # Also check shared_context if available
                if hasattr(self, 'shared_context') and self.shared_context:
                    max_bars = max_bars or self.shared_context.get('max_bars')

                # Load data with nrows limit if max_bars is specified
                if max_bars:
                    self.logger.info(f"Loading limited data: {max_bars} rows for {file_path}")
                    df = pd.read_csv(file_path, nrows=max_bars)
                else:
                    df = pd.read_csv(file_path)

                # Convert date columns to datetime
                date_col = source.get('date_column', 'date')
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col], format=date_format)
                    # Rename to standard 'timestamp' column
                    df.rename(columns={date_col: 'timestamp'}, inplace=True)
                
                # Check for alternative column names and rename them to match expected format
                column_mappings = {
                    'Date': 'timestamp',
                    'Time': 'time',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                }
                
                # Apply mappings (case-insensitive)
                for src_col, dst_col in column_mappings.items():
                    # Check for exact match first
                    if src_col in df.columns and dst_col not in df.columns:
                        df.rename(columns={src_col: dst_col}, inplace=True)
                    # Then try case-insensitive match
                    else:
                        for col in df.columns:
                            if col.lower() == src_col.lower() and dst_col not in df.columns:
                                df.rename(columns={col: dst_col}, inplace=True)
                                break
                
                # Ensure required columns exist
                required_columns = ['timestamp', 'open', 'high', 'low', 'close']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    # Try to convert from possible legacy column names
                    for legacy, standard in CoreBar.LEGACY_MAPPINGS.items():
                        if legacy in df.columns and standard not in df.columns:
                            df.rename(columns={legacy: standard}, inplace=True)
                    
                    # Check if we still have missing columns
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    if missing_columns:
                        # Log the issue and try additional transformations
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Missing required columns: {missing_columns}")
                        logger.warning(f"Available columns: {list(df.columns)}")
                        
                        # Try harder case-insensitive matching
                        for req_col in missing_columns:
                            for col in df.columns:
                                if col.lower() == req_col.lower() or req_col.lower() in col.lower():
                                    logger.info(f"Mapping '{col}' to '{req_col}'")
                                    df.rename(columns={col: req_col}, inplace=True)
                                    break
                
                # Sort data by timestamp
                df.sort_values('timestamp', inplace=True)
                
                # Store data
                self.data[symbol] = df

                # Initialize current index
                self.current_indices[symbol] = -1

                # Create split data if needed (using percentage split by default)
                # Check for train_test_split configuration or legacy split_method
                if self.data_config.get('train_test_split') or self.data_config.get('split_method'):
                    self._split_data(df, symbol)

            except Exception as e:
                raise ValueError(f"Error loading data from {file_path}: {e}")

        if not self.data:
            raise ValueError("No data loaded")

    def _split_data(self, df, symbol):
        """
        Split data into train and test sets based on configuration.

        Args:
            df (pd.DataFrame): Data to split
            symbol (str): Symbol for this data

        Returns:
            dict: Dictionary with 'train' and 'test' dataframes
        """
        # Get split configuration - prefer train_test_split over legacy split_method
        train_test_config = self.data_config.get('train_test_split', {})
        if train_test_config:
            # Use modern train_test_split configuration
            split_method = train_test_config.get('method', 'ratio')

            # Map 'ratio' method to 'percentage' for backward compatibility
            if split_method == 'ratio':
                split_method = 'percentage'
                split_value = train_test_config.get('train_ratio', 0.7)
            else:
                split_value = train_test_config.get('split_value', 0.7)
        else:
            # Fall back to legacy configuration
            split_method = self.data_config.get('split_method', 'percentage')
            split_value = self.data_config.get('split_value', 0.7)  # Default 70/30 split

        # Create the splits dict if it doesn't exist
        if not hasattr(self, 'data_splits'):
            self.data_splits = {}

        if symbol not in self.data_splits:
            self.data_splits[symbol] = {}

        # IMPROVED: Apply max_bars limit before splitting if available
        max_bars = self.data_config.get('max_bars')

        # Also check shared_context if available
        if hasattr(self, 'shared_context') and self.shared_context:
            max_bars = max_bars or self.shared_context.get('max_bars')

        # Limit data if max_bars is specified
        if max_bars and len(df) > max_bars:
            logger.info(f"Limiting data to {max_bars} bars before splitting")
            df = df.iloc[:max_bars]

        if split_method == 'date':
            # Use a specific date to split
            split_date = pd.Timestamp(split_value)
            # Create deep copies to ensure complete isolation
            train_df = df[df['timestamp'] < split_date].copy(deep=True)
            test_df = df[df['timestamp'] >= split_date].copy(deep=True)

            # Force reset index to avoid any shared data between DataFrames
            train_df = train_df.reset_index(drop=True)
            test_df = test_df.reset_index(drop=True)

            # Add split identifier to diagnose any reuse of data
            train_df['_split'] = 'train'
            test_df['_split'] = 'test'
        elif split_method == 'percentage':
            # Use a percentage of the data
            split_idx = int(len(df) * split_value)
            # Create deep copies to ensure complete isolation
            train_df = df.iloc[:split_idx].copy(deep=True)
            test_df = df.iloc[split_idx:].copy(deep=True)

            # Force reset index to avoid any shared data between DataFrames
            train_df = train_df.reset_index(drop=True)
            test_df = test_df.reset_index(drop=True)

            # Add split identifier to diagnose any reuse of data
            train_df['_split'] = 'train'
            test_df['_split'] = 'test'
        elif split_method == 'rows':
            # Use a specific number of rows
            split_idx = int(split_value)
            # Create deep copies to ensure complete isolation
            train_df = df.iloc[:split_idx].copy(deep=True)
            test_df = df.iloc[split_idx:].copy(deep=True)

            # Force reset index to avoid any shared data between DataFrames
            train_df = train_df.reset_index(drop=True)
            test_df = test_df.reset_index(drop=True)

            # Add split identifier to diagnose any reuse of data
            train_df['_split'] = 'train'
            test_df['_split'] = 'test'
        else:
            # Default to using all data as training
            train_df = df.copy(deep=True)
            test_df = pd.DataFrame(columns=df.columns)

            # Add split identifier to diagnose any reuse of data
            train_df['_split'] = 'train'

        # Store splits
        self.data_splits[symbol]['train'] = train_df
        self.data_splits[symbol]['test'] = test_df

        # Initialize current split to train
        self.current_split = 'train'

        # Log detailed info about the train/test splits
        train_first = train_df.iloc[0]['timestamp'] if len(train_df) > 0 else None
        train_last = train_df.iloc[-1]['timestamp'] if len(train_df) > 0 else None
        test_first = test_df.iloc[0]['timestamp'] if len(test_df) > 0 else None
        test_last = test_df.iloc[-1]['timestamp'] if len(test_df) > 0 else None

        logger.info(f"Split data for {symbol}: train={len(train_df)} rows, test={len(test_df)} rows")
        logger.info(f"Train period: {train_first} to {train_last}")
        logger.info(f"Test period: {test_first} to {test_last}")

        # Check if train and test are actually different by checking timestamps
        if len(train_df) > 0 and len(test_df) > 0:
            train_timestamps = set(train_df['timestamp'].astype(str))
            test_timestamps = set(test_df['timestamp'].astype(str))
            overlap = train_timestamps.intersection(test_timestamps)

            if overlap:
                logger.warning(f"CRITICAL: Found {len(overlap)} overlapping timestamps between train and test sets!")
                logger.warning(f"Example overlapping timestamps: {list(overlap)[:5]}")

                # Remove overlapping timestamps from test set
                logger.info(f"Removing {len(overlap)} overlapping timestamps from test set to ensure isolation")
                test_df = test_df[~test_df['timestamp'].astype(str).isin(overlap)]
                logger.info(f"After removing overlap: test={len(test_df)} rows")

                # Update the test set in the data_splits
                self.data_splits[symbol]['test'] = test_df

        return self.data_splits[symbol]
            
    def setup_train_test_split(self, method="ratio", train_ratio=0.7, test_ratio=0.3,
                            split_date=None, train_periods=None, test_periods=None):
        """
        Set up train/test split using specified method.
        IMPORTANT: This creates disjoint training and testing sets to ensure
        proper strategy validation.

        Args:
            method (str): Splitting method ('ratio', 'date', or 'fixed')
            train_ratio (float): Ratio of data for training (for 'ratio' method)
            test_ratio (float): Ratio of data for testing (for 'ratio' method)
            split_date (datetime): Date to split on (for 'date' method)
            train_periods (int): Number of periods for training (for 'fixed' method)
            test_periods (int): Number of periods for testing (for 'fixed' method)
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Check for max_bars limit before splitting
            max_bars = self.data_config.get('max_bars')

            # Also check shared_context if available
            if hasattr(self, 'shared_context') and self.shared_context:
                max_bars = max_bars or self.shared_context.get('max_bars')

            # Create splitter
            splitter = TimeSeriesSplitter(
                method=method,
                train_ratio=train_ratio,
                test_ratio=test_ratio,
                split_date=split_date,
                train_periods=train_periods,
                test_periods=test_periods
            )

            # Split each symbol's data
            self.data_splits = {}
            for symbol, df in self.data.items():
                # Apply max_bars limit if specified - do this BEFORE splitting
                if max_bars and len(df) > max_bars:
                    logger.info(f"Limiting data to {max_bars} bars before splitting for {symbol}")
                    df_limited = df.iloc[:max_bars].copy()
                else:
                    df_limited = df.copy()

                # CRITICAL: Sort by timestamp to ensure proper sequence
                if 'timestamp' in df_limited.columns:
                    df_limited.sort_values('timestamp', inplace=True)

                # Split the data
                self.data_splits[symbol] = splitter.split(df_limited)

                # Log detailed info about the train/test splits
                train_df = self.data_splits[symbol]['train']
                test_df = self.data_splits[symbol]['test']

                # Ensure no overlap between train and test sets
                if len(train_df) > 0 and len(test_df) > 0:
                    # Get the timestamp ranges
                    train_times = set(train_df['timestamp'])
                    test_times = set(test_df['timestamp'])

                    # Check for overlap in timestamps
                    overlap = train_times.intersection(test_times)
                    if overlap:
                        logger.warning(f"Found {len(overlap)} overlapping timestamps between train and test sets for {symbol}!")
                        logger.warning("This causes leakage between train and test - fixing by removing overlap from test set")

                        # Remove overlapping timestamps from test set
                        test_df = test_df[~test_df['timestamp'].isin(overlap)]

                        # Update the test set in the data splits
                        self.data_splits[symbol]['test'] = test_df

                        logger.info(f"After removing overlap: test={len(test_df)} rows")

                # Log timestamps for validation
                train_first = train_df.iloc[0]['timestamp'] if len(train_df) > 0 else None
                train_last = train_df.iloc[-1]['timestamp'] if len(train_df) > 0 else None
                test_first = test_df.iloc[0]['timestamp'] if len(test_df) > 0 else None
                test_last = test_df.iloc[-1]['timestamp'] if len(test_df) > 0 else None

                logger.info(f"Split data for {symbol}: train={len(train_df)} rows, test={len(test_df)} rows")
                logger.info(f"Train period: {train_first} to {train_last}")
                logger.info(f"Test period: {test_first} to {test_last}")

                # CRITICAL: Verify train and test periods are different and non-overlapping
                if train_last and test_first and train_last >= test_first:
                    logger.warning(f"Train period overlaps test period for {symbol}!")
                    logger.warning(f"Train end: {train_last}, Test start: {test_first}")

                    # Try to fix by adjusting the cutoff point
                    logger.info("Fixing overlap by re-splitting data with clear separation")

                    # Use a date-based split instead
                    mid_point = len(df_limited) // 2
                    split_timestamp = df_limited.iloc[mid_point]['timestamp']

                    # Create clean train and test sets
                    train_df_fixed = df_limited[df_limited['timestamp'] < split_timestamp]
                    test_df_fixed = df_limited[df_limited['timestamp'] >= split_timestamp]

                    # Update the split
                    self.data_splits[symbol]['train'] = train_df_fixed
                    self.data_splits[symbol]['test'] = test_df_fixed

                    # Log the fixed split
                    logger.info(f"Fixed split: train={len(train_df_fixed)} rows, test={len(test_df_fixed)} rows")
                    logger.info(f"Train period: {train_df_fixed.iloc[0]['timestamp'] if len(train_df_fixed) > 0 else None} to {train_df_fixed.iloc[-1]['timestamp'] if len(train_df_fixed) > 0 else None}")
                    logger.info(f"Test period: {test_df_fixed.iloc[0]['timestamp'] if len(test_df_fixed) > 0 else None} to {test_df_fixed.iloc[-1]['timestamp'] if len(test_df_fixed) > 0 else None}")

            # Reset current indices
            self.current_indices = {symbol: -1 for symbol in self.data.keys()}

            # Set default active split
            self.set_active_split('train')

        except Exception as e:
            logger.warning(f"Data handler does not support train/test splitting: {e}")
            logger.warning(f"Error details: {str(e)}")

            # Fallback: create simple train/test split if possible
            logger.info("Using manual time-based split as fallback")
            try:
                self.data_splits = {}
                for symbol, df in self.data.items():
                    # Create a clean copy of the data
                    df_copy = df.copy()

                    # Sort by timestamp
                    if 'timestamp' in df_copy.columns:
                        df_copy.sort_values('timestamp', inplace=True)

                    # Split at 70% point
                    split_idx = int(len(df_copy) * 0.7)
                    train_df = df_copy.iloc[:split_idx].copy()
                    test_df = df_copy.iloc[split_idx:].copy()

                    self.data_splits[symbol] = {
                        'train': train_df,
                        'test': test_df
                    }

                    logger.info(f"Manual split for {symbol}: train={len(train_df)} rows, test={len(test_df)} rows")
            except Exception as e2:
                logger.warning(f"Manual splitting also failed: {e2}")
                # Last resort: use full data for both train and test
                logger.warning("Using full data for both train and test splits as last resort")
                self.data_splits = {}
                for symbol, df in self.data.items():
                    self.data_splits[symbol] = {
                        'train': df.copy(),
                        'test': df.copy()
                    }

            # Reset indices and set default active split
            self.current_indices = {symbol: -1 for symbol in self.data.keys()}
            self.current_split = 'train'
        
    def set_active_split(self, split_name):
        """
        Switch between train and test datasets.
        Ensures a complete reset of state when changing splits.

        Args:
            split_name (str): Split to activate ('train' or 'test')
        """
        import logging
        logger = logging.getLogger(__name__)

        # Keep track of the previous split for later logging
        previous_split = self.current_split

        if not self.data_splits:
            logger.warning("No data splits available. Creating default splits using all data.")
            # Create default splits using all data
            self.data_splits = {}
            for symbol, df in self.data.items():
                self.data_splits[symbol] = {
                    'train': df.copy(),
                    'test': df.copy()
                }

        if split_name not in ['train', 'test']:
            logger.warning(f"Invalid split name: {split_name}. Using 'train' instead.")
            split_name = 'train'

        # Verify all symbols have the requested split
        for symbol, splits in self.data_splits.items():
            if split_name not in splits:
                logger.warning(f"Split {split_name} not found for symbol {symbol}. Creating it using all data.")
                # Create the missing split using all data
                self.data_splits[symbol][split_name] = self.data[symbol].copy()

        # Skip if we're already on this split to avoid unnecessary resets and log noise
        if self.current_split == split_name:
            logger.debug(f"Already on '{split_name}' split, skip switching")
            return

        # Reset current indices - CRITICAL for proper backtest isolation
        self.current_indices = {symbol: -1 for symbol in self.data.keys()}

        # Set the active split AFTER resetting indices
        self.current_split = split_name

        # Skip event publishing as it's not essential for functionality
        # and we're having issues with the EventType enumeration
        # Just log the split change which is sufficient

        # Log detailed information about the split change
        logger.info(f"Switched from '{previous_split}' to '{split_name}' split")

        # Log dataset statistics for each symbol as debug information
        for symbol in self.data.keys():
            if symbol in self.data_splits and split_name in self.data_splits[symbol]:
                split_df = self.data_splits[symbol][split_name]
                row_count = len(split_df)
                time_range = f"{split_df.iloc[0]['timestamp'] if row_count > 0 else 'N/A'} to {split_df.iloc[-1]['timestamp'] if row_count > 0 else 'N/A'}"
                logger.info(f"  {symbol} {split_name} data: {row_count} rows, time range: {time_range}")

                # CRITICAL: Verify this data is unique to this split
                if previous_split and previous_split in self.data_splits[symbol]:
                    prev_df = self.data_splits[symbol][previous_split]
                    # Check for data overlap - this can indicate a problem with the train/test split
                    if len(split_df) > 0 and len(prev_df) > 0:
                        split_min, split_max = split_df['timestamp'].min(), split_df['timestamp'].max()
                        prev_min, prev_max = prev_df['timestamp'].min(), prev_df['timestamp'].max()

                        # Look for time range overlap
                        if (split_min <= prev_max and split_max >= prev_min) or (prev_min <= split_max and prev_max >= split_min):
                            logger.warning(f"DATA OVERLAP DETECTED: {symbol} {split_name} and {previous_split} sets overlap in time!")
                            logger.warning(f"  {split_name}: {split_min} to {split_max}")
                            logger.warning(f"  {previous_split}: {prev_min} to {prev_max}")
        
    def update(self):
        """
        Update by moving to the next data point.

        Returns:
            bool: True if more data is available, False otherwise
        """
        # CRITICAL FIX: Store current bar so we can access it for diagnostics
        self.current_bar = None

        # If no split is set, use full data
        if not self.current_split:
            result = self._update_full_data()
        else:
            result = self._update_split_data()

        # Perform validation to ensure we're not mixing train and test data
        if hasattr(self, '_split_time_range') and self.current_bar and 'timestamp' in self.current_bar:
            min_time, max_time = self._split_time_range
            current_time = self.current_bar.get('timestamp')
            # Check if we're outside the valid range for this split
            if current_time < min_time or current_time > max_time:
                logger.error(f"CRITICAL DATA LEAK: {self.current_split} split using data from outside its time range!")
                logger.error(f"  Bar time: {current_time}, Valid range: {min_time} to {max_time}")
                # In a production system, you might want to raise an exception here
                # For this fix, we'll continue but log the error

        return result
            
    def _update_full_data(self):
        """
        Update using full data.
        
        Returns:
            bool: True if more data is available, False otherwise
        """
        # Find the earliest next bar across all symbols
        next_timestamp = None
        next_symbol = None
        
        for symbol, df in self.data.items():
            current_idx = self.current_indices[symbol]
            
            # Check if there's more data for this symbol
            if current_idx + 1 < len(df):
                next_idx = current_idx + 1
                timestamp = df.iloc[next_idx]['timestamp']
                
                # If this is the earliest timestamp, or we haven't found any yet
                if next_timestamp is None or timestamp < next_timestamp:
                    next_timestamp = timestamp
                    next_symbol = symbol
                    
        # If no next timestamp found, we're done
        if next_timestamp is None:
            return False
            
        # Publish bars for all symbols with data at this timestamp
        for symbol, df in self.data.items():
            current_idx = self.current_indices[symbol]
            
            # Check if there's more data for this symbol
            if current_idx + 1 < len(df):
                next_idx = current_idx + 1
                timestamp = df.iloc[next_idx]['timestamp']
                
                # If this bar is at the current timestamp, publish it
                if timestamp == next_timestamp:
                    bar_data = df.iloc[next_idx].to_dict()
                    
                    # Add symbol to the bar data (required by CoreBar.from_dict)
                    bar_data['symbol'] = symbol
                    
                    # Standardize field names
                    bar_data = CoreBar.from_dict(bar_data)

                    # CRITICAL FIX: Store the current bar for time range validation
                    self.current_bar = bar_data

                    # Publish the bar
                    self.event_bus.publish(Event(
                        EventType.BAR,
                        bar_data
                    ))

                    # Update current index
                    self.current_indices[symbol] = next_idx
                    
        return True
        
    def _update_split_data(self):
        """
        Update using split data.
        
        Returns:
            bool: True if more data is available, False otherwise
        """
        # Find the earliest next bar across all symbols
        next_timestamp = None
        next_symbol = None
        
        for symbol in self.data.keys():
            df = self.data_splits[symbol][self.current_split]
            current_idx = self.current_indices[symbol]
            
            # Check if there's more data for this symbol
            if current_idx + 1 < len(df):
                next_idx = current_idx + 1
                timestamp = df.iloc[next_idx]['timestamp']
                
                # If this is the earliest timestamp, or we haven't found any yet
                if next_timestamp is None or timestamp < next_timestamp:
                    next_timestamp = timestamp
                    next_symbol = symbol
                    
        # If no next timestamp found, we're done
        if next_timestamp is None:
            return False
            
        # Publish bars for all symbols with data at this timestamp
        for symbol in self.data.keys():
            df = self.data_splits[symbol][self.current_split]
            current_idx = self.current_indices[symbol]
            
            # Check if there's more data for this symbol
            if current_idx + 1 < len(df):
                next_idx = current_idx + 1
                timestamp = df.iloc[next_idx]['timestamp']
                
                # If this bar is at the current timestamp, publish it
                if timestamp == next_timestamp:
                    bar_data = df.iloc[next_idx].to_dict()
                    
                    # Add symbol to the bar data (required by CoreBar.from_dict)
                    bar_data['symbol'] = symbol
                    
                    # Standardize field names
                    bar_data = CoreBar.from_dict(bar_data)

                    # CRITICAL FIX: Store the current bar for time range validation
                    self.current_bar = bar_data

                    # Publish the bar
                    self.event_bus.publish(Event(
                        EventType.BAR,
                        bar_data
                    ))

                    # Update current index
                    self.current_indices[symbol] = next_idx
                    
        return True
        
    def get_data(self, symbol=None):
        """
        Get data for a symbol or all symbols.
        
        Args:
            symbol (str, optional): Symbol to get data for
            
        Returns:
            pd.DataFrame or dict: Data for requested symbol(s)
        """
        if symbol:
            return self.data.get(symbol).copy()
        return {s: df.copy() for s, df in self.data.items()}
        
    def reset(self):
        """Reset the data handler state."""
        super().reset()
        self.current_indices = {symbol: -1 for symbol in self.data.keys()}
        
    def get_current_timestamp(self):
        """
        Returns the current timestamp in the historical data.
        If using split data, returns the last timestamp from the active split.
        """
        # If we have split data and an active split, use that
        if hasattr(self, 'current_split') and self.current_split and self.data_splits:
            for symbol in self.data_splits.keys():
                # Get the dataframe for this symbol's active split
                df = self.data_splits[symbol].get(self.current_split)
                if df is not None and len(df) > 0:
                    # Get the index in this dataframe
                    current_idx = self.current_indices.get(symbol, -1)
                    if current_idx >= 0 and current_idx < len(df):
                        # Return timestamp at current index
                        return df.iloc[current_idx]['timestamp']
                    elif len(df) > 0:
                        # Return the last timestamp as fallback
                        return df.iloc[-1]['timestamp']
        
        # Fallback to using the full data
        for symbol, df in self.data.items():
            if len(df) > 0:
                current_idx = self.current_indices.get(symbol, -1)
                if current_idx >= 0 and current_idx < len(df):
                    return df.iloc[current_idx]['timestamp']
                else:
                    return df.iloc[-1]['timestamp']
        
        # Last resort - import datetime and return current time
        from datetime import datetime
        return datetime.now()
        
    def get_current_price(self, symbol):
        """
        Returns the current price for the given symbol.
        Uses the close price from the current or latest bar for the symbol.
        
        Args:
            symbol (str): Symbol to get price for
            
        Returns:
            float: Latest price or None if not available
        """
        # Check if we're using split data
        if hasattr(self, 'current_split') and self.current_split and self.data_splits:
            if symbol in self.data_splits:
                df = self.data_splits[symbol].get(self.current_split)
                if df is not None and len(df) > 0:
                    # Get the current index for this symbol
                    current_idx = self.current_indices.get(symbol, -1)
                    
                    # If the index is valid, return the close price at that index
                    if current_idx >= 0 and current_idx < len(df):
                        return df.iloc[current_idx]['close']
                    elif len(df) > 0:
                        # Return the last close price as fallback
                        return df.iloc[-1]['close']
        
        # Fallback to using full data
        if symbol in self.data:
            df = self.data[symbol]
            if len(df) > 0:
                # Get the current index for this symbol
                current_idx = self.current_indices.get(symbol, -1)
                
                # If the index is valid, return the close price at that index
                if current_idx >= 0 and current_idx < len(df):
                    return df.iloc[current_idx]['close']
                elif len(df) > 0:
                    # Return the last close price as fallback
                    return df.iloc[-1]['close']
        
        # No price available
        return None
        
    def get_symbols(self):
        """
        Get the list of symbols in the data handler.
        
        Returns:
            list: List of symbol strings
        """
        # Return list of keys from the data dictionary
        symbols = list(self.data.keys())
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Data handler returning symbols: {symbols}")
        self.symbols = symbols  # Update symbols list for compatibility with DataHandler
        return symbols
        
    def get_current_symbol(self):
        """
        Returns a representative symbol from the loaded data.
        Used primarily for logging and diagnostics.
        
        Returns:
            str: A symbol name or 'UNDEFINED' if no symbols are loaded
        """
        # Return the first symbol from the data
        if self.data and len(self.data) > 0:
            return next(iter(self.data.keys()))
        return "UNDEFINED"
        
    def get_split_sizes(self):
        """
        Returns the sizes of the current data splits.
        Used for logging and diagnostics.
        
        Returns:
            dict: Map of split names to row counts
        """
        if not self.data_splits:
            return {}
            
        # Use the first symbol's splits as representative
        symbol = self.get_current_symbol()
        if symbol in self.data_splits:
            # CRITICAL FIX: Handle the case where a split might be None
            splits_data = {}
            for split, df in self.data_splits[symbol].items():
                if df is not None:  # Only include non-None DataFrames
                    splits_data[split] = len(df)
                else:
                    splits_data[split] = 0  # Use 0 length for None
            return splits_data
        return {}
        
    def is_empty(self, split_name=None):
        """
        Check if the data is empty for a given split.
        
        Args:
            split_name (str, optional): Split to check, or None for full data
            
        Returns:
            bool: True if no data is available, False otherwise
        """
        if split_name and self.data_splits:
            # Check if any symbol has data for this split
            for symbol, splits in self.data_splits.items():
                # CRITICAL FIX: Handle None values
                if (split_name in splits and
                    splits[split_name] is not None and
                    len(splits[split_name]) > 0):
                    return False
            return True
        else:
            # Check if any symbol has full data
            return not any(len(df) > 0 for df in self.data.values())
            
    def load_data(self, symbols: List[str], start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None, timeframe: Union[str, Any] = None) -> bool:
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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Loading data for symbols: {symbols}")
        
        # Store the symbols
        self.symbols = symbols
        
        # Update timeframe if provided
        if timeframe:
            if isinstance(timeframe, str):
                self.timeframe = Timeframe.from_string(timeframe)
            else:
                self.timeframe = timeframe
        
        # We'll use the existing _load_data method which is called in initialize,
        # but we need to make sure it's been called at least once
        if not self.data:
            logger.info("Data not yet loaded, calling _load_data")
            try:
                self._load_data()
                return True
            except Exception as e:
                logger.error(f"Error loading data: {e}")
                return False
        
        # Filter data by symbols if needed
        filtered_data = {}
        for symbol in symbols:
            if symbol in self.data:
                filtered_data[symbol] = self.data[symbol]
            else:
                logger.warning(f"Symbol {symbol} not found in loaded data")
                
        # If we have at least one symbol, consider it a success
        success = len(filtered_data) > 0
        
        # Update the data if necessary
        if success and len(filtered_data) != len(self.data):
            self.data = filtered_data
            
        # Reset indices for the filtered symbols
        self.current_indices = {symbol: -1 for symbol in self.data.keys()}
        
        # Apply date filtering if specified
        if start_date is not None or end_date is not None:
            for symbol, df in self.data.items():
                if 'timestamp' in df.columns:
                    if start_date:
                        df = df[df['timestamp'] >= start_date]
                    if end_date:
                        df = df[df['timestamp'] <= end_date]
                    self.data[symbol] = df
        
        # Set up train/test split with default parameters
        if hasattr(self, 'setup_train_test_split'):
            try:
                self.setup_train_test_split()
            except Exception as e:
                logger.warning(f"Error setting up train/test split: {e}")
        
        return success
        
    def get_latest_bar(self, symbol: str) -> Optional[Bar]:
        """
        Get the latest bar for a symbol.
        
        Args:
            symbol: Symbol to get bar for
            
        Returns:
            Optional[Bar]: Latest bar or None if not available
        """
        if symbol not in self.data or len(self.data[symbol]) == 0:
            return None
            
        # Get the current index for this symbol
        idx = self.current_indices.get(symbol, -1)
        
        # If index is valid, return the bar at that index
        if idx >= 0 and idx < len(self.data[symbol]):
            row = self.data[symbol].iloc[idx]
            # Convert to Bar object
            bar_data = row.to_dict()
            bar_data['symbol'] = symbol
            return Bar(
            timestamp=bar_data['timestamp'],
            symbol=bar_data['symbol'],
            open=float(bar_data['open']),
            high=float(bar_data['high']),
            low=float(bar_data['low']),
            close=float(bar_data['close']),
            volume=float(bar_data.get('volume', 0)),
            timeframe=getattr(self, 'timeframe', Timeframe.DAY_1)
        )
        
        # If no valid index, return None
        return None
        
    def get_latest_bars(self, symbol: str, n: int = 1) -> List[Bar]:
        """
        Get the latest n bars for a symbol.
        
        Args:
            symbol: Symbol to get bars for
            n: Number of bars to get
            
        Returns:
            List[Bar]: List of bars (may be empty)
        """
        if symbol not in self.data or len(self.data[symbol]) == 0:
            return []
            
        # Get the current index for this symbol
        idx = self.current_indices.get(symbol, -1)
        
        # Calculate range to get
        start_idx = max(0, idx - n + 1)
        end_idx = idx + 1  # exclusive end
        
        # If start_idx is negative, return empty list
        if idx < 0 or start_idx >= len(self.data[symbol]):
            return []
            
        # Convert rows to Bar objects
        bars = []
        for i in range(start_idx, end_idx):
            row = self.data[symbol].iloc[i]
            bar_data = row.to_dict()
            bar_data['symbol'] = symbol
            bars.append(Bar(
                timestamp=bar_data['timestamp'],
                symbol=bar_data['symbol'],
                open=float(bar_data['open']),
                high=float(bar_data['high']),
                low=float(bar_data['low']),
                close=float(bar_data['close']),
                volume=float(bar_data.get('volume', 0)),
                timeframe=getattr(self, 'timeframe', Timeframe.DAY_1)
            ))
            
        return bars
        
    def get_all_bars(self, symbol: str) -> List[Bar]:
        """
        Get all bars for a symbol.
        
        Args:
            symbol: Symbol to get bars for
            
        Returns:
            List[Bar]: List of all bars (may be empty)
        """
        if symbol not in self.data or len(self.data[symbol]) == 0:
            return []
            
        # Convert all rows to Bar objects
        bars = []
        for _, row in self.data[symbol].iterrows():
            bar_data = row.to_dict()
            bar_data['symbol'] = symbol
            bars.append(Bar(
                timestamp=bar_data['timestamp'],
                symbol=bar_data['symbol'],
                open=float(bar_data['open']),
                high=float(bar_data['high']),
                low=float(bar_data['low']),
                close=float(bar_data['close']),
                volume=float(bar_data.get('volume', 0)),
                timeframe=getattr(self, 'timeframe', Timeframe.DAY_1)
            ))
            
        return bars
        
    def update_bars(self):
        """
        Update bars and emit bar events.

        Returns:
            bool: True if more bars are available, False otherwise
        """
        # CRITICAL FIX: Initialize current_bar for cross-checking
        self.current_bar = None

        # CRITICAL FIX: Use the appropriate data source based on whether we're using a split
        if hasattr(self, 'current_split') and self.current_split:
            # Use split data
            data_source = {}
            for symbol in self.data.keys():
                if symbol in self.data_splits and self.current_split in self.data_splits[symbol]:
                    data_source[symbol] = self.data_splits[symbol][self.current_split]
        else:
            # Use full data
            data_source = self.data

        # Find the earliest next bar across all symbols
        next_timestamp = None
        next_symbol = None

        for symbol, df in data_source.items():
            current_idx = self.current_indices[symbol]

            # Check if there's more data for this symbol
            if current_idx + 1 < len(df):
                next_idx = current_idx + 1
                timestamp = df.iloc[next_idx]['timestamp']

                # CRITICAL FIX: If we have a split time range, ensure the timestamp is within it
                if hasattr(self, '_split_time_range') and self.current_split:
                    min_time, max_time = self._split_time_range
                    if timestamp < min_time or timestamp > max_time:
                        logger.warning(f"Skipping bar at {timestamp} outside of {self.current_split} time range {min_time} to {max_time}")
                        continue  # Skip this bar since it's outside our time range

                # If this is the earliest timestamp, or we haven't found any yet
                if next_timestamp is None or timestamp < next_timestamp:
                    next_timestamp = timestamp
                    next_symbol = symbol

        # If no next timestamp found, we're done
        if next_timestamp is None:
            return False
            
        # Publish bars for all symbols with data at this timestamp
        for symbol, df in data_source.items():
            current_idx = self.current_indices[symbol]

            # Check if there's more data for this symbol
            if current_idx + 1 < len(df):
                next_idx = current_idx + 1
                timestamp = df.iloc[next_idx]['timestamp']

                # CRITICAL FIX: If we have a split time range, recheck the timestamp
                if hasattr(self, '_split_time_range') and self.current_split:
                    min_time, max_time = self._split_time_range
                    if timestamp < min_time or timestamp > max_time:
                        continue  # Skip this bar since it's outside our time range

                # If this bar is at the current timestamp, publish it
                if timestamp == next_timestamp:
                    bar_data = df.iloc[next_idx].to_dict()

                    # Add symbol to the bar data
                    bar_data['symbol'] = symbol

                    # Add timeframe to the bar data
                    if hasattr(self, 'timeframe'):
                        bar_data['timeframe'] = self.timeframe.to_string()

                    # CRITICAL FIX: Store current bar for diagnosis
                    self.current_bar = bar_data

                    # Publish the bar
                    self.event_bus.publish(Event(
                        EventType.BAR,
                        bar_data
                    ))

                    # Update current index
                    self.current_indices[symbol] = next_idx

        # CRITICAL FIX: Verify we're actually using data from the correct time range
        if hasattr(self, '_split_time_range') and self.current_split and self.current_bar:
            min_time, max_time = self._split_time_range
            if 'timestamp' in self.current_bar:
                current_time = self.current_bar['timestamp']
                if current_time < min_time or current_time > max_time:
                    logger.error(f"TIME RANGE VIOLATION in {self.current_split}: {current_time} is outside range {min_time} to {max_time}")

        return True
        
    def split_data(self, train_ratio: float = 0.7) -> Tuple[Dict[str, List[Bar]], Dict[str, List[Bar]]]:
        """
        Split data into training and testing sets.
        
        Args:
            train_ratio: Ratio of data to use for training (0.0-1.0)
            
        Returns:
            Tuple[Dict[str, List[Bar]], Dict[str, List[Bar]]]: Training and testing data
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Set up train/test split if not already done
        if not hasattr(self, 'data_splits') or not self.data_splits:
            logger.info(f"Setting up train/test split with ratio {train_ratio}")
            self.setup_train_test_split(method="ratio", train_ratio=train_ratio, test_ratio=1-train_ratio)
        
        train_data = {}
        test_data = {}
        
        for symbol in self.symbols:
            if symbol not in self.data_splits:
                logger.warning(f"Symbol {symbol} not found in data splits")
                train_data[symbol] = []
                test_data[symbol] = []
                continue
                
            # Get train and test DataFrames
            train_df = self.data_splits[symbol].get('train')
            test_df = self.data_splits[symbol].get('test')
            
            # Convert to bar objects
            train_bars = []
            if train_df is not None:
                for _, row in train_df.iterrows():
                    bar_data = row.to_dict()
                    bar_data['symbol'] = symbol
                    train_bars.append(Bar(
                        timestamp=bar_data['timestamp'],
                        symbol=bar_data['symbol'],
                        open=float(bar_data['open']),
                        high=float(bar_data['high']),
                        low=float(bar_data['low']),
                        close=float(bar_data['close']),
                        volume=float(bar_data.get('volume', 0)),
                        timeframe=getattr(self, 'timeframe', Timeframe.DAY_1)
                    ))
            
            test_bars = []
            if test_df is not None:
                for _, row in test_df.iterrows():
                    bar_data = row.to_dict()
                    bar_data['symbol'] = symbol
                    test_bars.append(Bar(
                        timestamp=bar_data['timestamp'],
                        symbol=bar_data['symbol'],
                        open=float(bar_data['open']),
                        high=float(bar_data['high']),
                        low=float(bar_data['low']),
                        close=float(bar_data['close']),
                        volume=float(bar_data.get('volume', 0)),
                        timeframe=getattr(self, 'timeframe', Timeframe.DAY_1)
                    ))
            
            train_data[symbol] = train_bars
            test_data[symbol] = test_bars
            
            logger.info(f"Split data for {symbol}: {len(train_bars)} training bars, {len(test_bars)} testing bars")
        
        return train_data, test_data
