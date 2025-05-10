"""
Portfolio component that uses the centralized TradeRepository.

This implementation ensures trades are consistently tracked in a single place
rather than across multiple components.
"""

import logging
from src.core.component import Component
from src.core.events.event_bus import Event, EventType
from src.core.data_model import Trade, Direction

class Portfolio(Component):
    """
    Portfolio component for tracking positions, cash, and trades.
    
    This implementation uses the centralized TradeRepository for
    consistent trade tracking.
    """
    
    def __init__(self, name, initial_capital):
        """
        Initialize the portfolio.
        
        Args:
            name (str): Component name
            initial_capital (float): Starting capital
        """
        super().__init__(name)
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # symbol -> quantity
        self.trade_repository = None  # Will be set in initialize()
        
        # Add detailed tracking of cash flows
        self.realized_pnl = 0.0  # Total realized PnL
        self.total_fees = 0.0    # Total fees paid
        self.total_interest = 0.0  # Total interest paid/received
        self.total_dividends = 0.0  # Total dividends received
        
        # Add history tracking for debugging
        self.cash_history = []  # History of cash values
        self.equity_history = []  # History of equity values
        self.timestamp_history = []  # Corresponding timestamps
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
    def initialize(self, context):
        """
        Initialize the portfolio with dependencies.
        
        Args:
            context (dict): Dependencies and configuration
        """
        super().initialize(context)
        
        # Get event bus and trade repository from context
        self.event_bus = context.get('event_bus')
        self.trade_repository = context.get('trade_repository')
        
        if not self.event_bus:
            raise ValueError("Portfolio requires event_bus in context")
            
        if not self.trade_repository:
            raise ValueError("Portfolio requires trade_repository in context")
            
        # Subscribe to fill events
        self.event_bus.subscribe(EventType.FILL, self.on_fill)
        
    def reset(self):
        """Reset the portfolio to its initial state."""
        super().reset()
        self.current_capital = self.initial_capital
        self.positions = {}
        # Reset all tracking variables
        self.realized_pnl = 0.0
        self.total_fees = 0.0
        self.total_interest = 0.0
        self.total_dividends = 0.0
        self.cash_history = []
        self.equity_history = []
        self.timestamp_history = []
        # No need to reset trade_repository here - that's managed centrally
        
    def _get_last_price(self, symbol):
        """Get the last known price for a symbol."""
        # Try to find the last fill price from trade repository
        if self.trade_repository:
            # Get all trades for this symbol
            symbol_trades = [t for t in self.trade_repository.get_trades() 
                          if t.get('symbol') == symbol]
            
            # Sort by timestamp to get the most recent
            if symbol_trades:
                # First try to get the most recent close price
                closed_trades = [t for t in symbol_trades if t.get('close_price') is not None]
                if closed_trades:
                    latest_closed = max(closed_trades, key=lambda t: t.get('close_time'))
                    return latest_closed.get('close_price')
                
                # If no close prices, try entry prices
                entry_trades = [t for t in symbol_trades if t.get('entry_price') is not None]
                if entry_trades:
                    latest_entry = max(entry_trades, key=lambda t: t.get('entry_time'))
                    return latest_entry.get('entry_price')
        
        # If we couldn't find a price, return None
        return None
        
    def on_fill(self, event):
        """
        Handle fill events by updating positions and capital.
        
        Args:
            event (Event): Fill event
        """
        fill_data = event.get_data()
        
        # Apply standardized field names
        symbol = fill_data.get('symbol')
        direction = fill_data.get('direction')
        quantity = fill_data.get('quantity')
        price = fill_data.get('price')
        timestamp = fill_data.get('timestamp')
        commission = fill_data.get('commission', 0.0)
        
        # Update position
        position_delta = quantity
        if direction == Direction.SHORT.value:
            position_delta = -quantity
            
        # Update or create position
        if symbol in self.positions:
            self.positions[symbol] += position_delta
        else:
            self.positions[symbol] = position_delta
            
        # If position crosses zero, we might have closing trades
        self._check_for_trade_close(fill_data)
        
        # Update capital based on transaction type
        transaction_value = price * quantity
        
        # For buys (LONG), we spend money
        # For sells (SHORT), we receive money
        if direction == Direction.LONG.value:  # Buying
            self.current_capital -= transaction_value
        else:  # Selling
            self.current_capital += transaction_value
            
        # Deduct commission for all transactions
        self.current_capital -= commission
        
        # Create new trade if this is an opening position
        self._check_for_trade_open(fill_data)
        
        # Calculate closed trade PnL only (for consistent metrics)
        closed_trades = self.get_closed_trades()
        closed_pnl_sum = sum(t.get('pnl', 0) for t in closed_trades)
        
        # Calculate market value of open positions
        # This is an estimate that will be used for separate tracking
        open_value = 0
        for pos_symbol, pos_quantity in self.positions.items():
            if pos_quantity != 0 and pos_symbol == symbol:  # We only have current price for the active symbol
                open_value += pos_quantity * price
        
        # Publish portfolio update event with both equity values
        self._publish_update(timestamp, closed_pnl_sum, open_value)
        
    def _check_for_trade_open(self, fill_data):
        """
        Check if a fill opens a new trade.
        
        Args:
            fill_data (dict): Fill data
        """
        symbol = fill_data.get('symbol')
        direction = fill_data.get('direction')
        
        # Determine if this is an opening trade
        is_opening = False
        if direction == Direction.LONG.value and self.positions.get(symbol, 0) > 0:
            is_opening = True
        elif direction == Direction.SHORT.value and self.positions.get(symbol, 0) < 0:
            is_opening = True
            
        # Create new trade
        if is_opening:
            trade_data = {
                'id': f"trade_{fill_data.get('id')}",
                'symbol': symbol,
                'direction': direction,
                'quantity': abs(fill_data.get('quantity')),
                'entry_price': fill_data.get('price'),
                'entry_time': fill_data.get('timestamp'),
                'closed': False,
                'related_order_ids': [fill_data.get('order_id')]
            }
            
            # Add to repository
            self.trade_repository.add_trade(trade_data)
            
            # Publish trade open event
            self.event_bus.publish(Event(
                EventType.TRADE_OPEN,
                trade_data
            ))
            
    def _check_for_trade_close(self, fill_data):
        """
        Check if a fill closes an existing trade.
        
        Args:
            fill_data (dict): Fill data
        """
        symbol = fill_data.get('symbol')
        direction = fill_data.get('direction')
        
        # Find open trades for this symbol
        open_trades = self.trade_repository.get_open_trades(symbol)
        
        # Check if this fill closes any trades
        for trade in open_trades:
            trade_direction = trade.get('direction')
            
            # If fill direction is opposite of trade direction, it might close the trade
            if ((trade_direction == Direction.LONG.value and direction == Direction.SHORT.value) or
                (trade_direction == Direction.SHORT.value and direction == Direction.LONG.value)):
                
                # Close the trade
                updated_trade = self.trade_repository.close_trade(
                    trade_id=trade.get('id'),
                    close_price=fill_data.get('price'),
                    close_time=fill_data.get('timestamp'),
                    quantity=abs(fill_data.get('quantity'))
                )
                
                if updated_trade and updated_trade.get('closed', False):
                    # Update realized PnL tracking with the same value that's in the trade
                    trade_pnl = updated_trade.get('pnl', 0.0)
                    self.realized_pnl += trade_pnl
                    
                    # Log the trade close with PnL for debugging
                    self.logger.info(f"Trade closed: {updated_trade.get('id')}, PnL: {trade_pnl:.2f}")
                    
                    # Publish trade close event
                    self.event_bus.publish(Event(
                        EventType.TRADE_CLOSE,
                        updated_trade
                    ))
    
    def _publish_update(self, timestamp=None, closed_pnl=0, open_value=0):
        """Publish portfolio update event."""
        # Calculate closed-only equity using closed trade PnL only
        closed_only_equity = self.initial_capital + closed_pnl

        # Calculate market value separately from cash positions
        # FIXED: Calculate market value for ALL open positions, not just the current symbol
        market_value = 0
        for symbol, quantity in self.positions.items():
            if quantity != 0:
                # If we have price data available for this symbol
                last_fill_price = self._get_last_price(symbol)
                if last_fill_price is not None:
                    position_value = quantity * last_fill_price
                    market_value += position_value
                    self.logger.debug(f"Position value for {symbol}: {quantity} x {last_fill_price:.2f} = {position_value:.2f}")
                else:
                    self.logger.warning(f"No price data available for {symbol} - position value not included in equity")

        # Log market value for debugging
        self.logger.debug(f"Total market value: {market_value:.2f}, Cash: {self.current_capital:.2f}")

        # Full equity includes both cash and market value
        full_equity = self.current_capital + market_value

        # Store values in history for tracking
        if timestamp:
            self.cash_history.append(self.current_capital)
            self.equity_history.append(full_equity)
            self.timestamp_history.append(timestamp)

        update_data = {
            'timestamp': timestamp,
            'capital': self.current_capital,  # Cash only
            'positions': self.positions.copy(),
            'closed_pnl': closed_pnl,  # Realized PnL from closed trades
            'open_value': market_value,  # Market value of open positions
            'closed_only_equity': closed_only_equity,  # Equity using only closed trades
            'market_value': market_value,  # Explicit market value
            'full_equity': full_equity  # Cash + market value
        }

        self.logger.debug(f"Portfolio update: Capital={self.current_capital:.2f}, "
                          f"Closed PnL={closed_pnl:.2f}, Market Value={market_value:.2f}, "
                          f"Full Equity={full_equity:.2f}")

        self.event_bus.publish(Event(
            EventType.PORTFOLIO,
            update_data
        ))
        
    def get_positions(self):
        """
        Get current positions.
        
        Returns:
            dict: Copy of current positions
        """
        return self.positions.copy()
        
    def get_capital(self):
        """
        Get current capital.
        
        Returns:
            float: Current capital
        """
        return self.current_capital
        
    def get_trades(self):
        """
        Get all trades.
        
        Returns:
            list: All trades from the repository
        """
        return self.trade_repository.get_trades()
        
    def get_open_trades(self, symbol=None):
        """
        Get open trades, optionally filtered by symbol.
        
        Args:
            symbol (str, optional): Symbol to filter by
            
        Returns:
            list: Open trades
        """
        return self.trade_repository.get_open_trades(symbol)
        
    def get_closed_trades(self, symbol=None):
        """
        Get closed trades, optionally filtered by symbol.

        Args:
            symbol (str, optional): Symbol to filter by

        Returns:
            list: Closed trades
        """
        return self.trade_repository.get_closed_trades(symbol)

    def close_all_positions(self, timestamp=None):
        """
        Close all open positions at the current timestamp.

        Args:
            timestamp (datetime, optional): Timestamp to use for closing

        Returns:
            list: Closed trades
        """
        if not timestamp:
            import datetime
            timestamp = datetime.datetime.now()

        self.logger.info(f"Closing all positions at timestamp: {timestamp}")

        closed_trades = []
        open_positions = [symbol for symbol, quantity in self.positions.items() if quantity != 0]

        # Nothing to close
        if not open_positions:
            self.logger.info("No open positions to close")
            return closed_trades

        for symbol in open_positions:
            # Get the quantity
            quantity = self.positions[symbol]
            if quantity == 0:
                continue

            # Get the last price for the symbol
            last_price = self._get_last_price(symbol)
            if not last_price:
                self.logger.warning(f"No price data for {symbol} to close position")
                continue

            # Find open trades for this symbol
            open_trades = self.trade_repository.get_open_trades(symbol)
            if not open_trades:
                self.logger.warning(f"No open trades found for {symbol} despite open position")
                continue

            # Close trades
            for trade in open_trades:
                trade_id = trade.get('id')
                try:
                    # Use the trade repository to close the trade
                    closed_trade = self.trade_repository.close_trade(
                        trade_id=trade_id,
                        close_price=last_price,
                        close_time=timestamp
                    )

                    if closed_trade:
                        closed_trades.append(closed_trade)
                        # Update realized PnL tracking
                        self.realized_pnl += closed_trade.get('pnl', 0.0)

                        # Log the trade close
                        self.logger.info(f"Closed trade {trade_id} at {last_price:.2f} with PnL {closed_trade.get('pnl', 0.0):.2f}")

                        # Set position to zero - this position is now closed
                        self.positions[symbol] = 0

                        # Publish trade close event for subscribers
                        self.event_bus.publish(Event(
                            EventType.TRADE_CLOSE,
                            closed_trade
                        ))
                except Exception as e:
                    self.logger.error(f"Error closing trade {trade_id}: {e}")

        # Update portfolio state
        total_closed_pnl = sum(t.get('pnl', 0) for t in closed_trades if t.get('pnl') is not None)
        self._publish_update(timestamp, closed_pnl=self.realized_pnl, open_value=0)

        self.logger.info(f"Closed {len(closed_trades)} trades with total PnL: {total_closed_pnl:.2f}")

        return closed_trades

    def add_trade(self, trade):
        """
        Add a trade to the portfolio.

        Args:
            trade (dict): Trade data

        Returns:
            bool: True if the trade was added successfully
        """
        if self.trade_repository:
            try:
                self.trade_repository.add_trade(trade)
                self.logger.info(f"Trade added to repository: {trade.get('id')}")
                return True
            except Exception as e:
                self.logger.error(f"Error adding trade to repository: {e}")
                return False
        else:
            self.logger.warning("No trade repository available")
            # Add trade to a local collection if no repository
            if not hasattr(self, 'trades'):
                self.trades = []
            self.trades.append(trade)
            self.logger.info(f"Trade stored locally: {trade.get('id')}")
            return True
