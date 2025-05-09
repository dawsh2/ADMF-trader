"""
Portfolio manager for tracking positions and equity.

This module provides classes for portfolio management, including cash, positions,
equity tracking, and performance metrics.
"""
import datetime
import uuid
import logging
import pandas as pd
from typing import Dict, Any, List, Optional, Union, Tuple
from collections import defaultdict

from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType
from src.risk.position import Position, PositionTracker

logger = logging.getLogger(__name__)

class PortfolioManager:
    """
    Portfolio manager for tracking positions, cash, and equity.
    
    Key features:
    - Track cash balance
    - Maintain position values
    - Calculate equity curve
    - Process fills to update portfolio state
    - Calculate portfolio returns
    - Generate portfolio-level events
    """
    
    def __init__(self, initial_cash: float = 10000.0, event_bus=None, name=None):
        """
        Initialize portfolio manager.
        
        Args:
            initial_cash: Initial cash balance
            event_bus: Optional event bus for emitting portfolio events
            name: Optional portfolio name
        """
        self._name = name or f"portfolio_{uuid.uuid4().hex[:8]}"
        self.event_bus = event_bus
        self.initial_cash = initial_cash
        self.cash = initial_cash
        
        # For compatibility with BacktestCoordinator which expects initial_capital
        self.initial_capital = initial_cash
        
        # Track trade history internally
        self.trades = []
        self.next_trade_id = 1
        
        # Initialize position tracker
        self.position_tracker = PositionTracker(event_bus)
        
        # Initialize equity tracking
        self.equity = initial_cash
        self.equity_curve = []
        self.equity_history = []
        
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
        
        # Processed fill IDs for deduplication
        self.processed_fill_ids = set()
        
        # Performance tracking
        self.peak_equity = initial_cash
        self.max_drawdown = 0.0
        self.max_drawdown_percent = 0.0
        
        # Register for events
        if self.event_bus:
            self.event_bus.subscribe(EventType.FILL, self.on_fill)
            self.event_bus.subscribe(EventType.BAR, self.on_bar)
    
    def initialize(self, context):
        """
        Initialize with dependencies from context.
        
        Args:
            context (dict): Shared context with dependencies
        """
        # Replace event bus if provided in context
        if 'event_bus' in context and not self.event_bus:
            self.event_bus = context['event_bus']
            self.event_bus.subscribe(EventType.FILL, self.on_fill)
            self.event_bus.subscribe(EventType.BAR, self.on_bar)
            logger.info(f"PortfolioManager {self._name} initialized with event bus from context")
            
        # We don't need to use the trade repository anymore
        # The portfolio manager now maintains its own trade history
            
    def start(self):
        """Start the portfolio manager operations."""
        logger.info(f"PortfolioManager {self._name} started")
        
    def stop(self):
        """Stop the portfolio manager operations."""
        logger.info(f"PortfolioManager {self._name} stopped")
        
    def get_trades(self):
        """
        Get all trades.
        
        Returns:
            list: All trades tracked by the portfolio
        """
        return self.trades.copy()
        
    def get_open_trades(self):
        """
        Get all open trades.
        
        Returns:
            list: Open trades
        """
        return [t for t in self.trades if not t.get('closed', False)]
        
    def get_closed_trades(self):
        """
        Get all closed trades.
        
        Returns:
            list: Closed trades
        """
        return [t for t in self.trades if t.get('closed', False)]
        
    def close_all_positions(self, timestamp=None):
        """
        Close all open positions at current market prices.
        
        Args:
            timestamp: Optional timestamp for the closing
            
        Returns:
            list: Trades that were closed
        """
        timestamp = timestamp or datetime.datetime.now()
        closed_trades = []
        
        # Process all open trades
        for trade in self.get_open_trades():
            symbol = trade['symbol']
            
            # Get current price for the symbol
            position = self.position_tracker.get_position(symbol)
            if not position or position.quantity == 0:
                # Position already closed somehow, just mark trade as closed
                trade['closed'] = True
                trade['exit_time'] = timestamp
                continue
                
            # Calculate exit price and PnL
            exit_price = position.current_price
            
            # Calculate PnL based on direction
            if trade['direction'] == 'BUY':  # Long position
                pnl = (exit_price - trade['entry_price']) * trade['quantity']
            else:  # Short position
                pnl = (trade['entry_price'] - exit_price) * trade['quantity']
                
            # Update trade record
            trade['exit_price'] = exit_price
            trade['exit_time'] = timestamp
            trade['closed'] = True
            trade['pnl'] = pnl
            
            # Add to closed trades
            closed_trades.append(trade)
            
            # Log the close
            logger.info(f"Closed position for {symbol} at {exit_price:.2f}, PnL: {pnl:.2f}")
            
        return closed_trades
        
    def reset(self):
        """Reset the portfolio manager state."""
        self.cash = self.initial_cash
        self.position_tracker.reset()
        self.equity = self.initial_cash
        self.equity_curve = []
        self.equity_history = []
        
        # Reset trade tracking
        self.trades = []
        self.next_trade_id = 1
        
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
        
        # Reset processed fill IDs
        self.processed_fill_ids = set()
        
        # Reset performance tracking
        self.peak_equity = self.initial_cash
        self.max_drawdown = 0.0
        self.max_drawdown_percent = 0.0
        
        # Ensure initial_capital is still consistent with initial_cash
        self.initial_capital = self.initial_cash
        
        logger.info(f"PortfolioManager {self._name} reset")
        
    def set_event_bus(self, event_bus):
        """
        Set the event bus.
        
        Args:
            event_bus: Event bus instance
        """
        self.event_bus = event_bus
        self.position_tracker.event_bus = event_bus
        
        # Register for events
        if self.event_bus:
            self.event_bus.subscribe(EventType.FILL, self.on_fill)
            self.event_bus.subscribe(EventType.BAR, self.on_bar)
    
    def on_fill(self, fill_event):
        """
        Handle fill events and update portfolio.
        
        Args:
            fill_event: Fill event to process
        """
        # Generate a unique ID for this fill to prevent duplicate processing
        fill_id = getattr(fill_event, 'id', None)
        if not fill_id:
            # Create a fill ID from its data
            fill_data = fill_event.data if hasattr(fill_event, 'data') else {}
            symbol = fill_data.get('symbol', 'UNKNOWN')
            direction = fill_data.get('direction', 'UNKNOWN')
            quantity = fill_data.get('quantity', fill_data.get('size', 0))
            fill_price = fill_data.get('price', fill_data.get('fill_price', 0.0))
            timestamp = getattr(fill_event, 'timestamp', datetime.datetime.now()).isoformat()
            fill_id = f"{symbol}_{direction}_{quantity}_{fill_price}_{timestamp}"
        
        # Check if we've already processed this fill
        if fill_id in self.processed_fill_ids:
            logger.debug(f"Fill {fill_id} already processed, skipping")
            return
        
        # Add to processed fills
        self.processed_fill_ids.add(fill_id)
        
        # Extract fill details
        fill_data = fill_event.data if hasattr(fill_event, 'data') else {}
        symbol = fill_data.get('symbol', 'UNKNOWN')
        direction = fill_data.get('direction', 'BUY')  # Default to BUY if not specified
        
        # Parse quantity and price
        try:
            # Try both 'quantity' and 'size' for compatibility
            quantity = float(fill_data.get('quantity', fill_data.get('size', 0)))
            if quantity <= 0:
                logger.warning(f"Skipping fill with zero or negative quantity: {quantity}")
                return
        except (ValueError, TypeError):
            logger.warning(f"Invalid quantity value in fill data: {fill_data}")
            quantity = 1  # Default to 1 if conversion fails
        
        try:
            # Try both 'price' and 'fill_price' for compatibility
            price = float(fill_data.get('price', fill_data.get('fill_price', 0.0)))
        except (ValueError, TypeError):
            logger.warning(f"Invalid price value in fill data: {fill_data}")
            price = 0.0  # Default to 0 if conversion fails
        
        try:
            commission = float(fill_data.get('commission', 0.0))
        except (ValueError, TypeError):
            logger.warning(f"Invalid commission value in fill data: {fill_data.get('commission')}")
            commission = 0.0  # Default to 0 if conversion fails
        
        timestamp = getattr(fill_event, 'timestamp', datetime.datetime.now())
        
        # Convert to position update 
        quantity_change = quantity if direction == 'BUY' else -quantity
        
        # Calculate trade value
        trade_value = price * abs(quantity_change)
        
        # Validate cash availability for buys
        if direction == 'BUY':
            if trade_value > self.cash:
                # Not enough cash
                logger.warning(f"Invalid trade: Insufficient cash: {self.cash:.2f} < {trade_value:.2f}, rejecting")
                return
        
        # Update position - this returns the PnL value
        position, realized_pnl = self.position_tracker.update_position(
            symbol, quantity_change, price, timestamp
        )
        
        # Update cash
        self.cash -= trade_value if direction == 'BUY' else -trade_value
        self.cash -= commission  # Deduct commission
        
        # Update statistics
        self.stats['trades_executed'] += 1
        self.stats['total_commission'] += commission
        self.stats['total_pnl'] += realized_pnl
        
        if direction == 'BUY':
            self.stats['long_trades'] += 1
        else:
            self.stats['short_trades'] += 1
        
        if realized_pnl > 0:
            self.stats['winning_trades'] += 1
        elif realized_pnl < 0:
            self.stats['losing_trades'] += 1
        else:
            self.stats['break_even_trades'] += 1
        
        # Update equity 
        self.update_equity(timestamp)
        
        # Log the fill
        logger.info(f"Fill: {direction} {quantity} {symbol} @ {price:.2f}, PnL: {realized_pnl:.2f}, Cash: {self.cash:.2f}, Equity: {self.equity:.2f}")
        
        # Record this as a trade for analytics
        trade_id = f"trade_{self.next_trade_id}"
        self.next_trade_id += 1
        
        # Create a trade record
        trade = {
            'id': trade_id,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'entry_price': price,
            'entry_time': timestamp,
            'exit_price': None,
            'exit_time': None,
            'commission': commission,
            'closed': False,
            'pnl': realized_pnl if realized_pnl != 0 else 0.0,  # Always provide a numeric PnL
            'rule_id': fill_data.get('rule_id')
        }
        
        # Add to trades list
        self.trades.append(trade)
        
        # Emit portfolio update event if event bus is available
        if self.event_bus:
            portfolio_event = Event(
                EventType.PORTFOLIO_UPDATE, 
                {
                    'portfolio_id': self._name,
                    'cash': self.cash,
                    'equity': self.equity,
                    'positions': self.get_positions_summary(),
                    'timestamp': timestamp
                }
            )
            self.event_bus.publish(portfolio_event)
    
    def on_bar(self, bar_event):
        """
        Handle bar events for mark-to-market updates.
        
        Args:
            bar_event: Bar event to process
        """
        # Get the bar data from the event object
        bar_data = bar_event.data if hasattr(bar_event, 'data') else {}
        
        symbol = bar_data.get('symbol', 'UNKNOWN')
        close_price = bar_data.get('close', 0.0)
        timestamp = getattr(bar_event, 'timestamp', datetime.datetime.now())
        
        # Mark position to market
        market_prices = {symbol: close_price}
        self.position_tracker.mark_to_market(market_prices, timestamp)
        
        # Update equity
        self.update_equity(timestamp)
    
    def update_market_data(self, market_prices: Dict[str, float], timestamp=None) -> float:
        """
        Update portfolio with current market prices.
        
        Args:
            market_prices: Dictionary mapping symbols to prices
            timestamp: Optional timestamp for the update
            
        Returns:
            float: Current equity
        """
        timestamp = timestamp or datetime.datetime.now()
        
        # Mark positions to market
        self.position_tracker.mark_to_market(market_prices, timestamp)
        
        # Update equity
        return self.update_equity(timestamp)
    
    def update_equity(self, timestamp=None) -> float:
        """
        Update portfolio equity with enhanced validation.
        
        Args:
            timestamp: Optional timestamp for the update
            
        Returns:
            float: Current equity value
        """
        timestamp = timestamp or datetime.datetime.now()
        
        try:
            # Get previous equity value for sanity checking
            previous_equity = self.equity
            
            # Calculate position value
            positions_value = sum(
                pos.get_market_value() for pos in self.position_tracker.positions.values()
            )
            
            # Calculate new equity
            new_equity = self.cash + positions_value
            
            # Sanity check for extreme changes
            equity_change = new_equity - previous_equity
            max_allowed_change = max(0.25 * abs(previous_equity), 10000)  # Allow 25% change or 10000, whichever is greater
            
            if abs(equity_change) > max_allowed_change and abs(previous_equity) > 1000:
                logger.warning(f"Suspicious equity change: {previous_equity:.2f} -> {new_equity:.2f} (change: {equity_change:.2f})")
                
                # Apply change limiting for stability
                if equity_change > 0:
                    new_equity = previous_equity + max_allowed_change
                    logger.warning(f"Limiting positive equity change to {max_allowed_change:.2f}")
                else:
                    new_equity = previous_equity - max_allowed_change
                    logger.warning(f"Limiting negative equity change to {max_allowed_change:.2f}")
            
            # Ensure equity doesn't go excessively negative
            if new_equity < -0.5 * self.initial_cash:
                logger.error(f"Severely negative equity calculated: {new_equity:.2f}, limiting to -50% of initial capital")
                new_equity = -0.5 * self.initial_cash
            
            # Apply sensible absolute limits
            max_equity = 10 * self.initial_cash  # 10x initial capital
            if abs(new_equity) > max_equity:
                logger.warning(f"Extreme equity value calculated: {new_equity:.2f}, capping to {max_equity:.2f}")
                if new_equity > 0:
                    new_equity = max_equity
                else:
                    new_equity = -max_equity * 0.5  # Allow less negative than positive
            
            # Update equity
            self.equity = new_equity
            
            # Record equity point
            equity_point = {
                'timestamp': timestamp,
                'equity': self.equity,
                'cash': self.cash,
                'positions_value': positions_value
            }
            self.equity_curve.append(equity_point)
            self.equity_history.append((timestamp, self.equity))
            
            # Update peak equity and drawdown
            if self.equity > self.peak_equity:
                self.peak_equity = self.equity
            
            current_drawdown = self.peak_equity - self.equity
            current_drawdown_percent = current_drawdown / self.peak_equity if self.peak_equity > 0 else 0
            
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
                
            if current_drawdown_percent > self.max_drawdown_percent:
                self.max_drawdown_percent = current_drawdown_percent
            
            return self.equity
            
        except Exception as e:
            logger.error(f"Error updating equity: {e}", exc_info=True)
            # Fallback to cash value
            self.equity = self.cash
            return self.cash
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position by symbol.
        
        Args:
            symbol: Position symbol
            
        Returns:
            Position object or None
        """
        return self.position_tracker.get_position(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """
        Get all positions.
        
        Returns:
            Dictionary of all positions
        """
        return self.position_tracker.get_all_positions()
        
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get positions in format expected by BacktestCoordinator.
        
        Returns:
            List of position dictionaries
        """
        # Convert positions to list of dictionaries with expected format
        return [
            {
                'symbol': symbol,
                'quantity': position.quantity,
                'price': position.average_price,
                'market_value': position.get_market_value(),
                'unrealized_pnl': position.unrealized_pnl
            }
            for symbol, position in self.position_tracker.get_all_positions().items()
        ]
    
    def get_positions_summary(self) -> List[Dict]:
        """
        Get summary of all positions.
        
        Returns:
            List of position dictionaries
        """
        return [pos.to_dict() for pos in self.position_tracker.get_all_positions().values()]
    
    def get_capital(self) -> float:
        """
        Get current portfolio capital/equity.
        
        Returns:
            float: Current equity value
        """
        return self.equity
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get portfolio summary.
        
        Returns:
            Dict with portfolio summary
        """
        position_metrics = self.position_tracker.get_position_metrics()
        
        return {
            'name': self._name,
            'cash': self.cash,
            'equity': self.equity,
            'initial_cash': self.initial_cash,
            'positions': len(self.position_tracker.get_all_positions()),
            'realized_pnl': position_metrics['total_realized_pnl'],
            'unrealized_pnl': position_metrics['total_unrealized_pnl'],
            'total_pnl': position_metrics['total_pnl'],
            'total_commission': self.stats['total_commission'],
            'trades_executed': self.stats['trades_executed'],
            'max_drawdown': self.max_drawdown,
            'max_drawdown_percent': self.max_drawdown_percent,
            'peak_equity': self.peak_equity,
            'long_exposure': position_metrics['long_exposure'],
            'short_exposure': position_metrics['short_exposure'],
            'net_exposure': position_metrics['net_exposure'],
            'exposure_ratio': position_metrics['gross_exposure'] / self.equity if self.equity > 0 else 0.0
        }
    
    def get_equity_curve_df(self) -> pd.DataFrame:
        """
        Get equity curve as DataFrame.
        
        Returns:
            DataFrame with equity curve
        """
        if not self.equity_curve:
            return pd.DataFrame(columns=['timestamp', 'equity', 'cash', 'positions_value'])
            
        df = pd.DataFrame(self.equity_curve)
        
        if not df.empty:
            df.set_index('timestamp', inplace=True)
            
        return df
    
    def get_returns(self) -> pd.Series:
        """
        Calculate return series from equity curve.
        
        Returns:
            Series with returns
        """
        equity_df = self.get_equity_curve_df()
        
        if equity_df.empty:
            return pd.Series()
            
        # Calculate returns
        returns = equity_df['equity'].pct_change().fillna(0)
        
        return returns
    
    def get_closed_trades(self) -> List[Dict]:
        """
        Get all closed trades.
        
        Returns:
            List of closed trade dictionaries
        """
        return self.position_tracker.get_all_closed_positions()
    
    def reset(self) -> None:
        """Reset portfolio to initial state."""
        self.cash = self.initial_cash
        self.position_tracker.reset()
        self.equity = self.initial_cash
        self.equity_curve = []
        self.equity_history = []
        self.processed_fill_ids.clear()
        
        # Reset peak equity and drawdown
        self.peak_equity = self.initial_cash
        self.max_drawdown = 0.0
        self.max_drawdown_percent = 0.0
        
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
        
        # Record initial equity point
        self.equity_curve.append({
            'timestamp': datetime.datetime.now(),
            'equity': self.equity,
            'cash': self.cash,
            'positions_value': 0.0
        })
        
        logger.info(f"Reset portfolio {self._name} to initial state with cash: ${self.initial_cash:.2f}")
        
        return self
    
    def configure(self, config):
        """
        Configure the portfolio.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        # Extract parameters from config
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        self.initial_cash = config_dict.get('initial_cash', 10000.0)
        self._name = config_dict.get('name', self._name)
        
        # Reset with new initial cash
        self.reset()
        
        logger.info(f"Configured portfolio {self._name} with initial cash: ${self.initial_cash:.2f}")
    
    @property
    def name(self):
        """Get portfolio name."""
        return self._name