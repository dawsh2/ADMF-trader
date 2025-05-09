"""
Event logger for debugging purposes.
"""

import logging
from src.core.events.event_types import EventType

logger = logging.getLogger(__name__)

class EventLogger:
    """
    Event logger for debugging event flow.
    """
    
    def __init__(self, event_bus, name="event_logger"):
        """
        Initialize the event logger.
        
        Args:
            event_bus: Event bus to monitor
            name (str): Logger name
        """
        self.event_bus = event_bus
        self.name = name
        self.signal_count = 0
        self.order_count = 0
        self.trade_count = 0
        self.bar_count = 0
        
        # Subscribe to events
        self._subscribe_to_events()
        
        logger.info(f"Event logger {name} initialized")
    
    def _subscribe_to_events(self):
        """Subscribe to all event types"""
        if self.event_bus:
            if hasattr(self.event_bus, 'subscribe'):
                # Subscribe to all event types
                self.event_bus.subscribe(EventType.SIGNAL, self._on_signal)
                self.event_bus.subscribe(EventType.ORDER, self._on_order)
                self.event_bus.subscribe(EventType.TRADE, self._on_trade)
                self.event_bus.subscribe(EventType.BAR, self._on_bar)
                
                logger.info(f"Event logger {self.name} subscribed to events")
            else:
                logger.warning(f"Event bus does not have subscribe method")
        else:
            logger.warning(f"No event bus provided to event logger")
    
    def _on_signal(self, event):
        """Log signal events"""
        self.signal_count += 1
        data = event.get_data()
        symbol = data.get('symbol')
        signal_value = data.get('signal_value')
        price = data.get('price')
        
        logger.info(f"SIGNAL #{self.signal_count}: symbol={symbol}, value={signal_value}, price={price}")
    
    def _on_order(self, event):
        """Log order events"""
        self.order_count += 1
        data = event.get_data()
        symbol = data.get('symbol')
        direction = data.get('direction')
        quantity = data.get('quantity')
        order_type = data.get('type')
        price = data.get('price')
        
        logger.info(f"ORDER #{self.order_count}: symbol={symbol}, direction={direction}, quantity={quantity}, type={order_type}, price={price}")
    
    def _on_trade(self, event):
        """Log trade events"""
        self.trade_count += 1
        data = event.get_data()
        symbol = data.get('symbol')
        direction = data.get('direction')
        quantity = data.get('quantity')
        price = data.get('price')
        
        logger.info(f"TRADE #{self.trade_count}: symbol={symbol}, direction={direction}, quantity={quantity}, price={price}")
    
    def _on_bar(self, event):
        """Log bar events"""
        self.bar_count += 1
        if self.bar_count % 100 == 0:  # Only log every 100th bar to avoid excessive logging
            data = event.get_data()
            symbol = data.get('symbol')
            timestamp = data.get('timestamp')
            close = data.get('close')
            
            logger.info(f"BAR #{self.bar_count}: symbol={symbol}, timestamp={timestamp}, close={close}")
    
    def print_summary(self):
        """Print a summary of event counts"""
        logger.info(f"EVENT SUMMARY for {self.name}:")
        logger.info(f"  Signals: {self.signal_count}")
        logger.info(f"  Orders: {self.order_count}")
        logger.info(f"  Trades: {self.trade_count}")
        logger.info(f"  Bars: {self.bar_count}")
        
        # Check for issues
        if self.signal_count > 0 and self.order_count == 0:
            logger.warning("ISSUE: Signals were generated but no orders - check risk manager")
        if self.order_count > 0 and self.trade_count == 0:
            logger.warning("ISSUE: Orders were generated but no trades - check broker")
        if self.bar_count == 0:
            logger.warning("ISSUE: No bars were processed - check data handler")


def attach_to_backtest(backtest_instance):
    """
    Attach event logger to a backtest instance.
    
    Args:
        backtest_instance: Backtest coordinator instance
    
    Returns:
        EventLogger: The attached event logger
    """
    # Get the event bus from the backtest
    event_bus = None
    if hasattr(backtest_instance, 'event_bus'):
        event_bus = backtest_instance.event_bus
    elif hasattr(backtest_instance, 'components') and isinstance(backtest_instance.components, dict):
        event_bus = backtest_instance.components.get('event_bus')
    
    if event_bus:
        # Create and return event logger
        return EventLogger(event_bus, f"backtest_logger_{id(backtest_instance)}")
    else:
        logger.warning(f"Could not find event bus in backtest instance")
        return None
