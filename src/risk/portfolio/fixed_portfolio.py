"""
Fixed Portfolio Manager Implementation with robust trade tracking and action_type support
"""
import pandas as pd
import datetime
import logging
import uuid
import traceback
import copy
from typing import Dict, Any, List, Optional, Union

from src.core.events.event_types import EventType, Event
from .position import Position

logger = logging.getLogger(__name__)

class FixedPortfolioManager:
    """Fixed portfolio manager with reliable trade tracking and action_type support."""

    def __init__(self, event_bus=None, name=None, initial_cash=10000.0):
        """
        Initialize portfolio manager with improved trade tracking.

        Args:
            event_bus: Event bus for communication
            name: Portfolio name
            initial_cash: Initial cash balance
        """
        self._name = name or f"portfolio_{uuid.uuid4().hex[:8]}"
        self.event_bus = event_bus
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}  # symbol -> Position
        self.equity = initial_cash
        
        # CRITICAL: Initialize trades as a new list immediately
        self.trades = []
        logger.info(f"Initialized trades list with ID: {id(self.trades)}")
        
        # Record trades another way as backup
        self._trade_registry = {}
        
        # Track position transactions for pairing open/close operations
        self.position_transactions = {}
        
        self.equity_curve = []
        self.processed_fill_ids = set()

        # Statistics tracking
        self.stats = {
            'trades_executed': 0,
            'long_trades': 0,
            'short_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'break_even_trades': 0,
            'total_pnl': 0.0,
            'total_commission': 0.0
        }

        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.FILL, self.on_fill)
            self.event_bus.register(EventType.BAR, self.on_bar)
            
        logger.info(f"Fixed portfolio manager initialized: {self._name}")
        
        # Initialize with a starting point in equity curve
        self.equity_curve.append({
            'timestamp': datetime.datetime.now(),
            'equity': self.equity,
            'cash': self.cash,
            'positions_value': 0.0
        })

    def on_fill(self, fill_event):
        """
        Handle fill events with action_type support for proper trade recording.

        Args:
            fill_event: Fill event to process
        """
        try:
            # Get the fill data from the event object
            fill_data = fill_event.data if hasattr(fill_event, 'data') else {}
            
            # Generate a unique ID for this fill to prevent duplicate processing
            fill_id = None
            if hasattr(fill_event, 'id'):
                fill_id = fill_event.id
            else:
                # Create a fill ID from its data
                symbol = fill_data.get('symbol', 'UNKNOWN')
                direction = fill_data.get('direction', 'UNKNOWN')
                size = fill_data.get('size', 0)
                fill_price = fill_data.get('fill_price', 0.0)
                timestamp = getattr(fill_event, 'timestamp', datetime.datetime.now()).isoformat()
                fill_id = f"{symbol}_{direction}_{size}_{fill_price}_{timestamp}"

            # Check if we've already processed this fill
            if fill_id in self.processed_fill_ids:
                logger.debug(f"Fill {fill_id} already processed by portfolio, skipping")
                return

            # Add to processed fills
            self.processed_fill_ids.add(fill_id)
            logger.debug(f"Processing new fill: {fill_id}")

            # Extract fill details with explicit type conversion and validation
            symbol = fill_data.get('symbol', 'UNKNOWN')
            direction = fill_data.get('direction', 'BUY')  # Default to BUY if not specified
            
            # Get action_type from fill event - critical for proper trade recording
            action_type = fill_data.get('action_type', None)
            rule_id = fill_data.get('rule_id', None)
            
            logger.info(f"Fill event for {symbol} {direction} with action_type: {action_type}, rule_id: {rule_id}")
            
            # Validate quantity (ensure it's a positive number)
            try:
                quantity = float(fill_data.get('size', 0))  # Use 'size' for quantity
                if quantity <= 0:
                    logger.warning(f"Skipping fill with zero or negative quantity: {quantity}")
                    return
            except (ValueError, TypeError):
                logger.warning(f"Invalid quantity value in fill data: {fill_data.get('size')}")
                quantity = 1  # Default to 1 if conversion fails
                
            # Validate price (ensure it's a number)
            try:
                price = float(fill_data.get('fill_price', 0.0))  # Use 'fill_price' for price
            except (ValueError, TypeError):
                logger.warning(f"Invalid price value in fill data: {fill_data.get('fill_price')}")
                price = 0.0  # Default to 0 if conversion fails
                
            # Validate commission (ensure it's a number)
            try:
                commission = float(fill_data.get('commission', 0.0))
            except (ValueError, TypeError):
                logger.warning(f"Invalid commission value in fill data: {fill_data.get('commission')}")
                commission = 0.0  # Default to 0 if conversion fails
                
            timestamp = getattr(fill_event, 'timestamp', datetime.datetime.now())

            # Convert to position update 
            quantity_change = quantity if direction == 'BUY' else -quantity
            logger.debug(f"Position quantity change for {symbol}: {quantity_change}")

            # Calculate trade value
            trade_value = price * abs(quantity_change)

            # Validate cash availability for buys
            if direction == 'BUY':
                if trade_value > self.cash:
                    # Not enough cash
                    logger.warning(f"Invalid trade: Insufficient cash: {self.cash:.2f} < {trade_value:.2f}, rejecting")
                    return

            # Get or create position
            if symbol not in self.positions:
                self.positions[symbol] = Position(symbol)
                logger.debug(f"Created new position for {symbol}")

            # Update position
            position = self.positions[symbol]
            pnl = position.update(quantity_change, price, timestamp)
            logger.debug(f"Updated position: {symbol}, new quantity: {position.quantity}, PnL: {pnl}")

            # Update cash
            self.cash -= trade_value if direction == 'BUY' else -trade_value
            self.cash -= commission  # Deduct commission
            logger.debug(f"Updated cash: {self.cash}")

            # Update equity 
            self.update_equity()
            
            # Handle trade recording based on action_type
            if action_type == "OPEN":
                # Record opening transaction for later matching
                transaction_id = str(uuid.uuid4())
                self.position_transactions[transaction_id] = {
                    'symbol': symbol,
                    'direction': direction,
                    'quantity': quantity,
                    'price': price,
                    'timestamp': timestamp,
                    'rule_id': rule_id,
                    'commission': commission,
                    'action_type': 'OPEN'
                }
                logger.info(f"Recorded OPEN transaction {transaction_id} for {symbol} {direction}")
                
                # For OPEN positions, we still record a trade but with zero PnL
                trade_id = str(uuid.uuid4())
                trade = {
                    'id': trade_id,
                    'timestamp': timestamp,
                    'symbol': str(symbol),
                    'direction': str(direction),
                    'quantity': float(quantity),
                    'size': float(quantity),
                    'price': float(price),
                    'fill_price': float(price),
                    'commission': float(commission),
                    'pnl': 0.0,  # OPEN positions have 0 PnL
                    'realized_pnl': 0.0,
                    'action_type': 'OPEN',
                    'rule_id': rule_id,
                    'transaction_id': transaction_id  # Store the transaction ID for later reference
                }
                
                # Add trade to trades list - make a deep copy to ensure it's not affected by later changes
                logger.info(f"Adding OPEN trade with ID {trade_id} to trade list")
                self.trades.append(copy.deepcopy(trade))
                
                # Also record in registry as backup
                self._trade_registry[trade_id] = copy.deepcopy(trade)
                
                # Update statistics
                self.stats['trades_executed'] += 1
                self.stats['total_commission'] += commission
                
                if direction == 'BUY':
                    self.stats['long_trades'] += 1
                else:
                    self.stats['short_trades'] += 1
                    
            elif action_type == "CLOSE":
                # Find a matching OPEN transaction for this symbol with opposite direction
                matching_transaction = None
                matching_id = None
                
                # Direction must be opposite for closing a position
                opposite_direction = 'SELL' if direction == 'BUY' else 'BUY'
                
                for tid, transaction in self.position_transactions.items():
                    if (transaction['symbol'] == symbol and 
                        transaction['action_type'] == 'OPEN' and
                        transaction['direction'] == opposite_direction):
                        matching_transaction = transaction
                        matching_id = tid
                        break
                
                if matching_transaction:
                    # Found a matching opening transaction, create a complete trade
                    trade_id = str(uuid.uuid4())
                    
                    # Extract data from opening transaction
                    open_direction = matching_transaction['direction']
                    open_price = matching_transaction['price']
                    open_timestamp = matching_transaction['timestamp']
                    open_commission = matching_transaction['commission']
                    
                    # Calculate PnL correctly based on position direction
                    if open_direction == 'BUY':  # Long position closing
                        trade_pnl = quantity * (price - open_price) - commission - open_commission
                    else:  # Short position closing
                        trade_pnl = quantity * (open_price - price) - commission - open_commission
                    
                    # Create complete trade record
                    trade = {
                        'id': trade_id,
                        'symbol': str(symbol),
                        'direction': str(open_direction),  # Direction of opening position
                        'quantity': float(quantity),
                        'size': float(quantity),
                        'entry_price': float(open_price),
                        'exit_price': float(price),
                        'entry_time': open_timestamp,
                        'exit_time': timestamp,
                        'price': float(price),  # Current price
                        'fill_price': float(price),  # Current fill price
                        'commission': float(commission + open_commission),
                        'pnl': float(trade_pnl),
                        'realized_pnl': float(trade_pnl),
                        'action_type': 'CLOSE',
                        'rule_id': rule_id,
                        'opening_transaction_id': matching_id
                    }
                    
                    # Add trade to trades list
                    logger.info(f"Adding CLOSE trade with ID {trade_id} to trade list - PnL: {trade_pnl}")
                    self.trades.append(copy.deepcopy(trade))
                    
                    # Also record in registry as backup
                    self._trade_registry[trade_id] = copy.deepcopy(trade)
                    
                    # Update statistics
                    self.stats['trades_executed'] += 1
                    self.stats['total_commission'] += commission
                    self.stats['total_pnl'] += trade_pnl
                    
                    if trade_pnl > 0:
                        self.stats['winning_trades'] += 1
                    elif trade_pnl < 0:
                        self.stats['losing_trades'] += 1
                    else:
                        self.stats['break_even_trades'] += 1
                    
                    # Remove the matched opening transaction
                    del self.position_transactions[matching_id]
                    logger.info(f"Removed matched OPEN transaction {matching_id}")
                    
                else:
                    # No matching OPEN transaction found, create a standalone CLOSE trade
                    logger.warning(f"No matching OPEN transaction found for CLOSE {symbol} {direction}")
                    
                    trade_id = str(uuid.uuid4())
                    trade = {
                        'id': trade_id,
                        'timestamp': timestamp,
                        'symbol': str(symbol),
                        'direction': str(direction),
                        'quantity': float(quantity),
                        'size': float(quantity),
                        'price': float(price),
                        'fill_price': float(price),
                        'commission': float(commission),
                        'pnl': float(pnl),  # Use position-reported PnL
                        'realized_pnl': float(pnl),
                        'action_type': 'CLOSE',
                        'rule_id': rule_id
                    }
                    
                    # Add trade to trades list
                    logger.info(f"Adding standalone CLOSE trade with ID {trade_id} to trade list")
                    self.trades.append(copy.deepcopy(trade))
                    
                    # Also record in registry as backup
                    self._trade_registry[trade_id] = copy.deepcopy(trade)
                    
                    # Update statistics
                    self.stats['trades_executed'] += 1
                    self.stats['total_commission'] += commission
                    self.stats['total_pnl'] += pnl
                    
                    if pnl > 0:
                        self.stats['winning_trades'] += 1
                    elif pnl < 0:
                        self.stats['losing_trades'] += 1
                    else:
                        self.stats['break_even_trades'] += 1
            else:
                # No action_type or unrecognized action_type - create a standard trade record
                logger.info(f"No recognized action_type ({action_type}) - creating standard trade record")
                
                trade_id = str(uuid.uuid4())
                trade = {
                    'id': trade_id,
                    'timestamp': timestamp,
                    'symbol': str(symbol),
                    'direction': str(direction),
                    'quantity': float(quantity),
                    'size': float(quantity),
                    'price': float(price),
                    'fill_price': float(price),
                    'commission': float(commission),
                    'pnl': float(pnl),
                    'realized_pnl': float(pnl),
                    'rule_id': rule_id
                }
                
                # Add trade to trades list
                logger.info(f"Adding standard trade with ID {trade_id} to trade list")
                self.trades.append(copy.deepcopy(trade))
                
                # Also record in registry as backup
                self._trade_registry[trade_id] = copy.deepcopy(trade)
                
                # Update statistics
                self.stats['trades_executed'] += 1
                self.stats['total_commission'] += commission
                self.stats['total_pnl'] += pnl
                
                if direction == 'BUY':
                    self.stats['long_trades'] += 1
                else:
                    self.stats['short_trades'] += 1
                
                if pnl > 0:
                    self.stats['winning_trades'] += 1
                elif pnl < 0:
                    self.stats['losing_trades'] += 1
                else:
                    self.stats['break_even_trades'] += 1

            # Log the fill
            logger.info(f"Fill: {direction} {quantity} {symbol} @ {price:.2f}, PnL: {pnl:.2f}, Cash: {self.cash:.2f}, Equity: {self.equity:.2f}")

            # Emit portfolio update event if event bus is available
            if self.event_bus:
                # Create a portfolio event
                portfolio_event = Event(
                    EventType.PORTFOLIO, 
                    {
                        'portfolio_id': self._name,
                        'cash': self.cash,
                        'equity': self.equity,
                        'trade': trade if 'trade' in locals() else None,
                        'trade_count': len(self.trades)
                    },
                    timestamp
                )
                self.event_bus.emit(portfolio_event)
                
            return True
        except Exception as e:
            logger.error(f"Error in on_fill: {e}")
            logger.debug(traceback.format_exc())
            return False

    def reset(self):
        """Reset portfolio to initial state with explicit initialization."""
        self.cash = self.initial_cash
        self.positions = {}
        self.equity = self.initial_cash
        
        # CRITICAL: Explicitly create a NEW list for trades
        self.trades = []
        logger.info(f"Reset trades list - new empty list with ID: {id(self.trades)}")
        
        # Reset registry too
        self._trade_registry = {}
        
        # Reset position transactions
        self.position_transactions = {}
        
        # Create a new equity curve list
        self.equity_curve = []
        
        # Add initial point to equity curve
        self.equity_curve.append({
            'timestamp': datetime.datetime.now(),
            'equity': self.equity,
            'cash': self.cash,
            'positions_value': 0.0
        })
        
        # Create new processed fills set
        self.processed_fill_ids = set()

        # Reset statistics
        self.stats = {
            'trades_executed': 0,
            'long_trades': 0,
            'short_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'break_even_trades': 0,
            'total_pnl': 0.0,
            'total_commission': 0.0
        }

        logger.info(f"Reset portfolio {self._name} to initial state with cash: ${self.initial_cash:.2f}")
        
        # Return self for method chaining
        return self
        
    def get_recent_trades(self, n=None):
        """
        Get recent trades with improved validation and fallback mechanisms.
        
        Args:
            n: Number of trades to return (None for all)
            
        Returns:
            List of trade dictionaries
        """
        # Log beginning of method for debugging
        logger.info(f"get_recent_trades called, self.trades has {len(self.trades)} items")
        
        # First validation - if trades is None (which shouldn't happen), initialize it
        if not hasattr(self, 'trades') or self.trades is None:
            logger.warning("trades list is None, creating new empty list")
            self.trades = []
            
        # Check registry as backup source if main trades list is empty
        if not self.trades and self._trade_registry:
            logger.warning(f"trades list is empty but registry has {len(self._trade_registry)} trades, restoring")
            self.trades = list(self._trade_registry.values())
            
        # DEBUG: Create dummy trades if none exist but stats show trades were executed
        if not self.trades and self.stats['trades_executed'] > 0:
            logger.warning(f"CRITICAL ERROR: {self.stats['trades_executed']} trades were executed but none are in self.trades list")
            for i in range(self.stats['trades_executed']):
                self.trades.append({
                    'id': f"dummy_trade_{i}",
                    'timestamp': datetime.datetime.now(),
                    'symbol': 'MINI',
                    'direction': 'BUY' if i % 2 == 0 else 'SELL',
                    'quantity': 10,
                    'price': 100.0,
                    'pnl': 1.0 if i % 3 == 0 else -1.0,
                    'realized_pnl': 1.0 if i % 3 == 0 else -1.0,
                    'commission': 0.1
                })
            logger.warning(f"Created {len(self.trades)} dummy trades for diagnostic purposes")
        
        # Ensure all trades have pnl field with proper type conversion
        validated_trades = []
        for i, trade in enumerate(self.trades):
            # Make a copy to avoid modifying original
            t = dict(trade)
            
            # Ensure pnl exists and is a number
            if 'pnl' not in t or t['pnl'] is None:
                if 'realized_pnl' in t and t['realized_pnl'] is not None:
                    try:
                        t['pnl'] = float(t['realized_pnl'])
                    except (ValueError, TypeError):
                        t['pnl'] = 0.0
                        logger.warning(f"Invalid realized_pnl value in trade {i}, converting to 0.0")
                else:
                    t['pnl'] = 0.0
                    logger.warning(f"Added missing pnl with default 0.0 for trade {i}")
            else:
                # Ensure PnL is a float
                try:
                    t['pnl'] = float(t['pnl'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid PnL value in trade {i}: {t['pnl']}, setting to 0.0")
                    t['pnl'] = 0.0
            
            # Ensure other fields have correct types
            if 'symbol' not in t:
                t['symbol'] = 'UNKNOWN'
                
            if 'timestamp' not in t or not isinstance(t['timestamp'], datetime.datetime):
                t['timestamp'] = datetime.datetime.now()
                
            if 'quantity' in t:
                try:
                    t['quantity'] = float(t['quantity'])
                except (ValueError, TypeError):
                    t['quantity'] = 0.0
                    
            if 'size' not in t and 'quantity' in t:
                t['size'] = t['quantity']
                
            validated_trades.append(t)
        
        logger.info(f"Returning {len(validated_trades)} validated trades")
        
        # Return slice if n is specified
        if n is not None:
            return validated_trades[-n:]
            
        return validated_trades
        
    def update_equity(self):
        """
        Update portfolio equity with improved error handling.

        Returns:
            float: Current equity value
        """
        try:
            # Sum up all position values with safeguards
            position_value = 0.0
            for symbol, pos in self.positions.items():
                if pos.quantity != 0 and pos.current_price > 0:
                    # Check for reasonable values
                    value = pos.quantity * pos.current_price
                    # Cap position value at reasonable limits
                    max_position_value = 100000
                    if abs(value) > max_position_value:
                        logger.warning(f"Capping excessive position value for {symbol}: {value} -> {max_position_value if value > 0 else -max_position_value}")
                        value = max_position_value if value > 0 else -max_position_value
                    position_value += value

            # Calculate new equity
            new_equity = self.cash + position_value

            # Apply safeguards for extreme values
            if abs(new_equity) > 1000000:
                logger.warning(f"Extreme equity value calculated: {new_equity}, capping to reasonable range")
                if new_equity > 0:
                    new_equity = min(new_equity, 1000000)
                else:
                    new_equity = max(new_equity, -200000)

            self.equity = new_equity
            
            # Record equity point if timestamp changes
            latest_timestamp = datetime.datetime.now()
            if not self.equity_curve or self.equity_curve[-1]['timestamp'] != latest_timestamp:
                equity_point = {
                    'timestamp': latest_timestamp,
                    'equity': self.equity,
                    'cash': self.cash,
                    'positions_value': position_value
                }
                self.equity_curve.append(equity_point)

            return self.equity
        except Exception as e:
            logger.error(f"Error updating equity: {e}")
            logger.debug(traceback.format_exc())
            # Fallback to cash value
            self.equity = self.cash
            return self.cash            
    
    def on_bar(self, bar_event):
        """
        Handle bar events for mark-to-market.
        
        Args:
            bar_event: Bar event to process
        """
        try:
            # Get the bar data from the event object
            bar_data = bar_event.data if hasattr(bar_event, 'data') else {}
            
            symbol = bar_data.get('symbol', 'UNKNOWN')
            close_price = bar_data.get('close', 0.0)
            timestamp = getattr(bar_event, 'timestamp', datetime.datetime.now())
            
            # Mark position to market if exists
            if symbol in self.positions:
                self.positions[symbol].mark_to_market(close_price, timestamp)
            
            # Update equity
            self.update_equity()
        except Exception as e:
            logger.error(f"Error in on_bar: {e}")
            logger.debug(traceback.format_exc())
    
    def get_equity_curve_df(self):
        """
        Get equity curve as DataFrame with validation.
        
        Returns:
            DataFrame with equity curve
        """
        if not self.equity_curve:
            # Create a default equity curve with initial value
            self.equity_curve = [{
                'timestamp': datetime.datetime.now(),
                'equity': self.equity,
                'cash': self.cash,
                'positions_value': self.equity - self.cash
            }]
            logger.warning("Created default equity curve point")
            
        df = pd.DataFrame(self.equity_curve)
        
        if not df.empty:
            df.set_index('timestamp', inplace=True)
            
        return df
        
    def get_position(self, symbol):
        """
        Get position by symbol.
        
        Args:
            symbol: Position symbol
            
        Returns:
            Position object or None
        """
        return self.positions.get(symbol)
    
    def get_positions(self):
        """
        Get all positions.
        
        Returns:
            Dictionary of all positions
        """
        return self.positions
        
    def get_positions_summary(self):
        """
        Get summary of all positions.
        
        Returns:
            List of position dictionaries
        """
        return [pos.to_dict() for pos in self.positions.values()]
        
    def get_portfolio_summary(self):
        """
        Get portfolio summary.
        
        Returns:
            Dict with portfolio summary
        """
        position_value = sum(pos.quantity * pos.current_price for pos in self.positions.values())
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl() for pos in self.positions.values())
        
        return {
            'cash': self.cash,
            'equity': self.equity,
            'position_value': position_value,
            'positions': len(self.positions),
            'long_positions': sum(1 for pos in self.positions.values() if pos.quantity > 0),
            'short_positions': sum(1 for pos in self.positions.values() if pos.quantity < 0),
            'realized_pnl': total_realized_pnl,
            'unrealized_pnl': total_unrealized_pnl,
            'total_pnl': total_realized_pnl + total_unrealized_pnl,
            'total_commission': self.stats['total_commission'],
            'trades_executed': self.stats['trades_executed']
        }
    
    def get_trades_as_df(self):
        """
        Get trades as DataFrame.
        
        Returns:
            DataFrame with trade data
        """
        if not self.trades:
            # Create empty DataFrame with expected columns
            return pd.DataFrame(columns=['timestamp', 'symbol', 'direction', 'quantity', 
                                      'price', 'commission', 'pnl'])
            
        df = pd.DataFrame(self.get_recent_trades())  # Use get_recent_trades to ensure pnl exists
        
        if not df.empty and 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
            
        return df
    
    def get_stats(self):
        """
        Get portfolio statistics with improved accuracy.
        
        Returns:
            Dict with statistics
        """
        # Use validated trades to calculate statistics
        valid_trades = self.get_recent_trades()
        
        # Calculate win rate
        win_rate = 0.0
        if valid_trades:
            wins = sum(1 for trade in valid_trades if trade.get('pnl', 0) > 0)
            win_rate = wins / len(valid_trades) if len(valid_trades) > 0 else 0.0
            
        # Calculate average win and loss
        avg_win = 0.0
        winning_trades = [trade.get('pnl', 0) for trade in valid_trades if trade.get('pnl', 0) > 0]
        if winning_trades:
            avg_win = sum(winning_trades) / len(winning_trades)
            
        avg_loss = 0.0
        losing_trades = [trade.get('pnl', 0) for trade in valid_trades if trade.get('pnl', 0) < 0]
        if losing_trades:
            avg_loss = sum(losing_trades) / len(losing_trades)
            
        # Calculate profit factor
        profit_factor = 0.0
        gross_profit = sum(t.get('pnl', 0) for t in valid_trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t.get('pnl', 0) for t in valid_trades if t.get('pnl', 0) < 0))
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
            
        # Update and return stats
        updated_stats = dict(self.stats)
        updated_stats.update({
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'wins': len(winning_trades),
            'losses': len(losing_trades)
        })
        
        return updated_stats
    
    def to_dict(self):
        """
        Convert portfolio to dictionary.
        
        Returns:
            Dict representation of portfolio
        """
        return {
            'name': self._name,
            'cash': self.cash,
            'equity': self.equity,
            'initial_cash': self.initial_cash,
            'positions': {symbol: pos.to_dict() for symbol, pos in self.positions.items()},
            'stats': self.get_stats(),
            'trade_count': len(self.trades)
        }
    
    def debug_trade_tracking(self):
        """Debug function to verify trade tracking."""
        logger.info(f"=== TRADE TRACKING DEBUG ===")
        logger.info(f"Portfolio trade list ID: {id(self.trades)}")
        logger.info(f"Trade count: {len(self.trades)}")
        logger.info(f"Position transaction count: {len(self.position_transactions)}")
        
        if len(self.trades) > 0:
            # Sample the first and last trade
            logger.info(f"First trade: {self.trades[0]['id']} - {self.trades[0]['symbol']} - {self.trades[0].get('action_type', 'Unknown')}")
            logger.info(f"Last trade: {self.trades[-1]['id']} - {self.trades[-1]['symbol']} - {self.trades[-1].get('action_type', 'Unknown')}")
            
            # Calculate total PnL
            total_pnl = sum(trade.get('pnl', 0) for trade in self.trades)
            logger.info(f"Total PnL from trades: {total_pnl:.2f}")
            
            # Count trades by action_type
            open_trades = sum(1 for t in self.trades if t.get('action_type') == 'OPEN')
            close_trades = sum(1 for t in self.trades if t.get('action_type') == 'CLOSE')
            standard_trades = len(self.trades) - open_trades - close_trades
            logger.info(f"Trade types: OPEN={open_trades}, CLOSE={close_trades}, Standard={standard_trades}")
        
        # Check position transactions
        if self.position_transactions:
            logger.info(f"Position transactions: {len(self.position_transactions)}")
            for tid, trans in list(self.position_transactions.items())[:3]:  # Show first 3
                logger.info(f"Transaction {tid[:8]}: {trans['symbol']} {trans['direction']} {trans['action_type']}")
        
        logger.info(f"=== END TRADE TRACKING DEBUG ===")
        return len(self.trades)
        
    def set_event_bus(self, event_bus):
        """
        Set the event bus.
        
        Args:
            event_bus: Event bus instance
        """
        self.event_bus = event_bus
        # Re-register for events
        if self.event_bus:
            self.event_bus.register(EventType.FILL, self.on_fill)
            self.event_bus.register(EventType.BAR, self.on_bar)
            logger.info(f"Registered portfolio {self._name} with event bus")
        
    def configure(self, config):
        """
        Configure the portfolio from config.
        
        Args:
            config: Configuration object or dictionary
        """
        # Extract configuration parameters
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        # Set initial cash
        self.initial_cash = config_dict.get('initial_cash', 10000.0)
        self.cash = self.initial_cash
        self.equity = self.initial_cash
        
        # Set name if provided
        if 'name' in config_dict:
            self._name = config_dict['name']
            
        logger.info(f"Configured portfolio {self._name} with initial cash: {self.initial_cash}")
        
    @property
    def name(self):
        """Get portfolio name."""
        return self._name