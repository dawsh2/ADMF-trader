#!/usr/bin/env python3
"""
Enhanced MA Crossover Strategy Validation

This script implements a complete backtest simulation to match the main system,
including the edge cases and behavior of the event system. It processes the same
data (MINI_1min.csv) with identical parameters and event handling logic.
"""

import pandas as pd
import numpy as np
import logging
import datetime
import os
import uuid
from collections import defaultdict, deque

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ma_strategy_verification_enhanced.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ma_strategy_verification_enhanced')

class EventBus:
    """Simplified event bus with deduplication for verification."""
    
    def __init__(self):
        """Initialize the event bus."""
        self.processed_events = {}
        self.processed_rule_ids = set()
        
    def is_duplicate(self, rule_id):
        """Check if a rule ID has been processed."""
        return rule_id in self.processed_rule_ids
        
    def add_rule_id(self, rule_id):
        """Add a rule ID to the processed set."""
        if rule_id:
            logger.info(f"Adding rule_id to processed set: {rule_id}")
            self.processed_rule_ids.add(rule_id)
    
    def reset(self):
        """Reset the event bus state."""
        self.processed_events.clear()
        self.processed_rule_ids.clear()
        logger.info("Event bus reset")

class Portfolio:
    """Simple portfolio for tracking positions and PnL."""
    
    def __init__(self, initial_cash=100000.0):
        """Initialize the portfolio."""
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
    def process_trade(self, timestamp, symbol, direction, quantity, price, rule_id=None):
        """Process a trade and update the portfolio."""
        # Calculate commission
        commission = price * quantity * 0.001  # 0.1% commission
        
        # Create unique trade ID
        trade_id = str(uuid.uuid4())
        
        # Handle BUY order
        if direction == "BUY":
            cost = price * quantity + commission
            self.cash -= cost
            
            # Calculate PnL if closing a position
            pnl = 0.0
            realized_pnl = 0.0
            
            if symbol in self.positions and self.positions[symbol]['quantity'] < 0:
                # Closing or reducing a short position
                existing_quantity = abs(self.positions[symbol]['quantity'])
                existing_price = self.positions[symbol]['price']
                
                if quantity <= existing_quantity:
                    # Calculate the realized PnL: (sell_price - buy_price) * quantity - commissions
                    realized_pnl = (existing_price - price) * quantity - commission
                    pnl = realized_pnl
                    
                    # Update position
                    remaining_quantity = existing_quantity - quantity
                    if remaining_quantity > 0:
                        self.positions[symbol]['quantity'] = -remaining_quantity
                    else:
                        del self.positions[symbol]
                else:
                    # Closing short position and opening long position
                    realized_pnl = (existing_price - price) * existing_quantity - commission
                    pnl = realized_pnl
                    
                    # Create new long position
                    self.positions[symbol] = {
                        'quantity': quantity - existing_quantity,
                        'price': price,
                        'direction': 'BUY'
                    }
            else:
                # Opening a new long position
                if symbol not in self.positions:
                    self.positions[symbol] = {
                        'quantity': quantity,
                        'price': price,
                        'direction': 'BUY'
                    }
                else:
                    # Adding to existing long position
                    existing_quantity = self.positions[symbol]['quantity']
                    existing_price = self.positions[symbol]['price']
                    
                    # Calculate new average price
                    total_quantity = existing_quantity + quantity
                    total_cost = (existing_quantity * existing_price) + (quantity * price)
                    avg_price = total_cost / total_quantity
                    
                    self.positions[symbol] = {
                        'quantity': total_quantity,
                        'price': avg_price,
                        'direction': 'BUY'
                    }
        
        # Handle SELL order  
        else:  # direction == "SELL"
            proceeds = price * quantity - commission
            self.cash += proceeds
            
            # Calculate PnL if closing a position
            pnl = 0.0
            realized_pnl = 0.0
            
            if symbol in self.positions and self.positions[symbol]['quantity'] > 0:
                # Closing or reducing a long position
                existing_quantity = self.positions[symbol]['quantity']
                existing_price = self.positions[symbol]['price']
                
                if quantity <= existing_quantity:
                    # Calculate the realized PnL: (sell_price - buy_price) * quantity - commissions
                    realized_pnl = (price - existing_price) * quantity - commission
                    pnl = realized_pnl
                    
                    # Update position
                    remaining_quantity = existing_quantity - quantity
                    if remaining_quantity > 0:
                        self.positions[symbol]['quantity'] = remaining_quantity
                    else:
                        del self.positions[symbol]
                else:
                    # Closing long position and opening short position
                    realized_pnl = (price - existing_price) * existing_quantity - commission
                    pnl = realized_pnl
                    
                    # Create new short position
                    self.positions[symbol] = {
                        'quantity': -(quantity - existing_quantity),
                        'price': price,
                        'direction': 'SELL'
                    }
            else:
                # Opening a new short position
                if symbol not in self.positions:
                    self.positions[symbol] = {
                        'quantity': -quantity,  # Negative quantity for short positions
                        'price': price,
                        'direction': 'SELL'
                    }
                else:
                    # Adding to existing short position
                    existing_quantity = abs(self.positions[symbol]['quantity'])
                    existing_price = self.positions[symbol]['price']
                    
                    # Calculate new average price
                    total_quantity = existing_quantity + quantity
                    total_cost = (existing_quantity * existing_price) + (quantity * price)
                    avg_price = total_cost / total_quantity
                    
                    self.positions[symbol] = {
                        'quantity': -total_quantity,  # Negative quantity for short positions
                        'price': avg_price,
                        'direction': 'SELL'
                    }
        
        # Store the trade
        trade = {
            'id': trade_id,
            'timestamp': timestamp,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'size': quantity,  # Match the main system's format
            'price': price,
            'fill_price': price,  # Match the main system's format
            'commission': commission,
            'pnl': pnl,
            'realized_pnl': realized_pnl,
            'rule_id': rule_id
        }
        self.trades.append(trade)
        
        # Calculate equity
        equity = self.cash
        for sym, pos in self.positions.items():
            equity += pos['quantity'] * price
        
        self.equity_curve.append({
            'timestamp': timestamp,
            'cash': self.cash,
            'equity': equity
        })
        
        logger.info(f"Trade: {direction} {quantity} {symbol} @ {price:.2f}, PnL=${pnl:.2f}, Cash=${self.cash:.2f}")
        return trade
    
    def get_position(self, symbol):
        """Get the current position for a symbol."""
        return self.positions.get(symbol, None)
    
    def reset(self):
        """Reset the portfolio to initial state."""
        self.cash = self.initial_cash
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        logger.info(f"Portfolio reset to ${self.initial_cash:.2f}")

