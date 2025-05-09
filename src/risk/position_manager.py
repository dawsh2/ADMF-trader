"""
Position Manager for enforcing risk management rules.

This component enforces position limits and ensures consistent position
management across the system, preventing state leakage and duplicate positions.
"""

import logging
from src.core.component import Component
from src.core.event_bus import Event, EventType

class PositionManager(Component):
    """
    Position Manager that enforces risk management rules.
    
    Responsibilities:
    1. Enforce maximum number of allowed positions
    2. Block duplicate positions for the same symbol
    3. Manage position sizing based on risk parameters
    4. Coordinate with BacktestState to ensure proper state isolation
    """
    
    def __init__(self, name, config=None):
        """
        Initialize the position manager.
        
        Args:
            name (str): Component name
            config (dict): Configuration parameters
        """
        super().__init__(name)
        self.config = config or {}
        
        # Extract configuration parameters
        self.max_positions = self.config.get('max_positions', 1)  # Default to 1 position
        self.fixed_quantity = self.config.get('fixed_quantity', 100)  # Default to 100 shares
        self.enforce_single_position = self.config.get('enforce_single_position', True)
        
        # Internal state tracking
        self.active_signals = {}  # symbol -> {direction, rule_id}
        self.active_positions = {}  # symbol -> {quantity, direction, rule_id}
        self.position_counts = {'LONG': 0, 'SHORT': 0, 'TOTAL': 0}
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Position Manager initialized with max_positions={self.max_positions}, "
                        f"enforce_single_position={self.enforce_single_position}")
        
    def initialize(self, context):
        """
        Initialize with dependencies.
        
        Args:
            context (dict): Context containing dependencies
        """
        super().initialize(context)
        
        # Store references to required components
        self.event_bus = context.get('event_bus')
        self.trade_repository = context.get('trade_repository')
        
        if not self.event_bus:
            raise ValueError("PositionManager requires event_bus in context")
            
        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.SIGNAL, self.on_signal)
        self.event_bus.subscribe(EventType.PORTFOLIO_UPDATE, self.on_portfolio_update)
        self.event_bus.subscribe(EventType.TRADE_OPEN, self.on_trade_open)
        self.event_bus.subscribe(EventType.TRADE_CLOSE, self.on_trade_close)
        
        self.logger.info("Position Manager successfully initialized and subscribed to events")
        
    def on_signal(self, event):
        """
        Process incoming signals, enforcing position limits.
        
        Args:
            event (Event): Signal event
        """
        signal_data = event.get_data()
        
        # Extract signal information
        symbol = signal_data.get('symbol')
        direction = signal_data.get('direction')
        rule_id = signal_data.get('rule_id')
        
        self.logger.debug(f"Processing signal: symbol={symbol}, direction={direction}, rule_id={rule_id}")
        
        # Check if this is a duplicate signal
        if symbol in self.active_signals and self.active_signals[symbol]['rule_id'] == rule_id:
            self.logger.warning(f"Ignoring duplicate signal for {symbol} with rule_id {rule_id}")
            return
            
        # Check if we're at the position limit
        if (self.position_counts['TOTAL'] >= self.max_positions and 
                symbol not in self.active_positions):
            self.logger.warning(f"Ignoring signal for {symbol} - already at max positions ({self.max_positions})")
            return
            
        # Check if we already have a position in this symbol
        if symbol in self.active_positions:
            existing_direction = self.active_positions[symbol]['direction']
            
            # If the direction is the same, ignore this signal (duplicate)
            if direction == existing_direction:
                self.logger.warning(f"Ignoring redundant {direction} signal for {symbol} - already in that position")
                return
                
            # If enforce_single_position is True, we'll allow the position to be closed
            # and potentially reversed. Otherwise, we maintain only one position per symbol.
            if not self.enforce_single_position and direction != existing_direction:
                self.logger.warning(f"Ignoring contrary {direction} signal for {symbol} - enforcing single position")
                return
                
        # Update active signals tracker
        self.active_signals[symbol] = {
            'direction': direction,
            'rule_id': rule_id
        }
        
        # Adjust signal quantity based on position management rules
        original_quantity = signal_data.get('quantity', self.fixed_quantity)
        adjusted_quantity = self._calculate_position_size(symbol, direction, original_quantity)
        
        if adjusted_quantity == 0:
            self.logger.info(f"No position adjustment needed for {symbol}")
            return
            
        # Create a new signal with adjusted quantity
        modified_signal_data = signal_data.copy()
        modified_signal_data['quantity'] = adjusted_quantity
        
        # Log the modification
        self.logger.info(f"Modified signal for {symbol}: direction={direction}, "
                       f"quantity adjusted from {original_quantity} to {adjusted_quantity}")
        
        # Generate and publish an order event
        order_data = {
            'symbol': symbol,
            'quantity': adjusted_quantity,
            'direction': direction,
            'type': 'MARKET',  # Default to market orders
            'price': modified_signal_data.get('price', 0),
            'rule_id': rule_id,
            'timestamp': modified_signal_data.get('timestamp')
        }
        
        # Log the order generation
        self.logger.info(f"Generating order for {symbol}: direction={direction}, quantity={adjusted_quantity}")
        
        # Publish the order event
        self.event_bus.publish(Event(
            EventType.ORDER,
            order_data
        ))
        
    def on_portfolio_update(self, event):
        """
        Update internal position tracking based on portfolio updates.
        
        Args:
            event (Event): Portfolio update event
        """
        portfolio_data = event.get_data()
        positions = portfolio_data.get('positions', {})
        
        # Update internal position tracking
        for symbol, quantity in positions.items():
            if quantity != 0:
                # Determine direction from quantity
                direction = 'LONG' if quantity > 0 else 'SHORT'
                
                # Update or create position record
                if symbol not in self.active_positions:
                    # This is a new position
                    self.active_positions[symbol] = {
                        'quantity': abs(quantity),
                        'direction': direction,
                        'rule_id': self.active_signals.get(symbol, {}).get('rule_id', 'unknown')
                    }
                    
                    # Update position counts
                    self.position_counts[direction] += 1
                    self.position_counts['TOTAL'] += 1
                    
                    self.logger.info(f"New position tracked: {symbol}, {direction}, quantity={abs(quantity)}, "
                                   f"total positions={self.position_counts['TOTAL']}")
                else:
                    # Update existing position
                    old_direction = self.active_positions[symbol]['direction']
                    old_quantity = self.active_positions[symbol]['quantity']
                    
                    # If direction changed, update counters
                    if old_direction != direction:
                        self.position_counts[old_direction] -= 1
                        self.position_counts[direction] += 1
                        
                        self.logger.info(f"Position direction changed for {symbol}: {old_direction} -> {direction}")
                        
                    # Update quantity
                    self.active_positions[symbol]['quantity'] = abs(quantity)
                    self.active_positions[symbol]['direction'] = direction
                    
                    self.logger.debug(f"Updated position for {symbol}: {direction}, quantity={abs(quantity)}, "
                                   f"total positions={self.position_counts['TOTAL']}")
            elif symbol in self.active_positions:
                # Position was closed
                direction = self.active_positions[symbol]['direction']
                
                # Update counters
                self.position_counts[direction] -= 1
                self.position_counts['TOTAL'] -= 1
                
                # Remove from active positions
                del self.active_positions[symbol]
                
                self.logger.info(f"Position closed for {symbol}, remaining positions={self.position_counts['TOTAL']}")
                
    def on_trade_open(self, event):
        """
        Update internal state when a trade is opened.
        
        Args:
            event (Event): Trade open event
        """
        trade_data = event.get_data()
        symbol = trade_data.get('symbol')
        direction = trade_data.get('direction')
        
        self.logger.debug(f"Trade opened: {symbol}, {direction}")
        
    def on_trade_close(self, event):
        """
        Update internal state when a trade is closed.
        
        Args:
            event (Event): Trade close event
        """
        trade_data = event.get_data()
        symbol = trade_data.get('symbol')
        
        self.logger.debug(f"Trade closed: {symbol}")
        
        # We'll rely on portfolio updates for accurate position tracking
        
    def _calculate_position_size(self, symbol, direction, requested_quantity):
        """
        Calculate the appropriate position size based on risk rules.
        
        Args:
            symbol (str): Instrument symbol
            direction (str): Position direction ('LONG' or 'SHORT')
            requested_quantity (float): Requested position size
            
        Returns:
            float: Adjusted position size
        """
        # If we're enforcing a fixed quantity
        if self.config.get('position_sizing_method') == 'fixed':
            return self.fixed_quantity
            
        # If we already have a position in this symbol, handle it
        if symbol in self.active_positions:
            existing_direction = self.active_positions[symbol]['direction']
            existing_quantity = self.active_positions[symbol]['quantity']
            
            # If same direction, no action needed
            if direction == existing_direction:
                return 0
                
            # If opposite direction, close the position (set quantity to existing quantity)
            return existing_quantity
            
        # For new positions, use the specified quantity or fixed quantity
        return requested_quantity if requested_quantity > 0 else self.fixed_quantity
        
    def configure(self, config):
        """
        Update configuration.
        
        Args:
            config (dict): New configuration parameters
        """
        self.config.update(config)
        
        # Update parameters
        self.max_positions = self.config.get('max_positions', self.max_positions)
        self.fixed_quantity = self.config.get('fixed_quantity', self.fixed_quantity)
        self.enforce_single_position = self.config.get('enforce_single_position', self.enforce_single_position)
        
        self.logger.info(f"Position Manager reconfigured: max_positions={self.max_positions}, "
                       f"fixed_quantity={self.fixed_quantity}, "
                       f"enforce_single_position={self.enforce_single_position}")
        
    def reset(self):
        """Reset the component state."""
        super().reset()
        
        # Reset state tracking
        self.active_signals = {}
        self.active_positions = {}
        self.position_counts = {'LONG': 0, 'SHORT': 0, 'TOTAL': 0}
        
        self.logger.info("Position Manager reset")
