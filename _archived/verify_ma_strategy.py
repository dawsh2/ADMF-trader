#!/usr/bin/env python3
"""
Independent MA Crossover Strategy Validation

This script implements the same MA crossover strategy as in the main system,
but as a standalone script without using the event bus infrastructure.
It loads the same data (MINI_1min.csv) and applies the same parameters to verify
that signal generation patterns match the main backtest.
"""

import pandas as pd
import numpy as np
import logging
import datetime
import os
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ma_strategy_verification.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ma_strategy_verification')

class MAStrategyVerification:
    """
    Standalone implementation of the MA Crossover strategy for verification purposes.
    Uses the same logic and parameters as the main system implementation.
    """
    
    def __init__(self, fast_window=5, slow_window=15, price_key='Close'):
        """
        Initialize the MA strategy verifier with the same parameters.
        
        Args:
            fast_window: Fast MA period (default: 5)
            slow_window: Slow MA period (default: 15)
            price_key: Price column to use (default: 'Close')
        """
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.price_key = price_key
        self.signal_count = 0
        self.signal_directions = {}
        self.signal_groups = {}
        self.trades = []
        self.signals = []
    
    def load_data(self, file_path):
        """
        Load price data from CSV file.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            DataFrame: Loaded price data
        """
        logger.info(f"Loading data from {file_path}")
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        # Load data from CSV
        df = pd.read_csv(file_path)
        
        # Ensure timestamp is in datetime format
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        logger.info(f"Loaded {len(df)} data points from {file_path}")
        logger.info(f"Data columns: {df.columns.tolist()}")
        logger.info(f"First few rows:\n{df.head()}")
        
        return df
    
    def calculate_signals(self, df):
        """
        Calculate trading signals using the same logic as the main strategy.
        
        Args:
            df: DataFrame with price data
            
        Returns:
            DataFrame: DataFrame with added signal columns
        """
        logger.info(f"Calculating signals using fast_window={self.fast_window}, slow_window={self.slow_window}")
        
        # Calculate moving averages
        df['fast_ma'] = df[self.price_key].rolling(window=self.fast_window).mean()
        df['slow_ma'] = df[self.price_key].rolling(window=self.slow_window).mean()
        
        # Calculate previous moving averages for crossover detection
        df['fast_ma_prev'] = df['fast_ma'].shift(1)
        df['slow_ma_prev'] = df['slow_ma'].shift(1)
        
        # Calculate crossover signals using the same logic as in the strategy
        # Initialize signal column
        df['signal'] = 0
        
        # Find buy signals (fast MA crosses above slow MA)
        buy_mask = (df['fast_ma_prev'] <= df['slow_ma_prev']) & (df['fast_ma'] > df['slow_ma'])
        df.loc[buy_mask, 'signal'] = 1
        
        # Find sell signals (fast MA crosses below slow MA)
        sell_mask = (df['fast_ma_prev'] >= df['slow_ma_prev']) & (df['fast_ma'] < df['slow_ma'])
        df.loc[sell_mask, 'signal'] = -1
        
        # Create a column with detailed signal info
        df['signal_info'] = np.nan
        
        # Add details for buy signals
        for idx in df[buy_mask].index:
            fast = df.loc[idx, 'fast_ma']
            slow = df.loc[idx, 'slow_ma']
            crossover_pct = (fast - slow) / slow
            df.loc[idx, 'signal_info'] = f"BUY: fast MA ({fast:.2f}) crossed above slow MA ({slow:.2f}), crossover: {crossover_pct:.4%}"
            
        # Add details for sell signals
        for idx in df[sell_mask].index:
            fast = df.loc[idx, 'fast_ma']
            slow = df.loc[idx, 'slow_ma']
            crossover_pct = (slow - fast) / slow
            df.loc[idx, 'signal_info'] = f"SELL: fast MA ({fast:.2f}) crossed below slow MA ({slow:.2f}), crossover: {crossover_pct:.4%}"
        
        # Log signal count
        buy_signals = df[df['signal'] == 1]
        sell_signals = df[df['signal'] == -1]
        logger.info(f"Found {len(buy_signals)} buy signals and {len(sell_signals)} sell signals")
        
        return df
    
    def process_signals(self, df):
        """
        Process signals with the same grouping logic as the main strategy.
        
        Args:
            df: DataFrame with signals
            
        Returns:
            DataFrame: DataFrame with added direction change column
        """
        logger.info("Processing signals with direction change tracking")
        
        # Add columns for direction tracking
        df['current_direction'] = 0
        df['direction_change'] = False
        df['rule_id'] = None
        df['signal_group'] = None
        
        # Initialize state
        current_direction = 0
        current_group = 0
        symbol = "MINI"  # Same as in main system
        
        # Process each row that has a non-zero signal
        for idx in df[df['signal'] != 0].index:
            signal_value = df.loc[idx, 'signal']
            
            # Skip if same direction (exactly like main strategy)
            if signal_value == current_direction:
                continue
                
            # Direction has changed - create a new group
            current_group += 1
            df.loc[idx, 'direction_change'] = True
            df.loc[idx, 'current_direction'] = current_direction
            df.loc[idx, 'signal_group'] = current_group
            
            # Create group-based rule ID - match format in main strategy
            direction_name = "BUY" if signal_value == 1 else "SELL"
            rule_id = f"ma_crossover_{symbol}_{direction_name}_group_{current_group}"
            df.loc[idx, 'rule_id'] = rule_id
            
            # Record signal details
            signal_info = {
                'timestamp': idx,
                'symbol': symbol,
                'signal_value': signal_value,
                'price': df.loc[idx, self.price_key],
                'rule_id': rule_id,
                'group_id': current_group,
                'prev_direction': current_direction,
                'fast_ma': df.loc[idx, 'fast_ma'],
                'slow_ma': df.loc[idx, 'slow_ma']
            }
            self.signals.append(signal_info)
            
            # Log the signal
            logger.info(f"NEW SIGNAL GROUP: {symbol} direction changed to {direction_name}, "
                       f"group={current_group}, rule_id={rule_id}")
            
            # Generate simulated trade
            # Every sell signal generates a corresponding trade
            trade = {
                'timestamp': idx,
                'symbol': symbol,
                'direction': direction_name,
                'price': df.loc[idx, self.price_key],
                'quantity': 19.0,  # Matches quantity seen in main system
                'rule_id': rule_id
            }
            self.trades.append(trade)
            
            # Update current direction for next iteration
            current_direction = signal_value
            
        # Count direction changes
        direction_changes = df[df['direction_change'] == True]
        logger.info(f"Found {len(direction_changes)} direction changes (signal groups)")
        
        # Log all signal groups
        for group_id, group_df in df[df['signal_group'].notna()].groupby('signal_group'):
            first_row = group_df.iloc[0]
            direction = "BUY" if first_row['signal'] == 1 else "SELL"
            price = first_row[self.price_key]
            timestamp = first_row.name
            rule_id = first_row['rule_id']
            logger.info(f"Signal group {int(group_id)}: {direction} at {price:.2f} on {timestamp}, rule_id={rule_id}")
        
        return df
    
    def simulate_trades(self, df):
        """
        Simulate trades based on signals and generate summary.
        
        Args:
            df: DataFrame with processed signals
        """
        # Convert trades to DataFrame
        trades_df = pd.DataFrame(self.trades)
        
        if not trades_df.empty:
            # Sort by timestamp
            trades_df.sort_values('timestamp', inplace=True)
            
            # Add trade details for comparison
            trades_df['fill_price'] = trades_df['price']
            trades_df['commission'] = trades_df['price'] * trades_df['quantity'] * 0.001  # 0.1% commission
            
            # Simulate PnL for BUY trades (closing previous position)
            pnl = []
            prev_price = None
            prev_quantity = None
            
            for idx, row in trades_df.iterrows():
                if row['direction'] == 'SELL':
                    # Opening position
                    pnl.append(0.0)
                    prev_price = row['price']
                    prev_quantity = row['quantity']
                else:
                    # Closing position (BUY after SELL)
                    if prev_price is not None:
                        # Calculate PnL: (sell_price - buy_price) * quantity - commissions
                        trade_pnl = (prev_price - row['price']) * prev_quantity - row['commission']
                        pnl.append(trade_pnl)
                    else:
                        pnl.append(0.0)
            
            trades_df['pnl'] = pnl
            
            # Calculate win rate
            winning_trades = trades_df[trades_df['pnl'] > 0]
            win_rate = len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0
            
            # Calculate total PnL
            total_pnl = trades_df['pnl'].sum()
            
            logger.info(f"Simulated {len(trades_df)} trades")
            logger.info(f"Win rate: {win_rate:.2f}%")
            logger.info(f"Total PnL: ${total_pnl:.2f}")
            
            # Save trades to CSV for comparison
            output_file = 'ma_strategy_verification_trades.csv'
            trades_df.to_csv(output_file, index=False)
            logger.info(f"Trades saved to {output_file}")
            
            # Log each trade
            for idx, row in trades_df.iterrows():
                logger.info(f"Trade: {row['direction']} {row['quantity']} {row['symbol']} @ {row['price']:.2f}, "
                           f"rule_id={row['rule_id']}, PnL=${row['pnl']:.2f}")
            
            return trades_df
        else:
            logger.warning("No trades generated")
            return None
    
    def save_signals(self, df):
        """
        Save processed signals to CSV.
        
        Args:
            df: DataFrame with processed signals
        """
        # Create signals dataframe with the same format as main system
        signals_df = pd.DataFrame(self.signals)
        
        if not signals_df.empty:
            # Save to CSV
            output_file = 'ma_strategy_verification_signals.csv'
            signals_df.to_csv(output_file, index=False)
            logger.info(f"Signals saved to {output_file}")
            
            # Save full dataframe with MAs and signals
            full_output = 'ma_strategy_verification_full.csv'
            df.to_csv(full_output)
            logger.info(f"Full analysis saved to {full_output}")
            
            # Generate summary of signal groups
            signal_groups = defaultdict(list)
            
            for signal in self.signals:
                direction = "BUY" if signal['signal_value'] == 1 else "SELL"
                signal_groups[direction].append(signal)
            
            logger.info(f"Signal summary: {len(signal_groups.get('BUY', []))} BUY groups, "
                       f"{len(signal_groups.get('SELL', []))} SELL groups")
            
            return signals_df
        else:
            logger.warning("No signals generated")
            return None