class EnhancedMAStrategy:
    """
    Enhanced MA Crossover strategy that simulates the complete event system,
    including rule ID processing and deduplication.
    """
    
    def __init__(self, fast_window=5, slow_window=15, position_size=100, max_position_pct=0.1):
        """
        Initialize the MA strategy.
        
        Args:
            fast_window: Fast MA period (default: 5)
            slow_window: Slow MA period (default: 15)
            position_size: Base position size (default: 100)
            max_position_pct: Maximum position size as percentage of equity (default: 0.1)
        """
        self.name = "ma_crossover"
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.position_size = position_size
        self.max_position_pct = max_position_pct
        
        # Create event bus and portfolio
        self.event_bus = EventBus()
        self.portfolio = Portfolio()
        
        # Signal tracking
        self.data = {}
        self.signal_count = 0
        self.signal_directions = {}
        self.signal_groups = {}
        
        # Tracking variables
        self.signals = []
        self.orders = []
        
        # Setup event queue to process events
        self.event_queue = deque()
    
    def reset(self):
        """Reset the strategy."""
        self.event_bus.reset()
        self.portfolio.reset()
        self.data = {}
        self.signal_count = 0
        self.signal_directions = {}
        self.signal_groups = {}
        self.signals = []
        self.orders = []
        self.event_queue.clear()
        logger.info("Strategy reset")
    
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
        
        logger.info(f"Loaded {len(df)} data points from {file_path}")
        return df
    
    def calculate_signals(self, df):
        """
        Calculate trading signals.
        
        Args:
            df: DataFrame with price data
            
        Returns:
            tuple: (signals_df, trades_df)
        """
        logger.info(f"Running backtest with fast_window={self.fast_window}, slow_window={self.slow_window}")
        
        # Reset everything
        self.reset()
        
        symbol = "MINI"  # Symbol used in the main system
        
        # Process each bar
        for i, row in df.iterrows():
            # Skip rows with missing data
            if pd.isnull(row['Open']) or pd.isnull(row['Close']):
                continue
            
            timestamp = row['timestamp']
            price = row['Close']
            
            # Initialize data array for this symbol if needed
            if symbol not in self.data:
                self.data[symbol] = []
            
            # Store the bar data
            self.data[symbol].append({
                'timestamp': timestamp,
                'price': price
            })
            
            # Skip if we don't have enough data for both MAs
            if len(self.data[symbol]) <= self.slow_window:
                continue
            
            # Calculate moving averages
            prices = [bar['price'] for bar in self.data[symbol]]
            
            # Calculate fast MA - current and previous
            fast_ma = sum(prices[-self.fast_window:]) / self.fast_window
            fast_ma_prev = sum(prices[-(self.fast_window+1):-1]) / self.fast_window
            
            # Calculate slow MA - current and previous
            slow_ma = sum(prices[-self.slow_window:]) / self.slow_window
            slow_ma_prev = sum(prices[-(self.slow_window+1):-1]) / self.slow_window
            
            # Check for crossover
            signal_value = 0
            
            # Buy signal: fast MA crosses above slow MA
            if fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma:
                signal_value = 1
                crossover_pct = (fast_ma - slow_ma) / slow_ma
                logger.info(f"BUY crossover detected for {symbol}: fast MA ({fast_ma:.2f}) crossed above "
                         f"slow MA ({slow_ma:.2f}), crossover: {crossover_pct:.4%}")
            
            # Sell signal: fast MA crosses below slow MA
            elif fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma:
                signal_value = -1
                crossover_pct = (slow_ma - fast_ma) / slow_ma
                logger.info(f"SELL crossover detected for {symbol}: fast MA ({fast_ma:.2f}) crossed below "
                         f"slow MA ({slow_ma:.2f}), crossover: {crossover_pct:.4%}")
            
            # Skip if no signal
            if signal_value == 0:
                continue
            
            # Process signal only if direction changed
            current_direction = self.signal_directions.get(symbol, 0)
            
            logger.info(f"Signal generation: symbol={symbol}, signal_value={signal_value}, current_direction={current_direction}")
            if signal_value != current_direction:
                logger.info(f"DIRECTION CHANGE DETECTED: {current_direction} -> {signal_value}")
                
                # Direction has changed - create a new group
                self.signal_count += 1
                self.signal_groups[symbol] = self.signal_count
                self.signal_directions[symbol] = signal_value
                
                # Create group-based rule ID
                group_id = self.signal_groups[symbol]
                direction_name = "BUY" if signal_value == 1 else "SELL"
                rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"
                
                logger.info(f"RULE ID CREATED: {rule_id} for direction change {current_direction} -> {signal_value}")
                logger.info(f"NEW SIGNAL GROUP: {symbol} direction changed to {direction_name}, group={group_id}, rule_id={rule_id}")
                
                # Create signal
                signal = {
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'signal_value': signal_value,
                    'price': price,
                    'rule_id': rule_id,
                    'fast_ma': fast_ma,
                    'slow_ma': slow_ma
                }
                self.signals.append(signal)
                
                # Check if this rule ID has been processed already
                if self.event_bus.is_duplicate(rule_id):
                    logger.info(f"REJECTING: Signal with rule_id {rule_id} already processed")
                    continue
                
                # Process the signal
                self.process_signal(signal)
                
                # Add the rule ID to the processed set
                self.event_bus.add_rule_id(rule_id)
        
        # Process any remaining events in the queue
        while self.event_queue:
            event = self.event_queue.popleft()
            self.process_event(event)
        
        # Create DataFrames from signals and trades
        signals_df = pd.DataFrame(self.signals) if self.signals else pd.DataFrame()
        trades_df = pd.DataFrame(self.portfolio.trades) if self.portfolio.trades else pd.DataFrame()
        
        # Calculate performance metrics
        if not trades_df.empty:
            # Calculate total PnL
            total_pnl = trades_df['pnl'].sum()
            
            # Calculate win rate
            winning_trades = trades_df[trades_df['pnl'] > 0]
            win_rate = len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0
            
            logger.info(f"Backtest completed with {len(trades_df)} trades")
            logger.info(f"Total PnL: ${total_pnl:.2f}")
            logger.info(f"Win rate: {win_rate:.2f}%")
        
        return signals_df, trades_df
    
    def process_signal(self, signal):
        """
        Process a signal and generate an order if appropriate.
        
        Args:
            signal: Signal data dictionary
        """
        symbol = signal['symbol']
        signal_value = signal['signal_value']
        price = signal['price']
        timestamp = signal['timestamp']
        rule_id = signal.get('rule_id')
        
        # Skip if signal value is 0 (neutral)
        if signal_value == 0:
            return
        
        # Determine direction
        direction = 'BUY' if signal_value > 0 else 'SELL'
        
        # Calculate position size
        quantity = self.calculate_position_size(symbol, signal_value, price)
        
        # Skip if size is zero
        if quantity == 0:
            logger.info(f"Signal for {symbol} resulted in zero size, skipping")
            return
        
        # Create order
        order = {
            'timestamp': timestamp,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'rule_id': rule_id
        }
        self.orders.append(order)
        
        # Add order to event queue for processing
        self.event_queue.append(('order', order))
        logger.info(f"Created order: {direction} {quantity} {symbol} @ {price:.2f} with rule_id: {rule_id}")
    
    def process_event(self, event):
        """
        Process an event from the queue.
        
        Args:
            event: Tuple of (event_type, event_data)
        """
        event_type, event_data = event
        
        if event_type == 'order':
            # Process order and create trade
            symbol = event_data['symbol']
            direction = event_data['direction']
            quantity = event_data['quantity']
            price = event_data['price']
            timestamp = event_data['timestamp']
            rule_id = event_data.get('rule_id')
            
            # Execute the trade
            self.portfolio.process_trade(timestamp, symbol, direction, quantity, price, rule_id)
    
    def calculate_position_size(self, symbol, signal_value, price):
        """
        Calculate appropriate position size based on portfolio and risk settings.
        
        Args:
            symbol: Instrument symbol
            signal_value: Signal value (+1, -1, etc)
            price: Current price
            
        Returns:
            int: Position size to trade
        """
        # Get current position (if any)
        position = self.portfolio.get_position(symbol)
        current_quantity = position['quantity'] if position else 0
        
        # For BUY signals
        if signal_value > 0:
            # If we already have a full position, skip
            if current_quantity >= self.position_size:
                logger.debug(f"Already have maximum long position for {symbol}, skipping")
                return 0
                
            # If we have a short position, close it first
            if current_quantity < 0:
                # Full position reversal (close short + open long)
                target_size = abs(current_quantity) + self.position_size
            else:
                # Just add to existing long position up to target
                target_size = self.position_size - current_quantity
                
            # Apply constraints
            # 1. Check cash limits
            available_cash = self.portfolio.cash * 0.95  # Use 95% of available cash
            max_cash_size = int(available_cash / price) if price > 0 else 0
            
            # 2. Check position value limit (% of equity)
            max_position_value = self.portfolio.cash * self.max_position_pct
            max_position_size = int(max_position_value / price) if price > 0 else 0
            
            # Use most restrictive limit
            limited_size = min(target_size, max_cash_size, max_position_size)
            
            # Log the adjustment if any limits were applied
            if limited_size < target_size:
                logger.debug(f"Limited BUY size from {target_size} to {limited_size} for {symbol}")
            
            # Ensure minimum position size
            if 0 < limited_size < 10:
                logger.debug(f"Position size too small ({limited_size}), using minimum of 10")
                if limited_size < 10:
                    limited_size = 10
                
            return limited_size
            
        # For SELL signals
        else:
            # If we have a long position, close it first
            if current_quantity > 0:
                # Full position reversal: close long and open short
                target_size = current_quantity + self.position_size
            # If we already have a partial short position
            elif current_quantity < 0:
                # If we already have maximum short, skip
                if current_quantity <= -self.position_size:
                    logger.debug(f"Already have maximum short position for {symbol}, skipping")
                    return 0
                    
                # Add to existing short position up to target
                target_size = self.position_size + abs(current_quantity)
            else:
                # No position yet, full size
                target_size = self.position_size
            
            # Check position value limit for shorts (% of equity)
            max_position_value = self.portfolio.cash * self.max_position_pct
            max_position_size = int(max_position_value / price) if price > 0 else 0
            
            # Use most restrictive limit
            limited_size = min(target_size, max_position_size)
            
            # Log if limits were applied
            if limited_size < target_size:
                logger.debug(f"Limited SELL size from {target_size} to {limited_size} for {symbol}")
                
            # Ensure minimum position size
            if 0 < limited_size < 10:
                logger.debug(f"Short position size too small ({limited_size}), using minimum of 10")
                if limited_size < 10:
                    limited_size = 10
                
            return limited_size  # Positive value (quantity will be interpreted based on direction)
    
    def save_results(self, signals_df, trades_df):
        """
        Save backtest results to CSV files.
        
        Args:
            signals_df: DataFrame with signals
            trades_df: DataFrame with trades
        """
        # Save signals
        if not signals_df.empty:
            signals_df.to_csv('ma_strategy_verification_enhanced_signals.csv', index=False)
            logger.info("Signals saved to ma_strategy_verification_enhanced_signals.csv")
        
        # Save trades
        if not trades_df.empty:
            trades_df.to_csv('ma_strategy_verification_enhanced_trades.csv', index=False)
            logger.info("Trades saved to ma_strategy_verification_enhanced_trades.csv")
        
        # Save equity curve
        equity_curve_df = pd.DataFrame(self.portfolio.equity_curve)
        if not equity_curve_df.empty:
            equity_curve_df.to_csv('ma_strategy_verification_enhanced_equity.csv', index=False)
            logger.info("Equity curve saved to ma_strategy_verification_enhanced_equity.csv")
    
    def run_backtest(self, file_path):
        """
        Run a complete backtest simulation.
        
        Args:
            file_path: Path to price data CSV
        """
        # Load data
        df = self.load_data(file_path)
        if df is None:
            return None, None
        
        # Calculate signals and generate trades
        signals_df, trades_df = self.calculate_signals(df)
        
        # Save results
        self.save_results(signals_df, trades_df)
        
        return signals_df, trades_df

