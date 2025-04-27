# test_event_system.py
import logging
from src.core.events.event_types import EventType, Event
from src.core.events.event_bus import EventBus

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def event_handler(event):
    logger.info(f"Received event: {event.get_type()}")
    return True

def test_event_bus():
    # Create event bus
    event_bus = EventBus()
    
    # Register handler
    event_bus.register(EventType.BAR, event_handler)
    
    # Create and emit event
    event = Event(EventType.BAR, {'symbol': 'AAPL', 'price': 150.0})
    handlers_called = event_bus.emit(event)
    
    logger.info(f"Event emitted, {handlers_called} handlers called")
    
    # Check event counts
    stats = event_bus.get_stats()
    logger.info(f"Event bus stats: {stats}")
    
    return handlers_called > 0

if __name__ == "__main__":
    result = test_event_bus()
    logger.info(f"Test {'passed' if result else 'failed'}")
