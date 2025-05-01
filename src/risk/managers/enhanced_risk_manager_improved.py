"""
Enhanced Risk Manager with explicit position handling.

This implementation:
1. Tracks current positions and their directions
2. Explicitly handles position closings and openings
3. Provides more detailed tracking through rule_id naming
4. Eliminates redundant signal grouping
"""
import logging
import datetime
from typing import Dict, Any, Optional, Set, List

from src.core.events.event_types import EventType, Event
from src.core.events.event_utils import create_order_event
from src.risk.managers.risk_manager_base import RiskManagerBase

logger = logging.getLogger(__name__)

class EnhancedRiskManager(RiskManagerBase):
    """
    Enhanced risk manager with explicit position transition handling.
    
    This risk manager:
    1. Receives filtered signals from strategies
    2. Explicitly handles position transitions (open, close)
    3. Maintains clear state for current positions
    4. Generates unique rule IDs with descriptive action types
    5. Calculates position sizes based on risk parameters
    """
    
    def __init__(self, event_bus, portfolio_manager, name=None):
        """
        Initialize the enhanced risk manager.
        
        Args:
            event_bus: Event bus for communication
            portfolio_manager: PortfolioManager instance for position information
            name: Optional name for the risk manager
        """
        super().__init__(event_bus, portfolio_manager, name)
        
        # Risk parameters (will be loaded from config)
        self.position_sizing_method = 'fixed'  # 'fixed', 'percent_equity', 'percent_risk'
        self.position_size = 100  # Fixed position size
        self.equity_percent = 5.0  # Percentage of equity per position (if using percent_equity)
        self.risk_percent = 2.0    # Percentage of equity at risk per position (if using percent_risk)
        self.max_position_size = 1000  # Maximum position size
        self.default_stop_percent = 2.0  # Default stop loss percentage for percent_risk sizing
        
        # Track processed rule IDs to prevent duplicates
        self.processed_rule_ids = set()
        
        logger.info(f"Enhanced risk manager {self.name} initialized")
    
    def configure(self, config):
        """
        Configure the risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        super().configure(config)
        
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        # Load risk parameters from config
        self.position_sizing_method = config_dict.get('position_sizing_method', self.position_sizing_method)
        self.position_size = config_dict.get('position_size', self.position_size)
        self.equity_percent = config_dict.get('equity_percent', self.equity_percent)
        self.risk_percent = config_dict.get('risk_percent', self.risk_percent)
        self.max_position_size = config_dict.get('max_position_size', self.max_position_size)
        self.default_stop_percent = config_dict.get('default_stop_percent', self.default_stop_percent)
        
        logger.info(f"Risk manager {self.name} configured with: {config_dict}")
    
    def _get_position_direction(self, symbol):
        """
        Determine current position direction from portfolio.
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            int: Current position direction (1 for long, -1 for short, 0 for flat)
        """
        position = self.portfolio_manager.get_position(symbol)
        if position is None or position.quantity == 0:
            return 0  # Flat
        return 1 if position.quantity > 0 else -1  # Long or Short
    
    def _get_position_size(self, symbol):
        """
        Get the current position size from portfolio.
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            float: Current position size (absolute value)
        """
        position = self.portfolio_manager.get_position(symbol)
        if position is None:
            return 0.0
        return abs(position.quantity)
    
    def on_signal(self, signal_event):
        """
        Process a signal event and create orders when direction changes.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            List of order events or empty list if no action needed
        """
        # Check if this event has already been consumed
        if signal_event.is_consumed():
            logger.debug(f"Skipping already consumed signal event with ID: {signal_event.get_id()}")
            return []
            
        # Mark this event as consumed to prevent duplicate processing
        signal_event.mark_consumed()
        
        # Extract signal details
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        timestamp = signal_event.get_timestamp()
        
        # Log the received signal
        logger.info(f"Received signal: {symbol} direction={signal_value} at {price}")
        
        # Track this signal event for analytics
        self.event_tracker.track_event(signal_event)
        self.stats['signals_processed'] += 1
        
        # Get current position direction from portfolio
        current_direction = self._get_position_direction(symbol)
        
        # Only act if signal differs from current position
        if signal_value != current_direction:
            # Handle the direction change explicitly
            trading_decisions = self.handle_direction_change(
                symbol, current_direction, signal_value, price, timestamp)
            
            # Track orders generated
            if trading_decisions:
                self.stats['orders_generated'] += len(trading_decisions)
                
            return trading_decisions
        
        # Log when we're not acting on a signal
        logger.info(f"No action for {symbol} signal {signal_value}, matches current position {current_direction}")
        
        return []
    
    def size_position(self, signal_event):
        """
        Calculate position size for a signal event.
        
        Implements abstract method from RiskManagerBase.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            float: Position size (positive for buy, negative for sell)
        """
        # Extract signal details
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        
        # Calculate base position size
        position_size = self._calculate_position_size(symbol, price)
        
        # Apply direction
        if signal_value < 0:
            position_size = -position_size
            
        return position_size
    
    def handle_direction_change(self, symbol, current_direction, new_direction, price, timestamp):
        """
        Handle a change in position direction explicitly.
        
        Args:
            symbol: Trading symbol
            current_direction: Current position direction (1, -1, or 0)
            new_direction: New position direction (1, -1, or 0)
            price: Current price
            timestamp: Signal timestamp
            
        Returns:
            List of trading decisions
        """
        actions = []
        timestamp_str = timestamp.strftime('%Y%m%d%H%M%S')
        
        # Close existing position if any
        if current_direction != 0:
            close_size = self._get_position_size(symbol)
            close_direction = "BUY" if current_direction < 0 else "SELL"
            rule_id = f"{symbol}_{close_direction}_CLOSE_{timestamp_str}"
            
            # Skip if we've already processed this rule_id
            if rule_id not in self.processed_rule_ids:
                self.processed_rule_ids.add(rule_id)
                
                # Create the closing trading decision
                close_decision = self._create_trading_decision(
                    symbol, close_direction, close_size, price, timestamp, rule_id, "CLOSE")
                
                if close_decision:
                    actions.append(close_decision)
                    logger.info(f"Closing position: {close_direction} {close_size} {symbol} @ {price}, rule_id={rule_id}")
        
        # Open new position if new direction is not neutral
        if new_direction != 0:
            # Calculate new position size
            open_size = self._calculate_position_size(symbol, price)
            open_direction = "BUY" if new_direction > 0 else "SELL"
            rule_id = f"{symbol}_{open_direction}_OPEN_{timestamp_str}"
            
            # Skip if we've already processed this rule_id
            if rule_id not in self.processed_rule_ids:
                self.processed_rule_ids.add(rule_id)
                
                # Create the opening trading decision
                open_decision = self._create_trading_decision(
                    symbol, open_direction, open_size, price, timestamp, rule_id, "OPEN")
                
                if open_decision:
                    actions.append(open_decision)
                    logger.info(f"Opening position: {open_direction} {open_size} {symbol} @ {price}, rule_id={rule_id}")
        
        return actions
    
    def _calculate_position_size(self, symbol, price):
        """
        Calculate position size based on risk parameters.
        
        Args:
            symbol: Instrument symbol
            price: Current price
            
        Returns:
            float: Position size
        """
        # Calculate target position size based on sizing method
        if self.position_sizing_method == 'fixed':
            # Fixed position size
            target_size = self.position_size
            
        elif self.position_sizing_method == 'percent_equity':
            # Size based on percentage of equity
            equity = self.portfolio_manager.equity
            equity_fraction = self.equity_percent / 100.0
            target_value = equity * equity_fraction
            target_size = int(target_value / price) if price > 0 else 0
            
        elif self.position_sizing_method == 'percent_risk':
            # Size based on risk percentage
            equity = self.portfolio_manager.equity
            risk_amount = equity * (self.risk_percent / 100.0)
            stop_price = price * (1.0 - self.default_stop_percent / 100.0)
            risk_per_unit = abs(price - stop_price)
            
            # Check for zero division
            target_size = int(risk_amount / risk_per_unit) if risk_per_unit > 0 else 0
            
        else:
            logger.warning(f"Unknown position sizing method: {self.position_sizing_method}")
            target_size = 0
        
        # Apply maximum position size limit
        target_size = min(target_size, self.max_position_size)
        
        return float(target_size)
    
    def _create_trading_decision(self, symbol, direction, size, price, timestamp, rule_id, action_type):
        """
        Create a trading decision to send to the order manager.
        
        Args:
            symbol: Instrument symbol
            direction: Trade direction ("BUY" or "SELL")
            size: Position size
            price: Current price
            timestamp: Signal timestamp
            rule_id: Rule ID for tracking
            action_type: Action type ("OPEN" or "CLOSE")
            
        Returns:
            Order event with trading decision information
        """
        if size == 0:
            return None
        
        # Create order data with essential information
        order_data = {
            'symbol': symbol,
            'direction': direction,
            'quantity': abs(float(size)),
            'price': price,
            'timestamp': timestamp,
            'rule_id': rule_id,
            'action_type': action_type
        }
        
        # Create order event
        order_event = Event(EventType.ORDER, order_data, timestamp)
        
        # Emit order event
        logger.info(f"Trading decision: {direction} {abs(float(size))} {symbol} @ {price}, " + 
                   f"rule_id={rule_id}, timestamp={timestamp.strftime('%Y-%m-%d %H:%M:%S')}, " +
                   f"action={action_type}")
        self.event_bus.emit(order_event)
        
        return order_event
    
    def reset(self):
        """Reset risk manager state."""
        super().reset()
        # Reset processed rule IDs
        self.processed_rule_ids.clear()
        logger.debug(f"Risk manager {self.name} reset")
