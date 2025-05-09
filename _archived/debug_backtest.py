#!/usr/bin/env python
"""
Debug script to check if data is being loaded correctly and signals are being generated.
"""
import os
import sys
import yaml
import logging
import pandas as pd
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('backtest_debug')

def debug_backtest():
    """Debug the backtest process to see where it's failing."""
    # Check the HEAD_1min.csv file
    data_file = './data/HEAD_1min.csv'
    if not os.path.exists(data_file):
        logger.error(f"Data file not found: {data_file}")
        return False
    
    # Check data file size and content
    file_size = os.path.getsize(data_file)
    logger.info(f"Data file size: {file_size} bytes")
    
    try:
        # Load data to check its content
        df = pd.read_csv(data_file)
        logger.info(f"Data file rows: {len(df)}")
        logger.info(f"Data columns: {', '.join(df.columns)}")
        
        # Check date range
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            min_date = df['timestamp'].min()
            max_date = df['timestamp'].max()
            logger.info(f"Data date range: {min_date} to {max_date}")
        
        # Print a few sample rows
        logger.info("\nSample data:")
        print(df.head(5).to_string())
        
    except Exception as e:
        logger.error(f"Error analyzing data file: {str(e)}")
        return False
    
    # Load config
    config_file = 'config/optimization_test.yaml'
    if not os.path.exists(config_file):
        logger.error(f"Config file not found: {config_file}")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check backtest config
        backtest_config = config.get('backtest', {})
        logger.info("\nBacktest configuration:")
        logger.info(f"Symbols: {backtest_config.get('symbols', [])}")
        logger.info(f"Timeframe: {backtest_config.get('timeframe', '')}")
        logger.info(f"Start date: {backtest_config.get('start_date', '')}")
        logger.info(f"End date: {backtest_config.get('end_date', '')}")
        
        # Check if the date range matches the data
        if 'timestamp' in df.columns:
            config_start = pd.to_datetime(backtest_config.get('start_date', '2000-01-01'))
            config_end = pd.to_datetime(backtest_config.get('end_date', '2100-01-01'))
            
            if min_date > config_end or max_date < config_start:
                logger.error("WARNING: Config date range does not overlap with data date range!")
            else:
                # Calculate overlap
                overlap_start = max(min_date, config_start)
                overlap_end = min(max_date, config_end)
                overlap_days = (overlap_end - overlap_start).days
                logger.info(f"Date range overlap: {overlap_days} days ({overlap_start} to {overlap_end})")
        
    except Exception as e:
        logger.error(f"Error analyzing config: {str(e)}")
        return False
    
    # Run a quick test backtest with debug logging
    logger.info("\nRunning test backtest...")
    
    try:
        from src.core.system_bootstrap import Bootstrap
        
        # Set up a more verbose config for debugging
        debug_config = config.copy()
        debug_config['strategies']['simple_ma_crossover'].update({
            'fast_window': 2,
            'slow_window': 5,
            'price_key': 'close'
        })
        
        # Initialize bootstrap with debug logging
        bootstrap = Bootstrap(log_level="DEBUG")
        bootstrap.config = debug_config
        
        # Set up the system
        container, _ = bootstrap.setup()
        
        # Get key components
        data_handler = container.get('data_handler')
        strategy = container.get('strategy')
        event_bus = container.get('event_bus')
        
        # Check data loading
        logger.info("\nChecking data loading...")
        if hasattr(data_handler, 'get_symbols'):
            symbols = data_handler.get_symbols()
            logger.info(f"Available symbols: {symbols}")
            
            # Load a small batch of data
            if hasattr(data_handler, 'get_latest_bars'):
                for symbol in symbols:
                    bars = data_handler.get_latest_bars(symbol, 10)
                    if bars:
                        logger.info(f"Loaded {len(bars)} bars for {symbol}")
                        for i, bar in enumerate(bars[:3]):  # Show first 3 bars
                            logger.info(f"  Bar {i}: timestamp={bar.get_timestamp()}, open={bar.get_open()}, close={bar.get_close()}")
                    else:
                        logger.warning(f"No bars loaded for {symbol}")
        
        # Check strategy
        logger.info("\nChecking strategy configuration...")
        if hasattr(strategy, 'fast_window'):
            logger.info(f"Fast window: {strategy.fast_window}")
            logger.info(f"Slow window: {strategy.slow_window}")
            logger.info(f"Price key: {strategy.price_key}")
            logger.info(f"Symbols: {strategy.symbols}")
        
        # Run the backtest
        logger.info("\nRunning full backtest...")
        backtest = container.get('backtest')
        results = backtest.run()
        
        # Check results
        if results:
            trades = results.get('trades', [])
            metrics = results.get('metrics', {})
            logger.info(f"\nTrades generated: {len(trades)}")
            
            if trades:
                logger.info("\nSample trades:")
                for i, trade in enumerate(trades[:5]):  # Show first 5 trades
                    logger.info(f"  Trade {i}: {trade}")
            else:
                logger.warning("No trades were generated!")
                
                # Check signal events
                logger.info("\nChecking if any signal events were generated...")
                if hasattr(event_bus, 'event_counts'):
                    logger.info(f"Event counts: {event_bus.event_counts}")
                
                # Print possible reasons why no trades were generated
                logger.info("\nPossible reasons for no trades:")
                logger.info("1. No crossover signals detected in the data")
                logger.info("2. Insufficient price data movement for the given window sizes")
                logger.info("3. Date range in config doesn't match data or has insufficient data")
                logger.info("4. Risk management is blocking all trades")
                logger.info("5. Order manager is not converting signals to orders")
        else:
            logger.error("Backtest did not produce any results")
        
    except Exception as e:
        logger.error(f"Error during backtest: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    logger.info("\nDebug complete.")
    return True

if __name__ == "__main__":
    success = debug_backtest()
    sys.exit(0 if success else 1)