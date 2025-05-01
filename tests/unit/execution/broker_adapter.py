"""
Adapter for SimulatedBroker to match test expectations with current implementation.
"""

import pytest
from src.execution.broker.broker_simulator import SimulatedBroker


# Extend SimulatedBroker class with required test methods
def extend_simulated_broker():
    """Extend the SimulatedBroker class with methods expected by tests."""
    
    # Add set_slippage method if not exists
    if not hasattr(SimulatedBroker, 'set_slippage'):
        def set_slippage(self, slippage):
            """Set slippage for the broker."""
            self.slippage = slippage
        
        SimulatedBroker.set_slippage = set_slippage
    
    # Add set_commission method if not exists
    if not hasattr(SimulatedBroker, 'set_commission'):
        def set_commission(self, commission):
            """Set commission for the broker."""
            self.commission = commission
        
        SimulatedBroker.set_commission = set_commission


# Call this function at import time
extend_simulated_broker()


# Add fixture to ensure broker extension is applied
@pytest.fixture(autouse=True)
def ensure_broker_extension():
    """Ensure SimulatedBroker class has been extended."""
    extend_simulated_broker()
