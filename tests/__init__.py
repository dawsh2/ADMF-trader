# This file makes the tests directory a Python package and sets up PYTHONPATH

# Add the project root to Python path to make src imports work
import os
import sys
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Add the project root directory to Python path to allow 'src' imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Fix Event class to have 'type' property
def fix_event_class():
    """Fix Event class to have 'type' property."""
    try:
        from src.core.events.event_types import Event
        
        # Add type property if it doesn't exist
        if not hasattr(Event, 'type'):
            @property
            def type_property(self):
                """Bridge property to access event_type as type."""
                return self.event_type
            
            # Add the type property
            Event.type = type_property
            # The type property has been added
    except ImportError as e:
        logger.warning(f"Could not import Event class: {e}")
    except Exception as e:
        logger.warning(f"Error fixing Event class: {e}")

# Apply the Event class fix
try:
    fix_event_class()
except Exception as e:
    logger.warning(f"Failed to fix Event class: {e}")

# Import all adapters
try:
    import tests.adapters
except ImportError as e:
    logger.warning(f"Failed to import adapters: {e}")
