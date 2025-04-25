# src/execution/broker/simulated_broker.py
from .broker_base import BrokerBase
from core.events.event_types import EventType
from core.events.event_utils import create_fill_event
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SimulatedBroker(BrokerBase):
    """Simulated broker for executing orders in backtests."""
    
    def __init__(self, event_bus, name="simulated_broker"):
        """
        Initialize simulated broker.
        
        Args:
            event_bus: Event bus for communication
            name: Broker name
        """
        super().__init__(name)
        self.event_bus = event_bus
        
        # Default parameters
        self.slippage = 0.0  # Percentage slippage
        self.commission = 0.0  # Percentage commission
        
        # Register for events
        self.event_bus.register(EventType.ORDER, self.on_order)
    
    def configure(self, config):
        """
        Configure the broker.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config = config.as_dict()
            
        self.slippage = config.get('slippage', 0.0)
        self.commission = config.get('commission', 0.0)
        self.initialized = True
    
    def on_order(self, order_event):
        """
        Handle order events.
        
        Args:
            order_event: Order event to process
        """
        fill_event = self.process_order(order_event)
        if fill_event:
            self.event_bus.emit(fill_event)
    
    def process_order(self, order_event):
        """
        Process an order event.
        
        Args:
            order_event: Order event to process
            
        Returns:
            Fill event or None
        """
        self.stats['orders_processed'] += 1
        
        try:
            symbol = order_event.get_symbol()
            direction = order_event.get_direction()
            quantity = order_event.get_quantity()
            price = order_event.get_price()
            
            # Apply slippage to price
            if direction == 'BUY':
                fill_price = price * (1.0 + self.slippage)
            else:  # SELL
                fill_price = price * (1.0 - self.slippage)
            
            # Calculate commission
            commission = abs(quantity * fill_price) * self.commission
            
            # Create fill event
            fill_event = create_fill_event(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                price=fill_price,
                commission=commission,
                timestamp=order_event.get_timestamp()
            )
            
            self.stats['fills_generated'] += 1
            logger.debug(f"Processed order: {direction} {quantity} {symbol} @ {fill_price:.2f}")
            
            return fill_event
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error processing order: {e}")
            return None
    
    def get_account_info(self):
        """
        Get account information.
        
        Returns:
            Dict with account info
        """
        return {
            'broker': self.name,
            'account_id': 'simulated',
            'stats': self.get_stats()
        }
