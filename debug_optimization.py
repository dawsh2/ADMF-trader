import os
import sys
import logging
import yaml
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('debug_optimization')

def load_config(config_path):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def load_test_data(config):
    """Load test data based on configuration"""
    data = {}
    
    for source in config['data']['sources']:
        symbol = source['symbol']
        file_path = source['file']
        date_column = source['date_column']
        date_format = source.get('date_format', None)
        
        try:
            # Ensure the data file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Data file not found: {file_path}")
            
            # Load data from CSV
            df = pd.read_csv(file_path)
            
            # Convert date column to datetime
            if date_format:
                df[date_column] = pd.to_datetime(df[date_column], format=date_format)
            else:
                df[date_column] = pd.to_datetime(df[date_column])
            
            # Set the date column as index
            df.set_index(date_column, inplace=True)
            
            data[symbol] = df
            logger.info(f"Loaded data for {symbol}: {len(df)} rows")
            
            # Print first few rows for verification
            logger.info(f"First few rows of {symbol} data:\n{df.head()}")
            
        except Exception as e:
            logger.error(f"Error loading data for {symbol}: {e}")
            return None
    
    return data

def test_ma_crossover_signals(data, config):
    """Test MA Crossover signal generation"""
    signals = {}
    
    for symbol, df in data.items():
        # Extract strategy parameters
        fast_window = config['strategy']['parameters']['fast_window']
        slow_window = config['strategy']['parameters']['slow_window']
        price_column = config['data']['sources'][0]['price_column']
        
        try:
            # Calculate moving averages
            df[f'MA_Fast'] = df[price_column].rolling(window=fast_window).mean()
            df[f'MA_Slow'] = df[price_column].rolling(window=slow_window).mean()
            
            # Generate signals: 1 when fast MA crosses above slow MA, -1 when below
            df['Signal'] = 0
            df.loc[df[f'MA_Fast'] > df[f'MA_Slow'], 'Signal'] = 1
            df.loc[df[f'MA_Fast'] < df[f'MA_Slow'], 'Signal'] = -1
            
            # Find crossovers (signal changes)
            df['PrevSignal'] = df['Signal'].shift(1)
            df['Crossover'] = 0
            df.loc[(df['Signal'] == 1) & (df['PrevSignal'] <= 0), 'Crossover'] = 1  # Buy signal
            df.loc[(df['Signal'] == -1) & (df['PrevSignal'] >= 0), 'Crossover'] = -1  # Sell signal
            
            # Store signals
            signals[symbol] = df[df['Crossover'] != 0].copy()
            
            # Print signals
            if len(signals[symbol]) > 0:
                logger.info(f"Generated {len(signals[symbol])} signals for {symbol}")
                logger.info(f"Signals for {symbol}:\n{signals[symbol]}")
            else:
                logger.warning(f"No signals generated for {symbol}!")
            
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
    
    return signals

def main():
    """Main debug function"""
    logger.info("Starting debug optimization")
    
    # Load configuration
    config_path = "config/ma_crossover_fixed_symbols.yaml"
    config = load_config(config_path)
    if not config:
        logger.error("Failed to load configuration")
        return
    
    # Load test data
    data = load_test_data(config)
    if not data:
        logger.error("Failed to load test data")
        return
    
    # Test signal generation
    signals = test_ma_crossover_signals(data, config)
    
    # Summary
    total_signals = sum(len(df) for df in signals.values())
    logger.info(f"Debug complete. Generated {total_signals} signals across {len(signals)} symbols.")
    
    if total_signals == 0:
        logger.warning("No signals were generated! Check the strategy parameters and data.")
    else:
        logger.info("Signals were successfully generated. The strategy should work.")

if __name__ == "__main__":
    main()