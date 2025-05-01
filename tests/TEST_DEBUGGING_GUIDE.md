# ADMF-Trader Testing Debugging Guide

This guide provides a step-by-step approach to diagnose and fix testing issues with the ADMF-Trader system, especially issues related to tests hanging, timing out, or failing due to event system problems.

## Quick Start

If tests are hanging or timing out, start with the most minimal test possible and gradually add complexity:

```bash
# Run ultra minimal tests with no dependencies between components
python run_ultra_minimal_test.py

# Run minimal integration tests with basic component interactions
python run_minimal_test.py

# Run fixed integration tests with safety measures
python run_fixed_integration_test.py

# Run all tests with timeout protection
python run_tests_with_timeout.py --timeout 60
```

## Step 1: Verify Basic Component Initialization

First, ensure that all components can be initialized independently without hanging:

```python
# Test basic component creation
event_bus = EventBus()
portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
risk_manager = SimpleRiskManager(event_bus, portfolio)
broker = SimulatedBroker(event_bus)
order_manager = OrderManager(event_bus, broker)
strategy = MACrossoverStrategy(event_bus, None, parameters={...})
```

## Step 2: Check for Event Registration Issues

Look for issues in event registration and event handler calling:

1. **Check for duplicate registrations**: Make sure event handlers aren't being registered multiple times.
2. **Verify handler calling conventions**: Ensure handlers are called with the correct arguments.
3. **Look for circular registrations**: Check for handlers that register more handlers during initialization.

## Step 3: Diagnose Event Processing Issues

Common issues in event processing:

1. **Infinite Recursion**: Events that trigger handlers that emit the same events, causing an infinite loop.
2. **Deadlocks**: Handlers waiting for other handlers to complete, creating a circular dependency.
3. **Resource Exhaustion**: Handlers consuming too many resources (memory, CPU) causing the system to hang.

Add debug prints to identify where processing is getting stuck:

```python
def debug_emit(self, event):
    print(f"Emitting event: {event.type}")
    # Call original emit
    result = original_emit(self, event)
    print(f"Finished emitting event: {event.type}")
    return result
```

## Step 4: Fix Event System Issues

Implement these fixes to resolve common issues:

1. **Add recursion detection**: Track events being processed to avoid re-processing the same event.

```python
# Track currently processing events
self._processing_events = set()

# In emit method
event_id = event.get_id()
if event_id in self._processing_events:
    return []  # Skip if already processing

self._processing_events.add(event_id)
try:
    # Process event...
finally:
    self._processing_events.remove(event_id)
```

2. **Add processing limits**: Set a maximum number of events that can be processed to avoid infinite loops.

```python
# Global counter
self._event_counter = 0
self._max_events = 1000

# In emit method
self._event_counter += 1
if self._event_counter > self._max_events:
    raise Exception("Too many events processed - possible infinite loop")
```

3. **Fix weak reference issues**: Handle weak references properly to prevent errors.

```python
# Handle weak reference method calls
if isinstance(handler, weakref.WeakMethod):
    method_obj = handler()
    if method_obj is not None:
        result = method_obj(event)
else:
    result = handler(event)
```

## Step 5: Isolate Tests to Prevent Cross-Test Interference

Ensure each test operates independently:

1. **Reset state between tests**: Use fixtures to clean up state after each test.
2. **Avoid shared resources**: Create new instances of components for each test.
3. **Use timeouts**: Add timeouts to prevent tests from hanging indefinitely.

## Step 6: Gradually Expand Test Coverage

Once basic tests are working:

1. Start with unit tests for individual components
2. Add simple integration tests with minimal component interaction
3. Add more complex integration tests with full event chains
4. Finally, add system tests covering end-to-end workflows

## Tips for Writing Event-Based Tests

1. **Start with direct method calls**: Test components directly before testing event interactions.
2. **Test one event type at a time**: Don't test multiple event types in the same test initially.
3. **Add debugging helpers**: Use event trackers and counters to monitor test execution.
4. **Keep tests simple**: Each test should verify one specific behavior.
5. **Use timeout protection**: Always set timeouts to prevent tests from hanging.

## Common Symptoms and Solutions

| Symptom | Possible Cause | Solution |
|---------|---------------|----------|
| Test hangs indefinitely | Infinite event loop | Add recursion detection |
| Test times out | Deadlock between handlers | Fix handler registration order |
| Unexpected exceptions | Weak reference issues | Improve error handling for weak refs |
| Inconsistent test results | State leaking between tests | Reset state between tests |
| Too many events | Cascading event triggers | Limit event counts and add debugging |

## Using the Debug Tools

The repository includes several debug tools to help diagnose issues:

1. **Debug Integration Script**: Tests specific components in isolation
   ```bash
   python tests/integration/debug_integration.py
   ```

2. **Test Debugging Tools**: Provides detailed information about components
   ```bash
   python tests/debug_tools.py --event-bus
   python tests/debug_tools.py --strategy
   python tests/debug_tools.py --class src.core.events.event_bus EventBus
   ```

3. **Single Test Runner**: Run and debug one test at a time
   ```bash
   python run_single_test.py tests/unit/core/test_event_bus.py --debug
   ```
