"""
Event adapter to ensure compatibility between different Event interfaces.

This adapter ensures that components can work with any Event implementation
regardless of the specific interface.
"""

import logging

logger = logging.getLogger(__name__)

def patch_event_methods():
    """
    Patch Event class with compatibility methods.
    
    This function adds get_data(), get_symbol(), get_close(), and get_timestamp()
    methods to the Event class if they don't already exist.
    """
    from src.core.events.event_types import Event
    
    # Add get_data method if it doesn't exist
    if not hasattr(Event, 'get_data') or not callable(getattr(Event, 'get_data')):
        def get_data(self):
            """Get event data for compatibility."""
            return self.data
        Event.get_data = get_data
        logger.info("Added get_data method to Event class")
        
    # Add get_symbol method if it doesn't exist
    if not hasattr(Event, 'get_symbol') or not callable(getattr(Event, 'get_symbol')):
        def get_symbol(self):
            """Get symbol from event data for compatibility."""
            if hasattr(self, 'data') and isinstance(self.data, dict):
                return self.data.get('symbol')
            return None
        Event.get_symbol = get_symbol
        logger.info("Added get_symbol method to Event class")
        
    # Add get_close method if it doesn't exist
    if not hasattr(Event, 'get_close') or not callable(getattr(Event, 'get_close')):
        def get_close(self):
            """Get close price from event data for compatibility."""
            if hasattr(self, 'data') and isinstance(self.data, dict):
                return self.data.get('close')
            return None
        Event.get_close = get_close
        logger.info("Added get_close method to Event class")
        
    # Add get_timestamp method if it doesn't exist
    if not hasattr(Event, 'get_timestamp') or not callable(getattr(Event, 'get_timestamp')):
        def get_timestamp(self):
            """Get timestamp from event data for compatibility."""
            # First try to get from event data
            if hasattr(self, 'data') and isinstance(self.data, dict) and 'timestamp' in self.data:
                return self.data.get('timestamp')
            # Then try to get from event itself
            if hasattr(self, 'timestamp'):
                return self.timestamp
            return None
        Event.get_timestamp = get_timestamp
        logger.info("Added get_timestamp method to Event class")
