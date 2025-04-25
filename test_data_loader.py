# test_data_loader.py
import logging
import os
import pandas as pd
from src.data.sources.csv_handler import CSVDataSource

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_csv_data_source():
    # Create a test CSV file
    data_dir = "test_data"
    os.makedirs(data_dir, exist_ok=True)
    
    # Create sample data
    dates = pd.date_range(start='2023-01-01', periods=10)
    data = {
        'open': [100 + i for i in range(10)],
        'high': [105 + i for i in range(10)],
        'low': [95 + i for i in range(10)],
        'close': [101 + i for i in range(10)],
        'volume': [1000000 for _ in range(10)]
    }
    df = pd.DataFrame(data, index=dates)
    
    # Save to CSV
    filename = os.path.join(data_dir, "AAPL_1d.csv")
    df.to_csv(filename)
    logger.info(f"Created test file: {filename}")
    
    # Create CSV data source
    data_source = CSVDataSource(data_dir)
    
    # Load data
    loaded_df = data_source.get_data('AAPL', timeframe='1d')
    logger.info(f"Loaded {len(loaded_df)} rows")
    
    # Verify data
    success = len(loaded_df) == 10
    logger.info(f"Test {'passed' if success else 'failed'}")
    logger.info(f"Sample data:\n{loaded_df.head()}")
    
    return success

if __name__ == "__main__":
    test_csv_data_source()
