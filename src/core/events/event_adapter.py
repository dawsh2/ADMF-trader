"""
DEPRECATED: Event adapter for backward compatibility.

This module is deprecated. All code should import directly from 
src.core.event_system.event instead.
"""

import logging
import warnings

# Issue a deprecation warning
warnings.warn(
    "The event_adapter module is deprecated. "
    "Please import directly from src.core.event_system.event instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import and re-export the standard Event class
from src.core.event_system.event import Event, create_event
from src.core.event_system.event_types import EventType

logger = logging.getLogger(__name__)

def patch_event_methods():
    """
    Add any missing methods to the Event class.
    
    This function is maintained for backward compatibility, but should no
    longer be needed as the unified Event class contains all required methods.
    """
    # Add get_close method if it doesn't exist
    if not hasattr(Event, 'get_close') or not callable(getattr(Event, 'get_close')):
        def get_close(self):
            """Get close price from event data for compatibility."""
            if hasattr(self, 'data') and isinstance(self.data, dict):
                return self.data.get('close')
            return None
        Event.get_close = get_close
        logger.info("Added get_close method to Event class")

# For backward compatibility
patch_event_methods()
