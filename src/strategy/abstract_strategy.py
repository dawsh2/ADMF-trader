from abc import ABC, abstractmethod
from src.core.events.event_types import EventType
import logging

logger = logging.getLogger(__name__)

class AbstractStrategy(ABC):
    """
    Abstract base class for all trading strategies
    
    Strategies receive market data events and generate signal events
    """
    
    def __init__(self, event_bus, data_handler, name="AbstractStrategy"):
        """
        Initialize the strategy
        
        Args:
            event_bus: Event bus for publishing events
            data_handler: Data handler for accessing market data
            name: Strategy name
        """
        self.event_bus = event_bus
        self.data_handler = data_handler
        self.name = name
        
        # Subscribe to market data events
        if self.event_bus:
            self.event_bus.subscribe(EventType.BAR, self.on_bar)
            self.event_bus.subscribe(EventType.TICK, self.on_tick)
            logger.info(f"Strategy {self.name} subscribed to market data events")
    
    @abstractmethod
    def on_bar(self, event):
        """
        Process bar data and generate signals
        
        Args:
            event: Bar event containing market data
        """
        pass
    
    @abstractmethod
    def on_tick(self, event):
        """
        Process tick data and generate signals
        
        Args:
            event: Tick event containing market data
        """
        pass