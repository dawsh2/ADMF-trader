# src/risk/managers/simple.py
import logging
from typing import Dict, Any, Optional

from src.core.events.event_types import EventType
from src.core.events.event_utils import create_order_event
from src.risk.managers.risk_manager_base import RiskManagerBase

logger = logging.getLogger(__name__)

class SimpleRiskManager(RiskManagerBase):
    """Simple implementation of a risk manager with fixed position sizing and cash limits."""
    
    def __init__(self, event_bus, portfolio_manager, name=None):
        """Initialize simple risk manager."""
        super().__init__(event_bus, portfolio_manager, name)
        self.position_size = 100  # Default fixed position size
        self.max_position_pct = 0.1  # Maximum 10% of equity per position
        self.order_ids = set()  # Track created order IDs to avoid duplicates
    
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
            
        # Set parameters if provided
        self.position_size = config_dict.get('position_size', 100)
        self.max_position_pct = config_dict.get('max_position_pct', 0.1)
        
        logger.info(f"Risk manager configured with position_size={self.position_size}, max_position_pct={self.max_position_pct}")
    
    def on_signal(self, signal_event):
        """
        Handle signal events and create orders with proper position sizing.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            Order event or None
        """
        # Increment stats
        self.stats['signals_processed'] += 1
        
        # Extract signal details
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        timestamp = signal_event.get_timestamp()
        
        logger.debug(f"Processing signal: {signal_value} for {symbol} at {price:.2f}")
        
        # Skip neutral signals
        if signal_value == 0:
            self.stats['signals_filtered'] += 1
            logger.debug(f"Neutral signal for {symbol}, no order created")
            return None
        
        # Determine direction
        direction = 'BUY' if signal_value > 0 else 'SELL'
        
        # Calculate position size
        size = self.size_position(signal_event)
        
        # Skip if size is zero
        if size == 0:
            self.stats['signals_filtered'] += 1
            logger.debug(f"Signal for {symbol} resulted in zero size, skipping")
            return None
        
        try:
            # Create order event with order_id built from signal info for traceability
            import uuid
            order_id = str(uuid.uuid4())
            
            # Ensure we don't emit duplicate order for the same signal
            sig_id = f"{symbol}_{direction}_{timestamp.isoformat()}"
            if sig_id in self.order_ids:
                logger.debug(f"Skipping duplicate signal processing for {sig_id}")
                return None
                
            self.order_ids.add(sig_id)
            
            # Create order event
            order_event = create_order_event(
                symbol=symbol,
                order_type='MARKET',
                direction=direction,
                quantity=abs(size),
                price=price,
                timestamp=timestamp
            )
            
            # Add order ID to the event data
            order_event.data['order_id'] = order_id
            
            # Emit order event
            if self.event_bus:
                self.event_bus.emit(order_event)
                self.stats['orders_generated'] += 1
                logger.info(f"Created order: {direction} {abs(size)} {symbol} @ {price:.2f}")
            
            return order_event
        except Exception as e:
            logger.error(f"Error creating order: {e}", exc_info=True)
            self.stats['errors'] += 1
            return None
    
    def size_position(self, signal_event):
        """
        Calculate position size based on signal and portfolio constraints.
        
        Args:
            signal_event: Signal event to size
            
        Returns:
            int: Position size (positive or negative)
        """
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        
        # Start with base position size in direction of signal
        base_size = self.position_size if signal_value > 0 else -self.position_size
        
        # For BUY orders, check cash and position limits
        if signal_value > 0:
            # 1. Check cash limits
            available_cash = self.portfolio_manager.cash * 0.95  # Use 95% of available cash
            max_cash_size = int(available_cash / price) if price > 0 else 0
            
            if max_cash_size < self.position_size:
                logger.info(f"Cash-limited position size: {max_cash_size} (original: {self.position_size})")
                
            # 2. Check position value limit (% of equity)
            max_position_value = self.portfolio_manager.equity * self.max_position_pct
            max_position_size = int(max_position_value / price) if price > 0 else 0
            
            if max_position_size < self.position_size:
                logger.info(f"Reducing BUY size from {self.position_size} to {max_position_size} for {symbol} (value limit)")
            
            # Use most restrictive limit
            limited_size = min(self.position_size, max_cash_size, max_position_size)
            
            # Ensure minimum position size (avoid tiny orders)
            if 0 < limited_size < 10:
                logger.debug(f"Position size too small ({limited_size}), skipping")
                return 0
                
            return limited_size
            
        # For SELL orders
        else:
            # Check current position
            position = self.portfolio_manager.get_position(symbol)
            current_quantity = position.quantity if position else 0
            
            if current_quantity <= 0:
                logger.debug(f"No position to sell for {symbol}")
                return 0
                
            # Limit sell size to current position
            if abs(base_size) > current_quantity:
                logger.info(f"Reducing SELL size from {abs(base_size)} to {current_quantity} for {symbol}")
                return -current_quantity
                
            return base_size
    
    def reset(self):
        """Reset risk manager state."""
        super().reset()
        self.order_ids.clear()
        logger.info(f"Risk manager {self.name} reset")
