"""
CSV data source implementation.
"""
import os
import pandas as pd
import datetime
import logging
from typing import Dict, List, Optional, Union, Any

from ..data_source_base import DataSourceBase

logger = logging.getLogger(__name__)

class CSVDataSource(DataSourceBase):
    """Data source for CSV files."""
    
    def __init__(self, data_dir: str, filename_pattern='{symbol}_{timeframe}.csv', 
                 date_column='timestamp', date_format='%Y-%m-%d', 
                 column_map=None):
        """
        Initialize the CSV data source.
        
        Args:
            data_dir: Directory containing CSV files
            filename_pattern: Pattern for filenames
            date_column: Column containing dates
            date_format: Format of dates in CSV
            column_map: Map of CSV columns to standard column names
        """
        self.data_dir = data_dir
        self.filename_pattern = filename_pattern
        self.date_column = date_column
        self.date_format = date_format
        self.column_map = column_map or {
            'open': ['open', 'Open'],
            'high': ['high', 'High'],
            'low': ['low', 'Low'],
            'close': ['close', 'Close'],
            'volume': ['volume', 'Volume', 'vol', 'Vol']
        }

    # Improved date handling in src/data/sources/csv_handler.py

    def get_data(self, symbol: str, start_date=None, end_date=None, timeframe='1m') -> pd.DataFrame:
        """
        Get data for a symbol within a date range.

        Args:
            symbol: Symbol to get data for
            start_date: Start date (datetime or string)
            end_date: End date (datetime or string)
            timeframe: Data timeframe (e.g., '1d', '1h', '5m')

        Returns:
            DataFrame with OHLCV data
        """
        filename = self._get_filename(symbol, timeframe)
        logger.info(f"CSVDataSource: Loading file {filename}")

        if not os.path.exists(filename):
            logger.warning(f"File not found: {filename}")
            return pd.DataFrame()

        try:
            # Convert string dates to datetime if needed
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            if isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)

            # Read CSV
            df = pd.read_csv(filename)
            logger.info(f"CSVDataSource: Loaded {len(df)} rows")

            # Determine date column - check if configured column exists
            date_col = self.date_column
            if date_col not in df.columns:
                # Try common alternatives
                alternatives = ['date', 'timestamp', 'time', 'datetime']
                for alt in alternatives:
                    if alt in df.columns:
                        date_col = alt
                        logger.info(f"Using '{date_col}' column instead of configured '{self.date_column}'")
                        break
                else:
                    # If index is numeric, assume it's the date index
                    logger.warning(f"Date column '{self.date_column}' not found and no alternatives available")
                    # Try to create a date index from the first column
                    if df.shape[0] > 0:
                        df[self.date_column] = pd.date_range(
                            start=datetime.datetime.now() - datetime.timedelta(days=len(df)), 
                            periods=len(df), 
                            freq='D'
                        )
                        date_col = self.date_column
                        logger.info(f"Created synthetic date column '{date_col}'")

            # Convert date column to datetime with robust error handling
            if date_col in df.columns:
                # Log a sample of original timestamps
                if not df.empty:
                    logger.info(f"CSVDataSource: Original timestamp sample: {df[date_col].iloc[0]}")

                # Try multiple datetime parsing approaches
                try:
                    df[date_col] = pd.to_datetime(df[date_col])
                except Exception as e:
                    logger.warning(f"Standard datetime parsing failed: {e}, trying alternative formats")
                    # Try with different format inference
                    try:
                        df[date_col] = pd.to_datetime(df[date_col], infer_datetime_format=True, errors='coerce')
                    except Exception as e2:
                        logger.warning(f"Alternative datetime parsing failed: {e2}")

                # Check if conversion was successful
                if pd.api.types.is_datetime64_any_dtype(df[date_col]):
                    # Log a sample of parsed timestamps
                    if not df.empty:
                        logger.info(f"CSVDataSource: Parsed timestamp sample: {df[date_col].iloc[0]}")

                    # Remove timezone info to ensure consistency
                    if hasattr(df[date_col].dt, 'tz') and df[date_col].dt.tz is not None:
                        df[date_col] = df[date_col].dt.tz_localize(None)
                        logger.info(f"CSVDataSource: Removed timezone info from timestamps")

                    # Make sure filter dates are also timezone-naive
                    if start_date is not None and hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
                        start_date = start_date.replace(tzinfo=None)
                    if end_date is not None and hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
                        end_date = end_date.replace(tzinfo=None)

                    # Filter by date range
                    if start_date is not None:
                        df = df[df[date_col] >= start_date]
                        logger.info(f"CSVDataSource: Filtered for dates >= {start_date}")

                    if end_date is not None:
                        df = df[df[date_col] <= end_date]
                        logger.info(f"CSVDataSource: Filtered for dates <= {end_date}")

                    # Set date as index
                    df.set_index(date_col, inplace=True)
                    logger.info(f"CSVDataSource: Set {date_col} as index")
                else:
                    logger.error(f"Failed to convert {date_col} to datetime, date filtering will not work")

            # Map columns to standard names
            column_mapping = self._map_columns(df.columns)
            df = df.rename(columns=column_mapping)

            # Log info about the processed DataFrame
            if not df.empty:
                logger.info(f"CSVDataSource: Date range in data: {df.index.min()} to {df.index.max()}")
                logger.info(f"CSVDataSource: Columns after mapping: {list(df.columns)}")

            return df

        except Exception as e:
            logger.error(f"Error reading CSV file {filename}: {e}", exc_info=True)
            return pd.DataFrame()        

 

    def is_available(self, symbol: str, start_date=None, end_date=None, 
                   timeframe='1m') -> bool:
        """
        Check if data is available for the specified parameters.
        
        Args:
            symbol: Symbol to check
            start_date: Start date (datetime or string)
            end_date: End date (datetime or string)
            timeframe: Data timeframe (e.g., '1d', '1h', '5m')
            
        Returns:
            True if data is available, False otherwise
        """
        filename = self._get_filename(symbol, timeframe)
        return os.path.exists(filename)
    
    def _get_filename(self, symbol: str, timeframe: str) -> str:
        """
        Get the filename for a symbol and timeframe.
        
        Args:
            symbol: Symbol
            timeframe: Timeframe
            
        Returns:
            Full path to the file
        """
        # Normalize timeframe format (1m, 1min, 1M all become 1min)
        normalized_timeframe = self._normalize_timeframe(timeframe)
        
        # Try different format variations if needed
        filename = self.filename_pattern.format(symbol=symbol, timeframe=normalized_timeframe)
        full_path = os.path.join(self.data_dir, filename)
        
        # If the file doesn't exist, try alternatives
        if not os.path.exists(full_path):
            # Try common variations
            alternatives = [
                # Check with original timeframe
                self.filename_pattern.format(symbol=symbol, timeframe=timeframe),
                # Check with common variations
                f"{symbol}_{normalized_timeframe}.csv",
                f"{symbol}.csv"
            ]
            
            for alt_filename in alternatives:
                alt_path = os.path.join(self.data_dir, alt_filename)
                if os.path.exists(alt_path):
                    logger.info(f"Using alternative filename: {alt_path} instead of {full_path}")
                    return alt_path
        
        return full_path
    
    def _normalize_timeframe(self, timeframe: str) -> str:
        """
        Normalize timeframe format for consistency.
        
        Args:
            timeframe: Timeframe string like '1m', '1min', '1d', etc.
            
        Returns:
            Normalized timeframe string
        """
        # Strip any whitespace
        timeframe = timeframe.strip()
        
        # Common mappings
        mappings = {
            # Minutes
            '1m': '1min', 'm1': '1min', '1': '1min', '1min': '1min',
            # Days
            '1d': '1d', 'd1': '1d', 'day': '1d', 'daily': '1d',
            # Add more as needed
        }
        
        # Check direct mapping
        if timeframe.lower() in mappings:
            return mappings[timeframe.lower()]
        
        # Try to parse if not in mappings
        if timeframe.endswith('m') and timeframe[:-1].isdigit():
            return f"{timeframe[:-1]}min"
        elif timeframe.endswith('min') and timeframe[:-3].isdigit():
            return timeframe.lower()
        elif timeframe.endswith('d') and timeframe[:-1].isdigit():
            return timeframe.lower()
        
        # Default: return as is
        logger.debug(f"No normalization rule for timeframe: {timeframe}, using as is")
        return timeframe

    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """
        Map CSV columns to standard names.

        Args:
            columns: List of column names from CSV

        Returns:
            Dictionary mapping from CSV column names to standard names
        """
        result = {}

        for std_name, possible_names in self.column_map.items():
            for col in columns:
                # Compare case-insensitively
                if col.lower() in [name.lower() for name in possible_names]:
                    result[col] = std_name
                    break

        logger.debug(f"Column mapping result: {result}")
        return result
