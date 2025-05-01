#!/usr/bin/env python3
"""
Test signal flow with a contrived dataset to verify signal grouping.
This script sets up a very simple test with predictable MA crossovers
to validate that the signal group deduplication works correctly.
"""

import os
import sys
import logging
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler(f"test_signal_flow_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("test_signal_flow")

def create_test_data():
    """Create a contrived dataset with exactly 5 crossovers"""
    # Start date for our synthetic data
    start_date = datetime.datetime(2024, 1, 1)
    
    # Create date range with 100 minute bars
    dates = [start_date + datetime.timedelta(minutes=i) for i in range(100)]
    
    # Create contrived price data with exactly 5 crossovers
    # We'll make it oscillate to ensure we get alternating buy/sell signals
    prices = []
    for i in range(100):
        # Base price
        base = 100.0
        
        # Add oscillations that will create 5 clear crossovers
        if i < 20:
            # Uptrend
            prices.append(base + i * 0.1)
        elif i < 30:
            # Sharp downtrend to create first crossover (SELL)
            prices.append(base + 20 * 0.1 - (i - 20) * 0.3)
        elif i < 50:
            # Uptrend to create second crossover (BUY)
            prices.append(base + 20 * 0.1 - 10 * 0.3 + (i - 30) * 0.25)
        elif i < 60:
            # Downtrend for third crossover (SELL)
            prices.append(base + 20 * 0.1 - 10 * 0.3 + 20 * 0.25 - (i - 50) * 0.35)
        elif i < 75:
            # Uptrend for fourth crossover (BUY)
            prices.append(base + 20 * 0.1 - 10 * 0.3 + 20 * 0.25 - 10 * 0.35 + (i - 60) * 0.3)
        else:
            # Final downtrend for fifth crossover (SELL)
            prices.append(base + 20 * 0.1 - 10 * 0.3 + 20 * 0.25 - 10 * 0.35 + 15 * 0.3 - (i - 75) * 0.2)
    
    # Create DataFrame with our synthetic data
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + 0.1 for p in prices],
        'low': [p - 0.1 for p in prices],
        'close': prices,
        'volume': [1000] * len(prices)
    })
    
    # Save the data to CSV
    csv_path = 'test_data/test_ma_crossover.csv'
    os.makedirs('test_data', exist_ok=True)
    df.to_csv(csv_path, index=False)
    
    # Calculate MAs for validation
    fast_ma = df['close'].rolling(window=5).mean()
    slow_ma = df['close'].rolling(window=15).mean()
    
    # Find crossovers
    crossovers = []
    for i in range(1, len(df)):
        if i < 15:  # Skip until we have enough data
            continue
            
        if fast_ma[i-1] <= slow_ma[i-1] and fast_ma[i] > slow_ma[i]:
            crossovers.append(('BUY', i, df['timestamp'][i]))
        elif fast_ma[i-1] >= slow_ma[i-1] and fast_ma[i] < slow_ma[i]:
            crossovers.append(('SELL', i, df['timestamp'][i]))
    
    logger.info(f"Created test data with {len(crossovers)} crossovers:")
    for i, (direction, idx, timestamp) in enumerate(crossovers):
        logger.info(f"Crossover {i+1}: {direction} at {timestamp} (index {idx})")
    
    # Plot the data with crossovers
    plt.figure(figsize=(12, 6))
    plt.plot(df['timestamp'], df['close'], label='Price')
    plt.plot(df['timestamp'], fast_ma, label='Fast MA (5)')
    plt.plot(df['timestamp'], slow_ma, label='Slow MA (15)')
    
    # Mark crossovers
    for direction, idx, _ in crossovers:
        color = 'green' if direction == 'BUY' else 'red'
        marker = '^' if direction == 'BUY' else 'v'
        plt.scatter(df['timestamp'][idx], df['close'][idx], color=color, marker=marker, s=100)
    
    plt.title('Test Data with 5 MA Crossovers')
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.legend()
    plt.savefig('test_ma_crossover_data.png')
    
    logger.info(f"Test data saved to {csv_path}")
    logger.info(f"Test plot saved to test_ma_crossover_data.png")
    
    return csv_path, len(crossovers)

def run_backtest(csv_path):
    """Run backtest with the test data"""
    try:
        # Import the necessary modules
        from src.core.system_bootstrap import Bootstrap
        
        # Set up a config with our test data
        config_content = f"""
        data:
          source: "csv"
          csv_file: "{csv_path}"
          
        strategy:
          name: "ma_crossover"
          parameters:
            fast_window: 5
            slow_window: 15
            
        broker:
          commission: 0.0
          
        symbols:
          - TEST
        """
        
        # Save config to a temporary file
        config_path = 'test_data/test_config.yaml'
        with open(config_path, 'w') as f:
            f.write(config_content)
            
        # Set log level to get detailed output
        logging.getLogger("src.strategy.implementations.ma_crossover").setLevel(logging.INFO)
        logging.getLogger("src.risk.managers.simple").setLevel(logging.INFO)
        
        # Create bootstrap
        bs = Bootstrap(
            config_files=[config_path],
            log_level="INFO"
        )
        
        # Setup container and get backtest
        container, config = bs.setup()
        backtest = container.get('backtest')
        
        # Run backtest
        logger.info("Running backtest with test data...")
        results = backtest.run()
        
        # Check results
        if results and 'trades' in results:
            trades = results['trades']
            logger.info(f"Backtest completed with {len(trades)} trades")
            
            # Log details of each trade
            for i, trade in enumerate(trades):
                logger.info(f"Trade {i+1}: {trade.get('direction')} at {trade.get('timestamp')}")
                
            # Check alternating directions
            directions_alternate = True
            for i in range(1, len(trades)):
                if trades[i].get('direction') == trades[i-1].get('direction'):
                    directions_alternate = False
                    logger.error(f"Directions do not alternate at trades {i} and {i+1}")
                    
            if directions_alternate:
                logger.info("Trade directions correctly alternate between BUY and SELL")
            else:
                logger.error("Trade directions do not properly alternate!")
                
            return len(trades)
        else:
            logger.error("No trades generated in backtest")
            return 0
            
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        return -1

def main():
    """Main function to test signal flow"""
    logger.info("Starting signal flow test with contrived data")
    
    # Create test data
    csv_path, expected_crossovers = create_test_data()
    
    # Run backtest
    actual_trades = run_backtest(csv_path)
    
    # Check results
    logger.info("=" * 50)
    logger.info("TEST RESULTS")
    logger.info("=" * 50)
    logger.info(f"Expected crossovers: {expected_crossovers}")
    logger.info(f"Actual trades: {actual_trades}")
    
    if actual_trades == expected_crossovers:
        logger.info("SUCCESS: Actual trades match expected crossovers")
        logger.info("Signal grouping is working correctly!")
        return 0
    else:
        logger.error(f"FAILURE: Expected {expected_crossovers} trades but got {actual_trades}")
        logger.error("Signal grouping is NOT working correctly!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
