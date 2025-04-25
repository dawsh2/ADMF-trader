from core.events.event_types import EventType
from core.events.event_handlers import EventHandler

class StrategyHandler(EventHandler):
    """Handles events for strategy components."""
    
    def __init__(self, strategy, event_types=None):
        self._strategy = strategy
        self._name = f"{strategy.name}_handler"
        self._event_types = event_types or [EventType.BAR]
    
    def handle(self, event):
        """Route events to appropriate strategy methods."""
        event_type = event.get_type()
        
        # Check if strategy has a specific handler method
        if event_type == EventType.BAR and hasattr(self._strategy, 'on_bar'):
            return self._strategy.on_bar(event)
        elif event_type == EventType.SIGNAL and hasattr(self._strategy, 'on_signal'):
            return self._strategy.on_signal(event)
        elif event_type == EventType.TICK and hasattr(self._strategy, 'on_tick'):
            return self._strategy.on_tick(event)
        
        # Fall back to generic handle method if available
        if hasattr(self._strategy, 'handle'):
            return self._strategy.handle(event)
            
        return False  # Event not handled
