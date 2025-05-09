"""
Compatibility module for event_bus imports.
This is a compatibility shim for code that imports from src.core.event_bus.
"""

import logging
logger = logging.getLogger(__name__)
logger.warning("Importing from src.core.event_bus is deprecated. Use src.core.events.event_bus instead.")

# Re-export from the correct module
from src.core.events.event_bus import *
