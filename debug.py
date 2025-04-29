#!/usr/bin/env python
"""
Debug script for testing data loading directly.
"""
import logging
import pandas as pd
from src.data.sources.csv_handler import CSVDataSource

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_data_loading():
    """Test data loading directly with CSVDataSource."""
    # Create data source directly
    data_dir = "./data"
    data_source = CSVDataSource(data_dir)
    
    # Try explicitly loading the file with the correct timeframe
    symbol = "SPY"
    timeframe = "1min"
    
    # Debug the filename construction
    filename = data_source._get_filename(symbol, timeframe)
    logger.info(f"Trying to load file: {filename}")
    
    # Try to load data
    df = data_source.get_data(symbol, timeframe=timeframe)
    
    if df.empty:
        logger.error(f"Failed to load data for {symbol} with timeframe {timeframe}")
    else:
        logger.info(f"Successfully loaded {len(df)} rows for {symbol}")
        logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
        logger.info(f"Columns: {df.columns.tolist()}")
        logger.info(f"First few rows:\n{df.head()}")
    
    # Try direct file loading
    try:
        # Construct filename directly
        direct_file = f"{data_dir}/SPY_1min.csv"
        df_direct = pd.read_csv(direct_file)
        logger.info(f"Direct file load successful: {len(df_direct)} rows")
    except Exception as e:
        logger.error(f"Direct file load failed: {str(e)}")

if __name__ == "__main__":
    test_data_loading()
