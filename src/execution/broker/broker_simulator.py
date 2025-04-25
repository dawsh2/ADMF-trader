# src/execution/broker/simulated_broker.py
from .broker_base import BrokerBase
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_fill_event
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

    # Fix for broker handling in src/execution/broker/broker_simulator.py
    def on_order(self, order_event):
        """
        Handle order events.

        Args:
            order_event: Order event to process
        """
        try:
            # Process the order
            fill_event = self.process_order(order_event)

            # If a fill was generated, emit it
            if fill_event and self.event_bus:
                # Wait a brief moment to ensure order is processed first
                import time
                time.sleep(0.01)

                # Emit the fill event
                self.event_bus.emit(fill_event)
        except Exception as e:
            logger.error(f"Error processing order event: {e}", exc_info=True)    


            
    #     """
    #     Handle order events.

    #     Args:
    #         order_event: Order event to process
    #     """
    #     try:
    #         # Check if this is a proper OrderEvent or a status update
    #         if not hasattr(order_event, 'get_symbol') or not hasattr(order_event, 'get_direction'):
    #             # This might be a status update or other type of event
    #             if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
    #                 if order_event.data.get('status_update'):
    #                     # This is a status update, skip processing
    #                     logger.debug(f"Received order status update, skipping broker processing")
    #                     return
    #             logger.warning(f"Received invalid order event in broker, skipping")
    #             return

    #         # Process the order
    #         fill_event = self.process_order(order_event)

    #         # Emit fill event if order was filled
    #         if fill_event and self.event_bus:
    #             self.event_bus.emit(fill_event)
    #             logger.info(f"Broker emitted fill event for {order_event.get_symbol()}")
    #     except Exception as e:
    #         self.stats['errors'] += 1
    #         logger.error(f"Error in broker on_order: {e}", exc_info=True)

    # Fixed process_order method for src/execution/broker/broker_simulator.py
    # Modify process_order in SimulatedBroker class
    # Update the SimulatedBroker.process_order method

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

            # Extract order ID from event data
            order_id = order_event.data.get('order_id')

            # Apply slippage to price
            if direction == 'BUY':
                fill_price = price * (1.0 + self.slippage)
            else:  # SELL
                fill_price = price * (1.0 - self.slippage)

            # Calculate commission
            commission = abs(quantity * fill_price) * self.commission

            # Create fill event with the order_id
            from src.core.events.event_utils import create_fill_event

            fill_event = create_fill_event(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                price=fill_price,
                commission=commission,
                timestamp=order_event.get_timestamp()
            )

            # IMPORTANT: Set the order_id in the fill event's data
            if order_id:
                fill_event.data['order_id'] = order_id

            self.stats['fills_generated'] += 1
            logger.debug(f"Processed order: {direction} {quantity} {symbol} @ {fill_price:.2f}")

            logger.info(f"Broker emitted fill event for {symbol}")
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
