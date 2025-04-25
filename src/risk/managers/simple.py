# src/risk/managers/simple.py
from src.risk.managers.risk_manager_base import RiskManagerBase
from src.core.events.event_utils import create_order_event
import logging

logger = logging.getLogger(__name__)

class SimpleRiskManager(RiskManagerBase):
    """Simple implementation of a risk manager with fixed position sizing."""
    
    def __init__(self, event_bus, portfolio_manager, name=None):
        """Initialize simple risk manager."""
        super().__init__(event_bus, portfolio_manager, name)
        self.position_size = 100  # Default fixed position size
        self.max_position_pct = 0.2  # Max 20% of equity per position
    
    def on_signal(self, signal_event):
        """
        Handle signal events and create orders.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            Order event or None
        """
        # Extract signal details
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        timestamp = signal_event.get_timestamp()
        
        # Skip neutral signals
        if signal_value == 0:
            logger.info(f"Neutral signal for {symbol}, skipping")
            self.stats['signals_filtered'] += 1
            return None
        
        # Determine direction from signal
        direction = 'BUY' if signal_value > 0 else 'SELL'
        
        # Calculate position size with risk limits
        size = self.size_position(signal_event)
        
        # Skip if size is zero
        if size == 0:
            logger.info(f"Signal for {symbol} resulted in zero size, skipping")
            self.stats['signals_filtered'] += 1
            return None
        
        # Check current position to avoid excessive exposure
        current_position = self.portfolio_manager.get_position(symbol)
        current_qty = current_position.quantity if current_position else 0
        
        # For SELL signals, don't sell more than we own 
        if direction == 'SELL' and abs(size) > abs(current_qty) and current_qty > 0:
            logger.info(f"Reducing SELL size from {size} to {current_qty} for {symbol}")
            size = -current_qty  # Only sell what we have
        
        # For BUY signals, check portfolio value limits
        if direction == 'BUY':
            # Calculate position value
            position_value = abs(size) * price
            max_position_value = self.portfolio_manager.equity * self.max_position_pct
            
            if position_value > max_position_value:
                # Scale down the position to respect limits
                adjusted_size = int(max_position_value / price)
                logger.info(f"Reducing BUY size from {size} to {adjusted_size} for {symbol} (value limit)")
                size = adjusted_size
        
        # Skip if adjusted size is zero
        if size == 0:
            logger.info(f"Adjusted signal for {symbol} resulted in zero size, skipping")
            self.stats['signals_filtered'] += 1
            return None
        
        # Create order event
        order = create_order_event(
            symbol=symbol,
            order_type='MARKET',
            direction=direction,
            quantity=abs(size),  # Quantity is always positive
            price=price,
            timestamp=timestamp
        )
        
        # Emit order event
        if self.event_bus:
            self.event_bus.emit(order)
            self.stats['orders_generated'] += 1
            logger.info(f"Created order: {direction} {abs(size)} {symbol} @ {price:.2f}")
        else:
            logger.warning(f"No event bus available, order not emitted")
        
        return order
    
    def size_position(self, signal_event):
        """
        Calculate position size for a signal using fixed size.
        
        Args:
            signal_event: Signal event to size
            
        Returns:
            int: Position size (positive or negative)
        """
        signal_value = signal_event.get_signal_value()
        
        # Calculate available cash for buying
        if signal_value > 0 and hasattr(self.portfolio_manager, 'cash'):
            price = signal_event.get_price()
            if price > 0:
                # Limit position size based on available cash (80% of cash)
                max_size = int((self.portfolio_manager.cash * 0.8) / price)
                # Use the smaller of fixed size or cash-constrained size
                size = min(self.position_size, max_size)
                if size < self.position_size:
                    logger.info(f"Cash-limited position size: {size} (original: {self.position_size})")
                return size
        
        # Apply direction to position size
        if signal_value > 0:
            return self.position_size
        elif signal_value < 0:
            return -self.position_size
        else:
            return 0
    
    def configure(self, config):
        """
        Configure the risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        super().configure(config)
        
        # Extract parameters from config
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        # Set position size if provided
        if 'position_size' in config_dict:
            self.position_size = config_dict['position_size']
            
        # Set max position percentage if provided
        if 'max_position_pct' in config_dict:
            self.max_position_pct = config_dict['max_position_pct']
