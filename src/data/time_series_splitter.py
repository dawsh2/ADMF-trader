"""
Time series data splitting for train/test validation.

This module provides proper time series data splitting functionality
to support train/test validation in the optimization framework.
"""

import pandas as pd
from datetime import datetime, timedelta

class TimeSeriesSplitter:
    """
    Time series data splitter for train/test validation.
    
    This class provides various methods for splitting time series data
    into training and testing datasets while preserving temporal order.
    """
    
    def __init__(self, method="ratio", train_ratio=0.7, test_ratio=0.3,
                 split_date=None, train_periods=None, test_periods=None):
        """
        Initialize the splitter.
        
        Args:
            method (str): Splitting method ('ratio', 'date', or 'fixed')
            train_ratio (float): Ratio of data for training (for 'ratio' method)
            test_ratio (float): Ratio of data for testing (for 'ratio' method)
            split_date (datetime): Date to split on (for 'date' method)
            train_periods (int): Number of periods for training (for 'fixed' method)
            test_periods (int): Number of periods for testing (for 'fixed' method)
        """
        self.method = method
        self.train_ratio = train_ratio
        self.test_ratio = test_ratio
        self.split_date = split_date
        self.train_periods = train_periods
        self.test_periods = test_periods
        
        # Validate parameters
        self._validate_parameters()
        
    def _validate_parameters(self):
        """Validate the splitter parameters."""
        if self.method not in ["ratio", "date", "fixed"]:
            raise ValueError(f"Invalid split method: {self.method}")
            
        if self.method == "ratio":
            if not 0 < self.train_ratio < 1:
                raise ValueError(f"Train ratio must be between 0 and 1, got {self.train_ratio}")
            if not 0 < self.test_ratio < 1:
                raise ValueError(f"Test ratio must be between 0 and 1, got {self.test_ratio}")
            if self.train_ratio + self.test_ratio > 1:
                raise ValueError(f"Sum of train and test ratios exceeds 1")
                
        elif self.method == "date":
            if not self.split_date:
                raise ValueError("Split date must be specified when using date method")
                
        elif self.method == "fixed":
            if not self.train_periods or self.train_periods <= 0:
                raise ValueError(f"Train periods must be positive, got {self.train_periods}")
            if not self.test_periods or self.test_periods <= 0:
                raise ValueError(f"Test periods must be positive, got {self.test_periods}")
                
    def split(self, data):
        """
        Split the data into training and testing sets.
        
        Args:
            data (pd.DataFrame or dict): Time series data to split
            
        Returns:
            dict: Dictionary with 'train' and 'test' keys
        """
        # Handle different data types
        if isinstance(data, pd.DataFrame):
            return self._split_dataframe(data)
        elif isinstance(data, dict):
            return {k: self._split_dataframe(v) for k, v in data.items()}
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
            
    def _split_dataframe(self, df):
        """
        Split a pandas DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame to split
            
        Returns:
            dict: Dictionary with 'train' and 'test' keys
        """
        # Ensure data is sorted by date/time
        if 'timestamp' in df.columns:
            date_col = 'timestamp'
        elif 'date' in df.columns:
            date_col = 'date'
        else:
            # Try to find a datetime column
            date_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
            if date_cols:
                date_col = date_cols[0]
            else:
                raise ValueError("No datetime column found in data")
                
        # Sort the data by the date column
        df = df.sort_values(by=date_col).reset_index(drop=True)
        
        # Split according to the specified method
        if self.method == "ratio":
            return self._split_by_ratio(df, date_col)
        elif self.method == "date":
            return self._split_by_date(df, date_col)
        elif self.method == "fixed":
            return self._split_by_fixed_periods(df, date_col)
            
    def _split_by_ratio(self, df, date_col):
        """
        Split by ratio, ensuring separate copies of train and test data.

        Args:
            df (pd.DataFrame): DataFrame to split
            date_col (str): Column name with datetime values

        Returns:
            dict: Dictionary with 'train' and 'test' keys
        """
        total_rows = len(df)
        train_size = int(total_rows * self.train_ratio)

        # Split the data with explicit copies to ensure independence
        train_df = df.iloc[:train_size].copy(deep=True)
        test_df = df.iloc[train_size:].copy(deep=True)

        # Force reset index to avoid any shared data between DataFrames
        train_df = train_df.reset_index(drop=True)
        test_df = test_df.reset_index(drop=True)

        # Add split identifier to diagnose any reuse of data
        train_df['_split'] = 'train'
        test_df['_split'] = 'test'

        # Verify uniqueness
        import logging
        logger = logging.getLogger(__name__)

        # Perform extra validation - make sure train and test don't overlap in time
        if len(train_df) > 0 and len(test_df) > 0:
            train_times = set(train_df[date_col])
            test_times = set(test_df[date_col])
            overlap = train_times.intersection(test_times)

            if overlap:
                logger.warning(f"Found {len(overlap)} overlapping timestamps between train and test!")

                # Remove overlapping timestamps from test set
                logger.info(f"Removing {len(overlap)} overlapping timestamps from test set")
                test_df = test_df[~test_df[date_col].isin(overlap)]
                logger.info(f"After removing overlap: test={len(test_df)} rows")

        # Add dataset info for debugging
        logger.info(f"Created train dataset: {len(train_df)} rows")
        if len(train_df) > 0:
            logger.info(f"  Train period: {train_df[date_col].min()} to {train_df[date_col].max()}")

        logger.info(f"Created test dataset: {len(test_df)} rows")
        if len(test_df) > 0:
            logger.info(f"  Test period: {test_df[date_col].min()} to {test_df[date_col].max()}")

        return {'train': train_df, 'test': test_df}
        
    def _split_by_date(self, df, date_col):
        """
        Split by date, ensuring separate copies of train and test data.

        Args:
            df (pd.DataFrame): DataFrame to split
            date_col (str): Column name with datetime values

        Returns:
            dict: Dictionary with 'train' and 'test' keys
        """
        # Split the data with explicit deep copies
        train_df = df[df[date_col] < self.split_date].copy(deep=True)
        test_df = df[df[date_col] >= self.split_date].copy(deep=True)

        # Force reset index to avoid any shared data between DataFrames
        train_df = train_df.reset_index(drop=True)
        test_df = test_df.reset_index(drop=True)

        # Add split identifier to diagnose any reuse of data
        train_df['_split'] = 'train'
        test_df['_split'] = 'test'

        # Verify uniqueness
        import logging
        logger = logging.getLogger(__name__)

        # Perform extra validation - make sure train and test don't overlap in time
        if len(train_df) > 0 and len(test_df) > 0:
            train_times = set(train_df[date_col])
            test_times = set(test_df[date_col])
            overlap = train_times.intersection(test_times)

            if overlap:
                logger.warning(f"Found {len(overlap)} overlapping timestamps in date split!")

                # Remove overlapping timestamps from test set
                logger.info(f"Removing {len(overlap)} overlapping timestamps from test set")
                test_df = test_df[~test_df[date_col].isin(overlap)]
                logger.info(f"After removing overlap: test={len(test_df)} rows")

        # Add dataset info for debugging
        logger.info(f"Created train dataset: {len(train_df)} rows")
        if len(train_df) > 0:
            logger.info(f"  Train period: {train_df[date_col].min()} to {train_df[date_col].max()}")

        logger.info(f"Created test dataset: {len(test_df)} rows")
        if len(test_df) > 0:
            logger.info(f"  Test period: {test_df[date_col].min()} to {test_df[date_col].max()}")

        return {'train': train_df, 'test': test_df}
        
    def _split_by_fixed_periods(self, df, date_col):
        """
        Split by fixed number of periods, ensuring separate copies of train and test data.

        Args:
            df (pd.DataFrame): DataFrame to split
            date_col (str): Column name with datetime values

        Returns:
            dict: Dictionary with 'train' and 'test' keys
        """
        total_rows = len(df)

        # Ensure we have enough data
        if total_rows < self.train_periods + self.test_periods:
            raise ValueError(f"Not enough data: have {total_rows} rows, "
                           f"need {self.train_periods + self.test_periods}")

        # Calculate indices
        train_end = total_rows - self.test_periods

        # Split the data with explicit deep copies
        train_df = df.iloc[max(0, train_end - self.train_periods):train_end].copy(deep=True)
        test_df = df.iloc[train_end:train_end + self.test_periods].copy(deep=True)

        # Force reset index to avoid any shared data between DataFrames
        train_df = train_df.reset_index(drop=True)
        test_df = test_df.reset_index(drop=True)

        # Add split identifier to diagnose any reuse of data
        train_df['_split'] = 'train'
        test_df['_split'] = 'test'

        # Verify uniqueness
        import logging
        logger = logging.getLogger(__name__)

        # Perform extra validation - make sure train and test don't overlap in time
        if len(train_df) > 0 and len(test_df) > 0:
            train_times = set(train_df[date_col])
            test_times = set(test_df[date_col])
            overlap = train_times.intersection(test_times)

            if overlap:
                logger.warning(f"Found {len(overlap)} overlapping timestamps in period split!")

                # Remove overlapping timestamps from test set
                logger.info(f"Removing {len(overlap)} overlapping timestamps from test set")
                test_df = test_df[~test_df[date_col].isin(overlap)]
                logger.info(f"After removing overlap: test={len(test_df)} rows")

        # Add dataset info for debugging
        logger.info(f"Created train dataset: {len(train_df)} rows")
        if len(train_df) > 0:
            logger.info(f"  Train period: {train_df[date_col].min()} to {train_df[date_col].max()}")

        logger.info(f"Created test dataset: {len(test_df)} rows")
        if len(test_df) > 0:
            logger.info(f"  Test period: {test_df[date_col].min()} to {test_df[date_col].max()}")

        return {'train': train_df, 'test': test_df}
