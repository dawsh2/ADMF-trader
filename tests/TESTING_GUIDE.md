# ADMF-Trader Testing Guide

This guide explains how to run tests safely without hanging issues.

## Quick Setup

```python
# Install all required dependencies and prepare the environment
python setup_test_env.py
```

## Running Tests

```python
# Run the debug integration test
python run_tests.py --debug-integration

# Run all tests with safety measures
python run_tests.py

# Run specific tests
python run_tests.py tests/unit/core/test_event_bus.py

# Run with increased verbosity and coverage
python run_tests.py -v --with-coverage
```

## Understanding Test Hanging Issues

Test hanging in ADMF-Trader is typically caused by:

1. **Infinite Event Loops**: Events trigger handlers that emit more events recursively
2. **Missing Method Implementation**: Strategy components expect certain methods on Event objects
3. **Weak Reference Issues**: Handlers being garbage collected during test execution

## Core Solutions

The following solutions have been implemented:

### 1. Enhanced EventBus Adapter

The `EventBusAdapter` in `tests/adapters.py` enhances the EventBus with:

- Recursion detection to prevent infinite loops
- Event count limiting to prevent resource exhaustion
- Cycle detection to avoid processing the same event repeatedly
- Better weak reference handling

Apply this adapter in your tests:

```python
from tests.adapters import EventBusAdapter

# Create and enhance the event bus
event_bus = EventBus()
EventBusAdapter.apply(event_bus)
```

### 2. Timeout Protection

The `EventTimeoutWrapper` provides timeout protection for any function:

```python
from tests.adapters import EventTimeoutWrapper

try:
    result = EventTimeoutWrapper.run_with_timeout(potentially_hanging_function, timeout=5)
except TimeoutError:
    print("Function timed out")
```

### 3. Event Monitoring

The `EventMonitor` class helps track and debug event flow during tests:

```python
from tests.utils.event_monitor import EventMonitor

# Create monitor
with EventMonitor(event_bus) as monitor:
    # Run test code
    
    # Check results
    print(f"Total events: {monitor.get_event_count()}")
    monitor.print_summary()
```

## Debug Integration Test

For complex issues, the debug integration test helps identify issues step by step:

```python
python tests/integration/fixed_debug_integration.py
```

This test:
1. Creates each component with timeout protection
2. Tracks all events flowing through the system
3. Executes minimal functionality to verify basic integration
4. Handles errors gracefully without hanging

## Adding Safety to Your Tests

To make your existing tests more robust:

1. Add the EventBusAdapter to your event bus instances
2. Wrap potentially hanging functions with EventTimeoutWrapper
3. Use an EventMonitor to track events during complex tests
4. Add proper error handling to prevent test failures due to missing methods

Example test fixture with safety enhancements:

```python
@pytest.fixture
def safe_event_bus():
    """Create a safe event bus for testing."""
    from src.core.events.event_bus import EventBus
    from tests.adapters import EventBusAdapter
    
    # Create and enhance the event bus
    event_bus = EventBus()
    EventBusAdapter.apply(event_bus)
    
    yield event_bus
    
    # Clean up
    event_bus.reset()
```

## Common Issues and Solutions

1. **'Event' object has no attribute 'get_symbol'**
   - Use BarEvent instead of Event for bar events
   - Add missing methods to your test Event objects

2. **'PortfolioManager' object has no attribute 'get_positions'**
   - Access portfolio.positions directly
   - Use portfolio.get_position(symbol) to get specific positions

3. **Tests hanging indefinitely**
   - Apply EventBusAdapter to the event bus
   - Add timeout protection to potentially hanging functions
   - Monitor event flow to identify infinite loops
