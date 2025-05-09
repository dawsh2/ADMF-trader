#!/usr/bin/env python
"""
Patch the strategy adapter to add more debugging
"""

import logging
from src.strategy.strategy_adapters import StrategyAdapter

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("strategy_adapter_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('adapter_patch')

# Save the original initialize method
original_initialize = StrategyAdapter.initialize

# Create a patched version with more logging
def patched_initialize(self, context):
    logger.info(f"Patched strategy adapter initializing: {self.name}")
    
    # Call the original method
    original_initialize(self, context)
    
    # Add debugging for signal events
    if hasattr(self.strategy, 'event_bus') and self.strategy.event_bus:
        logger.info(f"Strategy has event_bus: {self.strategy.event_bus}")
        
        # Add a signal listener to the event bus
        from src.core.events.event_types import EventType
        
        def signal_listener(event):
            logger.info(f"SIGNAL from {self.strategy.__class__.__name__}: {event}")
        
        if hasattr(self.strategy.event_bus, 'subscribe'):
            self.strategy.event_bus.subscribe(EventType.SIGNAL, signal_listener)
            logger.info("Added signal listener to event bus")
    else:
        logger.warning(f"Strategy does NOT have event_bus!")
    
    # Check for required strategy attributes
    required_attrs = ['event_bus', 'data_handler', 'symbols']
    for attr in required_attrs:
        if hasattr(self.strategy, attr):
            val = getattr(self.strategy, attr)
            logger.info(f"Strategy has {attr}: {val}")
        else:
            logger.warning(f"Strategy missing {attr}")
    
    logger.info(f"Patched initialization complete for {self.name}")

# Apply the patch
logger.info("Applying patch to StrategyAdapter.initialize")
StrategyAdapter.initialize = patched_initialize
logger.info("Patch applied")

print("StrategyAdapter patched with additional debugging")
