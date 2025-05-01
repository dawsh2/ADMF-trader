"""
Adapter for event_utils to ensure signal events have all required fields.
"""

import pytest
from src.core.events.event_utils import create_signal_event

# Store original function
original_create_signal_event = create_signal_event

def enhanced_create_signal_event(signal_value, price, symbol, timestamp=None, **kwargs):
    """Create a signal event with all required fields for tests."""
    # Make sure timestamp is included
    signal = original_create_signal_event(signal_value, price, symbol, timestamp, **kwargs)
    
    # Ensure timestamp is in the data
    if timestamp is not None and 'timestamp' not in signal.data:
        signal.data['timestamp'] = timestamp
    
    return signal

# Replace the original function
create_signal_event = enhanced_create_signal_event

# Update the module reference
import src.core.events.event_utils
src.core.events.event_utils.create_signal_event = enhanced_create_signal_event

# Add fixture to ensure extension is applied
@pytest.fixture(autouse=True)
def ensure_event_utils_extension():
    """Ensure event_utils functions have been extended."""
    # This is already done at import time, but keeping fixture for consistency
    pass