def main():
    """Main execution function."""
    print("\n" + "=" * 50)
    print("ENHANCED MA CROSSOVER STRATEGY VERIFICATION")
    print("=" * 50)
    
    # Initialize strategy with same parameters as main system
    strategy = EnhancedMAStrategy(fast_window=5, slow_window=15, position_size=100, max_position_pct=0.1)
    
    # Run backtest
    data_file = 'data/MINI_1min.csv'
    signals_df, trades_df = strategy.run_backtest(data_file)
    
    if trades_df is None or signals_df is None:
        print("Backtest failed. See log for details.")
        return
    
    # Print summary
    print("\n" + "=" * 50)
    print("BACKTEST SUMMARY")
    print("=" * 50)
    print(f"Data file: {data_file}")
    print(f"Parameters: fast_window={strategy.fast_window}, slow_window={strategy.slow_window}")
    print(f"Total signals generated: {len(signals_df)}")
    print(f"Total trades executed: {len(trades_df)}")
    
    if not trades_df.empty:
        total_pnl = trades_df['pnl'].sum()
        win_rate = (trades_df['pnl'] > 0).mean() * 100
        
        print(f"Total PnL: ${total_pnl:.2f}")
        print(f"Win rate: {win_rate:.2f}%")
    
    print("\nEnhanced verification complete. The results should match the main system.")
    print("Use compare_ma_results.py to compare with the main system.")
    print("=" * 50)
    
    # Return directory listing to easily see output files
    print("\nOutput files:")
    os.system("ls -l ma_strategy_verification_enhanced_*.csv")
    
if __name__ == "__main__":
    main()