def main():
    """Main execution function."""
    logger.info("Starting MA Crossover Strategy Verification")
    
    # Initialize strategy verifier with same parameters as main system
    strategy = MAStrategyVerification(fast_window=5, slow_window=15, price_key='Close')
    
    # Load the same data file
    data_file = 'data/MINI_1min.csv'
    df = strategy.load_data(data_file)
    
    if df is None:
        logger.error("Failed to load data. Exiting.")
        return
    
    # Calculate signals
    df = strategy.calculate_signals(df)
    
    # Process signals with direction tracking
    df = strategy.process_signals(df)
    
    # Simulate trades
    trades_df = strategy.simulate_trades(df)
    
    # Save signals
    signals_df = strategy.save_signals(df)
    
    # Count signal types
    buy_signals = df[df['signal'] == 1].shape[0]
    sell_signals = df[df['signal'] == -1].shape[0]
    direction_changes = df[df['direction_change'] == True].shape[0]
    
    # Print summary for comparison
    print("\n" + "=" * 50)
    print("MA CROSSOVER STRATEGY VERIFICATION SUMMARY")
    print("=" * 50)
    print(f"Data file: {data_file}")
    print(f"Parameters: fast_window={strategy.fast_window}, slow_window={strategy.slow_window}")
    print(f"Total raw buy signals: {buy_signals}")
    print(f"Total raw sell signals: {sell_signals}")
    print(f"Total direction changes (signal groups): {direction_changes}")
    print(f"Total trades generated: {len(strategy.trades)}")
    
    if trades_df is not None:
        total_pnl = trades_df['pnl'].sum()
        print(f"Total PnL: ${total_pnl:.2f}")
    
    print("\nCompare these results with the main system to verify that:")
    print("1. The number of signal groups matches")
    print("2. The rule IDs follow the same pattern")
    print("3. The direction changes occur at the same points")
    print("=" * 50)
    
    logger.info("MA Crossover Strategy Verification completed")
    
if __name__ == "__main__":
    main()