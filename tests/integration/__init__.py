# This file makes the integration tests directory a Python package

# Import integration adapters
try:
    import tests.integration.integration_adapters
except ImportError:
    # Adapters might not be available during initial testing
    pass
