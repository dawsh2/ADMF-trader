# src/execution/broker/broker_simulator.py
import logging
from typing import Dict, Any, Optional
from src.core.events.event_types import EventType
from src.core.events.event_utils import create_fill_event
from src.execution.broker.broker_base import BrokerBase

logger = logging.getLogger(__name__)

class SimulatedBroker(BrokerBase):
    """Simulated broker for executing orders in backtests."""
    
    def __init__(self, event_bus=None, name="simulated_broker"):
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
        
        # Tracking for processed orders to avoid duplicates
        self.processed_order_ids = set()
        
        # Register for events if event bus provided
        if self.event_bus:
            self.event_bus.register(EventType.ORDER, self.on_order)
    
    def configure(self, config):
        """
        Configure the broker.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        self.slippage = config_dict.get('slippage', 0.0)
        self.commission = config_dict.get('commission', 0.0)
        self.initialized = True
        
        logger.info(f"Broker configured with slippage={self.slippage}, commission={self.commission}")
    
    def set_event_bus(self, event_bus):
        """
        Set the event bus.
        
        Args:
            event_bus: Event bus instance
        """
        self.event_bus = event_bus
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.ORDER, self.on_order)


    def on_order(self, order_event):
        """
        Handle order events.

        Args:
            order_event: Order event to process
        """
        # Extract order ID from the order event
        order_id = None
        if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
            order_id = order_event.data.get('order_id')

        # Process the order
        fill_event = self.process_order(order_event)

        # If a fill was generated, emit it
        if fill_event and self.event_bus:
            self.event_bus.emit(fill_event)            
    # def on_order(self, order_event):
    #     """
    #     Handle order events.
        
    #     Args:
    #         order_event: Order event to process
    #     """
    #     # Track order ID to prevent duplicate processing
    #     order_id = None
    #     if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
    #         order_id = order_event.data.get('order_id')
            
    #     # Skip if already processed this order
    #     if order_id and order_id in self.processed_order_ids:
    #         logger.debug(f"Order {order_id} already processed by broker, skipping")
    #         return
            
    #     # Process order to get fill
    #     fill_event = self.process_order(order_event)
        
    #     # Emit fill event if created
    #     if fill_event and self.event_bus:
    #         # Keep track of order ID to prevent duplicate processing
    #         if order_id:
    #             self.processed_order_ids.add(order_id)
                
    #             # Make sure fill has the order ID for tracing
    #             if hasattr(fill_event, 'data') and isinstance(fill_event.data, dict):
    #                 fill_event.data['order_id'] = order_id
                    
    #         # Emit the fill event
    #         logger.info(f"Broker emitting fill event for {fill_event.get_symbol()}")
    #         self.event_bus.emit(fill_event)

    def process_order(self, order_event):
        """Process an order event."""
        self.stats['orders_processed'] += 1

        try:
            # Extract order details
            symbol = order_event.get_symbol()
            direction = order_event.get_direction()
            quantity = order_event.get_quantity()
            price = order_event.get_price()

            # CRITICAL: Extract order ID directly
            order_id = None
            if hasattr(order_event, 'data') and isinstance(order_event.data, dict):
                order_id = order_event.data.get('order_id')

            # Log the extracted order ID for verification
            if order_id:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Broker extracted order_id: {order_id}")

            # Apply slippage to price
            if direction == 'BUY':
                fill_price = price * (1.0 + self.slippage)
            else:  # SELL
                fill_price = price * (1.0 - self.slippage)

            # Calculate commission
            commission = abs(quantity * fill_price) * self.commission

            # CRITICAL: Create fill event with explicit order_id
            from src.core.events.event_utils import create_fill_event

            # Create fill and EXPLICITLY pass the order_id
            fill_event = create_fill_event(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                price=fill_price,
                commission=commission,
                timestamp=order_event.get_timestamp(),
                order_id=order_id  # Important: Pass the exact same order_id
            )

            # Double-check the order_id was transferred
            if order_id and (not hasattr(fill_event, 'data') or 'order_id' not in fill_event.data):
                # Force it if create_fill_event failed to handle it
                if not hasattr(fill_event, 'data'):
                    fill_event.data = {}
                fill_event.data['order_id'] = order_id

                import logging
                logging.getLogger(__name__).debug(f"Manually forced order_id on fill: {order_id}")

            self.stats['fills_generated'] += 1
            logger.info(f"Broker processed order: {direction} {quantity} {symbol} @ {fill_price:.2f}")
            logger.info(f"Broker emitting fill event for {symbol}")

            return fill_event

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error processing order: {e}", exc_info=True)
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
    
    def reset(self):
        """Reset broker state."""
        # Call parent reset
        super().reset()
        # Clear processed order IDs
        self.processed_order_ids.clear()
        logger.debug(f"Reset broker {self.name}")
