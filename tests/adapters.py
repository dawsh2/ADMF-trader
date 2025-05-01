"""
Central adapter module that imports all adapters needed for tests.
"""

# Import all adapter modules
try:
    # Core module adapters
    from tests.unit.core.test_event_types_adapter import extend_event, ensure_event_extension
    from tests.unit.core.test_event_bus_adapter import extend_event_bus, ensure_event_bus_extension
    from tests.unit.core.test_event_utils_adapter import ensure_event_utils_extension
    
    # Execution module adapters
    from tests.unit.execution.broker_adapter import extend_simulated_broker, ensure_broker_extension
    
    # Strategy module adapters
    from tests.unit.strategy.strategy_adapter import extend_strategy_classes, ensure_strategy_extension
    
    # Integration adapters
    from tests.integration.integration_adapters import extend_simulated_broker_integration
    
    # Apply all adapters at import time
    def apply_all_adapters():
        """Apply all adapters for testing."""
        extend_event()
        extend_event_bus()
        extend_simulated_broker()
        extend_strategy_classes()
        extend_simulated_broker_integration()
        print("All adapters applied successfully.")
    
    # Call the function at import time
    apply_all_adapters()

except ImportError as e:
    print(f"Warning: Failed to import some adapters: {e}")
    
except Exception as e:
    print(f"Warning: Error applying adapters: {e}")
