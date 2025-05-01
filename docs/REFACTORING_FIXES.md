# Refactoring Architecture Fixes

This document outlines the additional fixes implemented to address issues found during testing of the refactored architecture.

## Issues Found

When testing the refactored architecture, we discovered several issues:

1. **Missing Order IDs**: The enhanced risk manager was creating orders without an order_id field, causing processing failures in the order manager and broker.

2. **Duplicate Signal Processing**: The same signal was being processed multiple times, causing duplicate rule IDs and orders.

3. **Event Consumption Tracking**: The event system needed improvements to properly track consumed events.

## Fixes Implemented

### 1. Added Order ID Generation

Updated the `_create_order_from_signal` method in `EnhancedRiskManager` to:
- Generate a unique order ID for each order using UUID
- Include this order ID in the order data
- Log the order ID in the creation message

```python
# Generate a unique order ID
import uuid
order_id = f"order_{uuid.uuid4().hex[:8]}"

# Include in order data
order_data = {
    # ... other fields ...
    'order_id': order_id
}
```

### 2. Improved Event Consumption Tracking

Enhanced the `Event` class to properly track consumption:
- Added a `consumed` flag to all events
- Added `mark_consumed()` and `is_consumed()` methods
- Updated the enhanced risk manager to use these methods

```python
# In Event class
def mark_consumed(self):
    """Mark this event as consumed to prevent duplicate processing."""
    self.consumed = True
    
def is_consumed(self):
    """Check if this event has been consumed."""
    return self.consumed
```

### 3. Fixed Event Bus Registration

Updated the component registration in the system bootstrap to:
- Better handle the enhanced risk manager case
- Unregister and re-register handlers with proper priority
- Skip previously consumed events

### 4. Improved Event Deduplication

Enhanced the event bus to:
- Check event consumption state using the new methods
- Skip already consumed events
- Properly track consumption state in the event registry

## How to Verify the Fixes

When running the system after these fixes, you should see:

1. **Clean Order Processing**: No more errors about missing order IDs
2. **Single Signal Processing**: Each signal is only processed once
3. **Proper Event Flow**: Events flow properly through the system components

Example of fixed log output:
```
2025-05-01 12:00:00 - simple_ma_crossover - INFO - BUY signal for MINI: fast MA crossed above slow MA
2025-05-01 12:00:00 - enhanced_risk_manager - INFO - Received signal: MINI direction=1 at 521.25
2025-05-01 12:00:00 - enhanced_risk_manager - INFO - Direction change for MINI: 0 -> 1, rule_id=MINI_BUY_group_1
2025-05-01 12:00:00 - enhanced_risk_manager - INFO - Creating order: BUY 100 MINI @ 521.25, rule_id=MINI_BUY_group_1, order_id=order_a1b2c3d4
2025-05-01 12:00:00 - src.execution.order_manager - INFO - Processing order order_a1b2c3d4: BUY 100 MINI @ 521.25
```

## Additional Notes

These fixes ensure that the refactored architecture works correctly with the existing event system. The enhanced event consumption tracking also provides a foundation for more robust event processing in the future.